#!/usr/bin/env python3
"""Vida Interesante - motor de videos cortos (1080x1920).
Uso: python3 engine.py videos/guiones/<slug>.json salida.mp4
Ver INSTRUCCIONES.md para el formato del guion."""
import numpy as np, subprocess, sys, os, math, json, random, shutil, tempfile, urllib.request, tarfile
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageDraw, ImageFont, ImageFilter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import stickman

W, H, FPS = 1080, 1920, 30
HERE = os.path.dirname(os.path.abspath(__file__))
FONTDIR = "/usr/share/fonts/truetype/google-fonts/ofl/"
EMOJI_FONT = "/usr/share/fonts/truetype/noto/NotoColorEmoji.ttf"
VOICE_DIR = os.path.expanduser("~/.cache/vida_voice")
VOICE_URL = "https://github.com/rhasspy/piper/releases/download/v0.0.2/voice-es-carlfm-x-low.tar.gz"
VOICE_FX = ("aresample=44100,rubberband=pitch=1.03:tempo=1.08,highpass=f=80,equalizer=f=200:t=q:w=1:g=3,"
            "equalizer=f=3500:t=q:w=1:g=3,acompressor=threshold=-26dB:ratio=4:makeup=8,aecho=0.8:0.5:40:0.1,loudnorm=I=-14:TP=-1")
LEAD, TAIL = 0.2, 0.45
YELLOW = (255, 205, 40)

# ------------------------------------------------------------------ fonts / helpers
def font(size, weight="Black"):
    f = ImageFont.truetype(FONTDIR + "montserrat/Montserrat[wght].ttf", size)
    try: f.set_variation_by_name(weight)
    except Exception: pass
    return f
def anton(size): return ImageFont.truetype(FONTDIR + "anton/Anton-Regular.ttf", size)
def ease(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t

def grad(top, bot, h=H, w=W):
    t = np.linspace(0, 1, h)[:, None, None]
    a = np.array(top, float)[None, None] * (1 - t) + np.array(bot, float)[None, None] * t
    return Image.fromarray(np.repeat(a, w, 1).astype(np.uint8)).convert("RGBA")

def paste_c(base, im, cx, cy, alpha=1.0):
    if alpha <= 0.01: return
    if alpha < 1:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda p: int(p * alpha)))
    base.alpha_composite(im, (int(cx - im.width / 2), int(cy - im.height / 2)))

def zoom(im, s, cx=W / 2, cy=H / 2):
    if abs(s - 1) < 1e-3: return im
    w, h = W / s, H / s
    return im.crop((int(cx - w / 2), int(cy - h / 2), int(cx + w / 2), int(cy + h / 2))).resize((W, H), Image.BILINEAR)

