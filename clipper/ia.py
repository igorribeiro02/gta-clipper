"""Editor com IA (opcional, precisa de ANTHROPIC_API_KEY).

Recebe a transcrição com tempos + os picos de volume e devolve:
- o trecho exato (começa forte, termina na frase de impacto, nunca no meio da frase)
- gancho no formato que mais viraliza: NOME DO STREAMER + O QUE ACONTECEU
- legenda do post e título do Short
"""
import json
import os

import requests


def _frases(palavras: list[dict], gap: float = 0.6) -> list[dict]:
    frases, atual = [], []
    for w in palavras:
        if atual and w["inicio"] - atual[-1]["fim"] > gap:
            frases.append(atual)
            atual = []
        atual.append(w)
    if atual:
        frases.append(atual)
    return [{"i": round(f[0]["inicio"], 1), "f": round(f[-1]["fim"], 1),
             "t": " ".join(x["texto"] for x in f)} for f in frases]


def analisar(c, palavras: list[dict], picos: list[int], dur: float, alvo: float) -> dict | None:
    chave = os.environ.get("ANTHROPIC_API_KEY")
    if not chave or not palavras:
        return None
    frases = "\n".join(f"[{f['i']}-{f['f']}] {f['t']}" for f in _frases(palavras))
    prompt = f"""Você é editor de cortes virais de lives de GTA em português do Brasil.
Streamer: {c.streamer} | Jogo: {c.extra.get('jogo', 'GTA')} | Título do clipe dado pelo chat: {c.titulo!r}
Duração do clipe: {dur:.0f}s. Segundos com volume mais alto (gritos/risadas): {picos}

Transcrição com tempos (segundos):
{frases[:6000]}

Escolha UM trecho entre 15 e {int(alvo) + 7} segundos que:
- comece no máximo 1s antes da ação/reação (sem enrolação nos 3 primeiros segundos)
- tenha começo, meio e fim
- TERMINE logo depois da frase de impacto ou da virada, nunca no meio de uma frase

Responda SÓ com JSON:
{{"inicio": segundos, "fim": segundos,
 "gancho": "frase em CAIXA ALTA de até 60 caracteres: NOME DO STREAMER + o que aconteceu (ex.: 'CORINGA ACHOU O PRIMEIRO BUG DO GTA 6')",
 "legenda": "legenda do post, até 150 caracteres, 1-2 emojis, sem hashtags",
 "titulo": "título do Short até 80 caracteres, com o nome do streamer e do jogo"}}
Não invente nada que não esteja na transcrição ou no título do clipe."""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={"model": os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"), "max_tokens": 500,
                  "messages": [{"role": "user", "content": prompt}]},
            timeout=90,
        )
        r.raise_for_status()
        txt = r.json()["content"][0]["text"]
        d = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        ini, fim = float(d["inicio"]), float(d["fim"])
        if not (0 <= ini < fim <= dur + 0.5 and 8 <= fim - ini <= alvo + 15):
            print(f"  [ia] trecho inválido {ini}-{fim}, usando automático")
            return None
        return {"inicio": ini, "fim": min(fim + 0.4, dur), "gancho": d["gancho"][:60],
                "legenda": d["legenda"], "titulo": d["titulo"][:95]}
    except Exception as e:
        print(f"  [ia] falhou ({e}), usando automático")
        return None
