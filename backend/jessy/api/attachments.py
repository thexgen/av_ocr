"""Chat attachment receive + vehicle / bank-cash processing."""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, Form, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse

from backend.api.deps import get_engine
from backend.vehicle.pipeline import process_vehicle_attachment

logger = logging.getLogger("jessy.attachments")

router = APIRouter(tags=["jessy-chat-attachments"])

_ALLOWED_EXTENSIONS = {".pdf", ".xlsx", ".xls", ".png", ".jpg", ".jpeg", ".webp", ".gif"}
_MAX_FILE_BYTES = 25 * 1024 * 1024


def _extension_ok(filename: str) -> bool:
    return Path(filename).suffix.lower() in _ALLOWED_EXTENSIONS


def _run_bank_job(job_id: str) -> None:
    try:
        engine = get_engine()
        result = engine.process_job(job_id)
        logger.info(
            "Chat bank-cash job finished | job_id=%s status=%s",
            job_id,
            result.get("status"),
        )
    except Exception:  # noqa: BLE001
        logger.exception("Chat bank-cash job crashed | job_id=%s", job_id)


@router.post("/chat/attachments")
async def receive_chat_attachments(
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    message: str = Form(default=""),
    conversation_id: str | None = Form(default=None),
) -> JSONResponse:
    """Accept attachments; stage Excel vehicles or queue bank-cash PDFs."""
    if not files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="At least one file is required.",
        )

    parsed_conversation_id: int | None = None
    if conversation_id is not None and str(conversation_id).strip() != "":
        try:
            parsed_conversation_id = int(conversation_id)
        except (TypeError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="conversation_id must be an integer.",
            ) from exc

    results: list[dict] = []
    all_steps: list[dict] = []

    for upload in files:
        original_name = Path(upload.filename or "").name
        if not original_name:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Each file must have a filename.",
            )
        if not _extension_ok(original_name):
            raise HTTPException(
                status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                detail=(
                    f"Unsupported file type for '{original_name}'. "
                    "Allowed: PDF, Excel (.xlsx/.xls), images."
                ),
            )

        contents = await upload.read()
        size = len(contents)
        if size == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Uploaded file '{original_name}' is empty.",
            )
        if size > _MAX_FILE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File '{original_name}' exceeds the 25 MB limit.",
            )

        logger.info(
            "Chat attachment received name=%s size=%s conversation_id=%s",
            original_name,
            size,
            parsed_conversation_id,
        )

        outcome = process_vehicle_attachment(
            content=contents,
            filename=original_name,
        )
        if outcome.get("needs_background_process") and outcome.get("job_id"):
            background_tasks.add_task(_run_bank_job, str(outcome["job_id"]))
        results.append(outcome)
        all_steps.extend(outcome.get("steps") or [])

    primary = results[0]
    file_names = [str(r.get("file_name") or "") for r in results]
    rows_total = sum(int(r.get("rows_staged") or 0) for r in results)

    progress_lines: list[str] = []
    for step in all_steps:
        mark = {
            "done": "✓",
            "error": "✗",
            "skipped": "·",
            "running": "…",
        }.get(str(step.get("status")), "•")
        line = f"{mark} {step.get('label')}"
        if step.get("detail"):
            line += f" — {step['detail']}"
        progress_lines.append(line)

    summary = primary.get("message") or f"Received {len(results)} file(s)."
    if len(results) > 1:
        summary = f"Processed {len(results)} file(s). {rows_total} row(s) staged."

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={
            "status": primary.get("status") or "success",
            "files_received": len(results),
            "file_name": file_names[0],
            "file_names": file_names,
            "files": results,
            "job_id": primary.get("job_id"),
            "vehicle_type": primary.get("vehicle_type"),
            "rows_staged": rows_total,
            "redirect_to": primary.get("redirect_to"),
            "steps": all_steps,
            "progress_text": "\n".join(progress_lines),
            "conversation_id": parsed_conversation_id,
            "message": message or "",
            "summary": summary,
        },
    )
