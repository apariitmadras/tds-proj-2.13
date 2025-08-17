import os, json
from typing import Dict, Any
from .log_store import LogStore
from config import LOG_DIR, LOG_FILE

class FileLogStore(LogStore):
    def __init__(self):
        os.makedirs(LOG_DIR, exist_ok=True)
        self.path = os.path.join(LOG_DIR, LOG_FILE)

    async def init(self) -> None:
        os.makedirs(LOG_DIR, exist_ok=True)

    async def save(self, req_id: str, entry: Dict[str, Any]) -> None:
        with open(self.path, "a", encoding="utf-8") as f:
            f.write(json.dumps({"req_id": req_id, **entry}, ensure_ascii=False) + "\n")
