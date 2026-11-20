"""Gancho, descrição do post (com hashtags) e título do YouTube.

A descrição segue o padrão dos cortes que mais performam:
  frase do momento + pergunta pra puxar comentário
  crédito do streamer (+ aviso de campanha, se houver)
  8–12 hashtags: amplas (#gta6) + nicho (#gtarp) + streamer + tema em alta + #shorts
"""
import re

MODELOS = [  # formato dos cortes que mais viralizaram: o que aconteceu + live do X + reação
    "Olha o que aconteceu no {j} no meio da live do {s}!!",
    "O {s} não esperava isso no {j} e o chat foi à loucura!!",
    "Isso aconteceu no {j} ao vivo e o {s} ficou sem reação!!",
    "O {s} viu isso no {j} e não acreditou!!",
]

PERGUNTAS = [
    "E você, faria o quê nessa situação? 👇",
    "Já aconteceu isso com você no GTA 6? Comenta 👇",
    "Marca aquele amigo que faria igualzinho 😂",
    "Nota de 0 a 10 pra esse momento? 👇",
    "Quer parte 2? Comenta \"PARTE 2\" 👇",
]


def titulo_ruim(t: str) -> bool:
    """Título de clipe feito por viewer costuma ser lixo: 'kkkkk', 'FDSF', 'Q ISSO'."""
    letras = re.sub(r"[^a-zA-ZÀ-ÿ]", "", t or "")
    if len(letras) < 8 or len((t or "").split()) < 3:
        return True
    return len(set(letras.lower())) <= 3


def _tag(t: str) -> str:
    t = re.sub(r"[^a-z0-9à-ÿ]", "", t.lower().lstrip("#"))
    return "#" + t if t else ""


def hashtags(c, base: list[str]) -> str:
    s = c.extra.get("cfg_streamer") or {}
    nome = _tag(c.canal)
    tags = [*base, *c.extra.get("tema_tags", []), nome, _tag("cortes" + c.canal), *s.get("hashtags", []), "#shorts"]
    vistos, out = set(), []
    for t in tags:
        t = _tag(t)
        if t and t not in vistos:
            vistos.add(t)
            out.append(t)
    return " ".join(out[:12])


def descricao(c, frase: str, base_tags: list[str]) -> str:
    s = c.extra.get("cfg_streamer") or {}
    pergunta = PERGUNTAS[sum(map(ord, c.chave)) % len(PERGUNTAS)]
    linhas = [frase.strip(), "", pergunta, "", f"🎥 Créditos: {c.credito}"]
    if s.get("aviso"):  # ex.: campanha paga exige aviso claro
        linhas.append(s["aviso"])
    linhas += ["", hashtags(c, base_tags)]
    return "\n".join(linhas)


def gerar(c, transcricao: str, base_tags: list[str], manual: dict | None = None) -> dict:
    jogo = c.extra.get("jogo") or "GTA"
    if titulo_ruim(c.titulo):
        base = MODELOS[sum(map(ord, c.chave)) % len(MODELOS)].format(s=c.streamer, j=jogo)
    else:
        base = re.sub(r"\s+", " ", c.titulo).strip()
    out = {
        "gancho": base[:115],
        "legenda": descricao(c, f"{base} 😂", base_tags),
        "titulo_youtube": f"{base[:80]} | {c.streamer}",
    }
    if manual:  # textos do config (ganchos_manuais) ou do editor com IA
        out["gancho"] = manual.get("gancho", out["gancho"])[:115]
        if manual.get("legenda"):
            out["legenda"] = descricao(c, manual["legenda"], base_tags)
        out["titulo_youtube"] = manual.get("titulo", out["titulo_youtube"])[:95]
    return out


def detectar_temas(texto: str, temas: list[dict]) -> tuple[int, list[str]]:
    """Quantos temas em alta o texto toca e as hashtags deles."""
    texto = (texto or "").lower()
    n, tags = 0, []
    for t in temas or []:
        if any(p in texto for p in t.get("palavras", [])):
            n += 1
            tags += t.get("hashtags", [])
    return n, tags
