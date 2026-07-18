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

_MONTH = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"

# Bank / card date-led transaction lines (order matters: more specific first).
_DATE_LINE_PATTERNS: list[re.Pattern[str]] = [
    # DD-MM-YYYY or DD/MM/YYYY or MM/DD/YYYY
    re.compile(r"^(\d{2}[-/]\d{2}[-/]\d{4})\b(.*)$"),
    # DD Mon YYYY  (e.g. 01 Sep 2023)
    re.compile(rf"^(\d{{2}}\s+{_MONTH}\s+\d{{4}})\b(.*)$", re.I),
    # DD-Mon-YYYY  (e.g. 01-Sep-2023)
    re.compile(rf"^(\d{{2}}-{_MONTH}-\d{{4}})\b(.*)$", re.I),
    # MM/DD/YY
    re.compile(r"^(\d{2}/\d{2}/\d{2})\b(.*)$"),
    # MM/DD (Chase-style: date alone on line or followed by spaces + merchant)
    re.compile(r"^(\d{2}/\d{2})(?:\s+|$)(.*)$"),
]

# Back-compat alias used by tests / callers that imported DATE_RE
DATE_RE = _DATE_LINE_PATTERNS[0]

AMOUNT_RE = re.compile(r"([+-]?\d{1,3}(?:,\d{2,3})*(?:\.\d{2})|[+-]?\d+\.\d{2})")
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

STANDARD_BANK_HEADERS = [
    "Date",
    "Narration",
    "Chq/Ref No",
    "Withdrawal (Dr)",
    "Deposit (Cr)",
    "Balance",
]


def _clean(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").strip())


def match_date_line(line: str) -> tuple[str, str] | None:
    """If line starts with a supported transaction date, return (date, rest)."""
    text = _clean(line)
    if not text:
        return None
    for pat in _DATE_LINE_PATTERNS:
        m = pat.match(text)
        if m:
            return m.group(1), _clean(m.group(2) if m.lastindex and m.lastindex >= 2 else "")
    return None


def count_date_led_lines(text: str) -> int:
    """Count lines that look like date-led transaction starts."""
    n = 0
    for ln in (text or "").splitlines():
        if match_date_line(ln):
            n += 1
    return n


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
    Parse bank-like statements where transactions start with a date line.
    Supports DD-MM-YYYY, DD Mon YYYY, DD-Mon-YYYY, MM/DD/YY, and MM/DD.
    Handles multi-line narrations from disordered PDF text extraction.
    """
    headers = list(STANDARD_BANK_HEADERS)
    lines = [_clean(ln) for ln in text.splitlines() if _clean(ln)]
    rows: list[dict[str, Any]] = []

    i = 0
    while i < len(lines):
        matched = match_date_line(lines[i])
        if not matched:
            i += 1
            continue

        date, rest = matched
        # Skip statement period lines: "01 Sep 2023 - 30 Sep 2023"
        if rest and re.match(
            rf"^[-–]\s*\d{{2}}[\s-]{_MONTH}",
            rest,
            re.I,
        ):
            i += 1
            continue
        if rest and re.search(rf"\d{{2}}\s*{_MONTH}\s+\d{{4}}", rest, re.I) and re.search(
            r"\s[-–]\s", rest[:48]
        ):
            i += 1
            continue

        narr_parts: list[str] = [rest] if rest else []
        amounts: list[str] = []
        refs: list[str] = []
        i += 1

        # Consume following lines until next date (or summary markers)
        while i < len(lines):
            cur = lines[i]
            next_date = match_date_line(cur)
            if next_date:
                # Value-date / secondary date before narration+amounts: keep consuming.
                if not amounts and len(_clean(" ".join(narr_parts))) < 8:
                    i += 1
                    continue
                break
            low = cur.lower()
            if low.startswith(
                (
                    "opening balance",
                    "total withdrawal",
                    "total deposit",
                    "closing balance",
                    "statement summary",
                    "period",
                    "cust.reln",
                )
            ):
                break
            # Skip repeated header labels and lone clock times
            if low in {
                "date",
                "narration",
                "chq/ref no",
                "withdrawal (dr)",
                "deposit(cr)",
                "deposit (cr)",
                "balance",
                "inr",
            }:
                i += 1
                continue
            if re.match(r"^\d{1,2}:\d{2}\s*(?:am|pm)?$", low):
                i += 1
                continue

            found_amounts = AMOUNT_RE.findall(cur)
            if found_amounts and not re.search(r"[A-Za-z]{3,}", cur.replace("Dr", "").replace("Cr", "")):
                amounts.extend(found_amounts)
            elif re.search(r"(?:RTGS|NEFT|IMPS|NACH|FCM|MF-|KKBK|HDFC)", cur, re.I) and len(cur) < 40:
                refs.append(cur)
            else:
                narr_line = cur
                trailing = list(AMOUNT_RE.finditer(cur))
                if trailing and trailing[-1].end() >= len(cur) - 2:
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

        # Normalize amount tokens; retain sign from source (+ credit / - debit).
        clean_amts: list[str] = []
        signs: list[str] = []
        for a in amounts:
            raw = a.replace(",", "").strip()
            sign = ""
            if raw.startswith("+"):
                sign = "+"
                raw = raw[1:]
            elif raw.startswith("-"):
                sign = "-"
                raw = raw[1:]
            clean_amts.append(raw)
            signs.append(sign)

        if len(clean_amts) == 1:
            deposit = clean_amts[0]
        elif len(clean_amts) >= 2:
            deposit = clean_amts[0]
            balance = clean_amts[-1]
            if len(clean_amts) >= 3:
                withdrawal = clean_amts[0]
                deposit = clean_amts[1]
                balance = clean_amts[-1]

        low_n = narration.lower()
        txn_amt = clean_amts[0] if clean_amts else ""
        txn_sign = signs[0] if signs else ""
        if txn_amt:
            if txn_sign == "+" or any(
                k in low_n
                for k in (
                    "received",
                    "recd",
                    "credit",
                    "redemption",
                    "deposit",
                    "int.pd",
                    "dividend",
                )
            ):
                deposit = txn_amt
                withdrawal = ""
            elif txn_sign == "-" or any(
                k in low_n
                for k in (
                    "purchase",
                    "sent",
                    "trf to",
                    "transfer to",
                    "withdrawal",
                    "outflow",
                    "debit",
                )
            ):
                withdrawal = txn_amt
                deposit = ""

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
