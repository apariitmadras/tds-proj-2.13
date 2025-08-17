############################################

import asyncio, os, time, json, uuid, tempfile, shutil
from typing import List, Dict, Any
from config import (
    TOTAL_DEADLINE_SEC, CLIENT_RESPOND_SEC,
    PLAN_SEC, CODEGEN1_SEC, RUN1_SEC, REPAIR_CODEGEN_SEC, REPAIR_RUN_SEC
)
from llm_client import plan_task, generate_code, compose_answer
from executor_b64 import run_user_code
from format_handler import make_format_spec, validate_and_coerce, ValidationError, make_dummy_answer

def now_monotonic() -> float:
    import time
    return time.monotonic()

async def handle_request(task_text: str, attachments: List[Dict[str, Any]], job_dir: str, logger) -> str:
    t0 = now_monotonic()
    deadline_client = t0 + CLIENT_RESPOND_SEC

    req_id = f"{int(time.time())}-{uuid.uuid4().hex[:8]}"
    run_dir = os.path.join("runs", req_id); os.makedirs(run_dir, exist_ok=True)
    await logger.init()
    await logger.save(req_id, {"phase":"start","attachments":[a["filename"] for a in attachments]})

    # 1) FormatSpec
    spec = make_format_spec(task_text)
    await logger.save(req_id, {"phase":"format_spec","spec":spec})

    async def main_flow():
        # 2) Plan
        plan = await asyncio.wait_for(plan_task(task_text, spec), timeout=min(PLAN_SEC, max(3, deadline_client - now_monotonic())))
        with open(os.path.join(run_dir, "plan.json"), "w", encoding="utf-8") as f: f.write(json.dumps(plan, ensure_ascii=False, indent=2))
        await logger.save(req_id, {"phase":"plan","ok":True})

        # 3) Codegen
        code = await asyncio.wait_for(
            generate_code(task_text, spec, plan),
            timeout=min(CODEGEN1_SEC, max(5, deadline_client - now_monotonic()))
        )
        with open(os.path.join(run_dir, "code.py"), "w", encoding="utf-8") as f: f.write(code)
        await logger.save(req_id, {"phase":"codegen1","ok":True})

        # 4) Execute
        ok, stdout, stderr = await run_user_code(code, cwd=job_dir, timeout=min(RUN1_SEC, max(10, deadline_client - now_monotonic())))
        with open(os.path.join(run_dir, "stdout1.txt"), "w", encoding="utf-8") as f: f.write(stdout or "")
        with open(os.path.join(run_dir, "stderr1.txt"), "w", encoding="utf-8") as f: f.write(stderr or "")
        await logger.save(req_id, {"phase":"run1","ok":ok})

        # 5) Validate
        if ok:
            try:
                payload = validate_and_coerce(stdout, spec)
                with open(os.path.join(run_dir, "final.txt"), "w", encoding="utf-8") as f: f.write(payload)
                await logger.save(req_id, {"phase":"validate1","result":"ok"})
                return payload
            except ValidationError as e:
                await logger.save(req_id, {"phase":"validate1","result":"fail","error":str(e)})

        # 6) Repair path if time allows
        if now_monotonic() < deadline_client:
            repair_ctx = f"""PREVIOUS STDOUT:\n{stdout}\n\nPREVIOUS STDERR:\n{stderr}\n"""
            code2 = await asyncio.wait_for(
                generate_code(task_text, spec, plan, repair_context=repair_ctx),
                timeout=min(REPAIR_CODEGEN_SEC, max(5, deadline_client - now_monotonic()))
            )
            with open(os.path.join(run_dir, "code_repaired.py"), "w", encoding="utf-8") as f: f.write(code2)
            await logger.save(req_id, {"phase":"codegen2","ok":True})

            ok2, stdout2, stderr2 = await run_user_code(code2, cwd=job_dir, timeout=min(REPAIR_RUN_SEC, max(10, deadline_client - now_monotonic())))
            with open(os.path.join(run_dir, "stdout2.txt"), "w", encoding="utf-8") as f: f.write(stdout2 or "")
            with open(os.path.join(run_dir, "stderr2.txt"), "w", encoding="utf-8") as f: f.write(stderr2 or "")
            await logger.save(req_id, {"phase":"run2","ok":ok2})

            if ok2:
                try:
                    payload2 = validate_and_coerce(stdout2, spec)
                    with open(os.path.join(run_dir, "final.txt"), "w", encoding="utf-8") as f: f.write(payload2)
                    await logger.save(req_id, {"phase":"validate2","result":"ok"})
                    return payload2
                except ValidationError as e:
                    await logger.save(req_id, {"phase":"validate2","result":"fail","error":str(e)})

        raise TimeoutError("valid payload not ready before client deadline")

    try:
        result = await asyncio.wait_for(main_flow(), timeout=max(1, deadline_client - now_monotonic()))
        return result
    except Exception:
        dummy = make_dummy_answer(spec)
        with open(os.path.join(run_dir, "final_dummy.txt"), "w", encoding="utf-8") as f: f.write(dummy)
        await logger.save(req_id, {"phase":"fallback_dummy"})
        return dummy
