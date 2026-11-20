"""Avisos no celular pelo app ntfy (grátis).

Instale o ntfy no celular, inscreva-se no tópico salvo no segredo NTFY_TOPIC.
Sem NTFY_TOPIC configurado, os avisos são simplesmente ignorados.
"""
import os

import requests


def enviar(titulo: str, mensagem: str, tags: list[str] | None = None,
           botoes: list[tuple[str, str]] | None = None, prioridade: int = 3) -> None:
    topico = os.environ.get("NTFY_TOPIC")
    if not topico:
        return
    corpo = {
        "topic": topico,
        "title": titulo,
        "message": mensagem,
        "tags": tags or [],
        "priority": prioridade,
    }
    if botoes:
        corpo["actions"] = [{"action": "view", "label": rotulo, "url": url} for rotulo, url in botoes[:3]]
        corpo["click"] = botoes[0][1]
    try:
        requests.post(os.environ.get("NTFY_SERVER", "https://ntfy.sh"), json=corpo, timeout=15).raise_for_status()
    except Exception as e:
        print(f"  [ntfy] falhou: {e}")


def link_metricool() -> str:
    blog = os.environ.get("METRICOOL_BLOG_ID", "")
    return f"https://app.metricool.com/planner?blogId={blog}"
