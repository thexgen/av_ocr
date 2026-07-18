"""
CSV generators — each projects CanonicalTransaction → a fixed column schema.

New document types add generators here; they must only read CanonicalTransaction.
"""

from __future__ import annotations

import csv
import io
from typing import Protocol

from poc.export.canonical import CanonicalTransaction, blank_export_row
from poc.export.schemas import CASH_COLUMNS, TRANSACTION_COLUMNS


def _cell(value: str | None) -> str:
    return "" if value is None else str(value)


class CsvGenerator(Protocol):
    """Pluggable export generator contract for future document types."""

    name: str
    columns: list[str]

    def filename(self, date_stamp: str) -> str: ...

    def row_from_canonical(self, txn: CanonicalTransaction) -> dict[str, str]: ...

    def build_csv(self, transactions: list[CanonicalTransaction]) -> str: ...


class TransactionCsvGenerator:
    """TRANSACTION_YYYYMMDD.csv"""

    name = "transaction"
    columns = TRANSACTION_COLUMNS

    def filename(self, date_stamp: str) -> str:
        return f"TRANSACTION_{date_stamp}.csv"

    def row_from_canonical(self, txn: CanonicalTransaction) -> dict[str, str]:
        out = blank_export_row(self.columns)
        out.update(
            {
                "CustomerID": _cell(txn.customer_id),
                "Custodian": _cell(txn.custodian),
                "AccountNumber": _cell(txn.account_number),
                "TransType": _cell(txn.trans_type),
                "SecurityType": _cell(txn.security_type),
                "Symbol": _cell(txn.symbol),
                "TradeDate": _cell(txn.trade_date),
                "SettlementDate": _cell(txn.settlement_date),
                "Units": _cell(txn.units),
                "Amount": _cell(txn.amount),
                "CurrencyCode": _cell(txn.currency_code),
                "SecurityDescription": _cell(txn.security_description),
                "Description": _cell(txn.description),
                "CheckNumber": _cell(txn.check_number),
                "ValueSign": _cell(txn.value_sign),
                "UniqueTransactionID": _cell(txn.unique_transaction_id),
                "CreateDate": _cell(txn.create_date),
                "UpdateDate": _cell(txn.update_date),
                "DeleteDate": _cell(txn.delete_date),
                "IUD": _cell(txn.iud),
                "OriginalCustodianTransactionType": _cell(
                    txn.original_custodian_transaction_type
                ),
                "ISIN": _cell(txn.isin),
                "Sedol": _cell(txn.sedol),
                "CUSIP": _cell(txn.cusip),
                "TransUser3": _cell(txn.trans_user3),
                "LocalPrice": _cell(txn.local_price),
                "BasePrice": _cell(txn.base_price),
                "BaseValue": _cell(txn.base_value),
                "BaseCurrencyCode": _cell(txn.base_currency_code),
                "ReversedFlag": _cell(txn.reversed_flag),
                "AccountTitle": _cell(txn.account_title),
                "SecuritySID": _cell(txn.security_sid),
            }
        )
        return out

    def build_csv(self, transactions: list[CanonicalTransaction]) -> str:
        return _write_csv(self.columns, [self.row_from_canonical(t) for t in transactions])


class CashCsvGenerator:
    """CASH_YYYYMMDD.csv"""

    name = "cash"
    columns = CASH_COLUMNS

    def filename(self, date_stamp: str) -> str:
        return f"CASH_{date_stamp}.csv"

    def row_from_canonical(self, txn: CanonicalTransaction) -> dict[str, str]:
        out = blank_export_row(self.columns)
        out.update(
            {
                "CustomerID": _cell(txn.customer_id),
                "AccountNumber": _cell(txn.account_number),
                "AccruedInterestLocal": _cell(txn.accrued_interest_local),
                "AccruedInterestBase": _cell(txn.accrued_interest_base),
                "AccruedIncomeLocal": _cell(txn.accrued_income_local),
                "AccruedIncomeBase": _cell(txn.accrued_income_base),
                "AsofDate": _cell(txn.asof_date or txn.trade_date),
                "CostLocal": _cell(txn.cost_local),
                "CostBase": _cell(txn.cost_base),
                "Coupon": _cell(txn.coupon),
                "CurrencyBase": _cell(txn.currency_base),
                "CurrencyLocal": _cell(txn.currency_local or txn.currency_code),
                "Quantity": _cell(txn.quantity),
                "CUSIP": _cell(txn.cusip),
                "Factor": _cell(txn.factor),
                "ExchangeRate": _cell(txn.exchange_rate),
                "ISIN": _cell(txn.isin),
                "MarketValueLocal": _cell(txn.market_value_local),
                "MarketValueBase": _cell(txn.market_value_base),
                "MaturityDT": _cell(txn.maturity_dt),
                "OriginalFace": _cell(txn.original_face),
                "PriceLocal": _cell(txn.price_local or txn.local_price),
                "PriceBase": _cell(txn.price_base or txn.base_price),
                "SecurityDescription": _cell(txn.security_description),
                "SecurityID": _cell(txn.security_id or txn.check_number),
                "SecurityType": _cell(txn.security_type),
                "SEDOL": _cell(txn.sedol),
                "Ticker": _cell(txn.ticker or txn.symbol),
                "OriginalSecType": _cell(txn.original_sec_type),
                "Custodian": _cell(txn.custodian),
                "CreateDate": _cell(txn.create_date),
                "UpdateDate": _cell(txn.update_date),
                "DeleteDate": _cell(txn.delete_date),
                "IUD": _cell(txn.iud),
                "AccountTitle": _cell(txn.account_title),
            }
        )
        return out

    def build_csv(self, transactions: list[CanonicalTransaction]) -> str:
        return _write_csv(self.columns, [self.row_from_canonical(t) for t in transactions])


def _write_csv(columns: list[str], rows: list[dict[str, str]]) -> str:
    buf = io.StringIO()
    writer = csv.DictWriter(
        buf,
        fieldnames=columns,
        extrasaction="ignore",
        lineterminator="\n",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in columns})
    return buf.getvalue()


def default_bank_statement_generators() -> list[CsvGenerator]:
    """Generators used for Bank Statement document type."""
    return [TransactionCsvGenerator(), CashCsvGenerator()]
