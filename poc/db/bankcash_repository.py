"""CRUD helpers for bankcashtemp staging table."""

from __future__ import annotations

import logging
from typing import Any

from poc.db.connection import DatabaseError, mysql_connection
from poc.db.settings import TXN_TYPE_LABELS, get_staging_defaults
from poc.db.temp_mapper import validate_and_build_temp_row
from poc.export.canonical import CanonicalTransaction

logger = logging.getLogger("holding_engine")

_INSERT_COLUMNS = [
    "uploadbatchid",
    "jobid",
    "rowno",
    "entityid",
    "accountid",
    "transactiontypeid",
    "transactiondate",
    "payeepayorid",
    "ledgerid",
    "amount",
    "description",
    "instrumentno",
    "positionid",
    "positiontagid",
    "accountrecon",
    "voucher",
    "statusid",
    "oldstatusid",
    "comments",
    "usercomments",
    "filename",
    "feedtransactionid",
    "syncdescription",
    "userid",
    "oldid",
    "ismultidistributed",
    "checkno",
    "memo",
    "checkbookid",
    "voidtransactiondate",
    "createdby",
    "updatedby",
    "txnfxrate",
    "payeeid",
    "consider_return_computation",
    "feedid",
    "billdotcomdoc",
    "txncustomfxcurrency",
    "iserror",
    "errordesc",
]


def insert_canonical_into_temp(
    *,
    job_id: str,
    transactions: list[CanonicalTransaction],
    filename: str | None,
) -> dict[str, Any]:
    """
    Replace any prior staging rows for this job, then insert all transactions.
    Returns insert summary (total / error / clean counts).
    """
    if not transactions:
        logger.warning("No canonical transactions to stage for job %s", job_id)
        return {
            "job_id": job_id,
            "inserted": 0,
            "error_rows": 0,
            "clean_rows": 0,
        }

    rows: list[dict[str, Any]] = []
    for idx, txn in enumerate(transactions, start=1):
        rows.append(
            validate_and_build_temp_row(
                txn,
                job_id=job_id,
                rowno=idx,
                filename=filename,
            )
        )

    placeholders = ", ".join([f"%({c})s" for c in _INSERT_COLUMNS])
    col_sql = ", ".join(f"`{c}`" for c in _INSERT_COLUMNS)
    insert_sql = f"INSERT INTO `bankcashtemp` ({col_sql}) VALUES ({placeholders})"

    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM `bankcashtemp` WHERE `jobid` = %s", (job_id,))
                deleted = cur.rowcount
                if deleted:
                    logger.info(
                        "Cleared %s prior bankcashtemp row(s) for job %s",
                        deleted,
                        job_id,
                    )

                payload = [{k: row.get(k) for k in _INSERT_COLUMNS} for row in rows]
                cur.executemany(insert_sql, payload)
    except DatabaseError:
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed inserting into bankcashtemp | job=%s", job_id)
        raise DatabaseError(
            f"Failed to save transactions to bankcashtemp for job {job_id}: {exc}"
        ) from exc

    error_rows = sum(1 for r in rows if int(r.get("iserror") or 0) == 1)
    clean_rows = len(rows) - error_rows
    logger.info(
        "Staged bankcashtemp | job=%s inserted=%s clean=%s error=%s",
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
        "entity_id": get_staging_defaults().entity_id,
        "entity_name": get_staging_defaults().entity_name,
    }


def fetch_temp_transactions_by_job(job_id: str) -> list[dict[str, Any]]:
    """Fetch staged rows for review UI / API."""
    defaults = get_staging_defaults()
    sql = """
        SELECT
            id, uploadbatchid, jobid, rowno, entityid, accountid,
            transactiontypeid, transactiondate, amount, description,
            instrumentno, checkno, filename, feedtransactionid,
            syncdescription, userid, memo, txncustomfxcurrency,
            iserror, errordesc, created, updated
        FROM `bankcashtemp`
        WHERE `jobid` = %s
        ORDER BY `rowno` ASC, `id` ASC
    """
    try:
        with mysql_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (job_id,))
                raw_rows = list(cur.fetchall() or [])
    except DatabaseError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DatabaseError(
            f"Failed to load bankcashtemp rows for job {job_id}: {exc}"
        ) from exc

    out: list[dict[str, Any]] = []
    for row in raw_rows:
        type_id = row.get("transactiontypeid")
        type_label = (
            row.get("syncdescription")
            or TXN_TYPE_LABELS.get(int(type_id) if type_id is not None else -1)
            or ""
        )
        is_error = int(row.get("iserror") or 0) == 1
        errordesc = (row.get("errordesc") or "").strip()
        errors = [e.strip() for e in errordesc.split(",") if e.strip()] if is_error else []

        amount = row.get("amount")
        amount_f = float(amount) if amount is not None else 0.0
        txn_date = row.get("transactiondate")
        trade_date = (
            txn_date.isoformat()
            if hasattr(txn_date, "isoformat")
            else (str(txn_date) if txn_date else "")
        )

        status = "missing_data" if is_error else "valid"
        confidence = 55.0 if is_error else 92.0

        out.append(
            {
                "id": str(row.get("id")),
                "rowno": row.get("rowno"),
                "job_id": row.get("jobid"),
                "entity_id": row.get("entityid") or defaults.entity_id,
                "entity_name": defaults.entity_name,
                "user_id": row.get("userid") or defaults.user_id,
                "tradeDate": trade_date,
                "type": type_label or "Unknown",
                "security": row.get("description") or "",
                "quantity": None,
                "price": None,
                "amount": amount_f,
                "status": status,
                "confidence": confidence,
                "originalText": row.get("description") or "",
                "normalizedJson": {
                    "id": row.get("id"),
                    "transactiondate": trade_date,
                    "transactiontypeid": type_id,
                    "amount": str(amount) if amount is not None else None,
                    "description": row.get("description"),
                    "checkno": row.get("checkno"),
                    "instrumentno": row.get("instrumentno"),
                    "filename": row.get("filename"),
                    "iserror": is_error,
                    "errordesc": errordesc or None,
                },
                "validationErrors": errors,
                "aiReasoning": (
                    f"Staged to bankcashtemp with errors: {errordesc}"
                    if is_error
                    else "Staged to bankcashtemp with mandatory fields present."
                ),
                "iserror": is_error,
                "errordesc": errordesc or None,
                "filename": row.get("filename"),
                "checkno": row.get("checkno"),
            }
        )
    return out
