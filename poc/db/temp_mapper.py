"""
Map CanonicalTransaction → bankcashtemp row dicts with mandatory-field validation.

Mandatory for staging:
  - transaction date
  - amount
  - transaction type (inferred from debit/credit sign when not explicit)

Other fields may be blank.
"""

from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from poc.db.settings import (
    TXN_TYPE_CREDIT,
    TXN_TYPE_DEBIT,
    TXN_TYPE_LABELS,
    get_staging_defaults,
)
from poc.export.canonical import CanonicalTransaction

_MONTHS = {
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

# Matches bankcashtemp VARCHAR limits (MySQL error 1406 if exceeded).
_COL_LIMITS = {
    "uploadbatchid": 64,
    "jobid": 64,
    "description": 1000,
    "instrumentno": 100,
    "voucher": 100,
    "comments": 1000,
    "usercomments": 1000,
    "filename": 255,
    "feedtransactionid": 100,
    "syncdescription": 500,
    "checkno": 100,
    "memo": 1000,
    "billdotcomdoc": 255,
    "txncustomfxcurrency": 10,
    "errordesc": 2000,
}


def _clip(value: Any, column: str) -> Any:
    if value is None:
        return None
    limit = _COL_LIMITS.get(column)
    text = str(value)
    if limit is None or len(text) <= limit:
        return text
    return text[:limit]


def parse_transaction_date(raw: str | None) -> date | None:
    text = (raw or "").strip()
    if not text:
        return None

    # 01 Sep 2023 / 01-Sep-2023
    m = re.match(
        r"^(\d{1,2})[\s\-]+([A-Za-z]{3,9})[\s\-]+(\d{4})$",
        text,
    )
    if m:
        d, mon, y = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
        if mon in _MONTHS:
            try:
                return date(y, _MONTHS[mon], d)
            except ValueError:
                return None

    # 09/Dec/2024
    m = re.match(r"^(\d{1,2})/([A-Za-z]{3,9})/(\d{4})$", text)
    if m:
        d, mon, y = int(m.group(1)), m.group(2)[:3].lower(), int(m.group(3))
        if mon in _MONTHS:
            try:
                return date(y, _MONTHS[mon], d)
            except ValueError:
                return None

    for fmt in (
        "%Y-%m-%d",
        "%d/%m/%Y",
        "%m/%d/%Y",
        "%d-%m-%Y",
        "%m-%d-%Y",
        "%d/%m/%y",
        "%m/%d/%y",
        "%Y/%m/%d",
        "%d.%m.%Y",
    ):
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    return None


def parse_amount(raw: str | None) -> Decimal | None:
    text = (raw or "").strip()
    if not text:
        return None
    # Keep leading sign; strip currency junk
    text = text.replace(",", "").replace("₹", "").replace("$", "").strip()
    text = re.sub(r"[^\d.\-+]", "", text)
    if not text or text in {"+", "-", ".", "+.", "-."}:
        return None
    try:
        return Decimal(text)
    except (InvalidOperation, ValueError):
        return None


def infer_transaction_type(
    txn: CanonicalTransaction,
) -> tuple[int | None, str | None]:
    """
    Returns (transactiontypeid, label).
    Prefer explicit trans_type; else debit/credit from value_sign / amount sign.
    """
    explicit = (txn.trans_type or txn.original_custodian_transaction_type or "").strip().lower()
    if explicit:
        if any(k in explicit for k in ("credit", "deposit", "cr", "receipt", "inflow")):
            return TXN_TYPE_CREDIT, TXN_TYPE_LABELS[TXN_TYPE_CREDIT]
        if any(k in explicit for k in ("debit", "withdrawal", "dr", "payment", "outflow", "purchase")):
            return TXN_TYPE_DEBIT, TXN_TYPE_LABELS[TXN_TYPE_DEBIT]

    sign = (txn.value_sign or "").strip()
    if sign == "+":
        return TXN_TYPE_CREDIT, TXN_TYPE_LABELS[TXN_TYPE_CREDIT]
    if sign == "-":
        return TXN_TYPE_DEBIT, TXN_TYPE_LABELS[TXN_TYPE_DEBIT]

    for candidate in (txn.market_value_local, txn.amount):
        if not candidate:
            continue
        s = str(candidate).strip()
        if s.startswith("+"):
            return TXN_TYPE_CREDIT, TXN_TYPE_LABELS[TXN_TYPE_CREDIT]
        if s.startswith("-"):
            return TXN_TYPE_DEBIT, TXN_TYPE_LABELS[TXN_TYPE_DEBIT]

    desc = (txn.security_description or txn.description or "").lower()
    if any(k in desc for k in ("credit", "deposit", "received", "recd", "neft-cr", "imps-cr")):
        return TXN_TYPE_CREDIT, TXN_TYPE_LABELS[TXN_TYPE_CREDIT]
    if any(k in desc for k in ("debit", "withdrawal", "sent", "purchase", "payment")):
        return TXN_TYPE_DEBIT, TXN_TYPE_LABELS[TXN_TYPE_DEBIT]

    return None, None


def validate_and_build_temp_row(
    txn: CanonicalTransaction,
    *,
    job_id: str,
    rowno: int,
    filename: str | None,
    uploadbatchid: str | None = None,
) -> dict[str, Any]:
    """Build one bankcashtemp insert dict + iserror / errordesc."""
    defaults = get_staging_defaults()
    errors: list[str] = []

    txn_date = parse_transaction_date(txn.trade_date or txn.asof_date or txn.settlement_date)
    if txn_date is None:
        errors.append("missing date")

    # Prefer signed market value for storage; else unsigned amount with sign
    amount_raw = txn.market_value_local or txn.amount
    amount = parse_amount(amount_raw)
    if amount is None and txn.amount:
        amount = parse_amount(txn.amount)
    if amount is None:
        errors.append("missing amount")
    elif txn.value_sign == "-" and amount > 0:
        amount = -amount
    elif txn.value_sign == "+" and amount < 0:
        amount = abs(amount)

    type_id, type_label = infer_transaction_type(txn)
    if type_id is None:
        errors.append("missing transaction type")

    description = txn.security_description or txn.description
    checkno = txn.check_number or txn.security_id
    memo = txn.description if txn.description != description else None

    is_error = 1 if errors else 0
    error_desc = ", ".join(errors) if errors else None

    return {
        "uploadbatchid": _clip(uploadbatchid or job_id, "uploadbatchid"),
        "jobid": _clip(job_id, "jobid"),
        "rowno": rowno,
        "entityid": defaults.entity_id,
        "accountid": None,
        "transactiontypeid": type_id,
        "transactiondate": txn_date,
        "payeepayorid": None,
        "ledgerid": None,
        "amount": amount,
        "description": _clip(description, "description"),
        "instrumentno": _clip(checkno, "instrumentno"),
        "positionid": None,
        "positiontagid": None,
        "accountrecon": 0,
        "voucher": None,
        "statusid": None,
        "oldstatusid": None,
        "comments": None,
        "usercomments": None,
        "filename": _clip(filename, "filename"),
        "feedtransactionid": _clip(txn.unique_transaction_id, "feedtransactionid"),
        "syncdescription": _clip(type_label, "syncdescription"),
        "userid": defaults.user_id,
        "oldid": None,
        "ismultidistributed": 0,
        "checkno": _clip(checkno, "checkno"),
        "memo": _clip(memo, "memo"),
        "checkbookid": None,
        "voidtransactiondate": None,
        "createdby": defaults.user_id,
        "updatedby": defaults.user_id,
        "txnfxrate": None,
        "payeeid": None,
        "consider_return_computation": 0,
        "feedid": None,
        "billdotcomdoc": None,
        "txncustomfxcurrency": _clip(
            txn.currency_code or txn.currency_local, "txncustomfxcurrency"
        ),
        "iserror": is_error,
        "errordesc": _clip(error_desc, "errordesc"),
        # Not inserted — used by API mapping only
        "_type_label": type_label or "",
    }
