"""
Universal statement parsers.

Goal: turn ANY extractable PDF/OCR text into row dicts for later schema mapping.
\"Holding table\" is our DB target schema — NOT something that must appear in the PDF.
"""

from __future__ import annotations

import logging
import re
from typing import Any

logger = logging.getLogger("holding_engine")

DATE_RE = re.compile(r"^(\d{2}[-/]\d{2}[-/]\d{4})\b(.*)$")
AMOUNT_RE = re.compile(r"(\d{1,3}(?:,\d{2,3})*(?:\.\d{2})|\d+\.\d{2})")
HEADER_TOKEN_HINTS = {
    "date",
    "narration",
    "particulars",
    "description",
    "withdrawal",
    "deposit",
    "balance",
    "debit",
    "credit",
    "isin",
    "qty",
    "quantity",
    "nav",
    "value",
    "scheme",
    "security",
    "company",
    "rate",
    "units",
    "ref",
    "chq",
}


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def detect_column_headers_from_text(text: str) -> list[str]:
    """
    Infer likely column names from statement vocabulary present in the document.
    Order matches common bank/holding layouts.
    """
    lower = text.lower()
    found: list[str] = []

    def add(label: str, *needles: str) -> None:
        if any(n in lower for n in needles) and label not in found:
            found.append(label)

    add("Date", "date")
    add("Narration", "narration", "particulars")
    add("Chq/Ref No", "chq/ref", "chq", "ref no")
    add("Withdrawal (Dr)", "withdrawal")
    add("Deposit (Cr)", "deposit")
    add("Balance", "balance")
    add("ISIN", "isin")
    add("Company Name", "company name", "scheme name", "security name")
    add("Quantity", "quantity", "curr. bal", "free bal", "units", "qty")
    add("Rate", "rate", "nav", "price")
    add("Value", "value", "market value")

    return found


def parse_bank_style_transactions(text: str) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Parse bank-like statements where transactions start with DD-MM-YYYY.
    Handles multi-line narrations from disordered PDF text extraction.
    """
    headers = ["Date", "Narration", "Chq/Ref No", "Withdrawal (Dr)", "Deposit (Cr)", "Balance"]
    lines = [_clean(ln) for ln in text.splitlines() if _clean(ln)]
    rows: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        m = DATE_RE.match(lines[i])
        if not m:
            i += 1
            continue

        date = m.group(1)
        rest = _clean(m.group(2))
        narr_parts: list[str] = [rest] if rest else []
        amounts: list[str] = []
        refs: list[str] = []
        i += 1

        # Consume following lines until next date (or summary markers)
        while i < len(lines):
            cur = lines[i]
            if DATE_RE.match(cur):
                break
            low = cur.lower()
            if low.startswith(("opening balance", "total withdrawal", "total deposit", "closing balance", "statement summary", "period", "cust.reln")):
                break
            # Skip repeated header labels
            if low in {"date", "narration", "chq/ref no", "withdrawal (dr)", "deposit(cr)", "deposit (cr)", "balance", "inr"}:
                i += 1
                continue

            found_amounts = AMOUNT_RE.findall(cur)
            if found_amounts and not re.search(r"[A-Za-z]{3,}", cur.replace("Dr", "").replace("Cr", "")):
                amounts.extend(found_amounts)
            elif re.search(r"(?:RTGS|NEFT|IMPS|NACH|FCM|MF-|KKBK|HDFC)", cur, re.I) and len(cur) < 40:
                refs.append(cur)
            else:
                # Strip trailing lone amounts from narration lines
                narr_line = cur
                trailing = list(AMOUNT_RE.finditer(cur))
                if trailing and trailing[-1].end() >= len(cur) - 2:
                    # keep amount separately if line ends with amount
                    amt = trailing[-1].group(1)
                    narr_line = _clean(cur[: trailing[-1].start()])
                    amounts.append(amt)
                if narr_line:
                    narr_parts.append(narr_line)
            i += 1

        narration = _clean(" ".join(p for p in narr_parts if p))
        if not narration and not amounts:
            continue

        withdrawal = ""
        deposit = ""
        balance = ""
        # Heuristic: last amount often balance (ends with context in original PDF as Cr/Dr on same token stream)
        # Without layout, assign: if 1 amount -> put in deposit/withdrawal unknown -> Market via deposit field
        # if 2+: first is txn amount, last is balance
        clean_amts = [a.replace(",", "") for a in amounts]
        if len(clean_amts) == 1:
            deposit = clean_amts[0]  # unknown direction; mapper/consumer can refine
        elif len(clean_amts) >= 2:
            deposit = clean_amts[0]
            balance = clean_amts[-1]
            if len(clean_amts) >= 3:
                withdrawal = clean_amts[0]
                deposit = clean_amts[1]
                balance = clean_amts[-1]

        # Prefer classifying by keywords in narration
        low_n = narration.lower()
        txn_amt = clean_amts[0] if clean_amts else ""
        if txn_amt:
            if any(k in low_n for k in ("purchase", "sent", "trf to", "transfer to", "withdrawal", "outflow", "debit")):
                withdrawal = txn_amt
                deposit = ""
            elif any(k in low_n for k in ("received", "recd", "from", "credit", "redemption", "deposit", "int.pd", "dividend")):
                deposit = txn_amt
                withdrawal = ""

        rows.append(
            {
                "Date": date,
                "Narration": narration,
                "Chq/Ref No": refs[0] if refs else "",
                "Withdrawal (Dr)": withdrawal,
                "Deposit (Cr)": deposit,
                "Balance": balance,
            }
        )

    logger.info("Bank-style parser produced %s rows", len(rows))
    return headers, rows


def parse_generic_lines(text: str) -> tuple[list[str], list[dict[str, Any]]]:
    """
    Last-resort: every meaningful line becomes a row.
    Ensures we always can export JSON/CSV when PDF has text.
    """
    headers = ["LineNo", "RawText"]
    rows: list[dict[str, Any]] = []
    skip_prefixes = ("page ", "http", "www.")
    for idx, raw in enumerate(text.splitlines(), start=1):
        line = _clean(raw)
        if len(line) < 3:
            continue
        if line.lower().startswith(skip_prefixes):
            continue
        rows.append({"LineNo": str(idx), "RawText": line})
    return headers, rows


def ensure_rows_from_text(text: str) -> tuple[list[str], list[dict[str, Any]], list[str]]:
    """
    Progressive extraction. Always returns something if text is non-empty.
    Returns (headers, rows, warnings).
    """
    warnings: list[str] = []
    text = text or ""
    if not text.strip():
        return [], [], ["No extractable text in document"]

    # 1) Bank/transaction style (date-led lines)
    headers, rows = parse_bank_style_transactions(text)
    if rows:
        warnings.append("Parsed as date-led statement rows (bank/cash-flow style)")
        return headers, rows, warnings

    # 2) Generic line dump
    headers, rows = parse_generic_lines(text)
    warnings.append(
        "No structured columns detected — exported raw text lines. "
        "Review mapping before posting to holdings DB."
    )
    return headers, rows, warnings
