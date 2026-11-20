# 🎮 GTA Clipper

Robô que pega os **momentos mais clipados** das lives de GTA RP (Twitch, Kick e YouTube), transforma em **vídeo vertical com legenda**, e **agenda no TikTok, Instagram Reels e YouTube Shorts** ao longo do dia.

Roda sozinho no **GitHub Actions a cada 30 minutos**, sem precisar deixar o PC ligado.

---

## Como funciona

```
 a cada 30 min (GitHub Actions)
          │
          ▼
 ┌─────────────────────┐
 │ 1. COLETA           │  Twitch: clipes mais vistos das últimas 8h (API oficial)
 │                     │  Kick:   clipes do dia (endpoint não oficial)
 │                     │  YouTube: picos do gráfico "mais repetidos" das lives
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 2. FILTRO + RANKING │  tira repetidos e já postados
 │                     │  o mesmo lance clipado por 5 pessoas → fica só 1
 │                     │  nota = views ÷ idade  (o que está bombando AGORA)
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 3. EDIÇÃO           │  vertical 1080x1920 (facecam em cima ou fundo desfocado)
 │                     │  legenda palavra a palavra (Whisper)
 │                     │  gancho no topo + crédito do streamer
 └─────────┬───────────┘
           ▼
 ┌─────────────────────┐
 │ 4. PUBLICAÇÃO       │  sobe pro Cloudflare R2
 │                     │  agenda no Metricool no próximo horário livre
 │                     │  modo aprovação → rascunho │ modo automático → publica
 └─────────────────────┘
```

---

## O que você precisa (e quanto custa)

| Serviço | Pra quê | Custo |
|---|---|---|
| GitHub | rodar o robô a cada 30 min | grátis (repositório **público**) |
| Twitch Developers | ler os clipes | grátis |
| Cloudflare R2 | hospedar o vídeo pronto | grátis até 10 GB |
| Metricool | publicar nas 3 redes | **API só nos planos Advanced/Custom** |
| Anthropic API (opcional) | escrever ganchos/títulos melhores | centavos por dia |

> **Por que repositório público?** Repo privado tem só 2.000 min/mês grátis de Actions, e o robô rodando a cada 30 min passa disso. Os segredos (senhas, tokens) continuam **escondidos** mesmo em repo público.

> **Por que Metricool e não a API de cada rede?** O TikTok só deixa apps **auditados** postarem em público — app novo posta tudo como privado. O Instagram exige app na Meta + conta Business. O Metricool já é aprovado nas três.

---

## Passo a passo

### Passo 1 — Criar as contas novas

1. Crie um **e-mail novo** só pro projeto (Gmail).
2. Com ele, crie:
   - **TikTok** → mantenha como **conta pessoal** (conta empresarial não entra no programa de monetização do TikTok).
   - **Instagram** → mude para *Conta Profissional / Criador*.
   - **Canal do YouTube** (em uma *Conta de Marca*).
3. Use o mesmo nome nas três (ex.: `@cortesgtarp_xxx`).

---

### Passo 2 — Pedir autorização aos streamers

Use o texto pronto em [`MENSAGEM_STREAMERS.md`](MENSAGEM_STREAMERS.md).

- Só coloque no `config.yaml` quem **autorizou**.
- Guarde o print da autorização.
- Se o streamer te colocar como **editor** na Twitch, marque `editor: true` — o download passa a ser pela API oficial.

---

### Passo 3 — App da Twitch

1. Acesse **dev.twitch.tv/console** → *Register Your Application*.
2. Nome: qualquer um. OAuth Redirect URL: `http://localhost:3000`. Categoria: *Application Integration*.
3. Copie o **Client ID** e gere um **Client Secret**.

*(Opcional, se for editor de algum canal)*: rode `python scripts/twitch_editor.py SEU_LOGIN`, autorize o link e anote o `TWITCH_EDITOR_ID`.

---

### Passo 4 — Cloudflare R2 (onde o vídeo fica hospedado)

1. Crie conta em **dash.cloudflare.com** → **R2** → *Create bucket* (ex.: `gta-cortes`).
2. No bucket: *Settings* → **Public Development URL** → *Allow*. Copie a URL (`https://pub-xxxx.r2.dev`).
3. No bucket: *Settings* → **Object lifecycle rules** → apagar objetos com mais de **7 dias** (economiza espaço).
4. Em R2 → *Manage API tokens* → *Create API token* com permissão **Object Read & Write**. Copie **Access Key ID**, **Secret Access Key** e o **Account ID**.

---

### Passo 5 — Metricool

1. Crie conta em **metricool.com** com o e-mail novo.
2. Na marca, conecte **TikTok, Instagram e YouTube** (as contas do passo 1).
3. Assine um plano com **API** (Advanced ou Custom).
4. Em *Configurações da conta → API*, copie o **token** (`METRICOOL_TOKEN`).
5. O `userId` e o `blogId` aparecem na URL quando você abre a marca no navegador (`...?blogId=123&userId=456`).

