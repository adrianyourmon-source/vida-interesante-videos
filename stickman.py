"""Personajes stickman animados para engine.py.
Escena JSON: "stickman": [{"action": "scared", "face": "fear", "x": 0.5, "facing": "right", "prop": "🔦", "color": "white"}]
Acciones: idle, talk, walk, run, run_away, scared, shiver, point, think, cheer, shrug, look, dizzy, sad, sneak, wave
Caras: neutral, happy, fear, surprised, sad, cold, thinking, angry, dizzy
"""
import math
from PIL import Image, ImageDraw

TORSO, NECK, HEAD_R = 190, 26, 52
UARM, FARM, THIGH, SHIN = 108, 100, 130, 125
GROUND = 1400
OUT = (18, 18, 24, 255)
COLORS = {"white": (250, 250, 250), "yellow": (255, 205, 40), "red": (240, 80, 70), "blue": (90, 170, 255), "green": (110, 220, 120)}

DEFAULT_FACE = {"scared": "fear", "shiver": "cold", "think": "thinking", "cheer": "happy", "run_away": "fear", "sad": "sad",
                "dizzy": "dizzy", "shrug": "neutral", "look": "surprised", "sneak": "fear", "wave": "happy"}

def pose(action, t, ph=0.0):
    """Devuelve ángulos (grados, 0 = hacia abajo, + = hacia el frente) y desplazamientos."""
    s = math.sin; T = t + ph
    p = dict(lean=0, head=0, ls=-12, le=0, rs=12, re=0, lh=-6, lk=0, rh=6, rk=0, dy=0, dx=0, shake=0, rot=0)
    if action == "idle":
        p.update(ls=-12 + 3 * s(T * 2), rs=12 - 3 * s(T * 2), dy=3 * s(T * 2))
    elif action == "talk":
        p.update(rs=60 + 25 * s(T * 5), re=70 + 20 * s(T * 5 + 1), ls=-15, head=4 * s(T * 3), dy=2 * s(T * 4))
    elif action in ("walk", "sneak"):
        k = 3.5 if action == "walk" else 2.2; a = 28 if action == "walk" else 18
        p.update(lh=a * s(T * k), rh=-a * s(T * k), lk=-25 * max(0, s(T * k + 1.2)) - 5, rk=-25 * max(0, -s(T * k + 1.2)) - 5,
                 ls=-a * s(T * k), rs=a * s(T * k), le=20, re=20, dy=-6 * abs(s(T * k)))
        if action == "sneak": p.update(lean=18, lk=p["lk"] - 30, rk=p["rk"] - 30, dy=40, ls=40, le=90, rs=50, re=95)
    elif action in ("run", "run_away"):
        k = 7
        p.update(lean=16, lh=45 * s(T * k), rh=-45 * s(T * k), lk=-70 * max(0, s(T * k + 1)) - 10, rk=-70 * max(0, -s(T * k + 1)) - 10,
                 ls=-55 * s(T * k), rs=55 * s(T * k), le=80, re=80, dy=-14 * abs(s(T * k)))
        if action == "run_away": p["dx"] = 1
    elif action == "scared":
        p.update(ls=-150, le=-30, rs=150, re=30, lh=-18, rh=18, lk=-25, rk=-25, dy=22, shake=6, head=-6)
    elif action == "shiver":
        p.update(ls=-25, le=125, rs=25, re=-125, lh=-4, rh=4, shake=5, dy=8, head=-4)
    elif action == "point":
        p.update(rs=125 + 3 * s(T * 2), re=8, ls=-15, head=-10)
    elif action == "think":
        p.update(rs=40, re=145, ls=25, le=80, head=10 + 3 * s(T * 1.5))
    elif action == "cheer":
        b = abs(s(T * 4)); p.update(ls=-160, rs=160, le=-10, re=10, dy=-40 * b, lk=-30 * b, rk=-30 * b, lh=-10, rh=10)
    elif action == "shrug":
        p.update(ls=-70, le=-70, rs=70, re=70, head=8 * s(T * 1.5))
    elif action == "look":
        p.update(rs=150, re=75, ls=-15, head=-8, lean=6)
    elif action == "dizzy":
        p.update(ls=-60 + 20 * s(T * 3), rs=60 + 20 * s(T * 3), rot=8 * s(T * 2.5), head=12 * s(T * 3), lk=-10, rk=-10)
    elif action == "sad":
        p.update(lean=10, head=22, ls=-5, rs=5, dy=6)
    elif action == "wave":
        p.update(rs=150, re=20 + 35 * s(T * 7), ls=-12)
    return p

def _pt(x, y, ang, ln, f):
    a = math.radians(ang) * f
    return x + ln * math.sin(a), y + ln * math.cos(a)

