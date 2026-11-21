"""Acha a câmera do streamer sozinho.

Ideia: o rosto da facecam fica PARADO no mesmo lugar o clipe inteiro,
enquanto rostos do jogo (NPCs) mudam de posição. Detecta rostos em
vários quadros e fica com o que aparece no mesmo lugar na maioria deles.
"""
import subprocess
import tempfile
from pathlib import Path


def _quadros(caminho: str, dur: float, n: int = 7) -> list[str]:
    pasta = Path(tempfile.mkdtemp())
    saidas = []
    for i in range(n):
        t = dur * (i + 0.5) / n
        p = pasta / f"q{i}.jpg"
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", f"{t:.2f}", "-i", caminho,
                        "-frames:v", "1", "-q:v", "3", str(p)], check=False)
        if p.exists():
            saidas.append(str(p))
    return saidas


def detectar(caminho: str, dur: float):
    """Retorna [x, y, w, h] em frações do quadro, ou None se não achar com segurança."""
    try:
        import cv2
    except ImportError:
        return None
    cascata = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    deteccoes = []  # (quadro, x, y, w, h) normalizados
    W = H = None
    quadros = _quadros(caminho, dur)
    for i, q in enumerate(quadros):
        img = cv2.imread(q)
        if img is None:
            continue
        H, W = img.shape[:2]
        cinza = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        for (x, y, w, h) in cascata.detectMultiScale(cinza, 1.1, 6, minSize=(int(W * 0.02), int(W * 0.02))):
            if w / W > 0.25:  # rosto enorme = cena do jogo, não facecam
                continue
            deteccoes.append((i, x / W, y / H, w / W, h / H))
    if not deteccoes or not W:
        return None
    # agrupa rostos no mesmo lugar e conta em quantos quadros diferentes apareceram
    melhor, votos = None, 0
    for _, x, y, w, h in deteccoes:
        cx, cy = x + w / 2, y + h / 2
        quadros_com = {j for j, x2, y2, w2, h2 in deteccoes
                       if abs((x2 + w2 / 2) - cx) < w * 0.6 and abs((y2 + h2 / 2) - cy) < h * 0.6}
        if len(quadros_com) > votos:
            melhor, votos = (x, y, w, h), len(quadros_com)
    if votos < max(3, len(quadros) // 2):
        return None
    x, y, w, h = melhor
    # webcam fica no canto/lateral e o rosto nela é pequeno; rosto grande no meio = personagem do jogo
    if w > 0.07 or 0.33 < x + w / 2 < 0.67:
        return None
    # caixa da webcam ~ 5x a largura do rosto, proporção 16:9 (em pixels)
    cw = min(w * 5.0, 0.45)
    ch = min(cw * (W / H) * 9 / 16, 0.6)
    cx, cy = x + w / 2, y + h / 2 + h * 0.15
    bx = min(max(cx - cw / 2, 0), 1 - cw)
    by = min(max(cy - ch / 2, 0), 1 - ch)
    return [round(float(v), 4) for v in (bx, by, cw, ch)]
