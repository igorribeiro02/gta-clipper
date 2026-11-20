import os

import requests
import yt_dlp


def baixar_url_direta(url: str, destino: str) -> str:
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    return destino


def baixar_com_ytdlp(url: str, destino: str, inicio: float | None = None, fim: float | None = None) -> str:
    base = os.path.splitext(destino)[0]
    opts = {
        "outtmpl": base + ".%(ext)s",
        "format": "bv*[height<=1080]+ba/b[height<=1080]/b",
        "merge_output_format": "mp4",
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    cookies = os.environ.get("YTDLP_COOKIES_FILE")
    if cookies and os.path.exists(cookies):
        opts["cookiefile"] = cookies
    if inicio is not None and fim is not None:
        opts["download_ranges"] = yt_dlp.utils.download_range_func(None, [(inicio, fim)])
        opts["force_keyframes_at_cuts"] = True
    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([url])
    for ext in ("mp4", "mkv", "webm"):
        p = f"{base}.{ext}"
        if os.path.exists(p):
            if p != destino:
                os.replace(p, destino)
            return destino
    raise FileNotFoundError(f"yt-dlp não gerou arquivo para {url}")
