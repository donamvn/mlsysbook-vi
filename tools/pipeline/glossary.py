"""Đọc bảng thuật ngữ; tạo tập con xuất hiện trong văn bản để nhắc model."""
from __future__ import annotations
import csv, re
from . import config as C

def load() -> list[dict]:
    rows=[]
    for p in (C.GLOSSARY_SEED, C.GLOSSARY_CSV):
        if p.exists():
            with open(p, encoding="utf-8", newline="") as f:
                for r in csv.DictReader(f):
                    if r.get("en"): rows.append(r)
    seen={}; out=[]
    for r in rows:
        k=r["en"].lower().strip()
        seen[k]=r
    return list(seen.values())

def subset(rows: list[dict], text: str, limit=80) -> list[dict]:
    low=text.lower()
    hits=[r for r in rows if r["en"].lower() in low]
    hits.sort(key=lambda r:-len(r["en"]))
    return hits[:limit]

def as_prompt(rows: list[dict]) -> str:
    lines=[]
    for r in rows:
        if r.get("mode")=="keep":
            lines.append(f'- "{r["en"]}": giữ nguyên tiếng Anh')
        else:
            lines.append(f'- "{r["en"]}" → "{r["vi"]}"')
    return "\n".join(lines)
