"""Filtro visual de nudez/conteúdo sexual (NudeNet, roda no CPU).

O GTA 6 tem clube de strip, praia de nudismo etc. Conta nova que posta isso
toma restrição. Analisa 1 quadro por segundo da área do jogo no corte final.
"""
import os
import subprocess
import tempfile
from collections import Counter

EXPLICITO = {"BUTTOCKS_EXPOSED", "FEMALE_BREAST_EXPOSED", "FEMALE_GENITALIA_EXPOSED",
             "MALE_GENITALIA_EXPOSED", "ANUS_EXPOSED"}
_det = None


def analisar(video: str, dividido: bool) -> tuple[bool, dict]:
    """Retorna (bloquear, contagem). Bloqueia se 2+ quadros com nudez >= 0.4 ou 1 quadro >= 0.6."""
    global _det
    from nudenet import NudeDetector
    if _det is None:
        _det = NudeDetector()
    recorte = "crop=1080:1152:0:768" if dividido else "crop=1080:608:0:656"
    with tempfile.TemporaryDirectory() as d:
        subprocess.run(["ffmpeg", "-loglevel", "error", "-i", video, "-vf", f"fps=1,{recorte}",
                        os.path.join(d, "%03d.jpg")], check=True)
        quadros, forte = Counter(), 0.0
        for f in sorted(os.listdir(d)):
            achou = set()
            for det in _det.detect(os.path.join(d, f)):
                if det["class"] in EXPLICITO and det["score"] >= 0.4:
                    achou.add(det["class"])
                    forte = max(forte, det["score"])
            for a in achou:
                quadros[a] += 1
    total = sum(quadros.values())
    return (total >= 2 or forte >= 0.6), {**quadros, "max": round(forte, 2)}
