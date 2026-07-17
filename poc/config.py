from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

POC_ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = POC_ROOT.parent
CONFIG_PATH = POC_ROOT / "config.yaml"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(POC_ROOT / ".env")

# Kept for schema / alias stability (not runtime knobs)
STANDARD_SCHEMA = [
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
    "Custodian",
    "AccountTitle",
]

# Deprecated: aliases now live in mapping_dictionary.json (+ learned file).
# Kept only so older imports do not break; mapping_engine does not use this.
FIELD_ALIASES: dict[str, str] = {}


def _deep_get(data: dict[str, Any], *keys: str, default: Any = None) -> Any:
    cur: Any = data
    for key in keys:
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


@lru_cache(maxsize=1)
def load_config() -> dict[str, Any]:
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"Missing config.yaml at {CONFIG_PATH}")
    with CONFIG_PATH.open("r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        raise ValueError("config.yaml must be a mapping")
    return data


def get_config() -> dict[str, Any]:
    return load_config()


def reload_config() -> dict[str, Any]:
    load_config.cache_clear()
    return load_config()


# --- Convenience accessors (env can override secrets / toggles) ---

def cfg(*keys: str, default: Any = None) -> Any:
    return _deep_get(get_config(), *keys, default=default)


SAMPLE_DATA_PREFIX: str = str(cfg("storage", "sample_data_prefix", default="sample_data"))
OUTPUT_PREFIX: str = str(cfg("storage", "output_prefix", default="output"))
JOBS_PREFIX: str = str(cfg("storage", "jobs_prefix", default="jobs"))
UPLOADS_PREFIX: str = str(cfg("storage", "uploads_prefix", default="sample_data/uploads"))

TEXT_PDF_CHAR_THRESHOLD: int = int(
    os.getenv("TEXT_PDF_CHAR_THRESHOLD")
    or cfg("processing", "text_pdf_char_threshold", default=40)
)

QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL") or str(
    cfg("qwen", "base_url", default="https://dashscope-intl.aliyuncs.com/compatible-mode/v1")
)
QWEN_MODEL: str = os.getenv("QWEN_MODEL") or str(cfg("qwen", "model", default="qwen-plus"))

ALLOW_LOCAL_MAPPER_FALLBACK: bool = (
    os.getenv("ALLOW_LOCAL_MAPPER_FALLBACK")
    or str(cfg("processing", "allow_local_mapper_fallback", default=True))
).lower() in {"1", "true", "yes"}

LOGGER_NAME: str = str(cfg("logging", "logger_name", default="holding_engine"))