---

### Passo 6 — GitHub

1. Crie um repositório **público** (ex.: `gta-clipper`) e suba estes arquivos.
2. Vá em *Settings → Secrets and variables → Actions → New repository secret* e crie:

| Segredo | De onde vem |
|---|---|
| `TWITCH_CLIENT_ID` | passo 3 |
| `TWITCH_CLIENT_SECRET` | passo 3 |
| `TWITCH_EDITOR_ID` | passo 3 (opcional) |
| `R2_ACCOUNT_ID` | passo 4 |
| `R2_ACCESS_KEY_ID` | passo 4 |
| `R2_SECRET_ACCESS_KEY` | passo 4 |
| `R2_BUCKET` | passo 4 (nome do bucket) |
| `R2_PUBLIC_BASE_URL` | passo 4 (`https://pub-xxxx.r2.dev`) |
| `METRICOOL_TOKEN` | passo 5 |
| `METRICOOL_USER_ID` | passo 5 |
| `METRICOOL_BLOG_ID` | passo 5 |
| `NTFY_TOPIC` | nome do tópico que você assinou no app ntfy (avisos no celular) |
| `ANTHROPIC_API_KEY` | opcional — console.anthropic.com |
| `YTDLP_COOKIES` | opcional — só se o YouTube bloquear (ver abaixo) |

3. Em *Settings → Actions → General → Workflow permissions*, marque **Read and write**.

---

### Passo 7 — Configurar os streamers

Edite o [`config.yaml`](config.yaml) direto no GitHub:

```yaml
streamers:
  - nome: Fulano
    plataforma: twitch
    canal: fulano
    editor: true
    facecam: [0.75, 0.70, 0.25, 0.30]   # opcional
```

**Como achar a posição da facecam:** tire um print da live, veja onde a câmera começa e quanto ocupa.
Câmera no canto inferior direito ocupando 1/4 da largura e 30% da altura → `[0.75, 0.70, 0.25, 0.30]`.

---

### Passo 8 — Testar

1. Aba **Actions** → *gta-clipper* → **Run workflow**.
2. Abra o log da execução: deve aparecer `[twitch] Fulano: N candidatos` e `✔ rascunho criado`.
3. No app do Metricool, veja os rascunhos no calendário.

Teste local do visual (no seu PC, com ffmpeg instalado):

```bash
pip install -r requirements.txt
python -m clipper.main --arquivo um_clipe.mp4
python -m clipper.main --arquivo um_clipe.mp4 --facecam 0.75,0.7,0.25,0.3
```

---

### Passo 9 — De "aprovação" para "automático"

No começo, `modo: aprovacao`:

- Cada corte vira um **rascunho** no Metricool, já com data e hora.
- Você abre o app do Metricool no celular, assiste, e aprova (ou apaga).

Quando estiver confiante na qualidade (sugestão: depois de ~1 semana sem precisar apagar quase nada):

```yaml
modo: automatico
```

Pronto — a partir da próxima rodada os cortes saem sozinhos.

---

## ⚠️ Avisos importantes

**1. YouTube corta o alcance de canais que só repostam.**
Desde outubro/2026, Shorts reupados com pouca mudança recebem menos recomendação, e legenda/template automático não conta como "original". Para crescer no YouTube, vale gravar de vez em quando um comentário seu por cima, ou uma narração contando o contexto do RP. TikTok e Instagram costumam ser mais tolerantes com cortes.

**2. Permissão não te livra da regra de "conteúdo reutilizado" do YouTube.**
A autorização protege de *copyright*; monetização no YouTube depende de você **acrescentar algo**.

**3. Kick é instável.**
Não existe API oficial de clipes. Se aparecer `HTTP 403`, a Kick bloqueou o servidor do GitHub — o resto continua funcionando.

**4. YouTube pode bloquear o servidor do GitHub** ("confirme que não é um robô").
Solução: instale a extensão *Get cookies.txt LOCALLY*, exporte os cookies do youtube.com (logado numa conta secundária) e cole o conteúdo no segredo `YTDLP_COOKIES`.

**5. GitHub atrasa crons.**
"A cada 30 min" na prática pode virar 35–50 min em horários de pico. Como os posts são agendados com antecedência, isso não afeta os horários de publicação.

---

## Estrutura

```
clipper/
  main.py          orquestra a rodada
  sources/         twitch.py · kick.py · youtube.py
  download.py      baixa clipes (API oficial ou yt-dlp)
  legendas.py      Whisper → legenda .ass (gancho + legenda + crédito)
  render.py        ffmpeg → vertical 1080x1920
  textos.py        gancho, legenda do post e título (IA opcional)
  armazenamento.py upload no Cloudflare R2
  metricool.py     agendamento nas 3 redes
  estado.py        memória (o que já foi postado)
config.yaml        tudo que você ajusta
state/state.json   memória do robô (atualizada sozinha)
```
