import asyncio, os, sys, uuid
from typing import Tuple

RUN_FILENAME = "runner_user_code.py"

WRAP_TEMPLATE = """\
# Auto-generated runner. Writes user code to file then execs it.
import os, sys, runpy
USER_FILE = "user_code_exec.py"
code = r"""{USER_CODE}"""
with open(USER_FILE, "w", encoding="utf-8") as f:
    f.write(code)
runpy.run_path(USER_FILE, run_name="__main__")
"""

async def run_user_code(user_code: str, cwd: str, timeout: int) -> Tuple[bool, str, str]:
    if not user_code.strip():
        return False, "", "empty code"
    wrapper = WRAP_TEMPLATE.replace("{USER_CODE}", user_code)
    with open(os.path.join(cwd, RUN_FILENAME), "w", encoding="utf-8") as f:
        f.write(wrapper)

    proc = await asyncio.create_subprocess_exec(
        sys.executable, RUN_FILENAME,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={**os.environ, "PYTHONUNBUFFERED":"1", "OPENAI_API_KEY":""}
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        ok = (proc.returncode == 0)
        return ok, (out or b"").decode("utf-8","replace"), (err or b"").decode("utf-8","replace")
    except asyncio.TimeoutError:
        try: proc.kill()
        except Exception: pass
        return False, "", "timeout"
