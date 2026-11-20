"""Capa 100% original, desenhada por código (sem quadro da live, sem arte do jogo).

Estilo "neon tropical": céu em degradê, sol listrado, grade em perspectiva,
palmeiras em silhueta, e o gancho gigante no meio. Paleta muda por corte.
Nada aqui vem de terceiros, então não há risco de copyright na capa.
"""
import math
import random

from PIL import Image, ImageDraw, ImageFilter, ImageFont

W, H = 1080, 1920
FONTES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/dejavu/DejaVuSans-Bold.ttf",
]

PALETAS = [  # céu topo, céu base, sol topo, sol base, chão, linhas
    ("#120428", "#ff2d75", "#ffe66d", "#ff3d7f", "#0b0220", "#ff3df2"),   # pôr do sol rosa
    ("#020b2b", "#1fa2ff", "#d9fbff", "#30e3ff", "#020718", "#30e3ff"),   # noite ciano
    ("#1a0010", "#ff6a00", "#fff3a0", "#ff8c1a", "#100008", "#ffb347"),   # laranja quente
    ("#04121f", "#00c896", "#e6fff5", "#00e0a4", "#020c12", "#00ffc3"),   # tropical verde
    ("#0d0221", "#7b2ff7", "#ffd6ff", "#c86bfa", "#07010f", "#ff5ef7"),   # roxo
]


def _fonte(tam):
    for f in FONTES:
        try:
            return ImageFont.truetype(f, tam)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def _mix(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def _palmeira(d, x, base_y, altura, cor, rnd, inclina):
    # tronco curvo
    pts = []
    for i in range(30):
        t = i / 29
        px = x + inclina * altura * (t ** 2)
        py = base_y - altura * t
        pts.append((px, py))
    for i in range(len(pts) - 1):
        larg = int(26 * (1 - i / 40))
        d.line([pts[i], pts[i + 1]], fill=cor, width=larg)
    topo = pts[-1]
    # folhas
    for k in range(9):
        ang = math.radians(-170 + k * 22 + rnd.uniform(-6, 6))
        comp = altura * rnd.uniform(0.30, 0.40)
        poly = [topo]
        for j in range(1, 13):
            t = j / 12
            a = ang + 0.9 * t * (1 if math.cos(ang) > 0 else -1) * 0.35 + 0.55 * t * t
            r = comp * t
            poly.append((topo[0] + r * math.cos(a), topo[1] + r * math.sin(a) + 40 * t * t))
        for j in range(12, 0, -1):
            t = j / 12
            a = ang + 0.55 * t * t
            r = comp * t
            off = 15 * math.sin(math.pi * t)
            poly.append((topo[0] + r * math.cos(a) - off * math.sin(a), topo[1] + r * math.sin(a) + off * math.cos(a) + 40 * t * t))
        d.polygon(poly, fill=cor)


def _quebrar(texto, fonte, largura, d):
    palavras, linhas, atual = texto.split(), [], ""
    for p in palavras:
        teste = (atual + " " + p).strip()
        if d.textlength(teste, font=fonte) <= largura:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = p
    if atual:
        linhas.append(atual)
    return linhas


def gerar(saida: str, gancho: str, streamer: str, credito: str, semente: str = "") -> str:
    rnd = random.Random(semente or gancho)
    ceu_t, ceu_b, sol_t, sol_b, chao, linha = [_hex(c) for c in rnd.choice(PALETAS)]
    img = Image.new("RGB", (W, H))
    d = ImageDraw.Draw(img)
    horizonte = int(H * 0.66)

    # céu
    for y in range(horizonte):
        d.line([(0, y), (W, y)], fill=_mix(ceu_t, ceu_b, (y / horizonte) ** 1.6))
    # estrelas
    for _ in range(140):
        x, y = rnd.randrange(W), rnd.randrange(int(horizonte * 0.6))
        b = rnd.randint(120, 255)
        d.point((x, y), fill=(b, b, b))

    # sol listrado com brilho
    cx, cy, r = W // 2, horizonte - 120, 330
    brilho = Image.new("RGB", (W, H))
    ImageDraw.Draw(brilho).ellipse([cx - r - 90, cy - r - 90, cx + r + 90, cy + r + 90], fill=_mix(sol_b, (0, 0, 0), 0.35))
    img = Image.blend(img, Image.composite(brilho.filter(ImageFilter.GaussianBlur(70)), img,
                                           brilho.convert("L").point(lambda v: 255 if v else 0)), 0.55)
    d = ImageDraw.Draw(img)
    for y in range(cy - r, cy + r):
        dy = y - cy
        meia = int(math.sqrt(max(r * r - dy * dy, 0)))
        t = (y - (cy - r)) / (2 * r)
        faixa = y > cy - r * 0.1 and int((y - cy) / 18) % 2 == 1 and t > 0.45
        if not faixa:
            d.line([(cx - meia, y), (cx + meia, y)], fill=_mix(sol_t, sol_b, t))

    # chão com grade em perspectiva
    d.rectangle([0, horizonte, W, H], fill=chao)
    for i in range(1, 26):
        y = horizonte + int((H - horizonte) * (i / 25) ** 2.2)
        d.line([(0, y), (W, y)], fill=_mix(chao, linha, 0.55), width=2)
    for i in range(-14, 15):
        d.line([(W / 2 + i * 22, horizonte), (W / 2 + i * 260, H)], fill=_mix(chao, linha, 0.55), width=2)
    d.line([(0, horizonte), (W, horizonte)], fill=linha, width=4)

    # palmeiras nas laterais
    silhueta = (6, 2, 14)
    _palmeira(d, -20, horizonte + 40, 760, silhueta, rnd, 0.28)
    _palmeira(d, W + 30, horizonte + 60, 680, silhueta, rnd, -0.30)
    if rnd.random() < 0.6:
        _palmeira(d, 140, horizonte + 10, 430, silhueta, rnd, 0.18)

    # escurece o meio pra destacar o texto
    sombra = Image.new("L", (W, H), 0)
    ImageDraw.Draw(sombra).rectangle([0, int(H * 0.30), W, int(H * 0.66)], fill=55)
    img = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), img, sombra.filter(ImageFilter.GaussianBlur(80)))
    d = ImageDraw.Draw(img)

    # selo com o nome do streamer
    f_selo = _fonte(64)
    nome = streamer.upper()
    lw = d.textlength(nome, font=f_selo)
    x0, y0 = (W - lw) / 2 - 34, 230
    d.rounded_rectangle([x0, y0, x0 + lw + 68, y0 + 100], radius=22, fill=(255, 214, 0))
    d.text((W / 2, y0 + 50), nome, font=f_selo, fill=(0, 0, 0), anchor="mm")

    # gancho gigante
    texto = gancho.upper()
    for tam in (128, 116, 104, 94, 84, 76):
        f = _fonte(tam)
        linhas = _quebrar(texto, f, W - 120, d)
        if len(linhas) <= 4:
            break
    alt_linha = int(tam * 1.22)
    y = int(H * 0.48) - alt_linha * len(linhas) // 2
    for ln in linhas:
        d.text((W / 2, y), ln, font=f, fill=(255, 255, 255), anchor="mt",
               stroke_width=max(6, tam // 14), stroke_fill=(0, 0, 0))
        y += alt_linha

    # rodapé com crédito
    d.text((W / 2, H - 170), f"▶ {credito}", font=_fonte(46), fill=(255, 255, 255), anchor="mm",
           stroke_width=4, stroke_fill=(0, 0, 0))
    img.save(saida, "JPEG", quality=90)
    return saida
