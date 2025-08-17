from fastapi import FastAPI, Request, UploadFile, HTTPException
from fastapi.responses import PlainTextResponse
import os, tempfile, shutil
from typing import Dict, Any, List
from orchestrator import handle_request
from storage.log_store_file import FileLogStore

app = FastAPI(title="LLM Orchestrated Q&A API")

@app.get("/health")
def health():
    return {"ok": True}

@app.post("/api/", response_class=PlainTextResponse)
async def api_entry(request: Request):
    form = await request.form()
    uploads: Dict[str, UploadFile] = {k:v for k,v in form.multi_items() if isinstance(v, UploadFile)}
    if "questions.txt" not in uploads:
        raise HTTPException(400, "questions.txt is required; field name must be 'questions.txt'")

    job_dir = tempfile.mkdtemp(prefix="job_")
    attach_dir = os.path.join(job_dir, "attachments")
    os.makedirs(attach_dir, exist_ok=True)
    saved: List[Dict[str, Any]] = []

    try:
        for field, up in uploads.items():
            data = await up.read()
            path = os.path.join(attach_dir, up.filename or field)
            with open(path, "wb") as f: f.write(data)
            saved.append({"field": field, "filename": up.filename or field, "path": path, "content_type": up.content_type})

        # read questions.txt
        qpath = next(s["path"] for s in saved if s["field"] == "questions.txt")
        with open(qpath, "rb") as f:
            task_text = f.read().decode("utf-8", "replace")

        logger = FileLogStore()
        result = await handle_request(task_text, saved, job_dir, logger)
        return PlainTextResponse(result)
    except Exception as e:
        raise HTTPException(500, f"failure: {e}")
    finally:
        shutil.rmtree(job_dir, ignore_errors=True)
