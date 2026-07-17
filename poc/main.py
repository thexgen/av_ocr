from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from poc.config import SAMPLE_DATA_PREFIX
from poc.create_sample import DEFAULT_SAMPLE_KEY, create_sample_holding_pdf
from poc.engine import ProcessingEngine
from poc.exceptions import ProcessingError
from poc.logging_setup import setup_logging
from poc.services.storage_service import get_storage_service

logger = logging.getLogger("holding_engine")


def _to_input_key(pdf_arg: str) -> str:
    normalized = pdf_arg.replace("\\", "/").lstrip("./")
    if normalized.startswith(f"{SAMPLE_DATA_PREFIX}/"):
        return normalized
    name = Path(normalized).name
    return f"{SAMPLE_DATA_PREFIX}/{name}"


def main(argv: list[str] | None = None) -> int:
    setup_logging()
    parser = argparse.ArgumentParser(
        description="Holding Statement Processing Engine (local, production-ready)"
    )
    parser.add_argument(
        "pdf",
        nargs="?",
        help="Storage key or filename under sample_data/",
    )
    parser.add_argument(
        "--create-sample",
        action="store_true",
        help="Create a sample holding PDF and process it as a job",
    )
    parser.add_argument(
        "--force-ocr",
        action="store_true",
        help="Force PaddleOCR path",
    )
    parser.add_argument(
        "--user-id",
        default=None,
        help="Placeholder user id for upload history",
    )
    args = parser.parse_args(argv)

    storage = get_storage_service()
    engine = ProcessingEngine(storage)

    if args.create_sample:
        source_key = create_sample_holding_pdf(storage)
        original = Path(DEFAULT_SAMPLE_KEY).name
    elif args.pdf:
        source_key = _to_input_key(args.pdf)
        original = Path(source_key).name
    else:
        parser.print_help()
        logger.error("Provide a PDF under sample_data/ or use --create-sample")
        return 2

    try:
        result = engine.submit_and_process(
            source_key=source_key,
            original_file_name=original,
            user_id=args.user_id,
            force_ocr=args.force_ocr,
        )
        status = result.get("status")
        logger.info(
            "Engine finished | job_id=%s status=%s",
            result.get("job_id"),
            status,
        )
        return 0 if status and str(status).startswith("SUCCESS") else 1
    except ProcessingError as exc:
        logger.error("Engine rejected upload | %s: %s", exc.code, exc.message)
        return 1
    except Exception as exc:  # noqa: BLE001
        logger.exception("Engine fatal error | %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
