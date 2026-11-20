"""Hospeda o vídeo pronto num link público para o Metricool buscar.

- Se os segredos do Cloudflare R2 existirem, usa o R2.
- Senão, usa o próprio repositório: o vídeo vai para o branch "midia"
  e o link é o raw.githubusercontent.com (grátis, sem conta extra).
  O branch é recriado a cada envio guardando só os últimos dias,
  pra não inchar o repositório.
"""
import json
import os
import shutil
import subprocess
import time
from pathlib import Path

BRANCH = "midia"
PASTA = Path("/tmp/midia")
DIAS_GUARDAR = 4


def _r2_configurado() -> bool:
    return all(os.environ.get(k) for k in ("R2_ACCOUNT_ID", "R2_ACCESS_KEY_ID", "R2_SECRET_ACCESS_KEY", "R2_BUCKET", "R2_PUBLIC_BASE_URL"))


def _subir_r2(caminho: str, nome: str) -> str:
    import boto3
    s3 = boto3.client(
        "s3",
        endpoint_url=f"https://{os.environ['R2_ACCOUNT_ID']}.r2.cloudflarestorage.com",
        aws_access_key_id=os.environ["R2_ACCESS_KEY_ID"],
        aws_secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
        region_name="auto",
    )
    s3.upload_file(caminho, os.environ["R2_BUCKET"], nome, ExtraArgs={"ContentType": "video/mp4"})
    return f"{os.environ['R2_PUBLIC_BASE_URL'].rstrip('/')}/{nome}"


def _git(*args, cwd=PASTA, check=True):
    return subprocess.run(["git", *args], cwd=cwd, check=check, capture_output=True, text=True)


def _preparar_pasta():
    """Baixa o conteúdo atual do branch midia (se existir) para /tmp/midia."""
    if (PASTA / ".git").exists():
        return
    PASTA.mkdir(parents=True, exist_ok=True)
    origem = _git("remote", "get-url", "origin", cwd=".").stdout.strip()
    _git("init", "-q")
    _git("remote", "add", "origin", origem)
    _git("config", "user.name", "gta-clipper-bot")
    _git("config", "user.email", "gta-clipper-bot@users.noreply.github.com")
    # reaproveita o token do checkout do GitHub Actions
    extra = _git("config", "--get-all", "http.https://github.com/.extraheader", cwd=".", check=False).stdout.strip()
    if extra:
        _git("config", "http.https://github.com/.extraheader", extra)
    if _git("fetch", "-q", "--depth", "1", "origin", BRANCH, check=False).returncode == 0:
        _git("checkout", "-q", "FETCH_HEAD", "--", ".", check=False)


def _limpar_antigos():
    limite = time.time() - DIAS_GUARDAR * 86400
    for p in PASTA.rglob("*.mp4"):
        if p.stat().st_mtime < limite:
            p.unlink()


def _publicar_branch(msg: str):
    _git("checkout", "-q", "--orphan", f"tmp-{time.time_ns()}")
    _git("add", "-A")
    _git("commit", "-q", "-m", msg, check=False)
    for tentativa in range(3):
        if _git("push", "-q", "-f", "origin", f"HEAD:{BRANCH}", check=False).returncode == 0:
            return
        time.sleep(3 * (tentativa + 1))
    raise RuntimeError("não consegui enviar o vídeo para o branch midia")


def _subir_git(caminho: str, nome: str) -> str:
    _preparar_pasta()
    _limpar_antigos()
    destino = PASTA / nome
    destino.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy(caminho, destino)
    _publicar_branch(f"corte: {nome}")
    repo = os.environ.get("GITHUB_REPOSITORY", "igorribeiro02/gta-clipper")
    time.sleep(5)  # dá tempo do raw.githubusercontent enxergar o arquivo
    return f"https://raw.githubusercontent.com/{repo}/{BRANCH}/{nome}"


def subir(caminho: str, nome: str) -> str:
    return _subir_r2(caminho, nome) if _r2_configurado() else _subir_git(caminho, nome)


def registrar_na_fila(item: dict) -> None:
    """Quando não há token da API do Metricool, guarda o corte em fila.json
    (no branch midia) para o Claude agendar pelo conector."""
    _preparar_pasta()
    arq = PASTA / "fila.json"
    fila = json.loads(arq.read_text(encoding="utf-8")) if arq.exists() else []
    fila.append(item)
    arq.write_text(json.dumps(fila, ensure_ascii=False, indent=1), encoding="utf-8")
    _publicar_branch(f"fila: {item.get('chave')}")
