import asyncio, tempfile, os
from executor import run_user_code

def test_run_user_code_basic():
    code = 'print("[1, 2, 3]")'
    with tempfile.TemporaryDirectory() as d:
        ok, out, err = asyncio.get_event_loop().run_until_complete(run_user_code(code, d, timeout=5))
    assert ok
    assert out.strip() == "[1, 2, 3]"
