"""Engine tạo ảnh dịch nhãn cho file KHÔNG phải SVG (gemini-2.5-flash-image trên Vertex).

Model Gemini 3.1 Flash Image (vùng global) dịch nhãn raster tốt: đúng dấu tiếng Việt,
giữ bố cục/màu/mũi tên. Dùng cho sơ đồ raster (PNG/JPG) không có bản SVG.
Vẫn nên ưu tiên dịch SVG khi có bản vector (sắc nét, rẻ hơn).
"""
from __future__ import annotations
from pathlib import Path
from . import config as C
from . import budget
from .common import gemini, with_retry, log

IMG_MODEL = C.GEMINI_IMAGE_MODEL   # gemini-3.1-flash-image (global) — dịch nhãn raster tốt

_img_client=None
def _client():
    global _img_client
    if _img_client is None:
        from google import genai
        _img_client=genai.Client(vertexai=True, project=C.GCP_PROJECT, location=C.GEMINI_IMAGE_LOCATION)
    return _img_client

def translate_raster(src: Path, out: Path, mapping: dict[str,str] | None = None, extra: str = "") -> bool:
    from google.genai import types
    data=Path(src).read_bytes()
    mime="image/png" if str(src).lower().endswith("png") else "image/jpeg"
    img=types.Part.from_bytes(data=data, mime_type=mime)
    lines="\n".join(f"{k}→{v}" for k,v in (mapping or {}).items())
    prompt=("Edit this image: replace ONLY the English text labels with their Vietnamese translations, "
            "keeping every shape, color, arrow, position and font identical. Preserve Vietnamese diacritics exactly. "
            + (("Use these translations:\n"+lines) if lines else "") + ("\n"+extra if extra else ""))
    budget.guard(0.15)
    def call():
        return _client().models.generate_content(model=IMG_MODEL, contents=[img, prompt],
            config=types.GenerateContentConfig(response_modalities=["IMAGE"]))
    r=with_retry(call, what=f"img {IMG_MODEL}")
    for p in r.candidates[0].content.parts:
        if getattr(p,"inline_data",None) and p.inline_data.data:
            out.parent.mkdir(parents=True, exist_ok=True); out.write_bytes(p.inline_data.data)
            budget.charge_image(1); return True
    return False
