"""Staging + permanent CRUD for Fixed Income and Direct Equity."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.db.connection import DatabaseError, mysql_connection
from backend.db.settings import get_staging_defaults

logger = logging.getLogger("holding_engine")

_VEHICLE_TEMP_TABLE = {
    "fixed-income": "fixedincometemp",
    "direct-equity": "directequitytemp",
}

_VEHICLE_MAIN_TABLE = {
    "fixed-income": "fixedincome",
    "direct-equity": "directequity",
}

_TEMP_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  `id` int NOT NULL AUTO_INCREMENT,
  `jobid` varchar(64) DEFAULT NULL,
  `entityid` int DEFAULT NULL,
  `accountid` int DEFAULT NULL,
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

_MAIN_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS `{table}` (
  `id` int NOT NULL AUTO_INCREMENT,
  `entityid` int DEFAULT NULL,
  `accountid` int DEFAULT NULL,
  `transactiondate` date DEFAULT NULL,
  `txnqualifier` varchar(100) DEFAULT NULL,
  `syncdescription` varchar(500) DEFAULT NULL,
  `isin` varchar(64) DEFAULT NULL,
  `security_name` varchar(255) DEFAULT NULL,
  `units` decimal(20,6) DEFAULT NULL,
  `price` decimal(20,6) DEFAULT NULL,
  `amount` decimal(20,6) DEFAULT NULL,
  `filename` varchar(255) DEFAULT NULL,
  `created` datetime DEFAULT NULL,
  `updated` datetime DEFAULT NULL,
  `createdby` int DEFAULT NULL,
  `updatedby` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  KEY `idx_{table}_entity` (`entityid`),
  KEY `idx_{table}_account` (`accountid`),
  KEY `idx_{table}_date` (`transactiondate`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
"""

_MAIN_INSERT_COLUMNS = [
    "entityid",
    "accountid",
    "transactiondate",
    "txnqualifier",
    "syncdescription",
    "isin",
    "security_name",
    "units",
    "price",
    "amount",
    "filename",
    "created",
    "updated",
    "createdby",
    "updatedby",
]


def ensure_vehicle_staging_tables() -> None:
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                for table in _VEHICLE_TEMP_TABLE.values():
                    cur.execute(_TEMP_CREATE_SQL.format(table=table))
                    _ensure_column(cur, table, "accountid", "int DEFAULT NULL AFTER `entityid`")
                for table in _VEHICLE_MAIN_TABLE.values():
                    cur.execute(_MAIN_CREATE_SQL.format(table=table))
        logger.info("Ensured FI/DE temp + permanent tables")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ensure_vehicle_staging_tables skipped: %s", exc)


def _ensure_column(cur: Any, table: str, column: str, ddl_tail: str) -> None:
    cur.execute(
        """
        SELECT COUNT(*) AS cnt
        FROM information_schema.COLUMNS
        WHERE TABLE_SCHEMA = DATABASE()
          AND TABLE_NAME = %s
          AND COLUMN_NAME = %s
        """,
        (table, column),
    )
    row = cur.fetchone() or {}
    if int(row.get("cnt") or 0) == 0:
        cur.execute(f"ALTER TABLE `{table}` ADD COLUMN `{column}` {ddl_tail}")
        logger.info("Added %s.%s", table, column)


def _temp_table(vehicle: str) -> str:
    table = _VEHICLE_TEMP_TABLE.get(vehicle)
    if not table:
        raise ValueError(f"Unsupported vehicle for staging: {vehicle}")
    return table


def _main_table(vehicle: str) -> str:
    table = _VEHICLE_MAIN_TABLE.get(vehicle)
    if not table:
        raise ValueError(f"Unsupported vehicle for ledger: {vehicle}")
    return table


