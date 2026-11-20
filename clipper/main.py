"""Uma rodada do robô:
1. busca clipes em alta dos streamers
2. remove repetidos e já postados
3. ranqueia por "velocidade" (views / idade)
4. renderiza os melhores em vertical com legenda
5. sobe pro R2 e agenda no Metricool no próximo horário livre

Uso:
  python -m clipper.main                      # rodada normal
  python -m clipper.main --teste              # busca + renderiza, NÃO posta (salva em saida/)
  python -m clipper.main --arquivo video.mp4  # só renderiza um arquivo local (teste de visual)
"""
import argparse
import itertools
import os
import tempfile
import time
import traceback
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

from . import estado, legendas, notificacao, render, textos
from .sources import Candidato, kick, twitch, youtube

FONTES = {"twitch": twitch, "kick": kick, "youtube": youtube}


def carregar_config(caminho="config.yaml") -> dict:
    with open(caminho, encoding="utf-8") as f:
        return yaml.safe_load(f)


# ---------------------------------------------------------------- coleta
def coletar(cfg: dict) -> list[Candidato]:
    f = cfg["filtros"]
    todos = []
    for s in cfg["streamers"]:
        if s.get("autorizado") is not True:
            print(f"[pulado] {s.get('nome')}: sem 'autorizado: true' no config.yaml")
            continue
        mod = FONTES.get(s["plataforma"])
        if not mod:
            continue
        minimo = f.get(f"views_minimas_{s['plataforma']}", 0)
        try:
            achados = mod.buscar(s, f["janela_horas"], minimo)
            print(f"[{s['plataforma']}] {s['nome']}: {len(achados)} candidatos")
            for c in achados:
                c.extra["facecam"] = s.get("facecam")
            todos += achados
        except Exception as e:
            print(f"[{s['plataforma']}] {s['nome']}: ERRO {e}")
    return todos


def mesmo_momento(a_vod, a_off, b_vod, b_off, tolerancia=45) -> bool:
    return bool(a_vod) and a_vod == b_vod and a_off is not None and b_off is not None and abs(a_off - b_off) < tolerancia


def filtrar_e_ranquear(cands: list[Candidato], cfg: dict, st: dict) -> list[Candidato]:
    f = cfg["filtros"]
    agora = datetime.now(timezone.utc)
    ok = [
        c for c in cands
        if c.chave not in st["vistos"] and f["duracao_min_s"] <= c.duracao <= f["duracao_max_s"] + 30
    ]
    # o mesmo lance costuma ser clipado por várias pessoas: fica só o mais visto
    ok.sort(key=lambda c: c.views, reverse=True)
    unicos: list[Candidato] = []
    for c in ok:
        if any(mesmo_momento(c.vod_id, c.vod_offset, u.vod_id, u.vod_offset) for u in unicos):
            continue
        if any(mesmo_momento(c.vod_id, c.vod_offset, a.get("vod_id"), a.get("vod_offset")) for a in st["agendados"]):
            continue
        unicos.append(c)
    # velocidade: clipe novo com muita view sobe na frente
    unicos.sort(key=lambda c: c.views / (c.idade_horas(agora) + 2) ** 1.3, reverse=True)
    return unicos


# ---------------------------------------------------------------- horários
def proximos_horarios(cfg: dict, st: dict, dias: int = 3):
    p = cfg["postagem"]
    tz = ZoneInfo(cfg["fuso"])
    agora = datetime.now(tz)
    minimo = agora + timedelta(minutes=p["antecedencia_minima_min"])
    ocupados = {a["horario"] for a in st["agendados"]}
    por_dia: dict[str, int] = {}
    for a in st["agendados"]:
        por_dia[a["horario"][:10]] = por_dia.get(a["horario"][:10], 0) + 1
    for d in range(dias):
        dia = (agora + timedelta(days=d)).date()
        for hhmm in p["horarios"]:
            h, m = map(int, hhmm.split(":"))
            dt = datetime(dia.year, dia.month, dia.day, h, m, tzinfo=tz)
            chave = dt.strftime("%Y-%m-%dT%H:%M:%S")
            if dt < minimo or chave in ocupados or por_dia.get(chave[:10], 0) >= p["max_por_dia"]:
                continue
            yield chave