def face(d, cx, cy, r, kind, f, t):
    ex = r * 0.32; ey = cy - r * 0.12; eo = r * 0.18 * f; er = r * 0.11
    if kind == "dizzy":
        for sx in (-1, 1):
            x0 = cx + eo + sx * ex
            d.line([(x0 - er, ey - er), (x0 + er, ey + er)], fill=OUT, width=5); d.line([(x0 - er, ey + er), (x0 + er, ey - er)], fill=OUT, width=5)
    else:
        big = kind in ("fear", "surprised")
        rr = er * (1.5 if big else 1.0)
        for sx in (-1, 1):
            x0 = cx + eo + sx * ex
            if big: d.ellipse([x0 - rr, ey - rr, x0 + rr, ey + rr], fill=(255, 255, 255, 255), outline=OUT, width=4); d.ellipse([x0 - er * .6, ey - er * .6, x0 + er * .6, ey + er * .6], fill=OUT)
            elif kind == "happy": d.arc([x0 - er * 1.3, ey - er, x0 + er * 1.3, ey + er * 1.4], 200, 340, fill=OUT, width=5)
            else:
                blink = (t % 3.3) < 0.12
                if blink: d.line([(x0 - er, ey), (x0 + er, ey)], fill=OUT, width=5)
                else: d.ellipse([x0 - er, ey - er, x0 + er, ey + er], fill=OUT)
            if kind in ("angry", "sad", "fear", "thinking"):
                tilt = {"angry": 1, "sad": -1, "fear": -1, "thinking": 0.5 * sx}[kind] * sx
                d.line([(x0 - er * 1.4, ey - er * 2.3 - tilt * 5), (x0 + er * 1.4, ey - er * 2.3 + tilt * 5)], fill=OUT, width=5)
    my = cy + r * 0.38; mx = cx + eo
    if kind == "happy": d.chord([mx - r * .35, my - r * .25, mx + r * .35, my + r * .25], 0, 180, fill=OUT)
    elif kind in ("fear", "surprised"): o = r * (0.16 + 0.03 * math.sin(t * 12)); d.ellipse([mx - o, my - o * 1.2, mx + o, my + o * 1.2], fill=OUT)
    elif kind == "sad": d.arc([mx - r * .3, my - r * .02, mx + r * .3, my + r * .35], 200, 340, fill=OUT, width=5)
    elif kind == "cold":
        pts = [(mx - r * .32 + i * r * .08, my + (4 if i % 2 else -4) * (1 + 0.4 * math.sin(t * 30))) for i in range(9)]
        d.line(pts, fill=OUT, width=4)
    elif kind == "thinking": d.line([(mx - r * .25, my + 4), (mx + r * .2, my - 4)], fill=OUT, width=5)
    elif kind == "angry": d.arc([mx - r * .3, my, mx + r * .3, my + r * .35], 200, 340, fill=OUT, width=5)
    elif kind == "dizzy": d.arc([mx - r * .25, my - r * .1, mx + r * .25, my + r * .2], 0, 180, fill=OUT, width=5)
    else: d.line([(mx - r * .22, my), (mx + r * .22, my)], fill=OUT, width=5)

