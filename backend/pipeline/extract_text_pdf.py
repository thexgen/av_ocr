from __future__ import annotations

import logging
import re
from typing import Any

import fitz

from backend.pipeline.models import ExtractionResult
from backend.pipeline.statement_parse import STANDARD_BANK_HEADERS, ensure_rows_from_text

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

# Minimum score for a row to be treated as a transaction header schema.
HEADER_SCORE_THRESHOLD = 25.0

_TXN_HEADER_TOKENS = (
    "transaction date",
    "value date",
    "txn date",
    "tran id",
    "tran date",
    "transaction posted",
    "posted date",
    "narration",
    "particulars",
    "transaction details",
    "transaction remarks",
    "transaction description",
    "withdrawal",
    "deposit",
    "debit",
    "credit",
    "balance",
    "chq",
    "cheque",
    "ref no",
    "reference",
    "amount",
    "sl no",
    "sl. no",
    "s.no",
    "description",
)

_WARNING_PENALTY_PHRASES = (
    "minimum payment",
    "if you make",
    "estimated total",
    "important notice",
    "error resolution",
    "you will pay off",
    "additional charges using this card",
    "pay off the balance shown",
    "end up paying",
)


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


def _cell_looks_like_data(cell: str) -> bool:
    """True when a cell looks like transaction data rather than a column title."""
    c = (cell or "").strip()
    if not c:
        return False
    if re.match(r"^col_\d+$", c, re.I):
        return True
    compact = c.replace(" ", "")
    if re.match(r"^[\d,.\-+/]+$", compact) and any(ch.isdigit() for ch in c):
        return True
    if re.search(r"\d{1,3}(?:,\d{2,3})+\.\d{2}", c):
        return True
    if re.search(r"(?:NEFT|IMPS|RTGS|INF/)", c, re.I) and re.search(r"\d{6,}", c):
        return True
    # Tran-id style: S8751 1331
    if re.match(r"^[A-Z]\d{3,}", c) and sum(ch.isdigit() for ch in c) >= 3:
        return True
    if re.match(r"^\d{1,2}[/-](?:\d{1,2}|[A-Za-z]{3})", c):
        return True
    if re.match(r"^\d{2}\s+[A-Za-z]{3}\s+\d{2,4}", c):
        return True
    return False


