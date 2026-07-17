from __future__ import annotations

import logging
from typing import Annotated

from fastapi import BackgroundTasks, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response

from poc.api.deps import get_engine
from poc.config import OUTPUT_PREFIX
from poc.exceptions import ProcessingError, UnsupportedDocumentError
from poc.logging_setup import setup_logging

logger = logging.getLogger("holding_engine")


def create_app() -> FastAPI:
    setup_logging()

    app = FastAPI(
        title="Holding Statement Processing API",
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
        return {"status": "ok"}

    @app.post("/upload")
    async def upload(
        background_tasks: BackgroundTasks,
        file: Annotated[UploadFile, File(description="Holding statement file")],
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

    key = payload.get("csv_path") if kind == "csv" else payload.get("json_path")
    if not key:
        prefix = f"{OUTPUT_PREFIX}/{job_id}/"
        for candidate in engine.storage.list_keys(prefix):
            if candidate.endswith(f".{kind}") and "holding_" in candidate:
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
