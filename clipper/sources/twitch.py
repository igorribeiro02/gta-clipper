"""Twitch: pega os clipes mais vistos das últimas horas (feitos pelo próprio chat).

Clipe criado por viewer = sinal forte de "momento bom". A API devolve
os clipes de um canal já ordenados por views.
"""
import os
from datetime import datetime, timedelta, timezone

import requests

from . import Candidato
from ..download import baixar_url_direta, baixar_com_ytdlp

API = "https://api.twitch.tv/helix"
_token_cache = {}
_id_cache = {}


def _token():
    if "t" not in _token_cache:
        r = requests.post(
            "https://id.twitch.tv/oauth2/token",
            data={
                "client_id": os.environ["TWITCH_CLIENT_ID"],
                "client_secret": os.environ["TWITCH_CLIENT_SECRET"],
                "grant_type": "client_credentials",
            },
            timeout=20,
        )
        r.raise_for_status()
        _token_cache["t"] = r.json()["access_token"]
    return _token_cache["t"]


def _headers():
    return {"Client-Id": os.environ["TWITCH_CLIENT_ID"], "Authorization": f"Bearer {_token()}"}


def _broadcaster_id(login: str) -> str:
    if login not in _id_cache:
        r = requests.get(f"{API}/users", params={"login": login}, headers=_headers(), timeout=20)
        r.raise_for_status()
        data = r.json()["data"]
        if not data:
            raise ValueError(f"Canal da Twitch não encontrado: {login}")
        _id_cache[login] = data[0]["id"]
    return _id_cache[login]


def buscar(streamer: dict, janela_horas: int, views_minimas: int) -> list[Candidato]:
    login = streamer["canal"].lower()
    bid = _broadcaster_id(login)
    inicio = datetime.now(timezone.utc) - timedelta(hours=janela_horas)
    r = requests.get(
        f"{API}/clips",
        params={
            "broadcaster_id": bid,
            "started_at": inicio.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ended_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "first": 50,
        },
        headers=_headers(),
        timeout=20,
    )
    r.raise_for_status()
    out = []
    for c in r.json()["data"]:
        if c["view_count"] < views_minimas:
            continue
        out.append(
            Candidato(
                chave=f"twitch:{c['id']}",
                plataforma="twitch",
                streamer=streamer["nome"],
                canal=login,
                titulo=c["title"],
                url=c["url"],
                views=c["view_count"],
                criado_em=datetime.fromisoformat(c["created_at"].replace("Z", "+00:00")),
                duracao=float(c.get("duration") or 30),
                credito=f"twitch.tv/{login}",
                vod_id=c.get("video_id") or None,
                vod_offset=c.get("vod_offset"),
                extra={"clip_id": c["id"], "broadcaster_id": bid, "editor": bool(streamer.get("editor"))},
            )
        )
    return out


def baixar(c: Candidato, destino: str) -> str:
    """Se você for editor do canal, usa o download OFICIAL da API.
    Senão, cai pro yt-dlp com o link público do clipe."""
    editor_id = os.environ.get("TWITCH_EDITOR_ID")
    if c.extra.get("editor") and editor_id:
        r = requests.get(
            f"{API}/clips/downloads",
            params={"editor_id": editor_id, "broadcaster_id": c.extra["broadcaster_id"], "clip_id": c.extra["clip_id"]},
            headers=_headers(),
            timeout=30,
        )
        if r.ok and r.json().get("data"):
            url = r.json()["data"][0].get("landscape_download_url")
            if url:
                return baixar_url_direta(url, destino)
        print(f"  [twitch] download oficial falhou ({r.status_code}), usando yt-dlp")
    return baixar_com_ytdlp(c.url, destino)