def cota_streamer_ok(cfg, st, streamer, horario) -> bool:
    n = sum(1 for a in st["agendados"] if a["streamer"] == streamer and a["horario"][:10] == horario[:10])
    return n < cfg["postagem"]["max_por_streamer_por_dia"]


# ---------------------------------------------------------------- produção
def produzir(c: Candidato, cfg: dict, pasta: str) -> tuple[str, dict]:
    v = cfg["video"]
    bruto = os.path.join(pasta, "bruto.mp4")
    FONTES[c.plataforma].baixar(c, bruto)
    dur = min(render.duracao(bruto), cfg["filtros"]["duracao_max_s"])

    palavras = []
    if v.get("legendas", True):
        try:
            palavras = legendas.transcrever(bruto, v.get("modelo_whisper", "small"), v.get("idioma", "pt"))
        except Exception as e:
            print(f"  [legenda] falhou: {e}")
    transcricao = " ".join(w["texto"] for w in palavras)
    txt = textos.gerar(c, transcricao, v.get("hashtags", []))

    ass = legendas.gerar_ass(os.path.join(pasta, "legenda.ass"), dur, txt["gancho"], c.credito, legendas.agrupar(palavras))
    final = os.path.join(pasta, "final.mp4")
    render.renderizar(bruto, final, ass, c.extra.get("facecam"), dur)
    return final, txt


def verificar_publicacoes(cfg: dict, st: dict) -> None:
    """Avisa no celular quando um corte agendado realmente saiu (ou deu erro)."""
    from . import metricool
    tz = ZoneInfo(cfg["fuso"])
    agora = datetime.now(tz)
    for a in st["agendados"]:
        if a.get("avisado_publicacao") or not a.get("post_id"):
            continue
        quando = datetime.fromisoformat(a["horario"]).replace(tzinfo=tz)
        if agora < quando + timedelta(minutes=5):
            continue
        try:
            s = metricool.situacao(a["post_id"])
        except Exception as e:
            print(f"[publicação] erro consultando {a['post_id']}: {e}")
            continue
        if s == "publicado":
            notificacao.enviar("✅ Corte publicado", f"{a['streamer']}: {a.get('gancho', '')}",
                               tags=["white_check_mark"], botoes=[("Abrir Metricool", notificacao.link_metricool())])
            a["avisado_publicacao"] = True
        elif s == "erro":
            notificacao.enviar("⚠️ Falha ao publicar corte", f"{a['streamer']}: {a.get('gancho', '')}",
                               tags=["warning"], botoes=[("Abrir Metricool", notificacao.link_metricool())], prioridade=5)
            a["avisado_publicacao"] = True
        elif s == "apagado" or (s == "rascunho" and agora > quando + timedelta(hours=3)):
            a["avisado_publicacao"] = True  # você apagou ou não aprovou: para de checar


