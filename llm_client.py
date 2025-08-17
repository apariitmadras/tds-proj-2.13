from openai import OpenAI
from string import Template
from typing import Dict, Any, Optional
import os, json
from config import OPENAI_API_KEY, FAST_MODEL, REASONING_MODEL, CODEGEN_MODEL

_client = None
def client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=OPENAI_API_KEY)
    return _client

PROMPTS_DIR = os.path.join(os.path.dirname(__file__), "prompts")

def _load_prompt(name: str) -> Template:
    with open(os.path.join(PROMPTS_DIR, name), "r", encoding="utf-8") as f:
        return Template(f.read())

def _strip_code(text: str) -> str:
    t = text.strip()
    if t.startswith("```"):
        parts = t.split("```")
        if len(parts) >= 3:
            return parts[2].strip()
        return parts[-1].strip()
    return t

async def plan_task(task_text: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    tpl = _load_prompt("plan_prompt.txt")
    prompt = tpl.substitute(task_text=task_text, spec_json=json.dumps(spec, ensure_ascii=False))
    resp = client().responses.create(model=FAST_MODEL, input=prompt, max_output_tokens=700)
    txt = resp.output_text or "{}"
    try:
        return json.loads(txt)
    except Exception:
        return {"inputs": {}, "steps": [], "assumptions": []}

async def generate_code(task_text: str, spec: Dict[str, Any], plan: Dict[str, Any], repair_context: Optional[str] = None) -> str:
    tpl = _load_prompt("code_prompt.txt")
    prompt = tpl.substitute(
        task_text=task_text,
        spec_json=json.dumps(spec, ensure_ascii=False),
        plan_json=json.dumps(plan, ensure_ascii=False),
        repair_context=repair_context or ""
    )
    resp = client().responses.create(model=CODEGEN_MODEL, input=prompt, max_output_tokens=2200)
    return _strip_code(resp.output_text or "")

async def compose_answer(context: str, spec: Dict[str, Any]) -> str:
    tpl = _load_prompt("answer_prompt.txt")
    prompt = tpl.substitute(context=context, spec_json=json.dumps(spec, ensure_ascii=False))
    resp = client().responses.create(model=REASONING_MODEL, input=prompt, max_output_tokens=1200)
    return resp.output_text or context
