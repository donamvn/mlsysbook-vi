"""Điều phối dịch trọn một tập: văn xuôi (.qmd) → SVG → raster. Resumable, tôn trọng trần chi tiêu."""
from __future__ import annotations
import argparse, re, time
from pathlib import Path
from . import config as C
from .common import log, setup_logging
from . import budget
from .translate import translate_file
from .svg_translate import translate_svg
from .img_translate import translate_raster

def qmd_files(vol: str) -> list[Path]:
    base=C.BOOKS/vol
    files=sorted(base.glob("**/*.qmd"))
    skip={"references.qmd"}  # thư mục tài liệu tham khảo: bỏ
    return [f for f in files if f.name not in skip]

def referenced_images(vol: str):
    svgs=set(); rasters=set()
    for q in C.BOOKS.glob(f"{vol}/**/*.qmd"):
        chapdir=q.parent
        for m in re.finditer(r'!\[[^\]]*\]\((images/[^)]+?\.(svg|png|jpg|jpeg))\)', q.read_text(encoding="utf-8")):
            rel=m.group(1); ext=m.group(2).lower()
            p=(chapdir/rel).resolve()
            if not p.exists(): continue
            if "cover" in p.name.lower(): continue   # bìa: giữ nguyên
            (svgs if ext=="svg" else rasters).add(p)
    return sorted(svgs), sorted(rasters)

def main(vol=None, phases="text,svg", engine="gemini", force=False):
    setup_logging("run_vol")
    vol=vol or C.VOL
    phases=set(phases.split(","))
    log.info("=== Dịch %s | phases=%s | trần %.0f USD (đã tiêu %.3f) ===", vol, phases, budget.CAP, budget.state()["usd"])
    if "text" in phases:
        files=qmd_files(vol); log.info("Văn xuôi: %d file", len(files))
        for i,f in enumerate(files,1):
            try:
                r=translate_file(f, engine, None, force)
                if r.get("skipped"): log.info("[%d/%d] %s: bỏ qua (đã dịch)", i, len(files), r["file"])
                else: log.info("[%d/%d] %s: %d đoạn, thiếu %d, %ss | sổ %.3f USD",
                    i,len(files),r["file"],r["segments"],r.get("missing",0),r.get("sec",0),budget.state()["usd"])
            except budget.BudgetExceeded as e:
                log.error("DỪNG: %s", e); return
            except Exception as e:
                log.exception("[%d/%d] %s LỖI: %s", i, len(files), f.name, e)
    svgs, rasters = referenced_images(vol)
    if "svg" in phases:
        log.info("SVG: %d hình", len(svgs))
        for i,s in enumerate(svgs,1):
            rel=s.relative_to(C.BOOKS); dst=C.VI_DIR/rel
            if dst.exists() and not force: continue
            try:
                n=translate_svg(s, dst, engine); log.info("[%d/%d] svg %s: %d nhãn | sổ %.3f", i, len(svgs), rel.name, n, budget.state()["usd"])
            except budget.BudgetExceeded as e: log.error("DỪNG: %s", e); return
            except Exception as e: log.exception("svg %s LỖI: %s", s.name, e)
    if "raster" in phases:
        log.info("Raster: %d hình", len(rasters))
        for i,r in enumerate(rasters,1):
            rel=r.relative_to(C.BOOKS); dst=C.VI_DIR/rel
            if dst.exists() and not force: continue
            try:
                ok=translate_raster(r, dst); log.info("[%d/%d] raster %s: %s | sổ %.3f", i, len(rasters), rel.name, "OK" if ok else "không ảnh", budget.state()["usd"])
            except budget.BudgetExceeded as e: log.error("DỪNG: %s", e); return
            except Exception as e: log.exception("raster %s LỖI: %s", r.name, e)
    log.info("=== XONG. Tổng chi %.3f USD ===", budget.state()["usd"])

if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--vol", default=None); ap.add_argument("--phases", default="text,svg")
    ap.add_argument("--engine", default="gemini"); ap.add_argument("--force", action="store_true")
    a=ap.parse_args(); main(a.vol, a.phases, a.engine, a.force)
