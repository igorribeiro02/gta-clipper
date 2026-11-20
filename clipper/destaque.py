"""Acha o trecho mais forte do clipe e gera a capa.

Melhor trecho = janela de N segundos com maior "energia":
  volume do áudio (gritos, risadas, explosões)  +  densidade de fala (legenda)
É o jeito barato de achar o pico de reação do streamer sem assistir.
"""
import math
import re
import subprocess


def volume_por_segundo(caminho: str) -> list[float]:
    """RMS do áudio a cada 1s (em escala linear 0..1)."""
    cmd = [
        "ffmpeg", "-hide_banner", "-nostats", "-i", caminho, "-vn",
        "-af", "aresample=16000,asetnsamples=16000,astats=metadata=1:reset=1,"
               "ametadata=print:key=lavfi.astats.Overall.RMS_level",
        "-f", "null", "-",
    ]
    err = subprocess.run(cmd, capture_output=True, text=True).stderr
    vals = []
    for m in re.finditer(r"RMS_level=(-?[\d.]+|-inf)", err):
        db = m.group(1)
        vals.append(0.0 if db == "-inf" else 10 ** (float(db) / 20))
    return vals


def melhor_trecho(caminho: str, duracao: float, palavras: list[dict], alvo: float) -> tuple[float, float, float]:
    """Retorna (inicio, fim, segundo_de_pico)."""
    if duracao <= alvo + 3:
        vol = volume_por_segundo(caminho) or [0]
        pico = max(range(len(vol)), key=vol.__getitem__)
        return 0.0, duracao, float(pico)
    vol = volume_por_segundo(caminho)
    n = max(len(vol), int(math.ceil(duracao)))
    vol += [0.0] * (n - len(vol))
    mx = max(vol) or 1
    fala = [0] * n
    for w in palavras:
        s = int(w["inicio"])
        if 0 <= s < n:
            fala[s] += 1
    mf = max(fala) or 1
    nota = [0.7 * (v / mx) + 0.3 * (f / mf) for v, f in zip(vol, fala)]
    L = int(alvo)
    soma = sum(nota[:L])
    melhor, ini = soma, 0
    for i in range(1, n - L + 1):
        soma += nota[i + L - 1] - nota[i - 1]
        if soma > melhor:
            melhor, ini = soma, i
    # começa 1s antes pra não cortar a frase no meio, se der
    inicio = max(ini - 1, 0)
    if palavras:  # alinha o início com o começo de uma fala próxima
        perto = [w["inicio"] for w in palavras if inicio - 1.5 <= w["inicio"] <= inicio + 1.5]
        if perto:
            inicio = max(min(perto) - 0.3, 0)
    fim = min(inicio + alvo, duracao)
    fim = fechar_na_frase(palavras, fim, duracao)
    janela = range(int(inicio), int(fim))
    pico = max(janela, key=lambda s: vol[s]) if janela else inicio
    return float(inicio), float(fim), float(pico)


def fechar_na_frase(palavras: list[dict], fim: float, duracao: float) -> float:
    """Move o fim pro final de uma frase (pausa >= 0.5s) perto do fim escolhido."""
    candidatos = []
    for a, b in zip(palavras, palavras[1:] + [None]):
        pausa = (b["inicio"] - a["fim"]) if b else 9
        if pausa >= 0.5 and fim - 5 <= a["fim"] <= fim + 3:
            candidatos.append(a["fim"])
    if candidatos:
        return min(min(candidatos, key=lambda t: abs(t - fim)) + 0.5, duracao)
    return fim


def picos(caminho: str, n: int = 6) -> list[int]:
    vol = volume_por_segundo(caminho)
    return sorted(sorted(range(len(vol)), key=vol.__getitem__, reverse=True)[:n])


def deslocar(palavras: list[dict], inicio: float, fim: float) -> list[dict]:
    return [
        {"inicio": w["inicio"] - inicio, "fim": w["fim"] - inicio, "texto": w["texto"]}
        for w in palavras if inicio <= w["inicio"] < fim
    ]


CAPA_ASS = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Titulo,DejaVu Sans,104,&H00FFFFFF,&H00FFFFFF,&H00000000,&H96000000,1,0,0,0,100,100,0,0,1,9,6,5,70,70,0,1
Style: Faixa,DejaVu Sans,52,&H00000000,&H00000000,&H0000D7FF,&H00000000,1,0,0,0,100,100,0,0,3,16,0,8,70,70,170,1
Style: Credito,DejaVu Sans,44,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,4,0,2,60,60,150,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def _esc(t: str) -> str:
    return t.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def gerar_capa(entrada: str, segundo: float, saida_jpg: str, gancho: str, streamer: str,
               credito: str, ass_path: str, layout_filtro) -> str:
    """Pega o quadro do pico, monta vertical e escreve o gancho gigante no meio."""
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(CAPA_ASS)
        f.write(f"Dialogue: 0,0:00:00.00,0:00:05.00,Faixa,,0,0,0,,{_esc(streamer).upper()}\n")
        f.write(f"Dialogue: 0,0:00:00.00,0:00:05.00,Titulo,,0,0,0,,{_esc(gancho).upper()}\n")
        f.write(f"Dialogue: 0,0:00:00.00,0:00:05.00,Credito,,0,0,0,,▶ {_esc(credito)}\n")
    grafo = layout_filtro(ass_path)
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error", "-ss", f"{max(segundo, 0):.2f}", "-i", entrada,
        "-filter_complex", grafo, "-map", "[v]", "-frames:v", "1", "-q:v", "3", saida_jpg,
    ], check=True)
    return saida_jpg
