"""
Modular export framework.

Flow:
  extracted rows → CanonicalTransaction list → canonical_transactions.json
                                         ↘ TRANSACTION_YYYYMMDD.csv
                                         ↘ CASH_YYYYMMDD.csv

Future document types register their own Canonical builders / CSV generators
without changing OCR or extraction.
"""

from poc.export.canonical import CanonicalTransaction, build_canonical_transactions
from poc.export.generators import CashCsvGenerator, TransactionCsvGenerator
from poc.export.persist import persist_canonical_and_csvs
from poc.export.schemas import (
    CASH_COLUMNS,
    DOCUMENT_TYPE_BANK_STATEMENT,
    TRANSACTION_COLUMNS,
)

__all__ = [
    "CASH_COLUMNS",
    "TRANSACTION_COLUMNS",
    "DOCUMENT_TYPE_BANK_STATEMENT",
    "CanonicalTransaction",
    "CashCsvGenerator",
    "TransactionCsvGenerator",
    "build_canonical_transactions",
    "persist_canonical_and_csvs",
]
