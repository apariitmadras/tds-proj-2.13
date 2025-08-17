import asyncio, tempfile, os, types
import orchestrator as orch
import format_handler as fmt

class DummyLogger:
    async def init(self): pass
    async def save(self, req_id, entry): pass

async def fake_plan(task_text, spec): return {"steps":[{"id":"S1","op":"FORMAT","desc":"direct"}]}
async def fake_codegen(task_text, spec, plan, repair_context=None): return 'print("[\"N/A\"]")'

def test_orchestrator_dummy_flow(monkeypatch):
    monkeypatch.setattr(orch, "plan_task", fake_plan)
    monkeypatch.setattr(orch, "generate_code", fake_codegen)

    task_text = "Respond with a JSON array of strings with one item."
    with tempfile.TemporaryDirectory() as job:
        os.makedirs(os.path.join(job, "attachments"), exist_ok=True)
        res = asyncio.get_event_loop().run_until_complete(
            orch.handle_request(task_text, [], job, DummyLogger())
        )
    arr = fmt.json.loads(res)
    assert isinstance(arr, list) and len(arr) == 1
