from __future__ import annotations

import logging
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.api.deps import get_engine
from backend.config import OUTPUT_PREFIX
from backend.db.bankcash_repository import (
    backfill_bankcash_account_defaults,
    delete_temp_rows,
    fetch_bankcash_ledger,
    fetch_temp_transactions_by_job,
    process_temp_rows,
)
from backend.db.connection import DatabaseError, ping_database
from backend.db.mutualfund_repository import (
    delete_mf_temp_rows,
    ensure_mutualfundtemp_columns,
    fetch_mf_temp_by_job,
    fetch_mutualfund_ledger,
    fetch_recent_mf_temp,
    process_mf_temp_rows,
)
from backend.db.settings import get_staging_defaults
from backend.db.vehicle_staging import (
    delete_vehicle_temp_rows,
    ensure_vehicle_staging_tables,
    fetch_vehicle_ledger,
    fetch_vehicle_temp,
    process_vehicle_temp_rows,
)
from backend.exceptions import ProcessingError, UnsupportedDocumentError
from backend.jessy.db import ensure_jessy_tables
from backend.jessy.router import router as jessy_router
from backend.jessy.utils.qdrant_client import initialize_qdrant
from backend.logging_setup import setup_logging
from backend.vehicle.pipeline import process_vehicle_attachment


class TempRowIdsBody(BaseModel):
    ids: list[int | str] = Field(default_factory=list)


class VehicleTempRowIdsBody(BaseModel):
    job_id: str
    ids: list[int | str] = Field(default_factory=list)


