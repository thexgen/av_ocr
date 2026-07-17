from __future__ import annotations

import logging
import sys
import time
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from typing import Iterator

from poc.config import LOGGER_NAME, cfg

# Context for structured job logs
job_id_var: ContextVar[str] = ContextVar("job_id", default="-")
stage_var: ContextVar[str] = ContextVar("stage", default="INIT")
job_start_var: ContextVar[float] = ContextVar("job_start", default=0.0)
stage_start_var: ContextVar[float] = ContextVar("stage_start", default=0.0)


class JobLogFormatter(logging.Formatter):
    """
    [JOB_...]
    [HH:MM:SS]
    [STAGE]
    message (elapsed ...)
    """

    def format(self, record: logging.LogRecord) -> str:
        job_id = job_id_var.get()
        stage = stage_var.get()
        ts = datetime.now().strftime("%H:%M:%S")

        job_start = job_start_var.get()
        elapsed_job = (time.perf_counter() - job_start) if job_start else 0.0
        stage_start = stage_start_var.get()
        elapsed_stage = (time.perf_counter() - stage_start) if stage_start else 0.0

        # Allow callers to attach stage_elapsed via record
        extra_elapsed = getattr(record, "stage_elapsed", None)
        if extra_elapsed is not None:
            elapsed_note = f"Completed in {extra_elapsed:.1f} sec"
        else:
            elapsed_note = (
                f"stage={elapsed_stage:.1f}s job={elapsed_job:.1f}s"
            )

        msg = record.getMessage()
        return (
            f"[{job_id}]\n"
            f"[{ts}]\n"
            f"[{stage}]\n"
            f"{msg} | {elapsed_note}"
        )


def setup_logging(level: int | None = None) -> logging.Logger:
    name = LOGGER_NAME
    logger = logging.getLogger(name)

    # Also alias legacy name used in older modules
    legacy = logging.getLogger("holding_poc")

    if level is None:
        level_name = str(cfg("logging", "level", default="INFO")).upper()
        level = getattr(logging, level_name, logging.INFO)

    for lg in (logger, legacy):
        lg.handlers.clear()
        lg.setLevel(level)
        lg.propagate = False

    stream = sys.stdout
    try:
        stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:  # noqa: BLE001
        pass

    handler = logging.StreamHandler(stream)
    handler.setLevel(level)
    handler.setFormatter(JobLogFormatter())

    logger.addHandler(handler)
    legacy.addHandler(handler)

    # Bridge: holding_poc -> same handlers already attached
    return logger


def bind_job(job_id: str) -> None:
    job_id_var.set(job_id)
    job_start_var.set(time.perf_counter())
    stage_var.set("INIT")
    stage_start_var.set(time.perf_counter())


def set_stage(stage: str) -> None:
    stage_var.set(stage)
    stage_start_var.set(time.perf_counter())


@contextmanager
def stage(name: str, logger: logging.Logger | None = None) -> Iterator[None]:
    """Context manager that sets stage and logs completion elapsed time."""
    log = logger or logging.getLogger(LOGGER_NAME)
    set_stage(name)
    start = time.perf_counter()
    log.info("Started")
    try:
        yield
        elapsed = time.perf_counter() - start
        log.info("Completed", extra={"stage_elapsed": elapsed})
    except Exception:
        elapsed = time.perf_counter() - start
        log.info("Failed", extra={"stage_elapsed": elapsed})
        raise


def job_elapsed_seconds() -> float:
    start = job_start_var.get()
    if not start:
        return 0.0
    return time.perf_counter() - start


def format_processing_time(seconds: float) -> str:
    return f"{seconds:.1f} sec"
