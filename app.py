from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import os, tempfile, shutil
from typing import Dict, Any, List
from orchestrator import handle_request
from storage.log_store_file import FileLogStore

# Strict by default; set STRICT_FIELD_NAME=false to auto-accept common aliases
STRICT_FIELD_NAME = os.getenv("STRICT_FIELD_NAME", "true").lower() not in {"0", "false", "no"}

app = FastAPI(title="LLM Orchestrated Q&A API")

@app.get("/health")
def health():
    return {"ok": True}

def _is_upload_like(v: Any) -> bool:
    # Duck-typing avoids FastAPI/Starlette class mismatches
    return hasattr(v, "filename") and hasattr(v, "file") and callable(getattr(v, "read", None))

@app.post("/api/", response_class=PlainTextResponse)
async def api_entry(request: Request):
    form = await request.form()

    # Collect only file parts (robustly, keeps duplicates if any)
    raw_items = list(form.multi_items())
    uploads: Dict[str, Any] = {k: v for k, v in raw_items if _is_upload_like(v)}

    if "questions.txt" not in uploads:
        # Helpful debug so you can see what actually arrived
        try:
            print("DEBUG form keys:", list(form.keys()))
            print("DEBUG file-like keys:", [k for k, v in raw_items if _is_upload_like(v)])
        except Exception:
            pass

        seen = list(uploads.keys())
        msg = (
            "questions.txt is required; field name must be exactly 'questions.txt'. "
            f"Received file fields: {seen or '[]'}. "
            "Example: curl -F \"questions.txt=@question.txt\" https://<host>/api/"
        )
        if not STRICT_FIELD_NAME:
            # Optional automatic recovery for common mistakes
            fallback_key = next((k for k in seen if k.lower() in {"file", "question", "questions"}), None)
            if fallback_key:
                uploads["questions.txt"] = uploads.pop(fallback_key)
            else:
                raise HTTPException(status_code=400, detail=msg)
        else:
            raise HTTPException(status_code=400, detail=msg)

    # Prepare job dir
    job_dir = tempfile.mkdtemp(prefix="job_")
    attach_dir = os.path.join(job_dir, "attachments")
    os.makedirs(attach_dir, exist_ok=True)
    saved: List[Dict[str, Any]] = []

    try:
        # Persist files
        for field, up in uploads.items():
            data = await up.read()
            fname = getattr(up, "filename", None) or field
            path = os.path.join(attach_dir, fname)
            with open(path, "wb") as f:
                f.write(data)
            saved.append({
                "field": field,
                "filename": fname,
                "path": path,
                "content_type": getattr(up, "content_type", None),
            })

        # Read questions content from the required field
        qpath = next(item["path"] for item in saved if item["field"] == "questions.txt")
        with open(qpath, "rb") as f:
            task_text = f.read().decode("utf-8", "replace")

        logger = FileLogStore()
        result = await handle_request(task_text, saved, job_dir, logger)
        return PlainTextResponse(result)

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"failure: {e}")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)

# Accept POST /api (no trailing slash) to avoid redirect-induced 405s
@app.post("/api", include_in_schema=False)
async def api_entry_alias(request: Request):
    return await api_entry(request)
