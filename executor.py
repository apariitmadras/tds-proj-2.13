# executor.py
import asyncio, os, sys, base64
from typing import Tuple

RUN_FILENAME = "runner_user_code.py"

# We pass the code as base64 so we never fight with quotes/newlines.
WRAP_TEMPLATE = '''\
# Auto-generated runner: decodes base64 -> user_code_exec.py -> runs it.
import base64, runpy

USER_FILE = "user_code_exec.py"
code_b64 = "{USER_CODE_B64}"
with open(USER_FILE, "wb") as f:
    f.write(base64.b64decode(code_b64.encode("ascii")))
runpy.run_path(USER_FILE, run_name="__main__")
'''

async def run_user_code(user_code: str, cwd: str, timeout: int) -> Tuple[bool, str, str]:
    if not user_code.strip():
        return False, "", "empty code"

    code_b64 = base64.b64encode(user_code.encode("utf-8")).decode("ascii")
    wrapper = WRAP_TEMPLATE.replace("{USER_CODE_B64}", code_b64)

    with open(os.path.join(cwd, RUN_FILENAME), "w", encoding="utf-8") as f:
        f.write(wrapper)

    proc = await asyncio.create_subprocess_exec(
        sys.executable, RUN_FILENAME,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        env={
            **os.environ,
            "PYTHONUNBUFFERED": "1",
            # keep user code from seeing secrets
            "OPENAI_API_KEY": ""
        }
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        ok = (proc.returncode == 0)
        return ok, (out or b"").decode("utf-8", "replace"), (err or b"").decode("utf-8", "replace")
    except asyncio.TimeoutError:
        try:
            proc.kill()
        except Exception:
            pass
        return False, "", "timeout"