def text_img(txt, f, fill=(255, 255, 255), stroke=10, sc=(0, 0, 0)):
    bb = f.getbbox(txt, stroke_width=stroke); tw, th = bb[2] - bb[0], bb[3] - bb[1]
    layer = Image.new("RGBA", (tw + 40, th + 40), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.text((20 - bb[0], 20 - bb[1]), txt, font=f, fill=tuple(fill) + (255,), stroke_width=stroke, stroke_fill=tuple(sc) + (255,))
    return layer

def text_center(img, txt, y, f, fill=(255, 255, 255), stroke=10, scale=1.0, alpha=1.0, maxw=1000):
    if alpha <= 0.01 or not txt: return
    layer = text_img(txt, f, fill, stroke)
    s = scale * min(1.0, maxw / layer.width)
    if abs(s - 1) > 1e-3: layer = layer.resize((max(1, int(layer.width * s)), max(1, int(layer.height * s))), Image.BICUBIC)
    paste_c(img, layer, W / 2, y, alpha)

def wrap(txt, f, maxw):
    ws, lines, cur = txt.split(), [], ""
    for w in ws:
        t = (cur + " " + w).strip()
        if f.getlength(t) > maxw and cur: lines.append(cur); cur = w
        else: cur = t
    return lines + [cur]

def chip(img, txt, alpha=1.0, y=200):
    if not txt: return
    f = font(44, "ExtraBold"); bb = f.getbbox(txt); tw = bb[2] - bb[0]
    layer = Image.new("RGBA", (tw + 80, 96), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    d.rounded_rectangle([0, 0, tw + 79, 95], 48, fill=YELLOW + (255,))
    d.text((40 - bb[0], 48 - (bb[1] + bb[3]) / 2), txt, font=f, fill=(15, 15, 25, 255))
    paste_c(img, layer, W / 2, y, alpha)

_emoji_cache = {}
def emoji_img(e, size):
    key = (e, size)
    if key not in _emoji_cache:
        f = ImageFont.truetype(EMOJI_FONT, 109)
        im = Image.new("RGBA", (220, 160), (0, 0, 0, 0)); ImageDraw.Draw(im).text((10, 10), e, font=f, embedded_color=True)
        bb = im.getbbox() or (0, 0, 10, 10); im = im.crop(bb)
        s = size / max(im.width, im.height)
        im = im.resize((max(1, int(im.width * s)), max(1, int(im.height * s))), Image.LANCZOS)
        sh = Image.new("RGBA", (im.width + 60, im.height + 60), (0, 0, 0, 0))
        a = im.getchannel("A").point(lambda p: int(p * 0.55)); blk = Image.new("RGBA", im.size, (0, 0, 0, 255)); blk.putalpha(a)
        sh.alpha_composite(blk, (30, 42)); sh = sh.filter(ImageFilter.GaussianBlur(10)); sh.alpha_composite(im, (30, 30))
        _emoji_cache[key] = sh
    return _emoji_cache[key]

# ------------------------------------------------------------------ textures (earth / moon)
def value_noise(w, h, octaves=6, seed=0):
    r = np.random.default_rng(seed); out = np.zeros((h, w)); amp = 1; tot = 0
    for o in range(octaves):
        gw, gh = 4 * 2 ** o, 2 * 2 ** o
        g = (r.random((gh, gw)) * 255).astype(np.uint8); g = np.concatenate([g, g[:, :1]], 1)
        im = Image.fromarray(g).resize((w + w // gw, h), Image.BICUBIC).crop((0, 0, w, h))
        out += np.asarray(im, float) / 255 * amp; tot += amp; amp *= 0.5
    return out / tot

TW, TH = 1024, 512
_tex = {}
def textures():
    if _tex: return _tex
    lat_t = np.linspace(90, -90, TH)[:, None] * np.ones((1, TW))
    n = value_noise(TW, TH, 6, 3); land = n > 0.5
    ocean = np.stack([18 + 30 * n, 70 + 60 * n, 150 + 70 * n], -1)
    landc = np.stack([60 + 120 * (n - .5), 140 - 60 * (n - .5), 50 + 30 * n], -1)
    desert = value_noise(TW, TH, 4, 9) > 0.6
    landc[desert] = np.stack([170 + 40 * n, 140 + 30 * n, 90 + 20 * n], -1)[desert]
    E = np.where(land[..., None], landc, ocean)
    E[np.abs(lat_t) > 72 - 6 * value_noise(TW, TH, 3, 5)] = [235, 240, 245]
    _tex["earth"] = np.clip(E, 0, 255)
    _tex["cloud"] = np.clip((value_noise(TW, TH, 6, 11) - 0.5) * 3.2, 0, 1) * 0.85
    mn = value_noise(TW, TH, 6, 21)
    mim = Image.fromarray(np.stack([150 + 70 * mn] * 3, -1).astype(np.uint8)); md = ImageDraw.Draw(mim); cr = random.Random(4)
    for _ in range(140):
        x, y, r = cr.randint(0, TW), cr.randint(60, TH - 60), cr.choice([4, 6, 8, 10, 14, 20, 28])
        md.ellipse([x - r, y - r, x + r, y + r], fill=(118, 118, 118)); md.ellipse([x - r + 2, y - r + 2, x + r - 3, y + r - 3], fill=(140, 140, 140))
    for _ in range(7):
        x, y, r = cr.randint(0, TW), cr.randint(150, 360), cr.randint(40, 90)
        md.ellipse([x - r, y - r * .7, x + r, y + r * .7], fill=(105, 105, 110))
    _tex["moon"] = np.asarray(mim.filter(ImageFilter.GaussianBlur(1.5)), float)
    rn = value_noise(TW, TH, 6, 31)
    _tex["mars"] = np.stack([150 + 90 * rn, 70 + 50 * rn, 40 + 30 * rn], -1)
    sn = value_noise(TW, TH, 5, 41) * 0.6 + 0.4 * np.sin(np.linspace(0, 40, TH))[:, None]
    _tex["sun"] = np.clip(np.stack([255 * np.ones_like(sn), 150 + 90 * sn, 30 + 60 * sn], -1), 0, 255)
    return _tex

_geo = {}
def sphere(tex, r, off, light=(-0.6, -0.4, 0.7), clouds=None, coff=0, night=0.12, glow=None):
    if r not in _geo:
        y, x = np.mgrid[-r:r, -r:r] + 0.5; x, y = x / r, y / r; d2 = x * x + y * y
        z = np.sqrt(np.clip(1 - d2, 0, 1)); lat = np.arcsin(np.clip(-y, -1, 1)); lon = np.arctan2(x, z)
        _geo[r] = (x, y, z, lat, lon, np.clip((1 - np.sqrt(d2)) * r, 0, 1))
    x, y, z, lat, lon, aa = _geo[r]; th, tw = tex.shape[:2]
    u = (((lon / (2 * np.pi) + 0.5 + off) % 1) * (tw - 1)).astype(int); v = ((0.5 - lat / np.pi) * (th - 1)).astype(int)
    c = tex[v, u]
    if clouds is not None:
        uc = (((lon / (2 * np.pi) + 0.5 + coff) % 1) * (tw - 1)).astype(int); a = clouds[v, uc][..., None]; c = c * (1 - a) + 250 * a
    L = np.array(light, float); L /= np.linalg.norm(L)
    sh = np.clip(x * L[0] + y * L[1] + z * L[2], 0, 1) ** 0.8 * (1 - night) + night
    c = c * sh[..., None]
    if glow: c = c + np.array(glow)[None, None] * ((1 - z) ** 3)[..., None] * 0.9 * np.clip(sh, .3, 1)[..., None]
    return Image.fromarray(np.dstack([np.clip(c, 0, 255), aa * 255]).astype(np.uint8), "RGBA")

def atmosphere(r, color=(90, 160, 255), strength=170):
    s = int(r * 2.6); im = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = s // 2
    d.ellipse([c - r * 1.06, c - r * 1.06, c + r * 1.06, c + r * 1.06], fill=tuple(color) + (strength,))
    return im.filter(ImageFilter.GaussianBlur(r * 0.09))

def planet(img, kind, cx, cy, r, t, alpha=1.0):
    T = textures()
    if kind == "earth":
        paste_c(img, atmosphere(r), cx, cy, alpha)
        paste_c(img, sphere(T["earth"], r, t * 0.02, clouds=T["cloud"], coff=t * 0.03, glow=(40, 90, 200)), cx, cy, alpha)
    elif kind == "moon":
        paste_c(img, atmosphere(r, (220, 225, 255), 70), cx, cy, alpha)
        paste_c(img, sphere(T["moon"], r, 0.1 + t * 0.005, night=0.05), cx, cy, alpha)
    elif kind == "mars":
        paste_c(img, atmosphere(r, (255, 140, 90), 90), cx, cy, alpha)
        paste_c(img, sphere(T["mars"], r, t * 0.02, night=0.08), cx, cy, alpha)
    elif kind == "sun":
        paste_c(img, atmosphere(r, (255, 170, 60), 230), cx, cy, alpha)
        paste_c(img, sphere(T["sun"], r, t * 0.01, light=(0, 0, 1), night=0.85), cx, cy, alpha)

# ------------------------------------------------------------------ backgrounds
rng0 = np.random.default_rng(7)
N = 650
SX, SY = rng0.integers(0, W, N), rng0.integers(0, H, N)
SB, SP, SR = rng0.random(N) ** 2, rng0.random(N) * 6.28, rng0.choice([1, 1, 1, 2, 2, 3], N)
def stars(img, t, k=1.0, ymax=H):
    d = ImageDraw.Draw(img); b = (0.55 + 0.45 * np.sin(t * 2.2 + SP)) * SB * k
    for x, y, bb, r in zip(SX, SY, b, SR):
        if y > ymax or bb < 0.04: continue
        v = int(min(255, 70 + 185 * bb)); d.ellipse([x - r / 2, y - r / 2, x + r / 2, y + r / 2], fill=(v, v, min(255, v + 15), 255))

def hills(seed, layers):
    out = []; r = random.Random(seed)
    for i, (base, amp, col) in enumerate(layers):
        xs = np.arange(0, W + 10, 10); a, b = r.random() * 6, r.random() * 6
        ys = base - amp * (np.sin(xs / 170 + a) * .6 + np.sin(xs / 61 + b) * .3 + np.sin(xs / 23) * .1)
        out.append((list(zip(xs, ys)) + [(W, H), (0, H)], col))
    return out
HILLS = hills(1, [(1300, 90, (22, 28, 50)), (1460, 70, (14, 18, 34)), (1640, 50, (6, 8, 16))])
TREES = []
_tr = random.Random(5)
for layer in range(3):
    for _ in range(14 + layer * 4):
        TREES.append((layer, _tr.randint(-40, W + 40), 1180 + layer * 170 + _tr.randint(-30, 30), _tr.randint(260, 520) * (1 + layer * .25), _tr.randint(70, 130) * (1 + layer * .25)))
PART = [(rng0.random() * W, rng0.random() * H, rng0.random() * 6.28, 2 + rng0.random() * 6) for _ in range(220)]
WIN = [(random.Random(i).random() < .45) for i in range(4000)]
GRAIN = [Image.fromarray((np.random.default_rng(s).normal(128, 40, (H // 2, W // 2))).clip(0, 255).astype(np.uint8)).resize((W, H)) for s in range(4)]
CORALS = [(random.Random(i).randint(60, W - 60), random.Random(i + 50).randint(1560, 1780), random.Random(i).choice([(255, 120, 140), (255, 160, 80), (200, 110, 220), (255, 90, 110)]), random.Random(i + 9).random()) for i in range(9)]

def branch(d, x, y, ang, ln, w, col, depth):
    if depth == 0 or ln < 12: return
    x2, y2 = x + ln * math.cos(ang), y - ln * math.sin(ang)
    d.line([(x, y), (x2, y2)], fill=col, width=int(w)); d.ellipse([x2 - w / 2, y2 - w / 2, x2 + w / 2, y2 + w / 2], fill=col)
    branch(d, x2, y2, ang + 0.45, ln * 0.75, w * 0.75, col, depth - 1); branch(d, x2, y2, ang - 0.4, ln * 0.72, w * 0.75, col, depth - 1)

def vignette(strength=0.6):
    y, x = np.mgrid[0:H // 4, 0:W // 4]; d = np.sqrt(((x - W / 8) / (W / 8)) ** 2 + ((y - H / 8) / (H / 8)) ** 2)
    a = (np.clip(d - 0.55, 0, 1) * strength * 255).astype(np.uint8)
    im = Image.new("RGBA", (W // 4, H // 4), (0, 0, 0, 255)); im.putalpha(Image.fromarray(a)); return im.resize((W, H), Image.BILINEAR)
VIG = {}
def vig(s):
    if s not in VIG: VIG[s] = vignette(s)
    return VIG[s]

def bg_space(t, sc):
    im = grad((4, 6, 20), (14, 18, 48)); stars(im, t)
    p = sc.get("planet", "earth")
    if p and p != "none": planet(im, p, W / 2, 1700, 440, t)
    return im
def bg_night(t, sc):
    im = grad((5, 8, 20), (25, 35, 70)); stars(im, t, 1.0, 1300)
    if sc.get("planet") == "moon": planet(im, "moon", 300, 430, 110, t)
    d = ImageDraw.Draw(im)
    for poly, col in HILLS: d.polygon(poly, fill=col + (255,))
    return im
def bg_ocean(t, sc):
    im = grad((40, 110, 190), (150, 200, 235)); d = ImageDraw.Draw(im)
    xs = np.arange(0, W + 8, 8)
    for k, (lvl, col) in enumerate([(1250, (30, 100, 170)), (1330, (20, 80, 150)), (1430, (14, 62, 125))]):
        ys = lvl + 14 * np.sin(xs / (45 - k * 6) + t * (3 + k)) + 7 * np.sin(xs / 17 - t * 3)
        d.polygon(list(zip(xs, ys)) + [(W, H), (0, H)], fill=col + (255,))
    return im
def bg_underwater(t, sc):
    im = grad((20, 120, 150), (3, 25, 50))
    rays = Image.new("RGBA", (W, H), (0, 0, 0, 0)); rd = ImageDraw.Draw(rays)
    for i in range(6):
        x = 120 + i * 180 + 40 * math.sin(t * 0.5 + i); rd.polygon([(x, 0), (x + 70, 0), (x + 260, 1500), (x + 120, 1500)], fill=(200, 255, 255, 28))
    im.alpha_composite(rays.filter(ImageFilter.GaussianBlur(12))); d = ImageDraw.Draw(im)
    for x, y, ph, s in PART:
        yy = (y - t * 60 - ph * 40) % H; d.ellipse([x - s / 2, yy - s / 2, x + s / 2, yy + s / 2], fill=(220, 255, 255, 120))
    d.polygon([(0, 1720), (300, 1640), (700, 1700), (W, 1620), (W, H), (0, H)], fill=(60, 50, 60, 255))
    for x, y, col, r in CORALS:
        if r < 0.5: branch(d, x, y, math.pi / 2 + 0.1 * math.sin(t + r * 6), 100, 20, col + (255,), 5)
        else: d.ellipse([x - 65, y - 55, x + 65, y + 40], fill=col + (255,))
    return im
_FOG = {}
def _fog(layer):
    if layer not in _FOG:
        fog = Image.new("RGBA", (W * 2, 700), (0, 0, 0, 0)); fd = ImageDraw.Draw(fog); fr = random.Random(layer)
        for _ in range(18):
            fx, fy = fr.randint(200, W * 2 - 200), fr.randint(220, 480); fd.ellipse([fx - 260, fy - 70, fx + 260, fy + 70], fill=(170, 185, 185, 40))
        _FOG[layer] = fog.filter(ImageFilter.GaussianBlur(40))
    return _FOG[layer]
def bg_fog(t, sc):  # bosque oscuro con niebla (terror)
    im = grad((12, 18, 22), (40, 52, 55)); d = ImageDraw.Draw(im)
    if sc.get("planet") == "moon": planet(im, "moon", 840, 640, 100, t, 0.8)
    for layer in range(3):
        col = [(30, 40, 44), (18, 24, 27), (6, 8, 10)][layer]
        for l, x, y, h, w in TREES:
            if l != layer: continue
            d.polygon([(x, y - h), (x - w, y), (x + w, y)], fill=col + (255,))
        d.rectangle([0, 1180 + layer * 170 + 40, W, H], fill=col + (255,))
        fog = _fog(layer); off = int((t * (25 + 15 * layer)) % W)
        im.alpha_composite(fog.crop((off, 0, off + W, 700)), (0, 880 + layer * 170))
    return im
def bg_sepia(t, sc):  # papel antiguo (historia)
    n = value_noise(W // 4, H // 4, 5, 13)
    a = np.stack([200 + 40 * n, 170 + 40 * n, 120 + 35 * n], -1)
    im = Image.fromarray(a.astype(np.uint8)).resize((W, H), Image.BICUBIC).convert("RGBA"); d = ImageDraw.Draw(im)
    for i in range(0, H, 90): d.line([(60, i), (W - 60, i)], fill=(150, 120, 80, 60), width=2)
    for x, y, ph, s in PART[:60]:
        d.ellipse([x - s, y - s, x + s, y + s], fill=(110, 80, 50, 50))
    return im
def bg_lab(t, sc):  # ciencia / cuerpo humano
    im = grad((6, 20, 40), (2, 8, 20)); d = ImageDraw.Draw(im)
    for x in range(0, W, 90): d.line([(x, 0), (x, H)], fill=(40, 120, 160, 45), width=2)
    for y in range(int(t * 30) % 90, H, 90): d.line([(0, y), (W, y)], fill=(40, 120, 160, 45), width=2)
    for x, y, ph, s in PART[:120]:
        yy = (y - t * 40) % H; a = int(120 + 120 * math.sin(t * 2 + ph)); d.ellipse([x - s, yy - s, x + s, yy + s], fill=(80, 220, 255, max(0, a)))
    return im
def bg_fire(t, sc):  # rojo oscuro con brasas (terror / guerra / peligro)
    im = grad((20, 4, 4), (90, 20, 8)); d = ImageDraw.Draw(im)
    for x, y, ph, s in PART:
        yy = (y - t * 120 - ph * 60) % H; xx = x + 20 * math.sin(t * 2 + ph); a = int(255 * (yy / H))
        d.ellipse([xx - s / 2, yy - s / 2, xx + s / 2, yy + s / 2], fill=(255, 140 + int(60 * math.sin(ph)), 40, a))
    return im
def bg_desert(t, sc):
    im = grad((240, 160, 90), (250, 215, 150)); planet(im, "sun", 780, 480, 130, t)
    d = ImageDraw.Draw(im)
    for k, (base, amp, col) in enumerate([(1250, 80, (220, 160, 90)), (1420, 90, (200, 135, 70)), (1600, 70, (170, 110, 55))]):
        xs = np.arange(0, W + 10, 10); ys = base - amp * np.sin(xs / (300 - 60 * k) + k * 2)
        d.polygon(list(zip(xs, ys)) + [(W, H), (0, H)], fill=col + (255,))
    return im
def bg_city(t, sc):
    im = grad((8, 10, 30), (40, 30, 70)); stars(im, t, 0.6, 900); d = ImageDraw.Draw(im); r = random.Random(3); x = 0; k = 0
    while x < W:
        w = r.randint(90, 180); h = r.randint(350, 900); col = (12, 14, 30, 255)
        d.rectangle([x, H - 300 - h, x + w - 8, H], fill=col)
        for wy in range(H - 280 - h, H - 320, 50):
            for wx in range(x + 15, x + w - 30, 35):
                k += 1
                if WIN[k % 4000]: d.rectangle([wx, wy, wx + 16, wy + 24], fill=(255, 210, 120, 220))
        x += w
    return im

BGS = {"space": bg_space, "night": bg_night, "ocean": bg_ocean, "underwater": bg_underwater, "fog": bg_fog,
       "sepia": bg_sepia, "lab": bg_lab, "fire": bg_fire, "desert": bg_desert, "city": bg_city}
DARK = {"fog", "fire", "night"}

# ------------------------------------------------------------------ scene composition
def draw_emojis(im, sc, t, D, y=700):
    em = sc.get("emoji") or []
    if isinstance(em, str): em = [em]
    if not em: return
    anim = sc.get("anim", "float"); n = len(em); size = [400, 300, 240][min(n, 3) - 1]
    if sc.get("stickman"): size = int(size * 0.55); y = 560
    gap = W / (n + 1)
    for i, e in enumerate(em):
        ti = t - 0.15 - i * 0.25; p = ease(ti / 0.35)
        if p <= 0: continue
        s = 0.6 + 0.4 * p; dy = 18 * math.sin(t * 2 + i); alpha = p; rot = 0
        if anim == "shake": rot = 6 * math.sin(t * 25) * (0.5 + 0.5 * math.sin(t * 3))
        if anim == "pulse": s *= 1 + 0.07 * math.sin(t * 6)
        if anim == "fade_out": alpha = p * (1 - ease((t - D * 0.55) / 0.8)); s *= 1 - 0.3 * ease((t - D * 0.55) / 0.8)
        if anim == "spin": rot = (t * 60) % 360
        img = emoji_img(e, size)
        if abs(s - 1) > 1e-3: img = img.resize((max(1, int(img.width * s)), max(1, int(img.height * s))), Image.BICUBIC)
        if rot: img = img.rotate(rot, Image.BICUBIC, expand=True)
        paste_c(im, img, gap * (i + 1), y + dy, alpha)

CAPF = None
def captions(img, words, t, y=1555):
    global CAPF
    if CAPF is None: CAPF = font(76, "Black")
    cur = None
    for w0, w1, txt in words:
        if w0 <= t: cur = (w0, w1, txt)
    if not cur or t > cur[1] + 0.3: return
    sc = 0.85 + 0.15 * ease((t - cur[0]) / 0.12); lines = wrap(cur[2], CAPF, 960)
    for j, ln in enumerate(lines):
        text_center(img, ln, y + j * 100 - (len(lines) - 1) * 50, CAPF, stroke=9, scale=sc)

def chunks_for(line, dur, lead):
    words = line.split(); groups, g = [], []
    for w in words:
        g.append(w)
        if len(g) >= 4 or w[-1] in ".,?!:;…": groups.append(" ".join(g)); g = []
    if g: groups.append(" ".join(g))
    wts = [len(x) + (8 if x[-1] in ".?!:…" else 3 if x[-1] in ",;" else 0) for x in groups]
    tot = sum(wts); t = lead; out = []
    for gtxt, wt in zip(groups, wts):
        d = dur * wt / tot; out.append((t, t + d, gtxt.upper())); t += d
    return out

def frame(spec, i, t, D, words):
    sc = spec["scenes"][i]; kind = "hook" if i == 0 else "cta" if i == len(spec["scenes"]) - 1 else "body"
    bgname = sc.get("bg", spec.get("bg", "space"))
    im = BGS.get(bgname, bg_space)(t, sc)
    figs = sc.get("stickman") or []
    if isinstance(figs, dict): figs = [figs]
    if kind == "hook":
        if not figs: draw_emojis(im, sc, t, D, y=900)
        p = ease(t / 0.35); top, bot = sc.get("title", ["", ""])[:2]
        text_center(im, top, 300, anton(150), scale=.8 + .2 * p, alpha=p)
        text_center(im, bot, 470, anton(150), fill=YELLOW, scale=.8 + .2 * p, alpha=p)
    elif kind == "cta":
        p = ease(t / 0.35); ls = sc.get("title", ["¿QUÉ OTRO TEMA", "QUIERES VER?"])
        for j, ln in enumerate(ls[:3]):
            text_center(im, ln, 330 + j * 160, anton(140), fill=YELLOW if j == 1 else (255, 255, 255), scale=.8 + .2 * p, alpha=p)
        s = 1 + 0.06 * math.sin(t * 6)
        b = Image.new("RGBA", (300, 280), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([10, 10, 290, 200], 60, fill=(255, 255, 255, 255)); bd.polygon([(80, 190), (60, 270), (150, 195)], fill=(255, 255, 255, 255))
        for k in range(3): bd.ellipse([80 + k * 55, 90, 110 + k * 55, 120], fill=(20, 20, 30, 255))
        paste_c(im, b.resize((int(300 * s), int(280 * s))), W / 2, 330 + len(ls[:3]) * 160 + 180, ease((t - 0.3) / 0.3))
    else:
        draw_emojis(im, sc, t, D)
        if sc.get("big"):
            p = ease((t - D * 0.3) / 0.4); text_center(im, sc["big"], 390 if figs else 1040, anton(130), fill=YELLOW, scale=.8 + .2 * p, alpha=p)
        chip(im, sc.get("chip", ""), ease(t / 0.3))
    if figs: draw_decor(im, sc, bgname, t)
    for fg in figs: stickman.draw(im, fg, t, D, emoji_fn=emoji_img)
    weather(im, sc.get("weather", spec.get("weather", "auto")), bgname, t)
    if kind == "body": captions(im, words, t)
    overlay(im, spec, t)
    if bgname in DARK or spec.get("mood") == "dark":
        im.alpha_composite(vig(0.85))
        g = GRAIN[int(t * FPS / 3) % 4]; gl = Image.new("RGBA", (W, H), (255, 255, 255, 0)); gl.putalpha(g.point(lambda p: max(0, p - 150) // 3))
        im.alpha_composite(gl)
        if spec.get("mood") == "dark" and random.Random(int(t * FPS)).random() < 0.03:  # flicker
            im.alpha_composite(Image.new("RGBA", (W, H), (0, 0, 0, 90)))
    else:
        im.alpha_composite(vig(0.45))
    return zoom(im, 1.0 + 0.04 * t / D)

DECOR = {"fog": ["🌲", "🌲"], "night": ["🌲", "🏔️"], "sepia": ["📜", "🕯️"], "lab": ["🧪", "🧬"], "space": ["🛰️", "☄️"], "ocean": ["🐚", "⛵"],
         "underwater": ["🐟", "🐠"], "desert": ["🌵", "🐪"], "city": ["🚗", "🏢"], "fire": ["🔥", "🔥"]}
def draw_decor(im, sc, bgname, t):
    dec = sc.get("decor", DECOR.get(bgname, []))
    if isinstance(dec, str): dec = [dec]
    xs = [0.12, 0.88, 0.25, 0.75]
    for k, e in enumerate(dec[:4]):
        img = emoji_img(e, 210 if k < 2 else 150)
        paste_c(im, img, W * xs[k], stickman.GROUND - img.height / 2 + 30 + 6 * math.sin(t * 1.5 + k), 1.0)

WEATHER_AUTO = {"night": "snow", "fog": "dust", "fire": "none", "sepia": "dust", "lab": "none", "space": "none", "underwater": "none",
                "ocean": "none", "desert": "dust", "city": "rain"}
FLAKES = [(rng0.random() * W, rng0.random() * H, rng0.random() * 6.28, 3 + rng0.random() * 7, 0.5 + rng0.random()) for _ in range(160)]
def weather(im, kind, bgname, t):
    if kind == "auto": kind = WEATHER_AUTO.get(bgname, "none")
    if kind == "none": return
    d = ImageDraw.Draw(im)
    for x, y, ph, s, sp in FLAKES:
        if kind == "snow":
            yy = (y + t * 140 * sp) % H; xx = x + 30 * math.sin(t * sp + ph); d.ellipse([xx - s / 2, yy - s / 2, xx + s / 2, yy + s / 2], fill=(255, 255, 255, 200))
        elif kind == "rain":
            yy = (y + t * 1400 * sp) % H; xx = x - (t * 200) % W; xx %= W; d.line([(xx, yy), (xx - 6, yy + 40)], fill=(180, 200, 255, 120), width=3)
        elif kind == "dust":
            yy = (y - t * 20 * sp) % H; xx = (x + t * 25 * sp) % W; a = int(90 + 70 * math.sin(t * 2 + ph)); d.ellipse([xx - s / 3, yy - s / 3, xx + s / 3, yy + s / 3], fill=(230, 230, 220, max(0, a)))

HANDLE = "VIDA INTERESANTE"
def overlay(im, spec, t):
    g = spec.get("_start", 0) + t; tot = spec.get("_total", 1)
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([60, 1870, W - 60, 1884], 7, fill=(255, 255, 255, 70))
    d.rounded_rectangle([60, 1870, 60 + (W - 120) * min(1, g / tot), 1884], 7, fill=YELLOW + (255,))
    f = font(34, "ExtraBold"); d.text((W / 2, 1815), HANDLE, font=f, fill=(255, 255, 255, 150), anchor="mm", stroke_width=3, stroke_fill=(0, 0, 0, 120))

def render_scene(args):
    spec, i, D, vd, out = args
    words = chunks_for(spec["scenes"][i]["line"], vd - 0.3, LEAD)
    nf = int(round(D * FPS)); tmp = out.replace(".mp4", ".tmp.mp4")
    p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                          "-c:v", "libx264", "-preset", "veryfast", "-crf", "23", "-maxrate", "6M", "-bufsize", "12M", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
    for fr in range(nf):
        t = fr / FPS; im = frame(spec, i, t, D, words)
        if i > 0 and t < 0.15: im = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), im, t / 0.15)
        p.stdin.write(im.convert("RGB").tobytes())
    p.stdin.close(); p.wait()
    if p.returncode != 0: raise RuntimeError("ffmpeg falló en escena %d" % i)
    os.replace(tmp, out); return out

# ------------------------------------------------------------------ audio
def ensure_voice():
    m = os.path.join(VOICE_DIR, "es-carlfm-x-low.onnx")
    if not os.path.exists(m):
        os.makedirs(VOICE_DIR, exist_ok=True); tgz = os.path.join(VOICE_DIR, "v.tgz")
        subprocess.run(["curl", "-sSL", "-o", tgz, VOICE_URL], check=True)
        with tarfile.open(tgz) as tf: tf.extractall(VOICE_DIR, filter="data")
    return m

def tts(text, out):
    m = ensure_voice(); raw = out + ".raw.wav"
    subprocess.run([sys.executable, "-m", "piper", "-m", m, "--length-scale", "1.0", "--sentence-silence", "0.25", "-f", raw], input=text.encode(), check=True, capture_output=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", raw, "-af", VOICE_FX, "-ar", "48000", "-ac", "1", out], check=True)
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", out]))

def music(total, mood, starts, SR=48000):
    t = np.arange(int(total * SR)) / SR; mus = np.zeros_like(t)
    if mood == "dark":
        for f, a in [(55, 1), (82.4, .6), (87.3, .35), (110, .4), (116.5, .2)]:
            mus += a * np.sin(2 * np.pi * f * t + 2 * np.sin(2 * np.pi * 0.1 * t))
        mus *= 0.6 + 0.4 * np.sin(2 * np.pi * 0.07 * t) ** 2
        for k in range(int(total / 1.1)):  # latido
            o = int((0.5 + k * 1.1) * SR)
            for dd in (0, int(0.25 * SR)):
                n = int(0.18 * SR); tt = np.arange(n) / SR
                if o + dd + n < len(mus): mus[o + dd:o + dd + n] += 1.6 * np.sin(2 * np.pi * 50 * tt) * np.exp(-tt * 25)
    else:
        chords = [[220, 261.6, 329.6], [174.6, 220, 261.6], [130.8, 196, 261.6], [196, 246.9, 293.7]]; seg = 4.0
        for k in range(int(total / seg) + 2):
            m = (t >= k * seg) & (t < (k + 1) * seg + 1.0); tt = t[m] - k * seg
            env = np.clip(tt, 0, 1) * np.clip((seg + 1.0) - tt, 0, 1)
            for f in chords[k % 4]: mus[m] += env * (np.sin(2 * np.pi * f * tt) + .3 * np.sin(4 * np.pi * f * tt) + .5 * np.sin(np.pi * f * tt))
        mus *= 0.5 + 0.5 * np.sin(2 * np.pi * 0.25 * t) ** 2
    mus = mus / (np.abs(mus).max() + 1e-9) * 0.05
    r = np.random.default_rng(1)
    for s in starts[1:]:
        n = int(0.5 * SR); o = int((s - 0.25) * SR); w = np.convolve(r.standard_normal(n), np.ones(40) / 40, "same") * np.hanning(n) * 0.25
        if o >= 0 and o + n < len(mus): mus[o:o + n] += w
    fo = int(1.0 * SR); mus[-fo:] *= np.linspace(1, 0, fo)
    return mus

# ------------------------------------------------------------------ main
def build(spec_path, out_path):
    spec = json.load(open(spec_path, encoding="utf8"))
    work = tempfile.mkdtemp(prefix="vid_"); SR = 48000
    durs = [tts(sc["line"], f"{work}/l{i}.wav") for i, sc in enumerate(spec["scenes"])]
    Ds = [round((LEAD + d + TAIL) * FPS) / FPS for d in durs]
    starts = np.cumsum([0] + Ds[:-1]); total = sum(Ds)
    spec["_total"] = total
    jobs = [(dict(spec, _start=float(starts[i])), i, Ds[i], durs[i], f"{work}/s{i}.mp4") for i in range(len(Ds))]
    with ProcessPoolExecutor(max_workers=min(len(jobs), os.cpu_count() or 2)) as ex: files = list(ex.map(render_scene, jobs))
    voice = np.zeros(int(total * SR) + SR)
    for i, s in enumerate(starts):
        a = np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", f"{work}/l{i}.wav", "-f", "f32le", "-"]), np.float32)
        o = int((s + LEAD) * SR); voice[o:o + len(a)] += a
    voice[:].astype(np.float32).tofile(f"{work}/voice.f32")
    m = music(len(voice) / SR, spec.get("mood", "bright"), starts); m.astype(np.float32).tofile(f"{work}/music.f32")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", f"{work}/voice.f32", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", f"{work}/music.f32",
                    "-filter_complex", "[0:a]asplit=2[vo1][vo2];[1:a][vo1]sidechaincompress=threshold=0.02:ratio=6[md];[vo2]volume=1.4[vo3];[vo3][md]amix=inputs=2:normalize=0,loudnorm=I=-13:TP=-1,aresample=48000[out]",
                    "-map", "[out]", "-ac", "2", "-c:a", "aac", "-b:a", "192k", f"{work}/mix.m4a"], check=True)
    open(f"{work}/list.txt", "w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt", "-c", "copy", f"{work}/v.mp4"], check=True)
    tmp = out_path + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{work}/v.mp4", "-i", f"{work}/mix.m4a", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out_path); shutil.rmtree(work, ignore_errors=True)
    print("OK", out_path, round(total, 1), "s")

def preview(spec_path, out_dir):
    """Dibuja un cuadro por escena (en el momento de más contenido) para revisar antes de renderizar."""
    spec = json.load(open(spec_path, encoding="utf8")); os.makedirs(out_dir, exist_ok=True); thumbs = []
    for i, sc in enumerate(spec["scenes"]):
        D = 6.0; words = chunks_for(sc["line"], D - 1, LEAD); im = frame(spec, i, 2.5, D, words).convert("RGB")
        thumbs.append(im.resize((270, 480)))
    sheet = Image.new("RGB", (270 * min(5, len(thumbs)), 480 * ((len(thumbs) + 4) // 5)))
    for k, th in enumerate(thumbs): sheet.paste(th, ((k % 5) * 270, (k // 5) * 480))
    p = os.path.join(out_dir, "preview.jpg"); sheet.save(p, quality=85); print(p)

if __name__ == "__main__":
    if sys.argv[1] == "--preview": preview(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
    else: build(sys.argv[1], sys.argv[2])
