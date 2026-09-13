"""Dịch một chương .qmd: tách → dịch từng lô đoạn (Gemini/GPT-5) → ghép lại.

Giữ nguyên mã, công thức, LaTeX, callout, hình; chỉ dịch văn xuôi/tiêu đề/chú thích.
Cache theo hash nội dung. Engine: 'gemini' (Vertex) hoặc 'gpt' (Azure GPT-5).
"""
from __future__ import annotations
import argparse, json, re, time
from pathlib import Path
from . import config as C
from .common import sha1, read_json, write_json, log, setup_logging, gemini_text, gpt_json, with_retry
from . import glossary as G
from .qmd_segment import segment, reassemble, translatable, Seg

PROMPT_VERSION="v1"
BATCH_CHARS=6000

SYSTEM=(
"Bạn là dịch giả kỹ thuật Anh→Việt, đang dịch sách giáo khoa 'Machine Learning Systems' "
"(Harvard/MIT Press) cho sinh viên kỹ thuật Việt Nam.\n"
"NGUYÊN TẮC:\n"
"- Dịch chính xác, tự nhiên, văn phong học thuật rõ ràng; xưng hô trung tính.\n"
"- CHỈ dịch nội dung; GIỮ NGUYÊN mọi ký hiệu Markdown/Quarto có sẵn: **đậm**, *nghiêng*, `code`, "
"$công thức$, @tham-chiếu, [@trích-dẫn], liên kết. TUYỆT ĐỐI KHÔNG thêm dấu nhấn mạnh (* hoặc _) "
"mà bản gốc không có; không bọc thuật ngữ vào *...*.\n"
"- Giữ nguyên tên riêng, tên hàm, đường dẫn, số, đơn vị, ký hiệu toán.\n"
"- Thuật ngữ: theo BẢNG THUẬT NGỮ kèm theo. Thuật ngữ ngoài bảng: dùng thuật ngữ tin học/ML "
"tiếng Việt chuẩn; nếu chưa phổ biến, để tiếng Anh.\n"
"- Đầu vào là JSON danh sách đoạn [{id, text}]. Trả JSON {units:[{id, vi}]} đúng và đủ mọi id, "
"KHÔNG thêm/bớt đoạn. Mỗi 'vi' là bản dịch của 'text' cùng id.\n"
"- Với đoạn chỉ là tiêu đề ngắn hay nhãn, dịch ngắn gọn tương ứng."
)

SCHEMA={"type":"object","properties":{"units":{"type":"array","items":{"type":"object",
    "properties":{"id":{"type":"string"},"vi":{"type":"string"}},
    "required":["id","vi"],"additionalProperties":False}}},"required":["units"],"additionalProperties":False}

def batches(items, limit=BATCH_CHARS):
    out=[]; cur=[]; sz=0
    for it in items:
        n=len(it["text"])
        if cur and sz+n>limit: out.append(cur); cur=[]; sz=0
        cur.append(it); sz+=n
    if cur: out.append(cur)
    return out

def _gemini_batch(payload, gloss, model):
    from google.genai import types
    from .common import gemini
    user=("BẢNG THUẬT NGỮ:\n"+gloss+"\n\n" if gloss else "")+"CẦN DỊCH (JSON):\n"+json.dumps(payload, ensure_ascii=False)
    def call():
        return gemini().models.generate_content(model=model, contents=user,
            config=types.GenerateContentConfig(system_instruction=SYSTEM, temperature=0.2,
                max_output_tokens=48000, response_mime_type="application/json", response_schema=SCHEMA))
    from . import budget
    budget.guard(0.08)
    r=with_retry(call, what=f"gemini {model}")
    u=r.usage_metadata
    budget.charge_tokens(model, u.prompt_token_count or 0, u.candidates_token_count or 0)
    return json.loads(r.text), u

