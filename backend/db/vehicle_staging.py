"""Staging tables + CRUD for Fixed Income and Direct Equity temp rows."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.db.connection import DatabaseError, mysql_connection
from backend.db.settings import get_staging_defaults

logger = logging.getLogger("holding_engine")

_VEHICLE_TABLE = {
    "fixed-income": "fixedincometemp",
    "direct-equity": "directequitytemp",
}

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  `id` int NOT NULL AUTO_INCREMENT,
  `jobid` varchar(64) DEFAULT NULL,
  `entityid` int DEFAULT NULL,
  `transactiondate` date DEFAULT NULL,
  `txnqualifier` varchar(100) DEFAULT NULL,
  `syncdescription` varchar(500) DEFAULT NULL,
  `isin` varchar(64) DEFAULT NULL,
  `security_name` varchar(255) DEFAULT NULL,
  `units` decimal(20,6) DEFAULT NULL,
  `price` decimal(20,6) DEFAULT NULL,
  `amount` decimal(20,6) DEFAULT NULL,
  `filename` varchar(255) DEFAULT NULL,
  `iserror` tinyint(1) NOT NULL DEFAULT 0,
  `errordesc` text,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `createdby` int DEFAULT NULL,
  `updatedby` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_{table}_jobid` (`jobid`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""


def ensure_vehicle_staging_tables() -> None:
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                for table in _VEHICLE_TABLE.values():
                    cur.execute(_CREATE_SQL.format(table=table))
        logger.info("Ensured fixedincometemp / directequitytemp tables")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ensure_vehicle_staging_tables skipped: %s", exc)


def _table(vehicle: str) -> str:
    table = _VEHICLE_TABLE.get(vehicle)
    if not table:
        raise ValueError(f"Unsupported vehicle for staging: {vehicle}")
    return table


def insert_vehicle_rows(
    *,
    vehicle: str,
    job_id: str,
    rows: list[dict[str, Any]],
    filename: str | None,
) -> dict[str, Any]:
    ensure_vehicle_staging_tables()
    table = _table(vehicle)
    defaults = get_staging_defaults()
    now = datetime.now().replace(microsecond=0)

    if not rows:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM `{table}` WHERE `jobid` = %s", (job_id,))
        return {"job_id": job_id, "inserted": 0, "error_rows": 0, "clean_rows": 0}

    payload = []
    for row in rows:
        payload.append(
            {
                "jobid": job_id,
                "entityid": row.get("entity_id") or defaults.entity_id,
                "transactiondate": row.get("trade_date"),
                "txnqualifier": row.get("transaction_type"),
                "syncdescription": row.get("syncdescription"),
                "isin": row.get("isin"),
                "security_name": row.get("security_name"),
                "units": row.get("units"),
                "price": row.get("price"),
                "amount": row.get("amount"),
                "filename": (filename or "")[:255] or None,
                "iserror": int(row.get("iserror") or 0),
                "errordesc": row.get("errordesc"),
                "created": now,
                "updated": now,
                "createdby": defaults.user_id,
                "updatedby": defaults.user_id,
            }
        )

    cols = [
        "jobid",
        "entityid",
        "transactiondate",
        "txnqualifier",
        "syncdescription",
        "isin",
        "security_name",
        "units",
        "price",
        "amount",
        "filename",
        "iserror",
        "errordesc",
        "created",
        "updated",
        "createdby",
        "updatedby",
    ]
    placeholders = ", ".join([f"%({c})s" for c in cols])
    col_sql = ", ".join(f"`{c}`" for c in cols)
    sql = f"INSERT INTO `{table}` ({col_sql}) VALUES ({placeholders})"

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(f"DELETE FROM `{table}` WHERE `jobid` = %s", (job_id,))
                cur.executemany(sql, payload)
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(
            f"Failed to stage {vehicle} rows for job {job_id}: {exc}"
        ) from exc

    error_rows = sum(1 for r in rows if r.get("iserror"))
    return {
        "job_id": job_id,
        "inserted": len(rows),
        "error_rows": error_rows,
        "clean_rows": len(rows) - error_rows,
    }


def fetch_vehicle_temp(
    vehicle: str,
    *,
    job_id: str | None = None,
    limit: int = 200,
) -> list[dict[str, Any]]:
    ensure_vehicle_staging_tables()
    table = _table(vehicle)
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                if job_id:
                    cur.execute(
                        f"""
                        SELECT id, jobid, entityid, transactiondate, txnqualifier,
                               syncdescription, isin, security_name, units, price,
                               amount, filename, iserror, errordesc, created
                        FROM `{table}`
                        WHERE jobid = %s
                        ORDER BY id ASC
                        """,
                        (job_id,),
                    )
                else:
                    cur.execute(
                        f"""
                        SELECT id, jobid, entityid, transactiondate, txnqualifier,
                               syncdescription, isin, security_name, units, price,
                               amount, filename, iserror, errordesc, created
                        FROM `{table}`
                        ORDER BY id DESC
                        LIMIT %s
                        """,
                        (limit,),
                    )
                return list(cur.fetchall() or [])
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(f"Failed to load {table}: {exc}") from exc


def dec(value: Decimal | None) -> Decimal | None:
    return value
