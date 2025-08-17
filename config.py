import os

def getenv(name: str, default=None, cast=str):
    v = os.getenv(name)
    if v is None:
        return default
    try:
        return cast(v)
    except Exception:
        return v

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

FAST_MODEL = getenv("FAST_MODEL", "o4-mini")
REASONING_MODEL = getenv("REASONING_MODEL", "o3")
CODEGEN_MODEL = getenv("CODEGEN_MODEL", "o4-mini")

TOTAL_DEADLINE_SEC = getenv("TOTAL_DEADLINE_SEC", 300, int)
CLIENT_RESPOND_SEC = getenv("CLIENT_RESPOND_SEC", 285, int)

PLAN_SEC = getenv("PLAN_SEC", 12, int)
CODEGEN1_SEC = getenv("CODEGEN1_SEC", 40, int)
RUN1_SEC = getenv("RUN1_SEC", 90, int)
REPAIR_CODEGEN_SEC = getenv("REPAIR_CODEGEN_SEC", 35, int)
REPAIR_RUN_SEC = getenv("REPAIR_RUN_SEC", 70, int)

LOG_BACKEND = getenv("LOG_BACKEND", "file")
LOG_DIR = getenv("LOG_DIR", "logs")
LOG_FILE = getenv("LOG_FILE", "app.log")

# S3
AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = getenv("AWS_REGION", "us-east-1")
LOG_S3_BUCKET = os.getenv("LOG_S3_BUCKET")

# DB
DATABASE_URL = os.getenv("DATABASE_URL")
