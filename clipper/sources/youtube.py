"""YouTube: usa o gráfico "Mais repetidos" (heatmap) das lives/VODs recentes
para achar os picos de audiência e cortar só aquele trecho.

Observações:
- O heatmap só aparece depois que o vídeo junta views suficientes,
  então lives que acabaram de terminar podem não ter picos ainda
  (o robô tenta de novo nas próximas rodadas).
- Servidores do GitHub às vezes recebem "confirme que não é um robô".
  Se acontecer, exporte cookies do navegador e salve no segredo
  YTDLP_COOKIES (ver README).
"""
from datetime import datetime, timedelta, timezone

import yt_dlp

from . import Candidato
from ..download import baixar_com_ytdlp

ANTES_DO_PICO = 20
DEPOIS_DO_PICO = 30


def _opts():
    import os
    o = {"quiet": True, "no_warnings": True, "skip_download": True}
    c = os.environ.get("YTDLP_COOKIES_FILE")
    if c and os.path.exists(c):
        o["cookiefile"] = c
    return o


def _picos(heatmap: list[dict], n: int = 2) -> list[float]:
    """Retorna o centro dos n maiores picos sem sobreposição."""
    pts = sorted(heatmap, key=lambda h: h["value"], reverse=True)
    escolhidos: list[float] = []
    for h in pts:
        if h["value"] < 0.5:
            break
        centro = (h["start_time"] + h["end_time"]) / 2
        if all(abs(centro - e) > ANTES_DO_PICO + DEPOIS_DO_PICO for e in escolhidos):
            escolhidos.append(centro)
        if len(escolhidos) >= n:
            break
    return escolhidos


def buscar(streamer: dict, janela_horas: int, views_minimas: int) -> list[Candidato]:
    handle = streamer["canal"].lstrip("@")
    agora = datetime.now(timezone.utc)
    lista_url = f"https://www.youtube.com/@{handle}/streams"
    with yt_dlp.YoutubeDL({**_opts(), "extract_flat": True, "playlistend": 4}) as ydl:
        lista = ydl.extract_info(lista_url, download=False) or {}
    out = []
    # VODs têm heatmap só depois de um tempo, então olhamos uma janela maior
    limite = agora - timedelta(hours=max(janela_horas, 36))
    for e in lista.get("entries") or []:
        vid = e.get("id")
        if not vid:
            continue
        try:
            with yt_dlp.YoutubeDL(_opts()) as ydl:
                info = ydl.extract_info(f"https://www.youtube.com/watch?v={vid}", download=False)
        except Exception as ex:
            print(f"  [youtube] {vid}: {ex}")
            continue
        if info.get("is_live") or info.get("live_status") == "is_live":
            continue  # ainda ao vivo, espera acabar
        ts = info.get("release_timestamp") or info.get("timestamp")
        criado = datetime.fromtimestamp(ts, timezone.utc) if ts else agora
        if criado < limite:
            continue
        for centro in _picos(info.get("heatmap") or []):
            ini = max(centro - ANTES_DO_PICO, 0)
            fim = min(centro + DEPOIS_DO_PICO, info.get("duration") or centro + DEPOIS_DO_PICO)
            out.append(
                Candidato(
                    chave=f"youtube:{vid}:{int(ini)}",
                    plataforma="youtube",
                    streamer=streamer["nome"],
                    canal=handle,
                    titulo=info.get("title") or "",
                    url=info.get("webpage_url"),
                    views=int(info.get("view_count") or 0),
                    criado_em=criado,
                    duracao=fim - ini,
                    credito=f"youtube.com/@{handle}",
                    vod_id=vid,
                    vod_offset=ini,
                    extra={"inicio": ini, "fim": fim},
                )
            )
    return out


def baixar(c: Candidato, destino: str) -> str:
    return baixar_com_ytdlp(c.url, destino, c.extra["inicio"], c.extra["fim"])