def translate_file(src: Path, engine="gemini", model=None, force=False):
    """Dịch một file .qmd bất kỳ (chương/frontmatter/parts/backmatter)."""
    text=src.read_text(encoding="utf-8")
    segs=segment(text); idxs=translatable(segs)
    rel=src.relative_to(C.BOOKS); dst=C.VI_DIR/rel
    if dst.exists() and not force:
        return {"file":str(rel),"skipped":True,"segments":len(idxs)}
    rows=G.load()
    model=model or (C.GEMINI_MODEL if engine=="gemini" else C.DEPLOY_TRANSLATE)
    cdir=C.CACHE/"translate"/engine; cdir.mkdir(parents=True, exist_ok=True)
    results={}; items=[{"id":str(i),"text":segs[i].text} for i in idxs]
    t0=time.time(); tin=tout=0; allb=batches(items)
    for bi,b in enumerate(allb,1):
        alltext=" ".join(x["text"] for x in b)
        gloss=G.as_prompt(G.subset(rows, alltext))
        key=sha1(PROMPT_VERSION+model+gloss+json.dumps(b,ensure_ascii=False))
        cp=cdir/f"{key}.json"
        if cp.exists() and not force:
            res=read_json(cp)
        elif engine=="gemini":
            res,u=_gemini_batch(b, gloss, model); tin+=u.prompt_token_count or 0; tout+=u.candidates_token_count or 0; write_json(cp,res)
        else:
            user=("BẢNG THUẬT NGỮ:\n"+gloss+"\n\n" if gloss else "")+"CẦN DỊCH (JSON):\n"+json.dumps(b,ensure_ascii=False)
            res=gpt_json(SYSTEM,user,SCHEMA,deployment=model,name="tr"); write_json(cp,res)
        for u in res.get("units",[]):
            if u.get("id") is not None: results[u["id"]]=u["vi"]
    trans={int(k):v for k,v in results.items()}
    missing=[i for i in idxs if i not in trans]
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(reassemble(segs, trans), encoding="utf-8")
    return {"file":str(rel),"segments":len(idxs),"missing":len(missing),"batches":len(allb),
            "sec":round(time.time()-t0,1),"tok_in":tin,"tok_out":tout}


def translate_chapter(chap: str, engine="gemini", model=None, force=False):
    src=None
    for p in C.BOOKS.glob(f"{C.VOL}/*/{chap}.qmd"):
        src=p; break
    if src is None:
        for p in C.BOOKS.glob(f"{C.VOL}/**/{chap}.qmd"):
            src=p; break
    if src is None: raise SystemExit(f"Không thấy chương {chap}")
    text=src.read_text(encoding="utf-8")
    segs=segment(text)
    idxs=translatable(segs)
    rows=G.load()
    model=model or (C.GEMINI_MODEL if engine=="gemini" else C.DEPLOY_TRANSLATE)
    cdir=C.CACHE/"translate"/engine; cdir.mkdir(parents=True, exist_ok=True)
    results={}
    items=[{"id":str(i),"text":segs[i].text} for i in idxs]
    t0=time.time(); tok_in=tok_out=0
    allb=batches(items)
    for bi,b in enumerate(allb,1):
        alltext=" ".join(x["text"] for x in b)
        gloss=G.as_prompt(G.subset(rows, alltext))
        key=sha1(PROMPT_VERSION+model+gloss+json.dumps(b,ensure_ascii=False))
        cp=cdir/f"{key}.json"
        if cp.exists() and not force:
            res=read_json(cp)
        else:
            if engine=="gemini":
                res,u=_gemini_batch(b, gloss, model)
                tok_in+=u.prompt_token_count or 0; tok_out+=u.candidates_token_count or 0
            else:
                user=("BẢNG THUẬT NGỮ:\n"+gloss+"\n\n" if gloss else "")+"CẦN DỊCH (JSON):\n"+json.dumps(b,ensure_ascii=False)
                res=gpt_json(SYSTEM,user,SCHEMA,deployment=model,name="tr")
            write_json(cp,res)
        for u in res.get("units",[]):
            if u.get("id") is not None: results[u["id"]]=u["vi"]
        log.info("  %s lô %d/%d: %d đoạn", chap, bi, len(allb), len(b))
    trans={int(k):v for k,v in results.items()}
    missing=[i for i in idxs if i not in trans]
    out=reassemble(segs, trans)
    rel=src.relative_to(C.BOOKS)
    dst=C.VI_DIR/rel
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_text(out, encoding="utf-8")
    return {"chap":chap,"segments":len(idxs),"missing":len(missing),"batches":len(allb),
            "sec":round(time.time()-t0,1),"tok_in":tok_in,"tok_out":tok_out,"out":str(dst)}

if __name__=="__main__":
    setup_logging("translate")
    ap=argparse.ArgumentParser()
    ap.add_argument("chapters", nargs="+")
    ap.add_argument("--engine", choices=["gemini","gpt"], default="gemini")
    ap.add_argument("--model", default=None)
    ap.add_argument("--force", action="store_true")
    a=ap.parse_args()
    for c in a.chapters:
        r=translate_chapter(c, a.engine, a.model, a.force)
        log.info("%s: %d đoạn, thiếu %d, %ds, token in=%d out=%d → %s",
            r["chap"],r["segments"],r["missing"],r["sec"],r["tok_in"],r["tok_out"],r["out"])