def rodar(teste: bool = False):
    cfg = carregar_config()
    st = estado.carregar()
    if not teste:
        verificar_publicacoes(cfg, st)
    modo_aprovacao = cfg.get("modo", "aprovacao") != "automatico"
    print(f"Modo: {'APROVAÇÃO (rascunhos)' if modo_aprovacao else 'AUTOMÁTICO'}")

    fila = filtrar_e_ranquear(coletar(cfg), cfg, st)
    print(f"{len(fila)} candidatos novos após filtro")
    horarios = proximos_horarios(cfg, st)
    feitos = 0
    limite = cfg["postagem"]["max_cortes_por_execucao"]

    for c in fila:
        if feitos >= limite:
            break
        horario = next(horarios, None)
        if horario is None:
            print("Agenda cheia pelos próximos dias — nada a fazer.")
            break
        if not cota_streamer_ok(cfg, st, c.streamer, horario):
            horarios = itertools.chain([horario], horarios)  # devolve o horário pro próximo clipe
            continue
        print(f"\n▶ {c.streamer} | {c.views} views | {c.titulo[:60]} -> {horario}")
        try:
            with tempfile.TemporaryDirectory() as pasta:
                final, txt = produzir(c, cfg, pasta)
                if teste:
                    Path("saida").mkdir(exist_ok=True)
                    destino = Path("saida") / f"{c.chave.replace(':', '_')}.mp4"
                    os.replace(final, destino)
                    print(f"  [teste] salvo em {destino}\n  gancho: {txt['gancho']}\n  legenda: {txt['legenda']}")
                else:
                    from . import armazenamento, metricool
                    nome = f"cortes/{horario[:10]}/{c.chave.replace(':', '_')}.mp4"
                    url = armazenamento.subir(final, nome)
                    resp = metricool.agendar(
                        url, horario, cfg["fuso"], txt, cfg["redes"], modo_aprovacao,
                        cfg["postagem"].get("tiktok_privacidade", "PUBLIC_TO_EVERYONE"),
                        cfg["video"].get("hashtags", []),
                    )
                    post_id = metricool.id_do_post(resp)
                    hora = horario[11:16]
                    notificacao.enviar(
                        f"🎬 Novo corte {'pra aprovar' if modo_aprovacao else 'agendado'} — {hora}",
                        f"{c.streamer}: {txt['gancho']}\n{c.views} views no clipe original",
                        tags=["clapper"],
                        botoes=[("Ver vídeo", url), ("Abrir Metricool", notificacao.link_metricool())],
                        prioridade=4 if modo_aprovacao else 3,
                    )
                    print(f"  ✔ {'rascunho criado' if modo_aprovacao else 'agendado'} para {horario}")
            st["agendados"].append({
                "chave": c.chave, "streamer": c.streamer, "horario": horario,
                "vod_id": c.vod_id, "vod_offset": c.vod_offset, "ts": time.time(),
                "post_id": None if teste else post_id,
                "gancho": txt["gancho"], "avisado_publicacao": False,
            })
            feitos += 1
        except Exception:
            traceback.print_exc()
            # devolve o horário pra fila tentando outro clipe
            horarios = proximos_horarios(cfg, st)
        st["vistos"][c.chave] = time.time()

    if not teste:
        estado.salvar(st)
    print(f"\nFim: {feitos} corte(s) {'renderizado(s)' if teste else 'na agenda'}.")


def testar_arquivo(caminho: str, facecam=None):
    cfg = carregar_config()
    c = Candidato(
        chave="local:teste", plataforma="local", streamer="Streamer Teste", canal="streamerteste",
        titulo="Fugiu da polícia de bicicleta", url="", views=0,
        criado_em=datetime.now(timezone.utc), duracao=0, credito="twitch.tv/streamerteste",
    )
    dur = min(render.duracao(caminho), cfg["filtros"]["duracao_max_s"])
    palavras = []
    if cfg["video"].get("legendas", True):
        try:
            palavras = legendas.transcrever(caminho, cfg["video"]["modelo_whisper"], cfg["video"]["idioma"])
        except Exception as e:
            print(f"[legenda] indisponível: {e}")
    txt = textos.gerar(c, " ".join(w["texto"] for w in palavras), cfg["video"]["hashtags"])
    Path("saida").mkdir(exist_ok=True)
    ass = legendas.gerar_ass("saida/teste.ass", dur, txt["gancho"], c.credito, legendas.agrupar(palavras))
    render.renderizar(caminho, "saida/teste.mp4", ass, facecam, dur)
    print("Pronto: saida/teste.mp4")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--teste", action="store_true")
    ap.add_argument("--arquivo")
    ap.add_argument("--facecam", help="x,y,w,h em frações, ex.: 0.75,0.7,0.25,0.3")
    a = ap.parse_args()
    if a.arquivo:
        fc = [float(x) for x in a.facecam.split(",")] if a.facecam else None
        testar_arquivo(a.arquivo, fc)
    else:
        rodar(teste=a.teste)