def draw(img, spec, t, D, emoji_fn=None, scale=1.0):
    """Dibuja un stickman en img (RGBA 1080x1920)."""
    W = img.width; action = spec.get("action", "idle"); f = -1 if spec.get("facing", "right") == "left" else 1
    kind = spec.get("face") or DEFAULT_FACE.get(action, "neutral")
    col = COLORS.get(spec.get("color", "white"), COLORS["white"]) + (255,)
    p = pose(action, t, spec.get("phase", 0.0))
    x = spec.get("x", 0.5) * W
    if action in ("walk", "sneak") and spec.get("move", True): x += f * (t - D / 2) * 45
    if p["dx"]: x += f * max(0, t - 0.4) ** 1.6 * 160
    if spec.get("enter"): x -= f * max(0, 1 - t / 0.6) * W * 0.7
    x += p["shake"] * math.sin(t * 40)
    sc = scale * spec.get("size", 1.2)
    layer = Image.new("RGBA", (W, img.height), (0, 0, 0, 0)); d = ImageDraw.Draw(layer)
    hip_y = GROUND - (THIGH + SHIN) * sc + p["dy"] * sc; hip = (x, hip_y)
    lean = p["lean"]
    neck = _pt(hip[0], hip[1], 180 + lean, TORSO * sc, f)
    hc = _pt(neck[0], neck[1], 180 + lean + p["head"], (NECK + HEAD_R) * sc, f)
    sh = _pt(hip[0], hip[1], 180 + lean, (TORSO - 18) * sc, f)
    def limb(base, a1, a2, l1, l2):
        j = _pt(base[0], base[1], a1 + lean * 0.3, l1 * sc, f); e = _pt(j[0], j[1], a1 + a2 + lean * 0.3, l2 * sc, f); return j, e
    le_, lhand = limb(sh, p["ls"], p["le"], UARM, FARM); re_, rhand = limb(sh, p["rs"], p["re"], UARM, FARM)
    lk_, lfoot = limb(hip, p["lh"], p["lk"], THIGH, SHIN); rk_, rfoot = limb(hip, p["rh"], p["rk"], THIGH, SHIN)
    segs = [(hip, neck), (sh, le_), (le_, lhand), (sh, re_), (re_, rhand), (hip, lk_), (lk_, lfoot), (hip, rk_), (rk_, rfoot)]
    wo, wi = int(36 * sc), int(22 * sc)
    for w, c in ((wo, OUT), (wi, col)):
        for a, b in segs:
            d.line([a, b], fill=c, width=w)
            for q in (a, b): d.ellipse([q[0] - w / 2, q[1] - w / 2, q[0] + w / 2, q[1] + w / 2], fill=c)
    r = HEAD_R * sc
    d.ellipse([hc[0] - r - 6, hc[1] - r - 6, hc[0] + r + 6, hc[1] + r + 6], fill=OUT); d.ellipse([hc[0] - r, hc[1] - r, hc[0] + r, hc[1] + r], fill=col)
    face(d, hc[0], hc[1], r, kind, f, t)
    if p["rot"]: layer = layer.rotate(p["rot"], center=(x, GROUND), resample=Image.BICUBIC)
    sh_l = Image.new("RGBA", (W, img.height), (0, 0, 0, 0)); ImageDraw.Draw(sh_l).ellipse([x - 120 * sc, GROUND - 14, x + 120 * sc, GROUND + 14], fill=(0, 0, 0, 90))
    img.alpha_composite(sh_l); img.alpha_composite(layer)
    if spec.get("prop") and emoji_fn:
        pr = emoji_fn(spec["prop"], int(130 * sc)); hand = rhand
        img.alpha_composite(pr, (int(hand[0] - pr.width / 2), int(hand[1] - pr.height / 2)))
    if kind == "fear" or action in ("scared", "run_away"):  # gotas de sudor
        dd = ImageDraw.Draw(img)
        for k in range(2):
            yy = hc[1] - r * 0.6 + ((t * 120 + k * 40) % 60); xx = hc[0] - f * (r + 18 + k * 16)
            dd.ellipse([xx - 7, yy - 10, xx + 7, yy + 10], fill=(140, 210, 255, 230))
    if spec.get("say"):
        from PIL import ImageFont
        fnt = ImageFont.truetype("/usr/share/fonts/truetype/google-fonts/ofl/montserrat/Montserrat[wght].ttf", 46)
        try: fnt.set_variation_by_name("Black")
        except Exception: pass
        txt = spec["say"].upper(); tw = fnt.getlength(txt); pop = min(1, max(0, (t - 0.4) / 0.2))
        if pop > 0:
            bw, bh = tw + 60, 96; bx = min(max(hc[0] + f * (r + 40 + bw / 2), bw / 2 + 20), W - bw / 2 - 20); by = hc[1] - r - 70
            bl = Image.new("RGBA", (int(bw) + 20, bh + 50), (0, 0, 0, 0)); bd = ImageDraw.Draw(bl)
            bd.rounded_rectangle([4, 4, bw + 4, bh + 4], 40, fill=(255, 255, 255, 255), outline=OUT, width=5)
            tx = (hc[0] - (bx - bw / 2)) + 4; tx = min(max(tx, 40), bw - 40)
            bd.polygon([(tx - 18, bh), (tx + 18, bh), (tx, bh + 40)], fill=(255, 255, 255, 255))
            bd.text((34, 4 + bh / 2), txt, font=fnt, fill=OUT, anchor="lm")
            if pop < 1: bl = bl.resize((max(1, int(bl.width * pop)), max(1, int(bl.height * pop))))
            img.alpha_composite(bl, (int(bx - bl.width / 2), int(by - bl.height / 2)))
    if action == "think":
        dd = ImageDraw.Draw(img); bx = hc[0] + f * (r + 110); by = hc[1] - r + 20 - 8 * math.sin(t * 3)
        for k, rr in enumerate((10, 16, 0)):
            if rr: dd.ellipse([hc[0] + f * (r + 10 + k * 22) - rr, hc[1] - r - k * 22 - rr, hc[0] + f * (r + 10 + k * 22) + rr, hc[1] - r - k * 22 + rr], fill=(255, 255, 255, 230))
        if emoji_fn:
            q = emoji_fn("❓", 90); img.alpha_composite(q, (int(bx - q.width / 2), int(by - 60 - q.height / 2)))
