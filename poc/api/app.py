from __future__ import annotations

import logging
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel, Field

from poc.api.deps import get_engine
from poc.config import OUTPUT_PREFIX
from poc.db.bankcash_repository import (
    delete_temp_rows,
    fetch_temp_transactions_by_job,
    process_temp_rows,
)
from poc.db.connection import DatabaseError, ping_database
from poc.db.settings import get_staging_defaults
from poc.exceptions import ProcessingError, UnsupportedDocumentError
from poc.logging_setup import setup_logging


class TempRowIdsBody(BaseModel):
    ids: list[int | str] = Field(default_factory=list)

logger = logging.getLogger("holding_engine")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Bank Statement Processing API",
        version="1.0.0",
        description="Local FastAPI wrapper around the processing engine (no AWS/SQL).",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

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

    return app


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