def insert_vehicle_rows(
    *,
    vehicle: str,
    job_id: str,
    rows: list[dict[str, Any]],
    filename: str | None,
) -> dict[str, Any]:
    ensure_vehicle_staging_tables()
    table = _temp_table(vehicle)
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
                "entityid": defaults.entity_id,
                "accountid": defaults.account_id,
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
        "accountid",
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
    table = _temp_table(vehicle)
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                if job_id:
                    cur.execute(
                        f"""
                        SELECT id, jobid, entityid, accountid, transactiondate, txnqualifier,
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
                        SELECT id, jobid, entityid, accountid, transactiondate, txnqualifier,
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


def _normalize_ids(ids: list[int | str]) -> list[int]:
    out: list[int] = []
    for raw in ids:
        try:
            out.append(int(raw))
        except (TypeError, ValueError):
            continue
    return out


def delete_vehicle_temp_rows(
    *,
    vehicle: str,
    job_id: str,
    ids: list[int | str],
) -> dict[str, Any]:
    ensure_vehicle_staging_tables()
    table = _temp_table(vehicle)
    id_list = _normalize_ids(ids)
    if not id_list:
        return {"job_id": job_id, "deleted": 0}
    placeholders = ", ".join(["%s"] * len(id_list))
    sql = f"DELETE FROM `{table}` WHERE `jobid` = %s AND `id` IN ({placeholders})"
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (job_id, *id_list))
                deleted = cur.rowcount
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(
            f"Failed to delete {table} rows for job {job_id}: {exc}"
        ) from exc
    return {"job_id": job_id, "deleted": deleted}


def process_vehicle_temp_rows(
    *,
    vehicle: str,
    job_id: str,
    ids: list[int | str],
) -> dict[str, Any]:
    """Post clean selected rows from temp → permanent vehicle table."""
    ensure_vehicle_staging_tables()
    temp = _temp_table(vehicle)
    main = _main_table(vehicle)
    id_list = _normalize_ids(ids)
    if not id_list:
        return {
            "job_id": job_id,
            "requested": 0,
            "processed": 0,
            "skipped_errors": 0,
            "deleted_from_temp": 0,
        }

    defaults = get_staging_defaults()
    placeholders = ", ".join(["%s"] * len(id_list))
    select_sql = f"""
        SELECT * FROM `{temp}`
        WHERE `jobid` = %s AND `id` IN ({placeholders})
    """
    insert_placeholders = ", ".join([f"%({c})s" for c in _MAIN_INSERT_COLUMNS])
    col_sql = ", ".join(f"`{c}`" for c in _MAIN_INSERT_COLUMNS)
    insert_sql = f"INSERT INTO `{main}` ({col_sql}) VALUES ({insert_placeholders})"

    clean: list[dict[str, Any]] = []
    skipped = 0
    deleted = 0

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(select_sql, (job_id, *id_list))
                rows = list(cur.fetchall() or [])
                clean = [r for r in rows if int(r.get("iserror") or 0) == 0]
                skipped = len(rows) - len(clean)

                if clean:
                    now = datetime.now().replace(microsecond=0)
                    payload = []
                    for row in clean:
                        item = {c: row.get(c) for c in _MAIN_INSERT_COLUMNS}
                        item["entityid"] = defaults.entity_id
                        item["accountid"] = defaults.account_id
                        item["created"] = item.get("created") or now
                        item["updated"] = now
                        payload.append(item)
                    cur.executemany(insert_sql, payload)
                    clean_ids = [int(r["id"]) for r in clean]
                    del_ph = ", ".join(["%s"] * len(clean_ids))
                    cur.execute(
                        f"DELETE FROM `{temp}` WHERE `jobid` = %s AND `id` IN ({del_ph})",
                        (job_id, *clean_ids),
                    )
                    deleted = cur.rowcount
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(
            f"Failed to process {temp} → {main} for job {job_id}: {exc}"
        ) from exc

    return {
        "job_id": job_id,
        "requested": len(id_list),
        "processed": len(clean),
        "skipped_errors": skipped,
        "deleted_from_temp": deleted,
    }


def fetch_vehicle_ledger(
    vehicle: str,
    *,
    entity_id: int | None = None,
    account_id: int | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 1000,
) -> list[dict[str, Any]]:
    ensure_vehicle_staging_tables()
    table = _main_table(vehicle)
    clauses: list[str] = []
    params: list[Any] = []
    if entity_id is not None:
        clauses.append("`entityid` = %s")
        params.append(entity_id)
    if account_id is not None:
        clauses.append("`accountid` = %s")
        params.append(account_id)
    if from_date:
        clauses.append("`transactiondate` >= %s")
        params.append(from_date)
    if to_date:
        clauses.append("`transactiondate` <= %s")
        params.append(to_date)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT id, entityid, accountid, transactiondate, txnqualifier,
               syncdescription, isin, security_name, units, price, amount, filename
        FROM `{table}`
        {where}
        ORDER BY `transactiondate` DESC, `id` DESC
        LIMIT %s
    """
    params.append(max(1, min(int(limit), 5000)))
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, tuple(params))
                return list(cur.fetchall() or [])
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(f"Failed to load {table} ledger: {exc}") from exc


def dec(value: Decimal | None) -> Decimal | None:
    return value