logger = logging.getLogger("holding_engine")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Asset Vantage API",
        version="1.0.0",
        description="Bank statement processing + Jessy RAG chatbot.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Jessy routes: /chat, /chat/attachments, /search, /documents/upload
    # (Vite strips /api prefix, so frontend calls /api/chat → /chat here)
    app.include_router(jessy_router)

    @app.on_event("startup")
    def _startup_jessy() -> None:
        """Best-effort Jessy init — OCR still works if Qdrant/MySQL chat tables fail."""
        try:
            initialize_qdrant()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jessy Qdrant startup skipped: %s", exc)
        try:
            ensure_jessy_tables()
        except Exception as exc:  # noqa: BLE001
            logger.warning("Jessy chat tables startup skipped: %s", exc)
        try:
            ensure_mutualfundtemp_columns()
            ensure_vehicle_staging_tables()
            filled = backfill_bankcash_account_defaults()
            if filled:
                logger.info("Backfilled entity/account on %s bankcash row(s)", filled)
        except Exception as exc:  # noqa: BLE001
            logger.warning("vehicle staging ensure skipped: %s", exc)

    @app.get("/health")
    def health() -> dict:
        payload: dict = {"status": "ok"}
        try:
            payload["database"] = ping_database()
        except Exception as exc:  # noqa: BLE001
            payload["database"] = {"ok": False, "error": str(exc)}
        return payload

    @app.post("/upload")
    async def upload(
        background_tasks: BackgroundTasks,
        file: Annotated[UploadFile, File(description="Bank statement PDF")],
        user_id: Annotated[str | None, Form()] = None,
    ) -> dict:
        engine = get_engine()
        original_name = file.filename or "upload.pdf"
        content = await file.read()

        if not content:
            raise HTTPException(status_code=400, detail="Empty file upload")

        try:
            history = engine.register_upload(
                source_bytes=content,
                original_file_name=original_name,
                user_id=user_id,
                initial_status="PROCESSING",
            )
        except UnsupportedDocumentError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc
        except ProcessingError as exc:
            raise HTTPException(status_code=400, detail=exc.message) from exc

        job_id = history.job_id
        background_tasks.add_task(_run_job, job_id)
        logger.info("API upload accepted | job_id=%s status=PROCESSING", job_id)

        return {
            "job_id": job_id,
            "status": "PROCESSING",
        }

    @app.get("/job/{job_id}")
    def get_job(job_id: str) -> dict:
        engine = get_engine()
        payload = engine.get_job(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        return payload

    @app.get("/job/{job_id}/transactions")
    def get_job_transactions(job_id: str) -> dict:
        """Review list: staged bankcashtemp rows for this upload job."""
        engine = get_engine()
        payload = engine.get_job(job_id)
        if payload is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        defaults = get_staging_defaults()
        try:
            transactions = fetch_temp_transactions_by_job(job_id)
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

        error_count = sum(1 for t in transactions if t.get("iserror"))
        return {
            "job_id": job_id,
            "status": payload.get("status"),
            "original_file_name": payload.get("original_file_name"),
            "entity_id": defaults.entity_id,
            "entity_name": defaults.entity_name,
            "user_id": defaults.user_id,
            "total": len(transactions),
            "valid": len(transactions) - error_count,
            "errors": error_count,
            "transactions": transactions,
        }

    @app.post("/job/{job_id}/transactions/delete")
    def delete_job_transactions(job_id: str, body: TempRowIdsBody) -> dict:
        """Delete selected rows from bankcashtemp for this job."""
        engine = get_engine()
        if engine.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        try:
            return delete_temp_rows(job_id=job_id, ids=body.ids)
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

    @app.post("/job/{job_id}/transactions/process")
    def process_job_transactions(job_id: str, body: TempRowIdsBody) -> dict:
        """
        Post selected clean rows to bankcash; skip iserror=1 rows.
        Processed rows are removed from bankcashtemp.
        """
        engine = get_engine()
        if engine.get_job(job_id) is None:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")
        try:
            return process_temp_rows(job_id=job_id, ids=body.ids)
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

    @app.get("/job/{job_id}/download/csv")
    def download_csv(job_id: str) -> Response:
        return _download_artifact(job_id, kind="csv")

    @app.get("/job/{job_id}/download/json")
    def download_json(job_id: str) -> Response:
        return _download_artifact(job_id, kind="json")

    @app.post("/vehicle/upload")
    async def upload_vehicle(
        background_tasks: BackgroundTasks,
        file: Annotated[UploadFile, File(description="Vehicle Excel or bank PDF")],
        vehicle: Annotated[str | None, Form()] = "mutual-fund",
    ) -> dict:
        """Upload MF / FI / DE Excel (or bank PDF) and stage temp transactions."""
        original_name = file.filename or "upload.xls"
        content = await file.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file upload")

        outcome = process_vehicle_attachment(
            content=content,
            filename=original_name,
            expect_vehicle=vehicle,
        )
        if outcome.get("needs_background_process") and outcome.get("job_id"):
            background_tasks.add_task(_run_job, str(outcome["job_id"]))
        if vehicle and outcome.get("vehicle_type") and outcome["vehicle_type"] != vehicle:
            outcome["warning"] = (
                f"Selected tab is {vehicle}, but file looks like "
                f"{outcome['vehicle_type']}."
            )
        if outcome.get("status") == "failed":
            raise HTTPException(
                status_code=400, detail=outcome.get("message") or "Import failed"
            )
        return outcome

    @app.get("/vehicle/{vehicle}/staging")
    def list_vehicle_staging(
        vehicle: str,
        job_id: str | None = None,
        limit: int = 200,
    ) -> dict:
        """List staged temp rows for mutual-fund / fixed-income / direct-equity."""
        defaults = get_staging_defaults()
        try:
            if vehicle == "mutual-fund":
                rows = (
                    fetch_mf_temp_by_job(job_id)
                    if job_id
                    else fetch_recent_mf_temp(limit=max(1, min(limit, 500)))
                )
                transactions = _map_mf_staging_rows(rows, defaults)
            elif vehicle in {"fixed-income", "direct-equity"}:
                rows = fetch_vehicle_temp(
                    vehicle,
                    job_id=job_id,
                    limit=max(1, min(limit, 500)),
                )
                transactions = _map_vehicle_staging_rows(rows, defaults)
            else:
                raise HTTPException(status_code=404, detail=f"Unknown vehicle: {vehicle}")
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

        return {
            "total": len(transactions),
            "vehicle": vehicle,
            "entity_id": defaults.entity_id,
            "entity_name": defaults.entity_name,
            "transactions": transactions,
        }

    @app.post("/vehicle/{vehicle}/staging/process")
    def process_vehicle_staging(vehicle: str, body: VehicleTempRowIdsBody) -> dict:
        """Post selected clean temp rows into the permanent vehicle table."""
        if not body.job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        try:
            if vehicle == "mutual-fund":
                return process_mf_temp_rows(job_id=body.job_id, ids=body.ids)
            if vehicle in {"fixed-income", "direct-equity"}:
                return process_vehicle_temp_rows(
                    vehicle=vehicle, job_id=body.job_id, ids=body.ids
                )
            raise HTTPException(status_code=404, detail=f"Unknown vehicle: {vehicle}")
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

    @app.post("/vehicle/{vehicle}/staging/delete")
    def delete_vehicle_staging(vehicle: str, body: VehicleTempRowIdsBody) -> dict:
        """Delete selected temp rows for a vehicle job."""
        if not body.job_id:
            raise HTTPException(status_code=400, detail="job_id is required")
        try:
            if vehicle == "mutual-fund":
                return delete_mf_temp_rows(job_id=body.job_id, ids=body.ids)
            if vehicle in {"fixed-income", "direct-equity"}:
                return delete_vehicle_temp_rows(
                    vehicle=vehicle, job_id=body.job_id, ids=body.ids
                )
            raise HTTPException(status_code=404, detail=f"Unknown vehicle: {vehicle}")
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

    @app.get("/bankcash/ledger")
    def bankcash_ledger(
        entity_id: int | None = None,
        account_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 1000,
    ) -> dict:
        """Permanent bankcash rows for the Ledger tab."""
        defaults = get_staging_defaults()
        try:
            transactions = fetch_bankcash_ledger(
                entity_id=entity_id if entity_id is not None else defaults.entity_id,
                account_id=account_id,
                from_date=from_date,
                to_date=to_date,
                limit=limit,
            )
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc
        return {
            "total": len(transactions),
            "entity_id": defaults.entity_id,
            "entity_name": defaults.entity_name,
            "account_id": defaults.account_id,
            "transactions": transactions,
        }

    @app.get("/vehicle/{vehicle}/ledger")
    def vehicle_ledger(
        vehicle: str,
        entity_id: int | None = None,
        account_id: int | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 1000,
    ) -> dict:
        """Permanent ledger rows for MF / FI / DE."""
        defaults = get_staging_defaults()
        eid = entity_id if entity_id is not None else defaults.entity_id
        try:
            if vehicle == "mutual-fund":
                rows = fetch_mutualfund_ledger(
                    entity_id=eid,
                    account_id=account_id,
                    from_date=from_date,
                    to_date=to_date,
                    limit=limit,
                )
                transactions = _map_mf_staging_rows(rows, defaults)
            elif vehicle in {"fixed-income", "direct-equity"}:
                rows = fetch_vehicle_ledger(
                    vehicle,
                    entity_id=eid,
                    account_id=account_id,
                    from_date=from_date,
                    to_date=to_date,
                    limit=limit,
                )
                transactions = _map_vehicle_staging_rows(rows, defaults)
            else:
                raise HTTPException(status_code=404, detail=f"Unknown vehicle: {vehicle}")
        except DatabaseError as exc:
            raise HTTPException(status_code=503, detail=exc.message) from exc

        return {
            "total": len(transactions),
            "vehicle": vehicle,
            "entity_id": defaults.entity_id,
            "entity_name": defaults.entity_name,
            "account_id": defaults.account_id,
            "transactions": transactions,
        }

    return app


def _map_mf_staging_rows(rows: list, defaults) -> list[dict]:
    transactions = []
    for row in rows:
        sync = str(row.get("syncdescription") or "")
        parts = [p.strip() for p in sync.split("|")]
        scheme = parts[0] if parts else ""
        folio = str(row.get("voucher") or (parts[1] if len(parts) > 1 else ""))
        txn_type = str(
            row.get("txnqualifier") or (parts[2] if len(parts) > 2 else "-")
        )
        trade = row.get("transactiondate")
        transactions.append(
            {
                "id": str(row.get("id")),
                "jobId": row.get("jobid"),
                "entityId": str(row.get("entityid") or defaults.entity_id),
                "entityName": defaults.entity_name,
                "folioOrIsin": folio,
                "tradeDate": trade.isoformat()
                if hasattr(trade, "isoformat")
                else str(trade or ""),
                "type": txn_type,
                "schemeOrInstrument": scheme,
                "units": float(row["units"]) if row.get("units") is not None else 0,
                "navOrPrice": float(row["navperunit"])
                if row.get("navperunit") is not None
                else 0,
                "amount": float(row["amount"]) if row.get("amount") is not None else 0,
                "iserror": bool(row.get("iserror")),
                "errordesc": row.get("errordesc"),
                "filename": row.get("filename"),
            }
        )
    return transactions


def _map_vehicle_staging_rows(rows: list, defaults) -> list[dict]:
    transactions = []
    for row in rows:
        trade = row.get("transactiondate")
        transactions.append(
            {
                "id": str(row.get("id")),
                "jobId": row.get("jobid"),
                "entityId": str(row.get("entityid") or defaults.entity_id),
                "entityName": defaults.entity_name,
                "folioOrIsin": str(row.get("isin") or ""),
                "tradeDate": trade.isoformat()
                if hasattr(trade, "isoformat")
                else str(trade or ""),
                "type": str(row.get("txnqualifier") or "-"),
                "schemeOrInstrument": str(row.get("security_name") or ""),
                "units": float(row["units"]) if row.get("units") is not None else 0,
                "navOrPrice": float(row["price"]) if row.get("price") is not None else 0,
                "amount": float(row["amount"]) if row.get("amount") is not None else 0,
                "iserror": bool(row.get("iserror")),
                "errordesc": row.get("errordesc"),
                "filename": row.get("filename"),
            }
        )
    return transactions


def _download_artifact(job_id: str, *, kind: str) -> Response:
    engine = get_engine()
    payload = engine.get_job(job_id)
    if payload is None:
        raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

    if kind == "csv":
        key = payload.get("transaction_csv_path") or payload.get("csv_path")
    else:
        key = payload.get("canonical_json_path") or payload.get("json_path")
    if not key:
        prefix = f"{OUTPUT_PREFIX}/{job_id}/"
        for candidate in engine.storage.list_keys(prefix):
            name = candidate.rsplit("/", 1)[-1]
            if kind == "csv" and name.startswith("TRANSACTION_") and name.endswith(".csv"):
                key = candidate
                break
            if kind == "json" and name == "canonical_transactions.json":
                key = candidate
                break

    if not key or not engine.storage.exists(key):
        raise HTTPException(
            status_code=404,
            detail=f"{kind.upper()} artifact not ready for job {job_id}",
        )

    data = engine.storage.read_bytes(key)
    filename = key.rsplit("/", 1)[-1]
    media = "text/csv" if kind == "csv" else "application/json"
    return Response(
        content=data,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _run_job(job_id: str) -> None:
    try:
        engine = get_engine()
        result = engine.process_job(job_id)
        logger.info(
            "Background job finished | job_id=%s status=%s",
            job_id,
            result.get("status"),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Background job crashed | job_id=%s", job_id)


app = create_app()
