"""Dịch nhãn chữ trong SVG tại chỗ: giữ nguyên nét vẽ, chỉ đổi text/tspan sang tiếng Việt.

Sắc nét, sửa được, gần như miễn phí. Dùng cho sơ đồ SVG (phần lớn hình trong sách).
"""
from __future__ import annotations
import argparse, json, re
from pathlib import Path
from lxml import etree
from . import config as C
from . import glossary as G
from .common import sha1, read_json, write_json, log, setup_logging, with_retry

SVG_NS="http://www.w3.org/2000/svg"

def _text_nodes(root):
    # mỗi <text>: nếu có <tspan> con thì dịch từng tspan, nếu không dịch text trực tiếp
    nodes=[]
    for t in root.iter(f"{{{SVG_NS}}}text"):
        tspans=t.findall(f"{{{SVG_NS}}}tspan")
        if tspans:
            for ts in tspans:
                if ts.text and ts.text.strip(): nodes.append(ts)
        elif t.text and t.text.strip():
            nodes.append(t)
    return nodes

def extract(svg_path: Path) -> list[str]:
    root=etree.parse(str(svg_path)).getroot()
    return [n.text for n in _text_nodes(root)]

def _translate_labels(labels: list[str], gloss: str, engine: str, model: str) -> dict[str,str]:
    import json as _j
    payload=[{"id":str(i),"text":s} for i,s in enumerate(labels)]
    SYS=("Dịch nhãn trên sơ đồ kỹ thuật (sách ML Systems) sang tiếng Việt: NGẮN GỌN để vừa ô, "
         "giữ nguyên thuật ngữ theo bảng, giữ nguyên tên riêng/tên công nghệ/ký hiệu/số. "
         "Trả JSON {units:[{id,vi}]} đúng đủ mọi id.")
    SCH={"type":"object","properties":{"units":{"type":"array","items":{"type":"object",
        "properties":{"id":{"type":"string"},"vi":{"type":"string"}},"required":["id","vi"],
        "additionalProperties":False}}},"required":["units"],"additionalProperties":False}
    user=("BẢNG THUẬT NGỮ:\n"+gloss+"\n\n" if gloss else "")+"CẦN DỊCH (JSON):\n"+_j.dumps(payload,ensure_ascii=False)
    if engine=="gemini":
        from .common import gemini; from . import budget
        from google.genai import types
        budget.guard(0.02)
        def call(): return gemini().models.generate_content(model=model, contents=user,
            config=types.GenerateContentConfig(system_instruction=SYS, temperature=0.1,
                response_mime_type="application/json", response_schema=SCH, max_output_tokens=8000))
        r=with_retry(call, what=f"svg {model}"); u=r.usage_metadata
        budget.charge_tokens(model, u.prompt_token_count or 0, u.candidates_token_count or 0)
        res=_j.loads(r.text)
    else:
        from .common import gpt_json
        res=gpt_json(SYS,user,SCH,deployment=model,name="svg")
    return {u["id"]:u["vi"] for u in res.get("units",[])}

def translate_svg(svg_path: Path, out_path: Path, engine="gemini", model=None):
    rows=G.load()
    tree=etree.parse(str(svg_path)); root=tree.getroot()
    nodes=_text_nodes(root)
    labels=[n.text for n in nodes]
    if not labels:
        out_path.parent.mkdir(parents=True, exist_ok=True); out_path.write_bytes(svg_path.read_bytes()); return 0
    model=model or (C.GEMINI_MODEL if engine=="gemini" else C.DEPLOY_TRANSLATE)
    gloss=G.as_prompt(G.subset(rows, " ".join(labels)))
    tr=_translate_labels(labels, gloss, engine, model)
    for i,n in enumerate(nodes):
        v=tr.get(str(i))
        if v: n.text=v
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tree.write(str(out_path), encoding="utf-8", xml_declaration=True)
    return len(nodes)

if __name__=="__main__":
    setup_logging("svg")
    ap=argparse.ArgumentParser(); ap.add_argument("svg"); ap.add_argument("out"); ap.add_argument("--engine",default="gemini")
    a=ap.parse_args()
    n=translate_svg(Path(a.svg), Path(a.out), a.engine)
    log.info("dịch %d nhãn → %s", n, a.out)
