"""Production-style MySQL connection helpers (PyMySQL)."""

from __future__ import annotations

import logging
from contextlib import contextmanager
from typing import Any, Generator, Iterator

import pymysql
from pymysql.connections import Connection
from pymysql.cursors import DictCursor

from poc.db.settings import get_mysql_settings
from poc.exceptions import ProcessingError

logger = logging.getLogger("holding_engine")


class DatabaseError(ProcessingError):
    code = "DATABASE_ERROR"


def _connect() -> Connection:
    settings = get_mysql_settings()
    try:
        conn = pymysql.connect(
            host=settings.host,
            port=settings.port,
            user=settings.user,
            password=settings.password,
            database=settings.database,
            charset=settings.charset,
            cursorclass=DictCursor,
            autocommit=False,
            connect_timeout=settings.connect_timeout,
            read_timeout=settings.read_timeout,
            write_timeout=settings.write_timeout,
        )
        return conn
    except pymysql.MySQLError as exc:
        logger.exception("MySQL connection failed")
        raise DatabaseError(
            f"Unable to connect to MySQL "
            f"({settings.host}:{settings.port}/{settings.database}): {exc}"
        ) from exc


@contextmanager
def mysql_connection() -> Generator[Connection, None, None]:
    """Yield a connection; commit on success, rollback on error, always close."""
    conn = _connect()
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


@contextmanager
def mysql_cursor() -> Iterator[Any]:
    with mysql_connection() as conn:
        with conn.cursor() as cur:
            yield cur


def ping_database() -> dict[str, Any]:
    """Health check used by API / diagnostics."""
    settings = get_mysql_settings()
    with mysql_cursor() as cur:
        cur.execute("SELECT 1 AS ok, DATABASE() AS db")
        row = cur.fetchone() or {}
    return {
        "ok": True,
        "host": settings.host,
        "port": settings.port,
        "database": row.get("db") or settings.database,
    }
