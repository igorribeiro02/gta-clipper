"""Kick: clipes mais vistos do dia.

ATENÇÃO: a Kick não tem API oficial de clipes. Isso usa o endpoint
interno do site, que pode mudar ou bloquear IPs de servidores
(erro 403). Se parar de funcionar, o resto do pipeline continua.
"""
from datetime import datetime, timezone

import requests

from . import Candidato
from ..download import baixar_com_ytdlp, baixar_url_direta

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130 Safari/537.36",
    "Accept": "application/json",
}


def _data(s):
    try:
        return datetime.fromisoformat(str(s).replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def buscar(streamer: dict, janela_horas: int, views_minimas: int) -> list[Candidato]:
    slug = streamer["canal"].lower()
    r = requests.get(
        f"https://kick.com/api/v2/channels/{slug}/clips",
        params={"sort": "view", "time": "day"},
        headers=HEADERS,
        timeout=20,
    )
    if r.status_code != 200:
        print(f"  [kick] {slug}: HTTP {r.status_code} (endpoint não oficial bloqueou) — pulando")
        return []
    agora = datetime.now(timezone.utc)
    out = []
    for c in r.json().get("clips", []):
        views = int(c.get("views") or c.get("view_count") or 0)
        criado = _data(c.get("created_at"))
        if views < views_minimas or (agora - criado).total_seconds() > janela_horas * 3600:
            continue
        cid = str(c.get("id"))
        out.append(
            Candidato(
                chave=f"kick:{cid}",
                plataforma="kick",
                streamer=streamer["nome"],
                canal=slug,
                titulo=c.get("title") or "",
                url=f"https://kick.com/{slug}/clips/{cid}",
                views=views,
                criado_em=criado,
                duracao=float(c.get("duration") or 30),
                credito=f"kick.com/{slug}",
                vod_id=str(c.get("livestream_id") or "") or None,
                extra={"video_url": c.get("video_url") or c.get("clip_url"),
                       "jogo": "GTA 6" if "VI" in str((c.get("category") or {}).get("name", "")) else "GTA"},
            )
        )
    return out


def baixar(c: Candidato, destino: str) -> str:
    direta = c.extra.get("video_url")
    if direta and direta.endswith(".mp4"):
        return baixar_url_direta(direta, destino)
    return baixar_com_ytdlp(direta or c.url, destino)