def _mostly_data_cells(cells: list[str]) -> bool:
    nonempty = [c for c in cells if (c or "").strip()]
    if not nonempty:
        return False
    data_n = sum(1 for c in nonempty if _cell_looks_like_data(c))
    return data_n >= max(2, (len(nonempty) + 1) // 2)


def header_quality_score(cells: list[str]) -> float:
    """
    Score a candidate header row.
    Prefer transaction vocabulary; penalize data-like and warning/legal tables.
    """
    if not cells:
        return -100.0

    joined = " ".join(cells).lower()
    score = 0.0
    nonempty = [c for c in cells if (c or "").strip()]
    cols = len(nonempty)

    if cols >= 5:
        score += 20.0
    elif cols >= 3:
        score += 10.0
    elif cols < 2:
        score -= 50.0

    for tok in _TXN_HEADER_TOKENS:
        if tok in joined:
            score += 12.0

    for phrase in _WARNING_PENALTY_PHRASES:
        if phrase in joined:
            score -= 80.0

    data_like = sum(1 for c in nonempty if _cell_looks_like_data(c))
    if data_like >= max(2, (cols + 1) // 2):
        score -= 60.0
    score -= data_like * 8.0

    if any(re.match(r"^col_\d+$", c or "", re.I) for c in cells):
        score -= 40.0

    for c in nonempty:
        if len(c) > 60 and " " in c:
            score -= 25.0

    alpha_cells = sum(
        1
        for c in nonempty
        if re.search(r"[A-Za-z]{3,}", c) and not _cell_looks_like_data(c)
    )
    score += alpha_cells * 3.0

    # Tiny metadata blocks (title + account line) are weak headers
    if cols <= 2 and not any(tok in joined for tok in ("transaction", "withdrawal", "deposit", "balance", "narration")):
        score -= 15.0

    return score


def _normalize_split_header(header: str) -> str:
    """Repair common PDF line-wrap splits inside header labels (space required)."""
    h = header or ""
    repairs = (
        (r"(?i)withdra\s+wal", "Withdrawal"),
        (r"(?i)depos\s+it", "Deposit"),
        (r"(?i)transac\s+tion", "Transaction"),
        (r"(?i)parti\s+culars", "Particulars"),
        (r"(?i)narra\s+tion", "Narration"),
        (r"(?i)balan\s+ce", "Balance"),
    )
    for pat, repl in repairs:
        h = re.sub(pat, repl, h)
    return _clean_cell(h)


def _unique_headers(raw_headers: list[str]) -> list[str]:
    seen: dict[str, int] = {}
    unique: list[str] = []
    for h in raw_headers:
        key = _normalize_split_header(h) or "col"
        if key in seen:
            seen[key] += 1
            unique.append(f"{key}_{seen[key]}")
        else:
            seen[key] = 1
            unique.append(key)
    return unique


def _pad_row(cells: list[str], width: int) -> list[str]:
    if len(cells) < width:
        cells = cells + [""] * (width - len(cells))
    return cells[:width]


def _is_header_row(cells: list[str], threshold: float = HEADER_SCORE_THRESHOLD) -> bool:
    if _mostly_data_cells(cells):
        return False
    return header_quality_score(cells) >= threshold


def _merge_bank_statement_tables(
    page_tables: list[tuple[int, list[list[str]]]],
) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """
    Multi-page header propagation for bank statements.

    - Keep 1-row tables as header schema candidates (do not discard).
    - Prefer high header-quality scores over raw cols*rows size.
    - Continuation pages: if first row looks like data, do not treat it as header.
    """
    notes: list[str] = []
    if not page_tables:
        return [], [], notes

    best_header: list[str] | None = None
    best_score = float("-inf")
    best_page = 0

    for page_i, table in page_tables:
        if not table:
            continue
        first = table[0]
        cols = max(len(r) for r in table)
        if cols < 2:
            continue
        score = header_quality_score(first)
        # Prefer earlier pages when scores are close
        score -= page_i * 0.05
        # Slight preference for wider txn tables
        score += min(cols, 12) * 0.5
        if score > best_score:
            best_score = score
            best_header = first
            best_page = page_i

    if best_header is None or best_score < HEADER_SCORE_THRESHOLD:
        logger.info(
            "STEP | No high-quality txn header table (best_score=%s)",
            best_score if best_header is not None else None,
        )
        return [], [], notes

    headers = _unique_headers([_clean_cell(h) or f"col_{i+1}" for i, h in enumerate(best_header)])
    width = len(headers)
    notes.append(
        f"Selected header schema from page {best_page + 1} "
        f"(quality_score={best_score:.1f}, cols={width})"
    )
    logger.info(
        "STEP | Header schema selected | page=%s score=%.1f headers=%s",
        best_page + 1,
        best_score,
        headers,
    )

    rows: list[dict[str, Any]] = []
    for page_i, table in page_tables:
        if not table:
            continue
        table_width = max((len(r) for r in table), default=0)
        # Skip unrelated narrow / chart tables
        if table_width < max(2, width - 2):
            continue

        first = table[0]
        first_is_header = _is_header_row(first)

        if first_is_header:
            # Header-only table (Kotak): schema only, no data rows
            data_rows = table[1:]
            if page_i != best_page and data_rows:
                notes.append(f"Page {page_i + 1}: skipped repeated header, kept {len(data_rows)} data rows")
        else:
            # Continuation page: first row is data — do not promote to header
            data_rows = table
            notes.append(
                f"Page {page_i + 1}: continuation table — reused headers, "
                f"first row treated as data ({len(data_rows)} rows)"
            )

        for raw in data_rows:
            cells = _pad_row([_clean_cell(c) for c in raw], width)
            if not any(cells):
                continue
            if cells == headers:
                continue
            # Skip accidental repeated header rows mid-document
            if _is_header_row(cells):
                continue
            rows.append(dict(zip(headers, cells)))

    logger.info("STEP | Multi-page merge produced %s rows", len(rows))
    return headers, rows, notes


def _project_bank_rows_onto_headers(
    bank_rows: list[dict[str, Any]],
    target_headers: list[str],
) -> list[dict[str, Any]]:
    """Map standard bank-parser fields onto extracted table headers when possible."""
    if not bank_rows or not target_headers:
        return []

    field_for_header: dict[str, str] = {}
    for th in target_headers:
        tl = th.lower()
        if "balance" in tl:
            field_for_header[th] = "Balance"
        elif any(x in tl for x in ("chq", "cheque", "ref no", "reference")):
            field_for_header[th] = "Chq/Ref No"
        elif any(x in tl for x in ("detail", "narration", "particular", "remark", "description")):
            field_for_header[th] = "Narration"
        elif "value date" in tl:
            field_for_header[th] = "Date"
        elif "posted" in tl and "date" in tl:
            field_for_header[th] = "Date"
        elif "transaction date" in tl or tl in {"date", "txn date", "tran date"}:
            field_for_header[th] = "Date"
        elif "debit/credit" in tl or ("debit" in tl and "credit" in tl):
            field_for_header[th] = "_signed_amount"
        elif any(x in tl for x in ("withdrawal", "debit")):
            field_for_header[th] = "Withdrawal (Dr)"
        elif any(x in tl for x in ("deposit", "credit")):
            field_for_header[th] = "Deposit (Cr)"
        elif tl in {"#", "sl no", "sl. no", "s.no", "sno"} or re.match(r"^sl\b", tl):
            field_for_header[th] = "_index"

    if not field_for_header:
        return []

    projected: list[dict[str, Any]] = []
    for idx, br in enumerate(bank_rows, start=1):
        out: dict[str, Any] = {h: "" for h in target_headers}
        for th, src in field_for_header.items():
            if src == "_index":
                out[th] = str(idx)
            elif src == "_signed_amount":
                w = (br.get("Withdrawal (Dr)") or "").strip()
                d = (br.get("Deposit (Cr)") or "").strip()
                if w:
                    out[th] = f"-{w}" if not w.startswith("-") else w
                elif d:
                    out[th] = f"+{d}" if not d.startswith(("+", "-")) else d
            else:
                out[th] = br.get(src) or ""
        if any(str(v).strip() for v in out.values()):
            projected.append(out)
    return projected


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

    # Prefer the highest-quality header among early candidates
    header_idx = None
    best_local = float("-inf")
    for i, parts in candidates[:40]:
        score = header_quality_score(parts)
        if score > best_local and score >= HEADER_SCORE_THRESHOLD:
            best_local = score
            header_idx = i
            headers = parts

    if header_idx is None:
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
        page_tables: list[tuple[int, list[list[str]]]] = []

        for i, page in enumerate(doc):
            text = page.get_text("text") or ""
            full_text_parts.append(text)
            tables = _tables_from_page(page)
            logger.info("STEP | Page %s tables found: %s", i + 1, len(tables))
            for table in tables:
                page_tables.append((i, table))

        full_text = "\n".join(full_text_parts)
        metadata = _extract_metadata_from_text(full_text)
        logger.info("STEP | Metadata extracted: %s", metadata)

        headers, rows, merge_notes = _merge_bank_statement_tables(page_tables)
        warnings: list[str] = list(merge_notes)

        if headers:
            logger.info(
                "STEP | Table merge | headers=%s | rows=%s",
                headers,
                len(rows),
            )
        else:
            logger.warning("STEP | No quality txn tables — using line fallback")
            headers, rows = _fallback_parse_lines(full_text)
            logger.info(
                "STEP | Fallback parse | headers=%s | rows=%s",
                headers,
                len(rows),
            )

        preview = full_text[:500].replace("\n", " | ")

        # Header schema found but no grid rows (e.g. Kotak 1-row header tables):
        # parse date-led text and project onto the real headers when possible.
        if headers and not rows:
            logger.warning(
                "Header schema present but no table data rows — parsing date-led text"
            )
            text_headers, text_rows, text_warnings = ensure_rows_from_text(full_text)
            warnings.extend(text_warnings)
            if text_rows:
                projected = _project_bank_rows_onto_headers(text_rows, headers)
                if projected and header_quality_score(headers) >= HEADER_SCORE_THRESHOLD:
                    rows = projected
                    warnings.append(
                        "Filled rows from date-led text using propagated table headers"
                    )
                else:
                    headers, rows = text_headers, text_rows

        if not headers or not rows:
            logger.warning(
                "No formal table structure found — using universal statement parser"
            )
            headers, rows, more = ensure_rows_from_text(full_text)
            warnings.extend(more)

        if not full_text.strip():
            from backend.exceptions import EmptyPDFError

            raise EmptyPDFError("PDF has no extractable text content")

        # Never require a PDF 'holding table' — holdings is our DB target schema.
        if not rows:
            headers, rows, more = ensure_rows_from_text(full_text)
            warnings.extend(more)

        # Mark known bank-parser schema so validation can distinguish intentional
        # bank headers from synthetic garbage (col_N / data-as-header / prose).
        if headers == list(STANDARD_BANK_HEADERS) or headers == STANDARD_BANK_HEADERS:
            metadata = {**metadata, "_bank_parser_headers": True}

        result = ExtractionResult(
            pdf_type="text",
            extractor="pymupdf",
            metadata=metadata,
            headers=headers,
            rows=rows,
            raw_text=full_text,
            raw_text_preview=preview,
        )
        if warnings:
            metadata = {**result.metadata, "_extract_warnings": warnings}
            result.metadata = metadata
        return result
    finally:
        doc.close()
