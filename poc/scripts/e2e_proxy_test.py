"""E2E: upload + poll + download through Vite proxy -> FastAPI."""
from __future__ import annotations

import json
import time
import urllib.error
import urllib.request
from pathlib import Path

PROXY = "http://127.0.0.1:5173/api"
PDF = Path("poc/sample_data/sample_holding_statement.pdf")


def main() -> None:
    health = urllib.request.urlopen(f"{PROXY}/health").read().decode()
    print("HEALTH_PROXY", health)

    pdf = PDF.read_bytes()
    boundary = "----BoundaryHoldingE2E"
    parts = []
    parts.append(f"--{boundary}".encode())
    parts.append(
        b'Content-Disposition: form-data; name="file"; filename="sample_holding_statement.pdf"'
    )
    parts.append(b"Content-Type: application/pdf")
    parts.append(b"")
    parts.append(pdf)
    parts.append(f"--{boundary}--".encode())
    parts.append(b"")
    body = b"\r\n".join(parts)

    req = urllib.request.Request(
        f"{PROXY}/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    upload = json.loads(urllib.request.urlopen(req).read().decode())
    print("UPLOAD", upload)
    assert upload["status"] == "PROCESSING"
    job_id = upload["job_id"]

    final = None
    for i in range(40):
        job = json.loads(
            urllib.request.urlopen(f"{PROXY}/job/{job_id}").read().decode()
        )
        print("POLL", i, job.get("status"), job.get("csv_path"))
        if job.get("status") in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "FAILED"}:
            final = job
            break
        time.sleep(0.5)

    assert final is not None, "Job did not complete"
    print("SUMMARY", final.get("validation_summary"))
    assert str(final["status"]).startswith("SUCCESS")
    assert final.get("csv_path")
    assert final.get("json_path")

    csv = urllib.request.urlopen(f"{PROXY}/job/{job_id}/download/csv").read()
    js = urllib.request.urlopen(f"{PROXY}/job/{job_id}/download/json").read()
    print("CSV_BYTES", len(csv), "JSON_BYTES", len(js))
    assert len(csv) > 50 and len(js) > 50
    print("E2E_OK")


if __name__ == "__main__":
    try:
        main()
    except urllib.error.URLError as exc:
        raise SystemExit(f"Server not reachable: {exc}") from exc
