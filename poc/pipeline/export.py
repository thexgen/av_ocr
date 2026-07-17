from __future__ import annotations

import csv
import io
import json
import logging
from datetime import datetime
from typing import Any

from poc.config import OUTPUT_PREFIX, STANDARD_SCHEMA
from poc.interfaces.storage import StorageService
from poc.pipeline.mapping_dictionary import build_mapping_analysis

logger = logging.getLogger("holding_engine")


def date_stamp(asof_hint: str | None = None) -> str:
    """Prefer statement date as YYYYMMDD; else today."""
    if asof_hint:
        text = asof_hint.strip()
        for sep in ("-", "/", "."):
            parts = text.split(sep)
            if len(parts) == 3 and len(parts[0]) == 4 and parts[0].isdigit():
                y, m, d = parts
                if len(m) <= 2 and len(d) <= 2:
                    return f"{y}{int(m):02d}{int(d):02d}"
        for sep in ("/", "-", "."):
            parts = text.split(sep)
            if len(parts) == 3 and len(parts[2]) == 4 and parts[2].isdigit():
                d, m, y = parts
                if d.isdigit() and m.isdigit():
                    return f"{y}{int(m):02d}{int(d):02d}"
    return datetime.now().strftime("%Y%m%d")


def build_normalized_json_payload(
    records: list[dict[str, Any]],
    mapping_response: dict[str, Any],
    extraction_info: dict[str, Any],
    *,
    job_id: str,
) -> dict[str, Any]:
    return {
        "job_id": job_id,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "extraction": extraction_info,
        "mapping": {
            k: v for k, v in mapping_response.items() if not str(k).startswith("_")
        },
        "mapper": mapping_response.get("_mapper"),
        "record_count": len(records),
        "records": records,
    }


def build_holding_csv_text(records: list[dict[str, Any]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=STANDARD_SCHEMA, extrasaction="ignore")
    writer.writeheader()
    for row in records:
        writer.writerow(
            {k: row.get(k) if row.get(k) is not None else "" for k in STANDARD_SCHEMA}
        )
    return buf.getvalue()


def persist_extraction_debug_outputs(
    storage: StorageService,
    *,
    job_id: str,
    metadata: dict[str, Any],
    headers: list[str],
    rows: list[dict[str, Any]],
    raw_text: str,
    document_type: str,
    page_count: int,
) -> dict[str, str]:
    """Persist extraction and dictionary coverage before mapping alters anything."""
    base = f"{OUTPUT_PREFIX}/{job_id}"
    extracted_key = f"{base}/actual_extracted_output.json"
    analysis_key = f"{base}/mapping_analysis.json"
    extracted_payload = {
        "metadata": metadata,
        "headers": headers,
        "rows": rows,
        "raw_text": raw_text,
        "document_type": document_type,
        "page_count": page_count,
    }

    storage.write_text(
        extracted_key, json.dumps(extracted_payload, indent=2, ensure_ascii=False)
    )
    storage.write_text(
        analysis_key,
        json.dumps(build_mapping_analysis(headers), indent=2, ensure_ascii=False),
    )
    logger.info(
        "Persisted extraction debugging outputs | extracted=%s analysis=%s",
        extracted_key,
        analysis_key,
    )
    return {
        "actual_extracted_output_key": extracted_key,
        "mapping_analysis_key": analysis_key,
    }


def persist_outputs(
    storage: StorageService,
    records: list[dict[str, Any]],
    mapping_response: dict[str, Any],
    extraction_info: dict[str, Any],
    *,
    job_id: str,
    asof_hint: str | None = None,
) -> dict[str, str]:
    """
    Persist JSON + CSV via StorageService under output/{job_id}/.
    """
    stamp = date_stamp(asof_hint)
    base = f"{OUTPUT_PREFIX}/{job_id}"
    json_key = f"{base}/holding_{stamp}.json"
    csv_key = f"{base}/holding_{stamp}.csv"

    payload = build_normalized_json_payload(
        records, mapping_response, extraction_info, job_id=job_id
    )
    json_text = json.dumps(payload, indent=2, ensure_ascii=False)
    csv_text = build_holding_csv_text(records)

    storage.write_text(json_key, json_text)
    storage.write_text(csv_key, csv_text)

    logger.info("Persisted outputs | json=%s csv=%s", json_key, csv_key)
    return {"json_key": json_key, "csv_key": csv_key, "output_prefix": base}
