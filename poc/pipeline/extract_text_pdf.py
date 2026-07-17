from __future__ import annotations

import logging
import re
from typing import Any

import fitz

from poc.pipeline.models import ExtractionResult
from poc.pipeline.statement_parse import ensure_rows_from_text

logger = logging.getLogger("holding_poc")

DATE_PATTERNS = [
    re.compile(r"(?:as\s*of|as\s*on|statement\s*date|valuation\s*date)\s*[:\-]?\s*(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})", re.I),
    re.compile(r"(?:as\s*of|as\s*on|statement\s*date|valuation\s*date)\s*[:\-]?\s*(\d{4}[\/\-\.]\d{1,2}[\/\-\.]\d{1,2})", re.I),
]
ACCOUNT_PATTERNS = [
    re.compile(r"(?:account\s*(?:number|no\.?|#)?)\s*[:\-]?\s*([0-9][A-Z0-9\-]{5,})", re.I),
]
CUSTODIAN_PATTERNS = [
    re.compile(r"(?:custodian|broker|depository)\s*[:\-]?\s*([A-Za-z][A-Za-z0-9 &.\-]{2,60})", re.I),
]
CURRENCY_PATTERNS = [
    re.compile(r"(?:currency|ccy)\s*[:\-]?\s*(USD|EUR|GBP|INR|SGD|HKD|JPY|CHF|AUD|CAD)\b", re.I),
]
_KNOWN_CCY = {"USD", "EUR", "GBP", "INR", "SGD", "HKD", "JPY", "CHF", "AUD", "CAD"}


