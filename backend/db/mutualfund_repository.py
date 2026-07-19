"""CRUD helpers for mutualfundtemp staging."""

from __future__ import annotations

import logging
from datetime import datetime
from decimal import Decimal
from typing import Any

from backend.db.connection import DatabaseError, mysql_connection
from backend.db.settings import get_staging_defaults
from backend.vehicle.mf_excel import MfParsedRow

logger = logging.getLogger("holding_engine")

_INSERT_COLUMNS = [
    "jobid",
    "entityid",
    "transactiondate",
    "txnid",
    "transactiontypeid",
    "syncdescription",
    "units",
    "navperunit",
    "amount",
    "divperunit",
    "brokerage",
    "sttcharges",
    "servicetax",
    "transactioncharges",
    "stampduty",
    "othercharges",
    "tdsamount",
    "grossamount",
    "comments",
    "filename",
    "transfer",
    "transferdate",
    "transferunits",
    "transfernavperunit",
    "transfernetamount",
    "txnqualifier",
    "voucher",
    "created",
    "updated",
    "createdby",
    "updatedby",
    "iserror",
    "errordesc",
]


def ensure_mutualfundtemp_columns() -> None:
    """Add jobid if the staging table predates job-scoped imports."""
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COUNT(*) AS cnt
                    FROM information_schema.COLUMNS
                    WHERE TABLE_SCHEMA = DATABASE()
                      AND TABLE_NAME = 'mutualfundtemp'
                      AND COLUMN_NAME = 'jobid'
                    """
                )
                row = cur.fetchone() or {}
                if int(row.get("cnt") or 0) == 0:
                    cur.execute(
                        "ALTER TABLE `mutualfundtemp` "
                        "ADD COLUMN `jobid` varchar(64) NULL AFTER `id`, "
                        "ADD INDEX `idx_mutualfundtemp_jobid` (`jobid`)"
                    )
                    logger.info("Added mutualfundtemp.jobid column")
    except Exception as exc:  # noqa: BLE001
        logger.warning("ensure_mutualfundtemp_columns skipped: %s", exc)


def _dec(value: Decimal | None) -> Decimal | None:
    return value


def _build_row(
    parsed: MfParsedRow,
    *,
    job_id: str,
    filename: str | None,
) -> dict[str, Any]:
    defaults = get_staging_defaults()
    now = datetime.now().replace(microsecond=0)
    scheme = parsed.scheme_name or parsed.mf_name or ""
    folio = parsed.folio_number or parsed.isin or ""
    sync = " | ".join(p for p in [scheme, folio, parsed.transaction_type] if p)

    return {
        "jobid": job_id,
        "entityid": parsed.entity_id or defaults.entity_id,
        "transactiondate": parsed.trade_date,
        "txnid": parsed.transaction_id,
        "transactiontypeid": None,
        "syncdescription": sync[:500] if sync else None,
        "units": _dec(parsed.units),
        "navperunit": _dec(parsed.price),
        "amount": _dec(parsed.amount),
        "divperunit": _dec(parsed.dividend_rate),
        "brokerage": _dec(parsed.brokerage),
        "sttcharges": _dec(parsed.stt_charges),
        "servicetax": _dec(parsed.service_tax),
        "transactioncharges": _dec(parsed.transaction_charges),
        "stampduty": _dec(parsed.stamp_duty),
        "othercharges": _dec(parsed.other_charges),
        "tdsamount": _dec(parsed.tds),
        "grossamount": _dec(parsed.amount),
        "comments": parsed.notes,
        "filename": (filename or "")[:255] or None,
        "transfer": 1 if parsed.transfer_date or parsed.transfer_amount else 0,
        "transferdate": parsed.transfer_date,
        "transferunits": None,
        "transfernavperunit": _dec(parsed.transfer_price),
        "transfernetamount": _dec(parsed.transfer_amount),
        "txnqualifier": parsed.transaction_qualifier or parsed.transaction_type,
        "voucher": folio[:100] if folio else None,
        "created": now,
        "updated": now,
        "createdby": defaults.user_id,
        "updatedby": defaults.user_id,
        "iserror": int(parsed.iserror or 0),
        "errordesc": parsed.errordesc,
    }


def insert_mf_rows_into_temp(
    *,
    job_id: str,
    rows: list[MfParsedRow],
    filename: str | None,
) -> dict[str, Any]:
    """Replace prior staging rows for this job, then insert parsed MF rows."""
    ensure_mutualfundtemp_columns()

    if not rows:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `mutualfundtemp` WHERE `jobid` = %s", (job_id,))
        return {
            "job_id": job_id,
            "inserted": 0,
            "error_rows": 0,
            "clean_rows": 0,
        }

    payload = [_build_row(r, job_id=job_id, filename=filename) for r in rows]
    placeholders = ", ".join([f"%({c})s" for c in _INSERT_COLUMNS])
    col_sql = ", ".join(f"`{c}`" for c in _INSERT_COLUMNS)
    insert_sql = f"INSERT INTO `mutualfundtemp` ({col_sql}) VALUES ({placeholders})"

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `mutualfundtemp` WHERE `jobid` = %s", (job_id,))
                cur.executemany(insert_sql, payload)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed inserting into mutualfundtemp | job=%s", job_id)
        raise DatabaseError(
            f"Failed to save mutual fund rows to mutualfundtemp for job {job_id}: {exc}"
        ) from exc

    error_rows = sum(1 for r in rows if r.iserror)
    clean_rows = len(rows) - error_rows
    logger.info(
        "Staged mutualfundtemp | job=%s inserted=%s clean=%s error=%s",
        job_id,
        len(rows),
        clean_rows,
        error_rows,
    )
    return {
        "job_id": job_id,
        "inserted": len(rows),
        "error_rows": error_rows,
        "clean_rows": clean_rows,
    }


def fetch_mf_temp_by_job(job_id: str) -> list[dict[str, Any]]:
    ensure_mutualfundtemp_columns()
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, jobid, entityid, transactiondate, txnqualifier,
                           syncdescription, units, navperunit, amount, voucher,
                           filename, iserror, errordesc, created
                    FROM `mutualfundtemp`
                    WHERE `jobid` = %s
                    ORDER BY `id` ASC
                    """,
                    (job_id,),
                )
                return list(cur.fetchall() or [])
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(
            f"Failed to load mutualfundtemp rows for job {job_id}: {exc}"
        ) from exc


def fetch_recent_mf_temp(limit: int = 200) -> list[dict[str, Any]]:
    """Recent staged MF rows (for ledger preview)."""
    ensure_mutualfundtemp_columns()
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, jobid, entityid, transactiondate, txnqualifier,
                           syncdescription, units, navperunit, amount, voucher,
                           filename, iserror, errordesc, created
                    FROM `mutualfundtemp`
                    ORDER BY `id` DESC
                    LIMIT %s
                    """,
                    (limit,),
                )
                return list(cur.fetchall() or [])
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(f"Failed to load mutualfundtemp rows: {exc}") from exc
