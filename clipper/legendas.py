"""Transcreve o áudio (faster-whisper) e gera um arquivo .ass com:
- legenda palavra-por-palavra estilo TikTok
- gancho (título) no topo
- crédito do streamer embaixo
"""
_modelo = None


def _t(seg: float) -> str:
    seg = max(seg, 0)
    h = int(seg // 3600)
    m = int(seg % 3600 // 60)
    s = seg % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def _esc(txt: str) -> str:
    return txt.replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", " ").strip()


def transcrever(caminho: str, modelo: str = "small", idioma: str = "pt") -> list[dict]:
    global _modelo
    from faster_whisper import WhisperModel

    if _modelo is None:
        _modelo = WhisperModel(modelo, device="cpu", compute_type="int8")
    segs, _ = _modelo.transcribe(caminho, language=idioma, word_timestamps=True, vad_filter=True)
    palavras = []
    for s in segs:
        for w in s.words or []:
            palavras.append({"inicio": w.start, "fim": w.end, "texto": w.word.strip()})
    return palavras


def agrupar(palavras: list[dict], max_palavras: int = 3, max_gap: float = 0.6) -> list[dict]:
    blocos, atual = [], []
    for w in palavras:
        if atual and (len(atual) >= max_palavras or w["inicio"] - atual[-1]["fim"] > max_gap):
            blocos.append(atual)
            atual = []
        atual.append(w)
    if atual:
        blocos.append(atual)
    return [
        {"inicio": b[0]["inicio"], "fim": b[-1]["fim"], "texto": " ".join(x["texto"] for x in b)}
        for b in blocos
    ]


CABECALHO = """[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Legenda,DejaVu Sans,80,&H00FFFFFF,&H00FFFFFF,&H00000000,&H64000000,1,0,0,0,100,100,0,0,1,7,2,2,60,60,560,1
Style: Gancho,DejaVu Sans,62,&H00FFFFFF,&H00FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,3,18,0,8,70,70,150,1
Style: Credito,DejaVu Sans,38,&H30FFFFFF,&H30FFFFFF,&H00000000,&H00000000,1,0,0,0,100,100,0,0,1,3,0,2,60,60,110,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""


def gerar_ass(destino: str, duracao: float, gancho: str, credito: str, blocos: list[dict]) -> str:
    linhas = [CABECALHO]
    if gancho:
        linhas.append(f"Dialogue: 1,{_t(0)},{_t(duracao)},Gancho,,0,0,0,,{_esc(gancho).upper()}\n")
    if credito:
        linhas.append(f"Dialogue: 1,{_t(0)},{_t(duracao)},Credito,,0,0,0,,▶ {_esc(credito)}\n")
    for b in blocos:
        fim = max(b["fim"], b["inicio"] + 0.25)
        linhas.append(f"Dialogue: 0,{_t(b['inicio'])},{_t(fim)},Legenda,,0,0,0,,{_esc(b['texto']).upper()}\n")
    with open(destino, "w", encoding="utf-8") as f:
        f.writelines(linhas)
    return destino