def _clean_cell(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def _extract_metadata_from_text(text: str) -> dict[str, Any]:
    meta: dict[str, Any] = {
        "statement_date": None,
        "custodian": None,
        "currency": None,
        "account_number": None,
    }

    for pat in DATE_PATTERNS:
        m = pat.search(text)
        if m:
            meta["statement_date"] = m.group(1)
            break

    for pat in ACCOUNT_PATTERNS:
        m = pat.search(text)
        if m:
            meta["account_number"] = m.group(1)
            break

    for pat in CUSTODIAN_PATTERNS:
        m = pat.search(text)
        if m:
            meta["custodian"] = _clean_cell(m.group(1).split("\n")[0])[:80]
            break

    for pat in CURRENCY_PATTERNS:
        m = pat.search(text)
        if m:
            meta["currency"] = m.group(1).upper()
            break

    # Fallback: look for ISO currency codes in header region
    if not meta["currency"]:
        m = re.search(r"\b(USD|EUR|GBP|INR|SGD|HKD|JPY|CHF|AUD|CAD)\b", text[:2000])
        if m:
            meta["currency"] = m.group(1)

    if meta["currency"] and meta["currency"] not in _KNOWN_CCY:
        meta["currency"] = None

    return meta


def _tables_from_page(page: fitz.Page) -> list[list[list[str]]]:
    tables: list[list[list[str]]] = []
    try:
        finder = page.find_tables()
    except Exception as exc:  # noqa: BLE001
        logger.warning("STEP | find_tables failed on page: %s", exc)
        return tables

    for t in finder.tables:
        extracted = t.extract()
        if not extracted:
            continue
        cleaned = [[_clean_cell(c) for c in row] for row in extracted]
        tables.append(cleaned)
    return tables


def _pick_best_table(all_tables: list[list[list[str]]]) -> list[list[str]] | None:
    """Prefer tables with >= 3 columns and >= 2 data rows."""
    scored: list[tuple[int, list[list[str]]]] = []
    for table in all_tables:
        if len(table) < 2:
            continue
        cols = max(len(r) for r in table)
        if cols < 2:
            continue
        score = cols * len(table)
        scored.append((score, table))
    if not scored:
        return None
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def _looks_like_data_row(parts: list[str], headers: list[str]) -> bool:
    """Reject metadata / title lines that were split into multiple columns."""
    if not parts or not headers:
        return False
    joined = " ".join(parts).lower()
    if any(
        bad in joined
        for bad in (
            "statement date",
            "account number",
            "account title",
            "custodian:",
            "broker:",
            "as of date",
            "holding statement",
        )
    ):
        return False
    # Prefer rows that contain at least one numeric-looking cell
    numericish = sum(1 for p in parts if any(ch.isdigit() for ch in p))
    return numericish >= 1


def _fallback_parse_lines(text: str) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Fallback when find_tables finds nothing: treat first dense multi-column line
    as header and subsequent similar lines as rows (pipe/tab/multi-space split).
    """
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    headers: list[str] = []
    rows: list[dict[str, Any]] = []

    def split_line(ln: str) -> list[str]:
        if "|" in ln:
            return [_clean_cell(p) for p in ln.split("|") if _clean_cell(p)]
        if "\t" in ln:
            return [_clean_cell(p) for p in ln.split("\t") if _clean_cell(p)]
        return [_clean_cell(p) for p in re.split(r"\s{2,}", ln) if _clean_cell(p)]

    candidates = [(i, split_line(ln)) for i, ln in enumerate(lines)]
    candidates = [(i, parts) for i, parts in candidates if len(parts) >= 3]
    if not candidates:
        return headers, rows

    # Heuristic: first multi-column line with mostly alpha tokens = header
    header_idx = None
    for i, parts in candidates:
        alpha = sum(1 for p in parts if re.search(r"[A-Za-z]", p))
        numeric = sum(1 for p in parts if any(ch.isdigit() for ch in p))
        if alpha >= max(2, len(parts) // 2) and numeric == 0:
            header_idx = i
            headers = parts
            break

    if header_idx is None:
        header_idx, headers = candidates[0]

    for i, parts in candidates:
        if i <= header_idx:
            continue
        if len(parts) != len(headers):
            if len(parts) < len(headers):
                parts = parts + [""] * (len(headers) - len(parts))
            else:
                parts = parts[: len(headers)]
        if parts == headers:
            continue
        if not _looks_like_data_row(parts, headers):
            continue
        rows.append(dict(zip(headers, parts)))

    return headers, rows


def extract_with_pymupdf(pdf_bytes: bytes, source_label: str = "input") -> ExtractionResult:
    logger.info("STEP | Extracting with PyMuPDF (text PDF): %s", source_label)
    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    try:
        full_text_parts: list[str] = []
        all_tables: list[list[list[str]]] = []

        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            full_text_parts.append(text)
            page_tables = _tables_from_page(page)
            logger.info("STEP | Page %s tables found: %s", i + 1, len(page_tables))
            all_tables.extend(page_tables)

        full_text = "\n".join(full_text_parts)
        metadata = _extract_metadata_from_text(full_text)
        logger.info("STEP | Metadata extracted: %s", metadata)

        best = _pick_best_table(all_tables)
        headers: list[str] = []
        rows: list[dict[str, Any]] = []

        if best:
            headers = [_clean_cell(h) or f"col_{i+1}" for i, h in enumerate(best[0])]
            # Deduplicate header names
            seen: dict[str, int] = {}
            unique_headers: list[str] = []
            for h in headers:
                key = h or "col"
                if key in seen:
                    seen[key] += 1
                    unique_headers.append(f"{key}_{seen[key]}")
                else:
                    seen[key] = 1
                    unique_headers.append(key)
            headers = unique_headers

            for raw in best[1:]:
                cells = [_clean_cell(c) for c in raw]
                if len(cells) < len(headers):
                    cells += [""] * (len(headers) - len(cells))
                cells = cells[: len(headers)]
                if not any(cells):
                    continue
                # Skip repeated header rows
                if cells == headers or (
                    cells and cells[0].lower() == headers[0].lower() and cells[0].lower() in {
                        "scheme name", "security name", "fund name", "description"
                    }
                ):
                    continue
                rows.append(dict(zip(headers, cells)))
            logger.info(
                "STEP | Table selected via find_tables | headers=%s | rows=%s",
                headers,
                len(rows),
            )
        else:
            logger.warning("STEP | No tables via find_tables — using line fallback")
            headers, rows = _fallback_parse_lines(full_text)
            logger.info(
                "STEP | Fallback parse | headers=%s | rows=%s",
                headers,
                len(rows),
            )

        preview = full_text[:500].replace("\n", " | ")
        warnings: list[str] = []

        if not headers or not rows:
            logger.warning(
                "No formal table structure found — using universal statement parser"
            )
            headers, rows, warnings = ensure_rows_from_text(full_text)

        if not full_text.strip():
            from poc.exceptions import EmptyPDFError

            raise EmptyPDFError("PDF has no extractable text content")

        # Never require a PDF 'holding table' — holdings is our DB target schema.
        if not rows:
            headers, rows, more = ensure_rows_from_text(full_text)
            warnings.extend(more)

        result = ExtractionResult(
            pdf_type="text",
            extractor="pymupdf",
            metadata=metadata,
            headers=headers,
            rows=rows,
            raw_text=full_text,
            raw_text_preview=preview,
        )
        # stash warnings on metadata for runner
        if warnings:
            metadata = {**metadata, "_extract_warnings": warnings}
            result.metadata = metadata
        return result
    finally:
        doc.close()
