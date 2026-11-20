"""Gera gancho, legenda do post e título do YouTube.
Com ANTHROPIC_API_KEY usa IA; sem, usa um modelo simples baseado no título do clipe."""
import json
import os
import re

import requests


MODELOS = [
    "O {s} não esperava isso no {j}",
    "Olha o que aconteceu na live do {s}",
    "O {s} perdeu a linha no {j}",
    "Esse momento do {s} no {j}",
    "O chat do {s} não acreditou nisso",
]


def titulo_ruim(t: str) -> bool:
    """Título de clipe feito por viewer costuma ser lixo: 'kkkkk', 'FDSF', 'Q ISSO'."""
    letras = re.sub(r"[^a-zA-ZÀ-ÿ]", "", t or "")
    if len(letras) < 8 or len(t.split()) < 3:
        return True
    return len(set(letras.lower())) <= 3


def _fallback(c, hashtags):
    jogo = c.extra.get("jogo") or "GTA"
    if titulo_ruim(c.titulo):
        modelo = MODELOS[sum(map(ord, c.chave)) % len(MODELOS)]
        base = modelo.format(s=c.streamer, j=jogo)
    else:
        base = re.sub(r"\s+", " ", c.titulo).strip()
    tag_streamer = "#" + re.sub(r"[^a-z0-9]", "", c.canal.lower())
    return {
        "gancho": base[:45],
        "legenda": f"{base} 😂\n\n🎥 Créditos: {c.credito}\n{' '.join(hashtags)} {tag_streamer}",
        "titulo_youtube": f"{base[:80]} | {c.streamer}",
    }


def gerar(c, transcricao: str, hashtags: list[str], manual: dict | None = None) -> dict:
    if manual:  # texto escrito à mão no config.yaml (ganchos_manuais)
        out = _fallback(c, hashtags)
        out["gancho"] = manual.get("gancho", out["gancho"])[:60]
        if manual.get("legenda"):
            tag = "#" + re.sub(r"[^a-z0-9]", "", c.canal.lower())
            out["legenda"] = f"{manual['legenda']}\n\n🎥 Créditos: {c.credito}\n{' '.join(hashtags)} {tag}"
        out["titulo_youtube"] = manual.get("titulo", out["titulo_youtube"])[:95]
        return out
    chave = os.environ.get("ANTHROPIC_API_KEY")
    if not chave:
        return _fallback(c, hashtags)
    prompt = f"""Você escreve textos para cortes virais de GTA RP em português do Brasil.
Streamer: {c.streamer}
Título do clipe: {c.titulo}
Transcrição: {transcricao[:1500]}

Responda SÓ com JSON:
{{"gancho": "frase curta e chamativa pro topo do vídeo, máx 45 caracteres, sem emoji",
 "legenda": "legenda do post, máx 150 caracteres, pode ter 1-2 emojis, sem hashtags",
 "titulo_youtube": "título do Short, máx 80 caracteres"}}
Não invente fatos que não estejam na transcrição ou no título."""
    try:
        r = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": chave, "anthropic-version": "2023-06-01", "content-type": "application/json"},
            json={
                "model": os.environ.get("ANTHROPIC_MODEL", "claude-haiku-5-5"),
                "max_tokens": 400,
                "messages": [{"role": "user", "content": prompt}],
            },
            timeout=60,
        )
        r.raise_for_status()
        txt = r.json()["content"][0]["text"]
        d = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
        tag_streamer = "#" + re.sub(r"[^a-z0-9]", "", c.canal.lower())
        return {
            "gancho": d["gancho"][:45],
            "legenda": f"{d['legenda']}\n\n🎥 Créditos: {c.credito}\n{' '.join(hashtags)} {tag_streamer}",
            "titulo_youtube": d["titulo_youtube"][:95],
        }
    except Exception as e:
        print(f"  [textos] IA falhou ({e}), usando modelo simples")
        return _fallback(c, hashtags)
