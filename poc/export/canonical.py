"""
Canonical transaction model — single source of truth for all CSV exporters.

Built from extracted bank-statement rows (plus optional field_mapping hints).
Future document types (Holdings, Contract Notes, CAS) should produce the same
CanonicalTransaction shape (or a documented subtype) for the export framework.
"""

from __future__ import annotations

import logging
import re
from dataclasses import asdict, dataclass, fields
from typing import Any

from poc.export.schemas import DOCUMENT_TYPE_BANK_STATEMENT

logger = logging.getLogger("holding_engine")

_BLANK = (None, "")


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text if text else None


def _parse_signed_amount(raw: Any) -> tuple[str | None, str | None]:
    """
    Split a source amount into (unsigned Amount, ValueSign).
    ValueSign is '+' or '-' only when present in source text — never invented.
    """
    text = _clean(raw)
    if text is None:
        return None, None
    sign: str | None = None
    body = text
    if body.startswith("+"):
        sign = "+"
        body = body[1:].strip()
    elif body.startswith("-"):
        sign = "-"
        body = body[1:].strip()
    elif body.endswith("-") and body[:-1].replace(",", "").replace(".", "").isdigit():
        sign = "-"
        body = body[:-1].strip()
    body = body.lstrip("+").strip()
    return (body or None), sign


@dataclass
class CanonicalTransaction:
    """Neutral bank/cash transaction record used by all export generators."""

    document_type: str = DOCUMENT_TYPE_BANK_STATEMENT

    customer_id: str | None = None
    custodian: str | None = None
    account_number: str | None = None
    account_title: str | None = None

    trans_type: str | None = None
    security_type: str | None = None
    symbol: str | None = None
    trade_date: str | None = None
    settlement_date: str | None = None
    units: str | None = None
    amount: str | None = None
    currency_code: str | None = None
    security_description: str | None = None
    description: str | None = None
    check_number: str | None = None
    value_sign: str | None = None
    unique_transaction_id: str | None = None

    create_date: str | None = None
    update_date: str | None = None
    delete_date: str | None = None
    iud: str | None = None
    original_custodian_transaction_type: str | None = None

    isin: str | None = None
    sedol: str | None = None
    cusip: str | None = None
    trans_user3: str | None = None
    local_price: str | None = None
    base_price: str | None = None
    base_value: str | None = None
    base_currency_code: str | None = None
    reversed_flag: str | None = None
    security_sid: str | None = None

    # Cash / balance-oriented fields (still sourced only from statement)
    accrued_interest_local: str | None = None
    accrued_interest_base: str | None = None
    accrued_income_local: str | None = None
    accrued_income_base: str | None = None
    asof_date: str | None = None
    cost_local: str | None = None
    cost_base: str | None = None
    coupon: str | None = None
    currency_base: str | None = None
    currency_local: str | None = None
    quantity: str | None = None
    factor: str | None = None
    exchange_rate: str | None = None
    market_value_local: str | None = None
    market_value_base: str | None = None
    maturity_dt: str | None = None
    original_face: str | None = None
    price_local: str | None = None
    price_base: str | None = None
    security_id: str | None = None
    ticker: str | None = None
    original_sec_type: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def to_validation_record(self) -> dict[str, Any]:
        """Shape expected by row validation (SecurityDescription required)."""
        return {
            "SecurityDescription": self.security_description,
            "AccountNumber": self.account_number,
            "AsofDate": self.asof_date or self.trade_date,
            "MarketValueLocal": self.market_value_local,
            "CostLocal": self.cost_local,
        }


def _header_key(header: str) -> str:
    return re.sub(r"[^a-z0-9]", "", (header or "").lower())


def _find_cell(row: dict[str, Any], *needles: str) -> str | None:
    """Find first non-empty cell whose normalized header contains any needle."""
    for header, value in row.items():
        key = _header_key(str(header))
        if any(n in key for n in needles):
            cleaned = _clean(value)
            if cleaned is not None:
                return cleaned
    return None


