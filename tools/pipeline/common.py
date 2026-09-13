"""Tiện ích chung: log, cache, client Azure GPT-5 và Vertex Gemini, retry."""
from __future__ import annotations
import hashlib, json, logging, random, re, time
from pathlib import Path
from typing import Callable
from . import config as C

log = logging.getLogger("mlsys")

def setup_logging(name="mlsys"):
    C.LOG_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.StreamHandler(), logging.FileHandler(C.LOG_DIR/f"{name}.log", encoding="utf-8")])
    for noisy in ("azure","httpx","openai","urllib3","google","google_genai","google.genai"):
        logging.getLogger(noisy).setLevel(logging.WARNING)

def sha1(s: str) -> str: return hashlib.sha1(s.encode()).hexdigest()
def read_json(p: Path): return json.loads(Path(p).read_text(encoding="utf-8"))
def write_json(p: Path, o):
    Path(p).parent.mkdir(parents=True, exist_ok=True)
    Path(p).write_text(json.dumps(o, ensure_ascii=False, indent=1), encoding="utf-8")

def with_retry(fn: Callable, tries=6, base=4.0, what="api"):
    last=None
    for i in range(tries):
        try: return fn()
        except Exception as e:
            last=e; s=str(e)
            retriable=any(k in s for k in ("429","500","502","503","504","RESOURCE_EXHAUSTED",
                "rate","Rate","timeout","Timeout","Connection","overloaded","UNAVAILABLE","DeadlineExceeded"))
            if not retriable or i==tries-1: raise
            wait=base*(2**i)+random.uniform(0,2)
            m=re.search(r"retry.{0,10}?(\d+)\s*s", s, re.I)
            if m: wait=max(wait, float(m.group(1))+1)
            log.warning("%s lỗi (%s) → thử lại sau %.0fs [%d/%d]", what, s[:120], wait, i+1, tries)
            time.sleep(wait)
    raise last

_oai=None; _gem=None
def oai():
    global _oai
    if _oai is None:
        from openai import AzureOpenAI
        if not C.AZURE_OPENAI_KEY: raise SystemExit("Thiếu AZURE_OPENAI_KEY")
        _oai=AzureOpenAI(api_key=C.AZURE_OPENAI_KEY, azure_endpoint=C.AZURE_OPENAI_ENDPOINT,
            api_version=C.AZURE_OPENAI_API_VERSION, timeout=180, max_retries=0)
    return _oai

def gemini():
    global _gem
    if _gem is None:
        from google import genai
        if C.USE_VERTEX:
            _gem=genai.Client(vertexai=True, project=C.GCP_PROJECT, location=C.GCP_LOCATION)
        else:
            _gem=genai.Client(api_key=C.GEMINI_API_KEY)
    return _gem

def gpt_json(system, user, schema, *, deployment=None, effort="low", max_tokens=16000, name="out"):
    dep=deployment or C.DEPLOY_TRANSLATE
    msgs=[{"role":"system","content":system},{"role":"user","content":user}]
    def call():
        return oai().chat.completions.create(model=dep, messages=msgs, max_completion_tokens=max_tokens,
            reasoning_effort=effort, response_format={"type":"json_schema",
            "json_schema":{"name":name,"strict":True,"schema":schema}})
    r=with_retry(call, what=f"{dep} json")
    if r.choices[0].finish_reason=="length": raise RuntimeError("GPT phản hồi bị cắt; giảm chunk")
    return json.loads(r.choices[0].message.content)

def gemini_text(system, user, *, model=None, temperature=0.3, max_tokens=32000):
    from google.genai import types
    mdl=model or C.GEMINI_MODEL
    def call():
        return gemini().models.generate_content(model=mdl, contents=user,
            config=types.GenerateContentConfig(system_instruction=system, temperature=temperature,
                max_output_tokens=max_tokens))
    from . import budget
    budget.guard(0.05)
    r=with_retry(call, what=f"gemini {mdl}")
    u=r.usage_metadata
    budget.charge_tokens(mdl, u.prompt_token_count or 0, u.candidates_token_count or 0)
    return r.text or "", u
