"""
Mapping engine: dictionary lookup FIRST, LLM only for unknown headers.
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.config import (
    ALLOW_LOCAL_MAPPER_FALLBACK,
    LLM_MAX_TOKENS,
    STANDARD_SCHEMA,
    cfg,
)
from backend.llm.bedrock_client import bedrock_configured, get_bedrock_client
from backend.pipeline.mapping_dictionary import (
    lookup_headers,
    save_learned_aliases,
)
from backend.pipeline.mapping_prompt import (
    UNKNOWN_HEADERS_SYSTEM_PROMPT,
    build_unknown_headers_prompt,
)

logger = logging.getLogger("holding_engine")


def _strip_json_fence(text: str) -> str:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?\s*", "", text)
        text = re.sub(r"\s*```$", "", text)
    return text.strip()


def _sanitize_llm_mapping(
    raw: dict[str, Any],
    unknown_headers: list[str],
) -> dict[str, str]:
    allowed = set(unknown_headers)
    out: dict[str, str] = {}
    field_mapping = raw.get("field_mapping") if isinstance(raw, dict) else None
    if not isinstance(field_mapping, dict):
        return out
    for header, field in field_mapping.items():
        if header not in allowed:
            continue
        if field not in STANDARD_SCHEMA:
            continue
        out[str(header)] = str(field)
    return out


def _call_llm_for_unknown_headers(unknown_headers: list[str]) -> dict[str, Any]:
    """Send ONLY unknown headers to the LLM. Never the full document."""
    if not unknown_headers:
        return {"field_mapping": {}, "confidence": 100, "warnings": [], "_llm_used": False}

    llm_enabled = bool(cfg("processing", "llm_enabled", default=True))
    if not llm_enabled or not bedrock_configured():
        return {
            "field_mapping": {},
            "confidence": 40,
            "warnings": [
                f"Unknown headers left unmapped (LLM unavailable): {unknown_headers}"
            ],
            "_llm_used": False,
            "_mapper": "dictionary_only",
        }

    temperature = float(cfg("qwen", "temperature", default=0))
    logger.info(
        "Calling Bedrock for %s unknown header(s) only: %s",
        len(unknown_headers),
        unknown_headers,
    )

    client = get_bedrock_client()
    content = client.invoke_text(
        build_unknown_headers_prompt(unknown_headers),
        system=UNKNOWN_HEADERS_SYSTEM_PROMPT,
        temperature=temperature,
        max_tokens=LLM_MAX_TOKENS,
    )
    logger.info("Raw Bedrock response preview: %s", content[:500])
    cleaned = _strip_json_fence(content)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        logger.error("Failed to parse Bedrock JSON: %s", exc)
        if ALLOW_LOCAL_MAPPER_FALLBACK:
            return {
                "field_mapping": {},
                "confidence": 30,
                "warnings": [
                    f"LLM parse failed; unknown headers remain: {unknown_headers}"
                ],
                "_llm_used": True,
                "_mapper": "bedrock_parse_failed",
            }
        raise

    mapping = _sanitize_llm_mapping(parsed, unknown_headers)
    return {
        "field_mapping": mapping,
        "confidence": int(parsed.get("confidence") or 70),
        "warnings": list(parsed.get("warnings") or []),
        "_llm_used": True,
        "_mapper": "bedrock_unknown_headers",
    }


def resolve_field_mapping(
    metadata: dict[str, Any],
    headers: list[str],
    sample_rows: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """
    1) Dictionary lookup (seed + learned) — exact names never required
    2) LLM only for unknown headers
    3) Merge
    4) Persist new aliases to mapping_dictionary_learned.json
    """
    _ = sample_rows  # intentionally unused — do not send document rows to LLM
    headers = [h for h in (headers or []) if str(h).strip()]

    dict_mapped, unknown = lookup_headers(headers)
    logger.info("Dictionary mapped %s header(s): %s", len(dict_mapped), dict_mapped)
    logger.info("Unknown header(s): %s", unknown)

    llm_used = False
    llm_mapped: dict[str, str] = {}
    llm_warnings: list[str] = []
    llm_confidence = 100
    mapper_parts = ["dictionary"]

    if unknown:
        llm_result = _call_llm_for_unknown_headers(unknown)
        llm_mapped = dict(llm_result.get("field_mapping") or {})
        llm_warnings = list(llm_result.get("warnings") or [])
        llm_used = bool(llm_result.get("_llm_used"))
        llm_confidence = int(llm_result.get("confidence") or 50)
        mapper_parts.append(str(llm_result.get("_mapper") or "llm"))

        still_unknown = [h for h in unknown if h not in llm_mapped]
        if still_unknown:
            llm_warnings.append(f"Unmapped headers (pipeline continues): {still_unknown}")

        # Learn only newly LLM-mapped aliases
        learned = save_learned_aliases(llm_mapped)
        if learned:
            llm_warnings.append(f"Learned aliases saved: {learned}")

    # Merge: dictionary wins on conflict (deterministic)
    field_mapping = {**llm_mapped, **dict_mapped}

    confidence = 95 if not unknown else (85 if llm_mapped else 60)
    if llm_used and unknown:
        confidence = min(confidence, llm_confidence if llm_mapped else 50)

    warnings: list[str] = []
    if dict_mapped:
        warnings.append(f"Mapped {len(dict_mapped)} header(s) via mapping_dictionary")
    warnings.extend(llm_warnings)

    return {
        "document_type": str(cfg("processing", "document_type", default="Bank Statement")),
        "metadata": {
            "statement_date": metadata.get("statement_date"),
            "custodian": metadata.get("custodian"),
            "currency": metadata.get("currency"),
        },
        "field_mapping": field_mapping,
        "confidence": confidence,
        "warnings": warnings,
        "_mapper": "+".join(mapper_parts),
        "_llm_used": llm_used,
        "_unknown_headers": unknown,
        "_dictionary_mapped": dict_mapped,
        "_llm_mapped": llm_mapped,
    }


# Back-compat name used by runner
def call_qwen_for_mapping(
    metadata: dict[str, Any],
    headers: list[str],
    sample_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return resolve_field_mapping(metadata, headers, sample_rows)