def _amount_from_row(
    row: dict[str, Any],
    field_mapping: dict[str, str],
) -> tuple[str | None, str | None, str | None]:
    """
    Returns (unsigned_amount, value_sign, signed_market_value_for_cash).
    Prefers explicit debit/credit / debit-credit columns from the source row.
    """
    # Combined debit/credit column (Kotak)
    combined = _find_cell(row, "debitcredit", "debit/credit")
    if combined:
        amount, sign = _parse_signed_amount(combined)
        signed = None
        if amount and sign == "-":
            signed = f"-{amount}"
        elif amount and sign == "+":
            signed = f"+{amount}"
        elif amount:
            signed = amount
        return amount, sign, signed

    withdrawal = _find_cell(row, "withdrawal", "withdraw")
    deposit = _find_cell(row, "deposit")
    # Prefer non-empty side; do not invent the other
    if withdrawal and not deposit:
        amount, sign = _parse_signed_amount(withdrawal)
        if sign is None:
            sign = "-"
        return amount, sign, f"-{amount}" if amount else None
    if deposit and not withdrawal:
        amount, sign = _parse_signed_amount(deposit)
        if sign is None:
            sign = "+"
        signed = None
        if amount:
            signed = amount if amount.startswith(("+", "-")) else f"+{amount}"
        return amount, sign, signed
    if withdrawal and deposit:
        # Both present — keep whichever has a value already chosen by extract (prefer debit if both)
        w_amt, w_sign = _parse_signed_amount(withdrawal)
        d_amt, d_sign = _parse_signed_amount(deposit)
        if w_amt:
            return w_amt, w_sign or "-", f"-{w_amt}"
        if d_amt:
            return d_amt, d_sign or "+", f"+{d_amt}"

    # Fallback via holdings-oriented field_mapping (MarketValueLocal)
    for source, schema in field_mapping.items():
        if schema == "MarketValueLocal" and source in row:
            amount, sign = _parse_signed_amount(row.get(source))
            signed = _clean(row.get(source))
            return amount, sign, signed

    # Generic amount column
    generic = _find_cell(row, "amount")
    if generic:
        amount, sign = _parse_signed_amount(generic)
        return amount, sign, generic

    return None, None, None


def build_canonical_transactions(
    *,
    rows: list[dict[str, Any]],
    field_mapping: dict[str, str] | None = None,
    metadata: dict[str, Any] | None = None,
    mapping_metadata: dict[str, Any] | None = None,
    document_type: str = DOCUMENT_TYPE_BANK_STATEMENT,
) -> list[CanonicalTransaction]:
    """
    Build canonical transactions from extracted statement rows.

    Uses source headers first; field_mapping only as a hint for known schema aliases.
    Never invents financial values — missing fields stay None.
    """
    field_mapping = field_mapping or {}
    metadata = metadata or {}
    mapping_metadata = mapping_metadata or {}

    account_number = _clean(metadata.get("account_number"))
    custodian = _clean(mapping_metadata.get("custodian") or metadata.get("custodian"))
    currency = _clean(mapping_metadata.get("currency") or metadata.get("currency"))
    statement_date = _clean(
        mapping_metadata.get("statement_date") or metadata.get("statement_date")
    )

    # Invert mapping hints: schema field -> source headers
    sources_for: dict[str, list[str]] = {}
    for src, schema in field_mapping.items():
        sources_for.setdefault(schema, []).append(src)

    def mapped_value(row: dict[str, Any], schema_field: str) -> str | None:
        for src in sources_for.get(schema_field, []):
            if src in row:
                return _clean(row.get(src))
        return None

    canonical_rows: list[CanonicalTransaction] = []
    for row in rows:
        trade_date = (
            _find_cell(row, "transactiondate", "txndate", "trandate", "tradedate")
            or mapped_value(row, "AsofDate")
            or _find_cell(row, "date")
        )
        # Prefer explicit value/settlement date; do not copy trade_date if absent
        settlement_date = _find_cell(
            row, "valuedate", "settlementdate", "posteddate", "transactionposted"
        )

        security_description = (
            _find_cell(
                row,
                "transactiondetails",
                "transactionremarks",
                "transactiondescription",
                "narration",
                "particulars",
                "description",
                "merchant",
            )
            or mapped_value(row, "SecurityDescription")
        )

        check_number = (
            _find_cell(row, "chq", "cheque", "refno", "referenceno", "reference")
            or mapped_value(row, "SecurityID")
        )

        balance = _find_cell(row, "balance") or mapped_value(row, "CostLocal")
        amount, value_sign, signed_mv = _amount_from_row(row, field_mapping)

        asof = trade_date or settlement_date or statement_date

        txn = CanonicalTransaction(
            document_type=document_type,
            account_number=account_number,
            custodian=custodian,
            trade_date=trade_date,
            settlement_date=settlement_date,
            amount=amount,
            value_sign=value_sign,
            currency_code=currency,
            currency_local=currency,
            security_description=security_description,
            description=security_description,
            check_number=check_number,
            security_id=check_number,
            unique_transaction_id=check_number,
            asof_date=asof,
            cost_local=balance,
            market_value_local=signed_mv,
        )
        canonical_rows.append(txn)

    logger.info(
        "STEP | Canonical transactions built | count=%s document_type=%s",
        len(canonical_rows),
        document_type,
    )
    return canonical_rows


def canonical_list_to_dicts(rows: list[CanonicalTransaction]) -> list[dict[str, Any]]:
    return [row.to_dict() for row in rows]


def blank_export_row(columns: list[str]) -> dict[str, str]:
    return {c: "" for c in columns}


def canonical_field_names() -> list[str]:
    return [f.name for f in fields(CanonicalTransaction)]
