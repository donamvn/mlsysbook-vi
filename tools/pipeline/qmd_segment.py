"""Bộ tách tài liệu Quarto (.qmd) thành các đoạn: DỊCH hoặc GIỮ NGUYÊN.

Nguyên tắc: giữ nguyên tuyệt đối mã, công thức, LaTeX thô, YAML, bảng, HTML comment,
dòng nhúng hình; chỉ dịch văn xuôi, tiêu đề, mục danh sách, thân callout, và
thuộc tính fig-cap/fig-alt/title trong hình và callout. Cú pháp nội dòng
(`code`, $math$, @ref, [@cite], **đậm**) được giữ nhờ chỉ dẫn cho model khi dịch.

Đầu ra: danh sách segment [{kind, text, meta}] tái ghép lại đúng nguyên trạng.
kind = "keep" (không đụng) | "prose" (dịch) | "heading" | "attr" (fig-cap/alt/title).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class Seg:
    kind: str                 # keep | prose | heading | attr
    text: str                 # nội dung (với attr: chỉ phần giá trị cần dịch)
    meta: dict = field(default_factory=dict)


FENCE_RE = re.compile(r"^(\s*)(`{3,}|~{3,})(.*)$")
MATH_FENCE_RE = re.compile(r"^(\s*)\$\$(.*)$")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*$")
LATEX_BEGIN_RE = re.compile(r"^\s*\\begin\{([^}]+)\}")
HTML_COMMENT_OPEN = re.compile(r"^\s*<!--")
HTML_COMMENT_CLOSE = re.compile(r"-->")
DIV_FENCE_RE = re.compile(r"^\s*(:{3,})(.*)$")       # ::: {.callout-...} ... :::
LIST_RE = re.compile(r"^(\s*)([-*+]|\d{1,3}[.)])(\s+)(.*)$")
IMG_RE = re.compile(r"^\s*!\[(.*?)\]\((.*?)\)(.*)$")  # ![alt](path){attrs}
TABLE_RE = re.compile(r"^\s*\|.*\|\s*$")
RAW_LATEX_LINE_RE = re.compile(r"^\s*\\[a-zA-Z]+(\{.*\})*\s*$")  # \chapterminitoc, \noindent...
ATTR_CAP_RE = re.compile(r'(fig-cap|fig-alt|title)="((?:[^"\\]|\\.)*)"')


def _strip_yaml(lines: list[str]) -> tuple[list[str], int]:
    """Trả về (dòng header YAML, số dòng đã dùng). Header là khối --- ở đầu file."""
    if lines and lines[0].strip() == "---":
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                return lines[: i + 1], i + 1
    return [], 0


def _emit_attrs(line: str) -> list[Seg]:
    """Tách các thuộc tính dịch được (fig-cap/fig-alt/title) khỏi một dòng giữ nguyên.

    Trả về chuỗi segment xen kẽ keep/attr sao cho ghép lại đúng dòng gốc.
    """
    segs: list[Seg] = []
    pos = 0
    for m in ATTR_CAP_RE.finditer(line):
        if m.start() > pos:
            segs.append(Seg("keep", line[pos:m.start()]))
        segs.append(Seg("attr", m.group(2), {"name": m.group(1), "prefix": m.group(1) + '="', "suffix": '"'}))
        pos = m.end()
    tail = line[pos:]
    if not segs:
        return [Seg("keep", line)]
    if tail:
        segs.append(Seg("keep", tail))
    # mảnh đầu bắt đầu một dòng mới; các mảnh sau nối tiếp trên cùng dòng
    for k, seg in enumerate(segs):
        if k:
            seg.meta["inline"] = True
    return segs


def segment(text: str) -> list[Seg]:
    lines = text.split("\n")
    segs: list[Seg] = []
    header, used = _strip_yaml(lines)
    if header:
        segs.append(Seg("keep", "\n".join(header)))
    i = used
    n = len(lines)
    para: list[str] = []

    def flush_para():
        if para:
            raw = "\n".join(para)
            body = raw.strip("\n")
            indent = re.match(r"[ \t]*", body).group(0)
            segs.append(Seg("prose", body[len(indent):].rstrip(), {"prefix": indent}))
            para.clear()

    while i < n:
        line = lines[i]
        stripped = line.strip()

        # --- khối mã ``` hoặc ~~~ ---
        mf = FENCE_RE.match(line)
        if mf and (mf.group(2)[0] * 3) in (mf.group(2)[:3],):
            flush_para()
            fence = mf.group(2)
            block = [line]
            i += 1
            while i < n:
                block.append(lines[i])
                if lines[i].strip().startswith(fence[0] * len(fence)) and lines[i].strip() == lines[i].strip().rstrip():
                    if re.match(rf"^\s*{re.escape(fence[0])}{{{len(fence)},}}\s*$", lines[i]):
                        i += 1
                        break
                i += 1
            segs.append(Seg("keep", "\n".join(block)))
            continue

        # --- công thức $$ ... $$ (có thể thụt lề, nội dung ngay sau $$) ---
        mm = MATH_FENCE_RE.match(line)
        if mm:
            flush_para()
            block = [line]
            # $$...$$ gọn trên một dòng?
            if mm.group(2).strip().endswith("$$") or (mm.group(2).count("$$") >= 1):
                segs.append(Seg("keep", line)); i += 1; continue
            i += 1
            while i < n:
                block.append(lines[i])
                if "$$" in lines[i]:
                    i += 1
                    break
                i += 1
            segs.append(Seg("keep", "\n".join(block)))
            continue

        # --- LaTeX \begin{...} ... \end{...} ---
        mb = LATEX_BEGIN_RE.match(line)
        if mb:
            flush_para()
            env = mb.group(1)
            block = [line]
            i += 1
            end_re = re.compile(rf"\\end\{{{re.escape(env)}\}}")
            while i < n:
                block.append(lines[i])
                if end_re.search(lines[i]):
                    i += 1
                    break
                i += 1
            segs.append(Seg("keep", "\n".join(block)))
            continue

        # --- khối <style> / <script> ---
        mtag = re.match(r"^\s*<(style|script)\b", line, re.I)
        if mtag:
            flush_para()
            tag = mtag.group(1)
            block = [line]
            close = re.compile(rf"</{tag}>", re.I)
            if not close.search(line):
                i += 1
                while i < n:
                    block.append(lines[i])
                    if close.search(lines[i]):
                        break
                    i += 1
            i += 1
            segs.append(Seg("keep", "\n".join(block)))
            continue

        # --- HTML comment ---
        if HTML_COMMENT_OPEN.match(line):
            flush_para()
            block = [line]
            if not HTML_COMMENT_CLOSE.search(line):
                i += 1
                while i < n:
                    block.append(lines[i])
                    if HTML_COMMENT_CLOSE.search(lines[i]):
                        break
                    i += 1
            i += 1
            segs.append(Seg("keep", "\n".join(block)))
            continue

        # --- fence div ::: (callout / cột / content-visible) ---
        md = DIV_FENCE_RE.match(line)
        if md:
            flush_para()
            for s in _emit_attrs(line):  # title="..." trong callout dịch được
                segs.append(s)
            i += 1
            continue

        # --- dòng trống ---
        if stripped == "":
            flush_para()
            segs.append(Seg("keep", ""))
            i += 1
            continue

        # --- tiêu đề # ---
        mh = HEADING_RE.match(line)
        if mh:
            flush_para()
            title = mh.group(2)
            # bỏ phần {.unnumbered ...} hoặc {#sec-...} cuối tiêu đề khỏi phần dịch
            mattr = re.search(r"\s*(\{[^}]*\})\s*$", title)
            attr = ""
            if mattr:
                attr = " " + mattr.group(1)
                title = title[: mattr.start()].rstrip()
            segs.append(Seg("heading", title, {"prefix": mh.group(1) + " ", "suffix": attr}))
            i += 1
            continue

        # --- dòng hình ![]() ---
        if IMG_RE.match(line):
            flush_para()
            for s in _emit_attrs(line):
                segs.append(s)
            i += 1
            continue

        # --- bảng Markdown ---
        if TABLE_RE.match(line):
            flush_para()
            block = []
            while i < n and (TABLE_RE.match(lines[i]) or lines[i].strip().startswith(":")):
                block.append(lines[i])
                i += 1
            segs.append(Seg("keep", "\n".join(block)))  # bảng: giữ khung, dịch ô ở bước sau nếu cần
            continue

        # --- dòng LaTeX thô đứng riêng ---
        if RAW_LATEX_LINE_RE.match(line) and "\\" in line:
            flush_para()
            segs.append(Seg("keep", line))
            i += 1
            continue

        # --- mục danh sách ---
        ml = LIST_RE.match(line)
        if ml:
            flush_para()
            segs.append(Seg("prose", ml.group(4), {"prefix": ml.group(1) + ml.group(2) + ml.group(3)}))
            i += 1
            continue

        # --- văn xuôi thường: gộp thành đoạn ---
        para.append(line)
        i += 1

    flush_para()
    return segs


def reassemble(segs: list[Seg], translated: dict[int, str]) -> str:
    """Ghép lại; translated[idx] là bản dịch cho segment idx (nếu có)."""
    out: list[str] = []
    for idx, s in enumerate(segs):
        val = translated.get(idx, s.text)
        if s.kind == "keep":
            piece = s.text
        elif s.kind == "heading":
            piece = s.meta.get("prefix", "") + val + s.meta.get("suffix", "")
        elif s.kind == "attr":
            piece = s.meta["prefix"] + val + s.meta["suffix"]
        else:  # prose / list
            piece = s.meta.get("prefix", "") + val
        out.append(piece)
    # nối: segment inline (cùng dòng) nối trực tiếp, còn lại nối bằng newline
    res = []
    for idx, (s, piece) in enumerate(zip(segs, out)):
        if s.meta.get("inline") and res:
            res[-1] += piece
        else:
            res.append(piece)
    return "\n".join(res)


def translatable(segs: list[Seg]) -> list[int]:
    return [i for i, s in enumerate(segs) if s.kind in ("prose", "heading", "attr")]
