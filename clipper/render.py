"""Converte o clipe horizontal em vertical 1080x1920 e queima legenda/gancho/crédito."""
import json
import subprocess


def duracao(caminho: str) -> float:
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "json", caminho],
        capture_output=True, text=True, check=True,
    ).stdout
    return float(json.loads(out)["format"]["duration"])


def _filtro(facecam, ass_path, escurecer=False):
    if facecam:
        x, y, w, h = facecam
        # câmera em cima (1080x640) + gameplay embaixo (1080x1280)
        grafo = (
            f"[0:v]crop=iw*{w}:ih*{h}:iw*{x}:ih*{y},scale=1080:640:force_original_aspect_ratio=increase,crop=1080:640[cam];"
            f"[0:v]crop=ih*1080/1280:ih:(iw-ih*1080/1280)/2:0,scale=1080:1280[jogo];"
            f"[cam][jogo]vstack=inputs=2[base]"
        )
    else:
        # vídeo inteiro no meio + fundo desfocado preenchendo a tela
        grafo = (
            "[0:v]split=2[a][b];"
            "[a]scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,boxblur=25:2,eq=brightness=-0.08[fundo];"
            "[b]scale=1080:-2[frente];"
            "[fundo][frente]overlay=(W-w)/2:(H-h)/2[base]"
        )
    if escurecer:
        grafo += ";[base]eq=brightness=-0.12:saturation=1.2[base2]"
        base = "base2"
    else:
        base = "base"
    if ass_path:
        grafo += f";[{base}]ass={ass_path}[v]"
    else:
        grafo += f";[{base}]null[v]"
    return grafo


def renderizar(entrada: str, saida: str, ass_path: str | None, facecam=None, dur_max: float = 75,
               inicio: float = 0.0) -> str:
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{inicio:.2f}", "-i", entrada, "-t", f"{dur_max:.2f}",
        "-filter_complex", _filtro(facecam, ass_path),
        "-map", "[v]", "-map", "0:a?",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-pix_fmt", "yuv420p", "-r", "30",
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", saida,
    ]
    subprocess.run(cmd, check=True)
    return saida
