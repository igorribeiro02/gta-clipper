"""Memória do robô entre execuções (salva em state/state.json e commitada no repo)."""
import json
import time
from pathlib import Path

ARQ = Path("state/state.json")
DIAS_GUARDAR = 14


def carregar() -> dict:
    if ARQ.exists():
        s = json.loads(ARQ.read_text(encoding="utf-8"))
    else:
        s = {}
    s.setdefault("vistos", {})       # chave -> timestamp
    s.setdefault("agendados", [])    # [{chave, streamer, horario, vod_id, vod_offset}]
    return s


def salvar(s: dict) -> None:
    limite = time.time() - DIAS_GUARDAR * 86400
    s["vistos"] = {k: v for k, v in s["vistos"].items() if v > limite}
    s["agendados"] = [a for a in s["agendados"] if a.get("ts", time.time()) > limite]
    ARQ.parent.mkdir(parents=True, exist_ok=True)
    ARQ.write_text(json.dumps(s, ensure_ascii=False, indent=1), encoding="utf-8")
