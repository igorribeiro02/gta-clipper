"""Agenda o corte no Metricool, que publica no TikTok, Instagram e YouTube.

Por que Metricool e não as APIs de cada rede direto?
- TikTok: app próprio sem auditoria só posta em modo PRIVADO.
- Instagram: exige app no Meta for Developers + conta Business.
- YouTube: cota diária baixa por padrão.
O Metricool já é aprovado nas três. Requer plano com acesso à API.
"""
import os

import requests

BASE = "https://app.metricool.com/api"


def _auth():
    return (
        {"X-Mc-Auth": os.environ["METRICOOL_TOKEN"], "Content-Type": "application/json"},
        {"userId": os.environ["METRICOOL_USER_ID"], "blogId": os.environ["METRICOOL_BLOG_ID"]},
    )


def normalizar_midia(url_publica: str) -> str:
    """Faz o Metricool hospedar o vídeo nos servidores dele."""
    h, p = _auth()
    r = requests.get(f"{BASE}/actions/normalize/image/url", params={**p, "url": url_publica}, headers=h, timeout=120)
    r.raise_for_status()
    try:
        d = r.json()
        if isinstance(d, str):
            return d
        return d.get("url") or d.get("data") or url_publica
    except ValueError:
        return r.text.strip().strip('"') or url_publica


def agendar(video_url: str, quando_local: str, fuso: str, textos: dict, redes: list[str],
            rascunho: bool, tiktok_privacidade: str, tags: list[str], capa_url: str | None = None) -> dict:
    h, p = _auth()
    midia = normalizar_midia(video_url)
    corpo = {
        "publicationDate": {"dateTime": quando_local, "timezone": fuso},
        "text": textos["legenda"],
        "providers": [{"network": r} for r in redes],
        "media": [midia],
        "mediaAltText": [],
        "draft": rascunho,
        "autoPublish": True,
        "shortener": False,
        "firstCommentText": "",
        "descendants": [],
        "hasNotReadNotes": False,
        "smartLinkData": {"ids": []},
    }
    if capa_url:
        corpo["videoThumbnailUrl"] = capa_url
    if "instagram" in redes:
        corpo["instagramData"] = {"type": "REEL", "showReelOnFeed": True}
    if "tiktok" in redes:
        corpo["tiktokData"] = {
            "privacyOption": tiktok_privacidade,
            "title": textos["titulo_youtube"][:90],  # o Metricool exige título no TikTok
            "disableComment": False, "disableDuet": False, "disableStitch": False,
            "commercialContentThirdParty": False, "commercialContentOwnBrand": False,
        }
    if "youtube" in redes:
        corpo["youtubeData"] = {
            "title": textos["titulo_youtube"],
            "type": "short",
            "privacy": "public",
            "madeForKids": False,
            "category": "GAMING",
            "tags": [t.lstrip("#") for t in tags][:15],
        }
    r = requests.post(f"{BASE}/v2/scheduler/posts", params=p, headers=h, json=corpo, timeout=60)
    if not r.ok:
        raise RuntimeError(f"Metricool {r.status_code}: {r.text[:500]}")
    return r.json() if r.content else {}


def id_do_post(resposta: dict):
    d = resposta.get("data", resposta) if isinstance(resposta, dict) else {}
    return d.get("id") or d.get("postId") if isinstance(d, dict) else None


def situacao(post_id) -> str:
    """Devolve 'rascunho', 'erro', 'publicado' ou 'desconhecido'.
    (Os nomes exatos dos campos de status do Metricool serão confirmados no 1º teste real.)"""
    h, p = _auth()
    r = requests.get(f"{BASE}/v2/scheduler/posts/{post_id}", params=p, headers=h, timeout=30)
    if r.status_code == 404:
        return "apagado"
    if not r.ok:
        return "desconhecido"
    d = r.json()
    d = d.get("data", d)
    if d.get("draft"):
        return "rascunho"
    texto = str(d.get("providers", "")).upper() + str(d.get("status", "")).upper()
    if "ERROR" in texto or "FAIL" in texto:
        return "erro"
    if "PUBLISHED" in texto or "SUCCESS" in texto:
        return "publicado"
    return "desconhecido"
