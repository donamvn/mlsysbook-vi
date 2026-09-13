"""Sổ chi tiêu Google + trần cứng. Dừng trước khi vượt để bảo vệ credit."""
from __future__ import annotations
import json, os, threading
from pathlib import Path
from . import config as C

LEDGER = C.WORK / "spend.json"
CAP = float(os.getenv("GOOGLE_BUDGET_USD", "1.0"))
P = {
    "flash_in": float(os.getenv("PRICE_GEMINI_FLASH_IN","0.30"))/1e6,
    "flash_out": float(os.getenv("PRICE_GEMINI_FLASH_OUT","2.50"))/1e6,
    "pro_in": float(os.getenv("PRICE_GEMINI_PRO_IN","1.25"))/1e6,
    "pro_out": float(os.getenv("PRICE_GEMINI_PRO_OUT","10.0"))/1e6,
    "image": float(os.getenv("PRICE_GEMINI_IMAGE","0.04")),
}
_lock = threading.Lock()

class BudgetExceeded(RuntimeError): pass

def _load() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text())
    return {"usd":0.0,"flash_in":0,"flash_out":0,"pro_in":0,"pro_out":0,"images":0,"calls":0}

def _save(d): LEDGER.parent.mkdir(parents=True, exist_ok=True); LEDGER.write_text(json.dumps(d,indent=1))

def state() -> dict: return _load()
def remaining() -> float: return max(0.0, CAP - _load()["usd"])

def guard(est: float = 0.0):
    """Gọi TRƯỚC mỗi lệnh tốn tiền; chặn nếu (đã tiêu + ước tính) vượt trần."""
    d=_load()
    if d["usd"] + est > CAP:
        raise BudgetExceeded(f"Chạm trần Google {CAP:.2f} USD (đã tiêu {d['usd']:.4f}). "
                             f"Tăng GOOGLE_BUDGET_USD trong .env để chạy tiếp.")

def charge_tokens(model: str, tin: int, tout: int) -> float:
    pro = "pro" in (model or "")
    ci = P["pro_in" if pro else "flash_in"]; co = P["pro_out" if pro else "flash_out"]
    cost = tin*ci + tout*co
    with _lock:
        d=_load()
        d["usd"]+=cost; d["calls"]+=1
        d["pro_in" if pro else "flash_in"]+=tin; d["pro_out" if pro else "flash_out"]+=tout
        _save(d)
    return cost

def charge_image(n: int = 1) -> float:
    cost = n*P["image"]
    with _lock:
        d=_load(); d["usd"]+=cost; d["images"]+=n; d["calls"]+=1; _save(d)
    return cost
