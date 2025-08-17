# Optional S3 logger (skeleton)
import json, time
import boto3
from typing import Dict, Any
from .log_store import LogStore

class S3LogStore(LogStore):
    def __init__(self, bucket: str, region: str = "us-east-1"):
        self.bucket = bucket
        self.client = boto3.client("s3", region_name=region)

    async def init(self) -> None:
        pass

    async def save(self, req_id: str, entry: Dict[str, Any]) -> None:
        key = f"logs/{req_id}-{int(time.time()*1000)}.json"
        body = json.dumps(entry, ensure_ascii=False).encode("utf-8")
        self.client.put_object(Bucket=self.bucket, Key=key, Body=body, ContentType="application/json")
