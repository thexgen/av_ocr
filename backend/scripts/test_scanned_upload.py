"""Upload scanned PDF and poll until complete."""
from __future__ import annotations

import json
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000"
PDF = Path("backend/sample_data/scanned_pdf/Holing_Statement.pdf")


def main() -> None:
    for _ in range(40):
        try:
            print("HEALTH", urllib.request.urlopen(f"{API}/health").read().decode())
            break
        except Exception:
            time.sleep(0.5)
    else:
        raise SystemExit("API not up")

    pdf = PDF.read_bytes()
    boundary = "----BoundaryScan"
    parts = [
        f"--{boundary}".encode(),
        b'Content-Disposition: form-data; name="file"; filename="Holing_Statement.pdf"',
        b"Content-Type: application/pdf",
        b"",
        pdf,
        f"--{boundary}--".encode(),
        b"",
    ]
    body = b"\r\n".join(parts)
    req = urllib.request.Request(
        f"{API}/upload",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )
    up = json.loads(urllib.request.urlopen(req).read().decode())
    print("UPLOAD", up)
    job = up["job_id"]

    for i in range(90):
        j = json.loads(urllib.request.urlopen(f"{API}/job/{job}").read().decode())
        status = j.get("status")
        vs = j.get("validation_summary") or {}
        print("POLL", i, status, "rows=", vs.get("total_rows"))
        if status in {"SUCCESS", "SUCCESS_WITH_WARNINGS", "FAILED"}:
            print(json.dumps(vs, indent=2))
            print("csv", j.get("csv_path"))
            print("json", j.get("json_path"))
            if status == "FAILED":
                raise SystemExit(1)
            return
        time.sleep(1)
    raise SystemExit("timeout")


if __name__ == "__main__":
    main()
