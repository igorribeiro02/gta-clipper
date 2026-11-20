"""Gera gancho, legenda do post e título do YouTube.
Com ANTHROPIC_API_KEY usa IA; sem, usa um modelo simples baseado no título do clipe."""
import json
import os
import re

import requests


def _fallback(c, hashtags):
    base = re.sub(r"\s+", " ", c.titulo or "").strip() or f"Momento insano do {c.streamer} no GTA RP"
    tag_streamer = "#" + re.sub(r"[^a-z0-9]", "", c.canal.lower())
    return {
        "gancho": base[:45],
        "legenda": f"{base} 😂\n\n🎥 Créditos: {c.credito}\n{' '.join(hashtags)} {tag_streamer}",
        "titulo_youtube": f"{base[:80]} | {c.streamer}",
    }


def gerar(c, transcricao: str, hashtags: list[str]) -> dict:
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
