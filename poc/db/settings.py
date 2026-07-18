"""MySQL + staging defaults loaded from environment."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv

from poc.config import POC_ROOT, PROJECT_ROOT

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(POC_ROOT / ".env")


@dataclass(frozen=True)
class MySQLSettings:
    host: str
    port: int
    user: str
    password: str
    database: str
    charset: str
    connect_timeout: int
    read_timeout: int
    write_timeout: int


@dataclass(frozen=True)
class StagingDefaults:
    entity_id: int
    entity_name: str
    user_id: int


def get_mysql_settings() -> MySQLSettings:
    return MySQLSettings(
        host=os.getenv("MYSQL_HOST", "127.0.0.1").strip(),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "root").strip(),
        password=os.getenv("MYSQL_PASSWORD", ""),
        database=os.getenv("MYSQL_DATABASE", "avfamily").strip(),
        charset=os.getenv("MYSQL_CHARSET", "utf8mb4").strip(),
        connect_timeout=int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10")),
        read_timeout=int(os.getenv("MYSQL_READ_TIMEOUT", "30")),
        write_timeout=int(os.getenv("MYSQL_WRITE_TIMEOUT", "30")),
    )


def get_staging_defaults() -> StagingDefaults:
    return StagingDefaults(
        entity_id=int(os.getenv("DEFAULT_ENTITY_ID", "1")),
        entity_name=os.getenv("DEFAULT_ENTITY_NAME", "Krishna Deval").strip()
        or "Krishna Deval",
        user_id=int(os.getenv("DEFAULT_USER_ID", "1")),
    )


# Transaction type ids used until a real lookup table exists
TXN_TYPE_CREDIT = 1
TXN_TYPE_DEBIT = 2
TXN_TYPE_LABELS = {
    TXN_TYPE_CREDIT: "Credit",
    TXN_TYPE_DEBIT: "Debit",
}
