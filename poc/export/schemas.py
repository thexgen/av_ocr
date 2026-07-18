"""
Export column schemas for bank-statement (and future document-type) CSV outputs.

Generators read only from CanonicalTransaction and project into these schemas.
Unavailable fields stay blank — never invent financial values.
"""

from __future__ import annotations

DOCUMENT_TYPE_BANK_STATEMENT = "Bank Statement"
DOCUMENT_TYPE_HOLDINGS = "Holdings"
DOCUMENT_TYPE_CONTRACT_NOTE = "Contract Note"
DOCUMENT_TYPE_CAS = "CAS"

TRANSACTION_COLUMNS: list[str] = [
    "CustomerID",
    "Custodian",
    "AccountNumber",
    "TransType",
    "SecurityType",
    "Symbol",
    "TradeDate",
    "SettlementDate",
    "Units",
    "Amount",
    "CurrencyCode",
    "SecurityDescription",
    "Description",
    "CheckNumber",
    "ValueSign",
    "UniqueTransactionID",
    "CreateDate",
    "UpdateDate",
    "DeleteDate",
    "IUD",
    "OriginalCustodianTransactionType",
    "ISIN",
    "Sedol",
    "CUSIP",
    "TransUser3",
    "LocalPrice",
    "BasePrice",
    "BaseValue",
    "BaseCurrencyCode",
    "ReversedFlag",
    "AccountTitle",
    "SecuritySID",
]

CASH_COLUMNS: list[str] = [
    "CustomerID",
    "AccountNumber",
    "AccruedInterestLocal",
    "AccruedInterestBase",
    "AccruedIncomeLocal",
    "AccruedIncomeBase",
    "AsofDate",
    "CostLocal",
    "CostBase",
    "Coupon",
    "CurrencyBase",
    "CurrencyLocal",
    "Quantity",
    "CUSIP",
    "Factor",
    "ExchangeRate",
    "ISIN",
    "MarketValueLocal",
    "MarketValueBase",
    "MaturityDT",
    "OriginalFace",
    "PriceLocal",
    "PriceBase",
    "SecurityDescription",
    "SecurityID",
    "SecurityType",
    "SEDOL",
    "Ticker",
    "OriginalSecType",
    "Custodian",
    "CreateDate",
    "UpdateDate",
    "DeleteDate",
    "IUD",
    "AccountTitle",
]
