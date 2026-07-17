"""
Dictionary-first header mapping.

Seed file: mapping_dictionary.json (never overwritten)
Learned file: mapping_dictionary_learned.json (append-only aliases from LLM)
"""

from __future__ import annotations

import json
import logging
import re
import threading
from pathlib import Path
from typing import Any

from poc.config import POC_ROOT, STANDARD_SCHEMA, cfg

logger = logging.getLogger("holding_engine")

_lock = threading.Lock()


def normalize_header(value: str) -> str:
    """
    Match headers ignoring spaces, underscores, hyphens, and capitalization.
    Also strips other punctuation so 'Curr. Bal' / 'Chq/Ref No' still match.
    """
    text = (value or "").strip().lower()
    text = text.replace("_", "").replace("-", "").replace(" ", "")
    text = re.sub(r"[^a-z0-9]", "", text)
    return text


def _dictionary_path() -> Path:
    rel = str(cfg("mapping", "dictionary_path", default="mapping_dictionary.json"))
    path = Path(rel)
    return path if path.is_absolute() else POC_ROOT / path


def _learned_path() -> Path:
    rel = str(cfg("mapping", "learned_path", default="mapping_dictionary_learned.json"))
    path = Path(rel)
    return path if path.is_absolute() else POC_ROOT / path


def _load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Failed to load mapping dict %s: %s", path, exc)
        return {}
    return data if isinstance(data, dict) else {}


def _aliases_for_field(entry: Any) -> list[str]:
    if isinstance(entry, dict):
        aliases = entry.get("aliases") or []
        return [str(a) for a in aliases if str(a).strip()]
    if isinstance(entry, list):
        return [str(a) for a in entry if str(a).strip()]
    return []


def build_lookup_index(
    seed: dict[str, Any] | None = None,
    learned: dict[str, Any] | None = None,
) -> dict[str, str]:
    """
    normalized_alias -> schema_field

    Priority: seed first, then learned (learned can add new keys; won't remap
    an existing normalized alias to a different field).
    """
    seed = seed if seed is not None else _load_json(_dictionary_path())
    learned = learned if learned is not None else _load_json(_learned_path())
    index: dict[str, str] = {}

    def add_alias(alias: str, field: str) -> None:
        key = normalize_header(alias)
        if not key or field not in STANDARD_SCHEMA:
            return
        if key in index and index[key] != field:
            return
        index[key] = field

    # Schema field names always match themselves
    for field in STANDARD_SCHEMA:
        add_alias(field, field)

    for source in (seed, learned):
        for field, entry in source.items():
            if field not in STANDARD_SCHEMA:
                continue
            add_alias(field, field)
            for alias in _aliases_for_field(entry):
                add_alias(alias, field)

    return index


def lookup_headers(
    headers: list[str],
    index: dict[str, str] | None = None,
) -> tuple[dict[str, str], list[str]]:
    """
    Returns (mapped {exact_header: schema_field}, unknown_headers).
    """
    index = index if index is not None else build_lookup_index()
    mapped: dict[str, str] = {}
    unknown: list[str] = []

    for header in headers:
        if not str(header).strip():
            continue
        # Skip internal utility columns
        if normalize_header(header) in {"lineno", "linenumber", "rowno", "rownumber"}:
            continue
        field = index.get(normalize_header(header))
        if field:
            # Prefer Free Bal over generic Quantity when both appear
            if field == "Quantity" and "Quantity" in mapped.values():
                if "free" in normalize_header(header):
                    for src, dst in list(mapped.items()):
                        if dst == "Quantity":
                            del mapped[src]
                    mapped[header] = field
                # else keep existing Quantity
            else:
                mapped[header] = field
        else:
            unknown.append(header)

    return mapped, unknown


def build_mapping_analysis(headers: list[str]) -> dict[str, list[Any]]:
    """Describe dictionary coverage without applying or learning any mappings."""
    seed = _load_json(_dictionary_path())
    learned = _load_json(_learned_path())
    index = build_lookup_index(seed=seed, learned=learned)
    extracted_keys = {
        normalize_header(str(header))
        for header in headers
        if str(header).strip()
    }
    matched_headers: list[dict[str, str | None]] = []
    missing_headers: list[dict[str, str | None]] = []

    for header in headers:
        original = str(header)
        normalized = normalize_header(original)
        mapped_to = index.get(normalized)
        detail = {
            "original_header": original,
            "normalized_header": normalized,
            "mapped_to": mapped_to,
        }
        if mapped_to:
            matched_headers.append(detail)
        else:
            missing_headers.append(detail)

    unused_aliases: list[str] = []
    seen_aliases: set[str] = set()
    for source in (seed, learned):
        for entry in source.values():
            for alias in _aliases_for_field(entry):
                normalized = normalize_header(alias)
                if normalized and normalized not in extracted_keys and normalized not in seen_aliases:
                    unused_aliases.append(alias)
                    seen_aliases.add(normalized)

    return {
        "matched_headers": matched_headers,
        "missing_headers": missing_headers,
        "unused_dictionary_aliases": unused_aliases,
    }


def save_learned_aliases(new_mappings: dict[str, str]) -> list[str]:
    """
    Append LLM-discovered aliases into mapping_dictionary_learned.json.
    Never touches mapping_dictionary.json.
    Returns list of newly stored alias labels.
    """
    if not new_mappings:
        return []

    path = _learned_path()
    saved: list[str] = []

    with _lock:
        learned = _load_json(path)
        seed = _load_json(_dictionary_path())
        seed_index = build_lookup_index(seed=seed, learned={})

        for header, field in new_mappings.items():
            if field not in STANDARD_SCHEMA:
                continue
            key = normalize_header(header)
            if not key:
                continue
            # Already known in seed — no need to learn
            if seed_index.get(key) == field:
                continue

            entry = learned.get(field)
            if not isinstance(entry, dict):
                entry = {"aliases": []}
            aliases = list(entry.get("aliases") or [])
            # Store human-readable form; avoid duplicates by normalized key
            existing_norm = {normalize_header(a) for a in aliases}
            if key not in existing_norm:
                aliases.append(header)
                saved.append(f"{header} -> {field}")
            entry["aliases"] = aliases
            learned[field] = entry

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(learned, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        logger.info("Saved %s learned alias(es) to %s", len(saved), path.name)

    return saved
