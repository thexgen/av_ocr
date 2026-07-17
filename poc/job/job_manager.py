from __future__ import annotations

import json
import logging
import threading
from datetime import datetime

from poc.config import cfg
from poc.interfaces.storage import StorageService

logger = logging.getLogger("holding_engine")

_lock = threading.Lock()


class JobManager:
    """
    Generates unique Job IDs: JOB_YYYYMMDD_000001

    Counter is persisted via StorageService (local JSON today, DB/S3 later).
    """

    def __init__(self, storage: StorageService) -> None:
        self.storage = storage
        self.prefix = str(cfg("job", "id_prefix", default="JOB"))
        self.counter_key = str(cfg("job", "counter_key", default="jobs/job_counter.json"))

    def create_job_id(self) -> str:
        with _lock:
            date_part = datetime.now().strftime("%Y%m%d")
            counter = self._next_counter(date_part)
            job_id = f"{self.prefix}_{date_part}_{counter:06d}"
            logger.info("Created Job ID %s", job_id)
            return job_id

    def _next_counter(self, date_part: str) -> int:
        state: dict = {"date": date_part, "seq": 0}
        if self.storage.exists(self.counter_key):
            try:
                state = json.loads(self.storage.read_text(self.counter_key))
            except Exception:  # noqa: BLE001
                state = {"date": date_part, "seq": 0}

        if state.get("date") != date_part:
            state = {"date": date_part, "seq": 0}

        state["seq"] = int(state.get("seq", 0)) + 1
        self.storage.write_text(self.counter_key, json.dumps(state, indent=2))
        return int(state["seq"])
