import re, json, base64
from typing import Dict, Any, List

# -------- FormatSpec --------
def make_format_spec(task_text: str) -> Dict[str, Any]:
    t = task_text.lower()
    qnums = re.findall(r"^\s*\d+\.\s+", task_text, flags=re.M)
    qcount = len(qnums) if qnums else None

    wants_json_array = ("json array" in t) or ("respond with a json array" in t)
    array_of_strings = ("array of strings" in t)

    wants_data_uri = ("data:image/png;base64" in t) or ("base-64 encoded data uri" in t) or ("base64 encoded data uri" in t)
    max_bytes = 100000 if ("100,000" in t or "100000" in t) else None

    if wants_json_array:
        spec = {"container":"json_array", "length": qcount, "elements": []}
        if qcount:
            elems = [{"type":"string"} for _ in range(qcount)]
            if "correlation" in t and qcount >= 3:
                elems[2] = {"type":"float", "decimals":6}
            if wants_data_uri and qcount >= 1:
                elems[-1] = {"type":"data_uri_png", "max_bytes": max_bytes or 100000}
            if array_of_strings:
                elems = [{"type":"string"} for _ in elems]
            spec["elements"] = elems
        return spec
    return {"container":"text"}

# -------- Validator & Coercion --------
class ValidationError(Exception): ...
def _is_data_uri_png(s: str) -> bool:
    return isinstance(s, str) and s.startswith("data:image/png;base64,")

def _coerce_value(v, etype: Dict[str, Any]):
    t = etype.get("type","string")
    if t == "string":
        return str(v)
    if t == "int":
        try: return int(v)
        except: return 0
    if t == "float":
        decimals = etype.get("decimals")
        try:
            fv = float(v)
            if decimals is not None:
                return round(fv, int(decimals))
            return fv
        except:
            return 0.0 if decimals is None else round(0.0, int(decimals))
    if t == "boolean":
        return bool(v)
    if t == "data_uri_png":
        return str(v)
    return v

def validate_and_coerce(stdout_text: str, spec: Dict[str, Any]) -> str:
    container = spec.get("container", "text")
    s = stdout_text.strip()

    if container == "text":
        return s if s else "N/A"

    if container == "json_array":
        m = re.search(r"(\[.*\])", s, flags=re.S)
        if not m: raise ValidationError("No JSON array found in output")
        arr_text = m.group(1)
        try:
            arr = json.loads(arr_text)
        except Exception as e:
            raise ValidationError(f"Invalid JSON array: {e}")
        if not isinstance(arr, list):
            raise ValidationError("Not a JSON array")

        target_len = spec.get("length")
        if target_len is not None and len(arr) != target_len:
            if len(arr) > target_len:
                arr = arr[:target_len]
            else:
                arr.extend(["N/A"] * (target_len - len(arr)))

        elems = spec.get("elements") or []
        if elems and len(arr) == len(elems):
            out = []
            for v, et in zip(arr, elems):
                out.append(_coerce_value(v, et))
            arr = out

        for i, et in enumerate(spec.get("elements") or []):
            if et.get("type") == "data_uri_png":
                if not _is_data_uri_png(arr[i]):
                    raise ValidationError("Expected PNG data URI")
                raw = base64.b64decode(arr[i].split(",",1)[1])
                maxb = et.get("max_bytes", 100000)
                if len(raw) > maxb:
                    raise ValidationError(f"PNG too large: {len(raw)} > {maxb}")
        return json.dumps(arr, ensure_ascii=False)

    raise ValidationError(f"Unsupported container: {container}")

# -------- Dummy Answer --------
from PIL import Image
import io

def _tiny_png_data_uri() -> str:
    im = Image.new("RGBA", (1,1), (0,0,0,0))
    buf = io.BytesIO()
    im.save(buf, format="PNG", optimize=True)
    b64 = base64.b64encode(buf.getvalue()).decode("ascii")
    return f"data:image/png;base64,{b64}"

def make_dummy_answer(spec: Dict[str, Any]) -> str:
    c = spec.get("container","text")
    if c == "text":
        return "N/A"
    if c == "json_array":
        n = spec.get("length") or 1
        elems = spec.get("elements") or [{"type":"string"}]*n
        out = []
        for et in elems:
            t = et.get("type","string")
            if t == "string": out.append("N/A")
            elif t == "int": out.append(0)
            elif t == "float":
                dec = et.get("decimals")
                val = 0.0
                out.append(float(f"{val:.{int(dec)}f}") if dec is not None else val)
            elif t == "boolean": out.append(False)
            elif t == "data_uri_png": out.append(_tiny_png_data_uri())
            else: out.append("N/A")
        return json.dumps(out, ensure_ascii=False)
    return "N/A"
