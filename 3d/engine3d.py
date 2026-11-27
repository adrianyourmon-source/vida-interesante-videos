#!/usr/bin/env python3
"""Vida Interesante - motor de videos 3D (1080x1920) con voz neural.
Uso:
  python3 3d/engine3d.py guiones/<slug>.json videos/<slug>.mp4
  python3 3d/engine3d.py --preview guiones/<slug>.json /tmp/prev     (un cuadro por escena)
Formato del guion: ver INSTRUCCIONES.md (sección "Videos 3D")."""
import os, sys, json, math, random, subprocess, tempfile, shutil, urllib.request
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE); sys.path.insert(0, ROOT)
from PIL import Image, ImageDraw, ImageFilter
import engine as E                      # textos, subtítulos, emojis, música (motor 2D)
from gl3d import GL, W, H, T, S, RX, RY, RZ
import props3d as P

FPS = 30; LEAD, TAIL = 0.2, 0.45
KOKORO_DIR = os.path.expanduser("~/.cache/kokoro")
KOKORO_URLS = ["https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx",
               "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"]
VOICE, SPEED = "em_alex", 1.05

def ease(x): return E.ease(x)
def lerp(a, b, t): return a + (b - a) * t

# ------------------------------------------------------------------ escenarios
ENVS = {
    # nombre: cielo arriba, cielo abajo, estrellas, suelo, niebla, luz, ambiente
    "forest_day":  dict(top=(0.30, 0.55, 0.90), bot=(0.78, 0.88, 0.98), stars=0, ground=(0.42, 0.6, 0.3), fogd=0.025, L=(-0.5, 0.8, 0.6), amb=(0.38, 0.4, 0.46)),
    "forest_night": dict(top=(0.02, 0.03, 0.07), bot=(0.08, 0.12, 0.16), stars=0.8, ground=(0.16, 0.2, 0.2), fogd=0.06, fog=(0.1, 0.13, 0.16), L=(-0.4, 0.7, 0.6), Lcol=(0.55, 0.6, 0.8), amb=(0.14, 0.16, 0.22)),
    "snow_day":    dict(top=(0.45, 0.62, 0.85), bot=(0.88, 0.92, 0.97), stars=0, ground=(0.93, 0.95, 1.0), fogd=0.03, L=(-0.5, 0.8, 0.6), amb=(0.42, 0.45, 0.52)),
    "snow_night":  dict(top=(0.02, 0.03, 0.08), bot=(0.12, 0.16, 0.26), stars=1.0, ground=(0.7, 0.76, 0.88), fogd=0.05, fog=(0.12, 0.15, 0.24), L=(-0.4, 0.7, 0.6), Lcol=(0.6, 0.66, 0.85), amb=(0.18, 0.2, 0.28)),
    "desert":      dict(top=(0.95, 0.6, 0.3), bot=(0.99, 0.86, 0.62), stars=0, ground=(0.88, 0.68, 0.4), fogd=0.02, L=(-0.3, 0.7, 0.6), amb=(0.42, 0.36, 0.32)),
    "ocean":       dict(top=(0.30, 0.55, 0.90), bot=(0.78, 0.88, 0.98), stars=0, ground=(0.88, 0.8, 0.58), fogd=0.02, L=(-0.5, 0.8, 0.6), amb=(0.38, 0.4, 0.46), water=True),
    "city_night":  dict(top=(0.03, 0.03, 0.1), bot=(0.18, 0.12, 0.28), stars=0.6, ground=(0.18, 0.18, 0.22), fogd=0.03, fog=(0.15, 0.1, 0.22), L=(-0.4, 0.7, 0.6), Lcol=(0.6, 0.6, 0.85), amb=(0.2, 0.2, 0.28)),
    "lab":         dict(top=(0.02, 0.08, 0.14), bot=(0.04, 0.2, 0.28), stars=0, ground=(0.12, 0.2, 0.26), fogd=0.03, fog=(0.04, 0.16, 0.22), L=(-0.4, 0.8, 0.6), Lcol=(0.7, 0.9, 1.0), amb=(0.2, 0.28, 0.32)),
    "red":         dict(top=(0.1, 0.01, 0.01), bot=(0.4, 0.08, 0.03), stars=0, ground=(0.22, 0.08, 0.06), fogd=0.05, fog=(0.3, 0.06, 0.03), L=(-0.4, 0.7, 0.6), Lcol=(1.0, 0.6, 0.45), amb=(0.25, 0.12, 0.1)),
    "space":       dict(top=(0.01, 0.015, 0.05), bot=(0.05, 0.07, 0.16), stars=1.0, ground=None, fogd=0, L=(-0.7, 0.3, 0.6), amb=(0.06, 0.07, 0.1), rim=(0.2, 0.35, 0.7)),
}
DEFAULT_PROPS = {
    "forest_day": [("pine", -3, -3), ("pine", 3.2, -4), ("pine", -6, -8), ("pine", 5.5, -9), ("pine", 0.5, -12), ("house", -4.5, -6)],
    "forest_night": [("pine", -3, -3), ("pine", 3.2, -4), ("pine", -6, -8), ("pine", 5.5, -9), ("pine", 0.5, -12), ("pine", -1.5, -7)],
    "snow_day": [("snowpine", -3, -3), ("snowpine", 3.2, -4), ("snowpine", -6, -8), ("snowpine", 5.5, -9), ("rock", 2.2, -2)],
    "snow_night": [("snowpine", -3, -3), ("snowpine", 3.2, -4), ("snowpine", -6, -8), ("snowpine", 5.5, -9), ("snowpine", 0.5, -12)],
    "desert": [("cactus", -2.8, -2.5), ("cactus", 3.3, -4), ("rock", 1.8, -6)],
    "ocean": [("house", 3.5, -3), ("pine", 5.5, -6)],
    "city_night": [("building", -3, -4), ("building", 3, -5), ("building", -6, -9), ("building", 6, -10), ("building", 0, -14)],
    "lab": [("table", 2.6, -1.5), ("flask", 2.4, -1.5), ("flask", 2.9, -1.4)],
    "red": [("deadtree", -3, -3), ("deadtree", 3.3, -4.5), ("rock", 1.5, -2)],
    "space": [],
}
WEATHER_AUTO = {"snow_night": "snow", "snow_day": "snow", "forest_night": "dust", "red": "embers", "city_night": "rain", "desert": "dust"}

RNG = random.Random(11)
FLAKES = [(RNG.uniform(-5, 5), RNG.uniform(0, 6), RNG.uniform(-4, 3), RNG.uniform(0.6, 1.4), RNG.uniform(0, 6.28)) for _ in range(140)]

def tex_setup(g):
    tx = E.textures(); c = tx["cloud"][..., None]
    g.texture("earth", tx["earth"] * (1 - c) + 250 * c)
    g.texture("moon", tx["moon"]); g.texture("mars", tx["mars"])

def prop(g, pr, t, D, o):
    k = pr["type"]; x, z = pr.get("x", 0.0), pr.get("z", -2.0); s = pr.get("s", 1.0); col = pr.get("color")
    if k == "pine": P.tree(g, x, z, 2.4 * s, sway=0.04 * math.sin(t * 2 + x), col=tuple(col) if col else (0.18, 0.45, 0.22))
    elif k == "snowpine":
        P.tree(g, x, z, 2.4 * s, sway=0.03 * math.sin(t * 2 + x), col=(0.2, 0.4, 0.3))
        g.draw("cone", T(x, 2.4 * s * 0.62, z) @ S(2.4 * s * 0.18, 2.4 * s * 0.32, 2.4 * s * 0.18), (0.95, 0.97, 1.0), spec=0.3)
    elif k == "cedar":
        g.draw("cyl", T(x, 0, z) @ S(0.28 * s, 5.5 * s, 0.28 * s), (0.4, 0.27, 0.16), spec=0)
        for j in range(5): g.draw("cone", T(x, (2.2 + j * 0.8) * s, z) @ S((1.6 - j * 0.25) * s, 1.4 * s, (1.6 - j * 0.25) * s), (0.14, 0.35, 0.2), spec=0.1)
        if pr.get("broken"):
            for j in range(6): g.draw("cyl", T(x + 0.25 * s, (0.8 + j * 0.6) * s, z + 0.1) @ RZ(-1.2 + 0.2 * j) @ S(0.05, 0.5, 0.05), (0.75, 0.6, 0.4))
    elif k == "deadtree":
        g.draw("cyl", T(x, 0, z) @ RZ(0.08) @ S(0.12 * s, 2.6 * s, 0.12 * s), (0.2, 0.14, 0.1), spec=0)
        for j in range(4): g.draw("cyl", T(x, (1.2 + j * 0.4) * s, z) @ RZ((-1) ** j * 0.9) @ S(0.05 * s, 0.9 * s, 0.05 * s), (0.2, 0.14, 0.1), spec=0)
    elif k == "house": P.house(g, x, z, 1.3 * s, 1.1 * s)
    elif k == "building": P.building(g, T(x, 0, z), 1.3 * s, 3.5 * s + (abs(x) % 1.5), tuple(col) if col else (0.3, 0.32, 0.42))
    elif k == "factory":
        P.building(g, T(x, 0, z), 2.0 * s, 1.8 * s, (0.5, 0.5, 0.55))
        for j in (-0.5, 0.5):
            g.draw("cyl", T(x + j * s, 1.8 * s, z) @ S(0.18 * s, 1.6 * s, 0.18 * s), (0.55, 0.45, 0.4))
            for q in range(4):
                ph = (t * 0.4 + q * 0.25) % 1.0; g.ball((x + j * s + ph * 0.6, (3.4 + ph * 1.8) * s, z), (0.2 + ph * 0.35) * s, (0.75, 0.75, 0.78), alpha=0.6 * (1 - ph))
    elif k == "tent":
        g.draw("pyr", T(x, 0, z) @ RY(math.pi / 4) @ S(1.1 * s, 1.1 * s, 1.1 * s), tuple(col) if col else (0.85, 0.5, 0.2), spec=0.2)
        if pr.get("buried"): g.draw("sphere", T(x, -0.4 * s, z) @ S(1.4 * s, 0.75 * s, 1.2 * s), (0.93, 0.95, 1.0), spec=0.2)
        if pr.get("torn"): g.draw("box", T(x, 0.45 * s, z + 0.56 * s) @ RZ(0.2) @ S(0.08, 0.6 * s, 0.02), (0.05, 0.05, 0.07))
    elif k == "fire":
        for a in (0.5, -0.5): g.draw("cyl", T(x, 0.06, z) @ RY(a) @ RZ(math.pi / 2) @ T(0, -0.35 * s, 0) @ S(0.06 * s, 0.7 * s, 0.06 * s), (0.35, 0.22, 0.12))
        for j, (c, hh) in enumerate([((1.0, 0.45, 0.1), 0.6), ((1.0, 0.8, 0.2), 0.4)]):
            fl = 1 + 0.18 * math.sin(t * 13 + j * 2)
            g.draw("cone", T(x, 0.05, z) @ S(0.22 * s * (1 - j * 0.3), hh * s * fl, 0.22 * s * (1 - j * 0.3)), c, emis=1.0)
        q = g.project((x, 0.4 * s, z)); o.setdefault("glows", []).append((q, int(220 * s), (255, 150, 50))) if q else None
    elif k == "rock": g.draw("lsphere", T(x, 0.15 * s, z) @ S(0.7 * s, 0.45 * s, 0.6 * s), tuple(col) if col else (0.45, 0.43, 0.42), spec=0.2)
    elif k == "cactus":
        g.draw("cyl", T(x, 0, z) @ S(0.18 * s, 1.6 * s, 0.18 * s), (0.25, 0.55, 0.3)); g.ball((x, 1.6 * s, z), 0.18 * s, (0.25, 0.55, 0.3))
        g.draw("cyl", T(x + 0.18 * s, 0.7 * s, z) @ RZ(-1.2) @ S(0.1 * s, 0.4 * s, 0.1 * s), (0.25, 0.55, 0.3))
    elif k == "boots":
        n = pr.get("n", 9)
        for j in range(n): g.draw("box", T(x + (j - (n - 1) / 2) * 0.22 * s, 0.1 * s, z) @ S(0.13 * s, 0.2 * s, 0.28 * s), (0.25, 0.16, 0.1), spec=0.3)
    elif k == "footprints":
        for j in range(pr.get("n", 12)): g.draw("lsphere", T(x + j * 0.45 * s, 0.01, z + (0.12 if j % 2 else -0.12)) @ S(0.1, 0.01, 0.16), (0.35, 0.38, 0.45))
    elif k == "orbs":
        for j in range(pr.get("n", 3)):
            p = (x + (j - 1) * 1.4 * s + 0.3 * math.sin(t * 0.7 + j), pr.get("y", 4.0) + 0.4 * math.sin(t * 0.9 + j * 2), z)
            g.ball(p, 0.28 * s, (1.0, 0.55, 0.15), mesh="sphere", emis=1.0)
            q = g.project(p); o.setdefault("glows", []).append((q, int(170 * s), (255, 140, 40))) if q else None
    elif k == "moon":
        p = (x, pr.get("y", 5.0), z); g.ball(p, 0.7 * s, (0.95, 0.95, 0.9), mesh="sphere", emis=0.9)
        q = g.project(p); o.setdefault("glows", []).append((q, int(200 * s), (200, 210, 255))) if q else None
    elif k == "ravine":
        for sx in (-1, 1): g.draw("box", T(x + sx * 3.2 * s, 1.2 * s, z) @ RZ(sx * 0.15) @ S(3.0 * s, 4 * s, 12), (0.9, 0.93, 0.98), spec=0.2)
    elif k == "avalanche":
        k2 = ease(t / D); g.draw("box", T(lerp(-7, 0.5, k2), lerp(3.0, 0.4, k2), z) @ RZ(-0.35) @ S(6 * s, 0.9 * s, 6), (0.96, 0.97, 1.0), spec=0.3)
        for j in range(25): g.ball((lerp(-7, 0.5, k2) + 3 * math.cos(j) , lerp(3.4, 0.8, k2) + 0.5 * math.sin(j * 3 + t * 5), z + (j % 5) - 2), 0.25, (1, 1, 1), alpha=0.8)
    elif k == "wave": P.wave(g, lerp(-12, pr.get("to", 0.5), ease(t / D)), lerp(1.5, 2.8 * s, ease(t / D)))
    elif k == "table":
        g.draw("box", T(x, 0.75 * s, z) @ S(1.4 * s, 0.08, 0.8 * s), (0.85, 0.88, 0.9), spec=0.6)
        for sx in (-1, 1): g.draw("box", T(x + sx * 0.6 * s, 0.37 * s, z) @ S(0.06, 0.75 * s, 0.06), (0.6, 0.62, 0.65))
    elif k == "flask":
        g.ball((x, 0.95, z), 0.16 * s, tuple(col) if col else (0.3, 1.0, 0.5), mesh="sphere", emis=0.6, alpha=0.85)
        g.draw("cyl", T(x, 1.05, z) @ S(0.05, 0.25, 0.05), (0.85, 0.9, 1.0), alpha=0.7)
    elif k == "glow_items":  # objetos que brillan (radiación, energía)
        for j in range(pr.get("n", 4)):
            p = (x + (j - 1.5) * 0.5 * s, 0.15 + 0.08 * math.sin(t * 3 + j), z); g.draw("box", T(*p) @ RY(j) @ S(0.4 * s, 0.12 * s, 0.3 * s), (0.25, 0.5, 0.25), spec=0.2)
            q = g.project(p); o.setdefault("glows", []).append((q, int(120 * s), (90, 255, 90))) if q else None
    elif k in ("earth", "moon_planet", "mars"):
        r = pr.get("r", 1.0); c = (x, pr.get("y", -0.1), z); rot = t * pr.get("spin", 0.4)
        tex = {"earth": "earth", "moon_planet": "moon", "mars": "mars"}[k]
        P.earth(g, c, r, rot, tex=tex, tilt=pr.get("tilt", 0.2), halo=(k == "earth"))
    elif k == "sun":
        c = (x, pr.get("y", 0.0), z); g.ball(c, pr.get("r", 0.6), (1.0, 0.75, 0.25), mesh="sphere", emis=1.0)
        q = g.project(c); o.setdefault("glows", []).append((q, int(300 * pr.get("r", 0.6) / 0.6), (255, 190, 80))) if q else None
    elif k == "ring": g.draw("torus", T(x, pr.get("y", 0), z) @ S(pr.get("r", 1.0), 0.5, pr.get("r", 1.0)), tuple(col) if col else (1.0, 0.8, 0.15), emis=0.8)

def camera(sc, env, t, D):
    if env == "space":
        cam = sc.get("camera", "space")
        z = lerp(7.0, 6.4, ease(t / D)) if cam != "space_far" else 9.0
        return (0.3 * math.sin(t * 0.2), 0.5, z), (0, 0.0, 0), 38
    c = sc.get("camera", "medium")
    sway = 0.35 * math.sin(t * 0.35)
    if c == "close": return (sway, 1.5, lerp(5.2, 4.7, ease(t / D))), (0, 1.15, 0), 38
    if c == "wide": return (sway, 2.6, lerp(11, 10, ease(t / D))), (0, 1.2, 0), 38
    if c == "low": return (sway, 0.5, 6.2), (0, 1.7, 0), 40
    if c == "high": return (sway, 6.5, 6.5), (0, 0.6, 0), 38
    if c == "tall": return (sway, 2.4, 9.5), (0, 2.6, 0), 40
    return (sway, 1.6, lerp(7.4, 6.8, ease(t / D))), (0, 1.1, 0), 38

def weather(g, kind, t):
    if kind == "snow":
        for x, y, z, sp, ph in FLAKES: g.ball((x + 0.3 * math.sin(t * sp + ph), 6 - ((t * 0.7 * sp + y) % 6), z), 0.025, (1, 1, 1), emis=0.8)
    elif kind == "embers":
        for x, y, z, sp, ph in FLAKES[:80]: g.ball((x + 0.2 * math.sin(t + ph), (t * 0.6 * sp + y) % 6, z), 0.02, (1.0, 0.55, 0.15), emis=1.0)
    elif kind == "dust":
        for x, y, z, sp, ph in FLAKES[:70]: g.ball(((x + t * 0.2 * sp) % 10 - 5, 0.3 + (y + 0.2 * math.sin(t + ph)) % 4, z), 0.015, (0.9, 0.9, 0.85), emis=0.5, alpha=0.7)
    elif kind == "rain":
        for x, y, z, sp, ph in FLAKES: g.draw("box", T(x, 6 - ((t * 9 * sp + y) % 6), z) @ RZ(0.15) @ S(0.012, 0.35, 0.012), (0.7, 0.8, 1.0), emis=0.6, alpha=0.6)

def draw_figs(g, sc, t, D, env):
    figs = sc.get("stickman") or []
    if isinstance(figs, dict): figs = [figs]
    heads = []
    for fg in figs:
        x = (fg.get("x", 0.5) - 0.5) * 2.8; z = fg.get("z", 0.0); y = fg.get("y", 0.0)
        if fg.get("move") or fg.get("action") in ("walk", "sneak"): x += (1 if fg.get("facing", "right") == "right" else -1) * (t - D / 2) * 0.35 * (0 if fg.get("move") is False else 1)
        if fg.get("action") == "run_away": x += (1 if fg.get("facing", "right") == "right" else -1) * max(0, t - 0.4) ** 1.3 * 0.3
        f = -1 if fg.get("facing", "right") == "left" else 1
        col = {"white": P.WHITE, "yellow": (1.0, 0.82, 0.2), "red": (0.95, 0.35, 0.3), "blue": (0.4, 0.7, 1.0), "green": (0.45, 0.85, 0.5), "orange": (1.0, 0.62, 0.3)}.get(fg.get("color", "white"), P.WHITE)
        sc_ = fg.get("size", 1.0) * (0.00095 if env == "space" else 0.00313); r = 0.05 * fg.get("size", 1.0) * (0.3 if env == "space" else 1)
        base = np.array([x if env != "space" else fg.get("wx", 0.0), y if env != "space" else fg.get("wy", 0.45), z], "f4")
        xf = None
        if fg.get("fly"):
            fly = ease((t - fg.get("fly_at", 0.8)) / 1.5); ang = fly * 6
            if fly > 0:
                b2 = base + np.array([fly * 6, math.sin(min(fly, 1) * math.pi) * 1.6, 0], "f4")
                R = np.array([[math.cos(ang), math.sin(ang), 0], [-math.sin(ang), math.cos(ang), 0], [0, 0, 1]], "f4")
                xf = (lambda b0, b2, R: (lambda Pp: b2 + (Pp - b0 - np.array([0, 0.9, 0], "f4")) @ R + np.array([0, 0.9, 0], "f4")))(base, b2, R)
        J = P.stick(g, base, fg.get("action", "idle"), t, phase=fg.get("phase", 0.0), yaw=fg.get("yaw", -0.15 * f), s=sc_, color=col, face=fg.get("face"), f=f, xf=xf, r=r)
        if env != "space" and not fg.get("fly") and y < 0.05: P.shadow(g, J["hip"][0], z)
        heads.append((fg, J))
    return heads

# ------------------------------------------------------------------ overlays
_bf = None
def bubble(im, txt, x, y):
    global _bf
    if _bf is None: _bf = E.font(46, "Black")
    tw = _bf.getlength(txt); bw, bh = int(tw + 60), 96; x = min(max(x, bw / 2 + 20), W - bw / 2 - 20)
    bl = Image.new("RGBA", (bw + 10, bh + 50), (0, 0, 0, 0)); d = ImageDraw.Draw(bl)
    d.rounded_rectangle([4, 4, bw + 4, bh + 4], 40, fill=(255, 255, 255, 255), outline=(18, 18, 24, 255), width=5)
    d.polygon([(bw / 2 - 18, bh), (bw / 2 + 18, bh), (bw / 2, bh + 40)], fill=(255, 255, 255, 255))
    d.text((bw / 2 + 4, 4 + bh / 2), txt, font=_bf, fill=(18, 18, 24, 255), anchor="mm")
    im.alpha_composite(bl, (int(x - bl.width / 2), int(y - bl.height)))

_glowc = {}
def glow(im, pos, r, col):
    if pos is None or r <= 0: return
    key = (r, col)
    if key not in _glowc:
        s = int(r * 2); gl = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(gl)
        for k in range(12, 0, -1):
            rr = r * k / 12; d.ellipse([r - rr, r - rr, r + rr, r + rr], fill=tuple(col) + (int(110 * (1 - k / 12) ** 1.5),))
        _glowc[key] = gl.filter(ImageFilter.GaussianBlur(max(1, r / 8)))
    im.alpha_composite(_glowc[key], (int(pos[0] - r), int(pos[1] - r)))

def frame(g, spec, i, t, D, words):
    sc = spec["scenes"][i]; n = len(spec["scenes"]); kind = "hook" if i == 0 else "cta" if i == n - 1 else "body"
    env = sc.get("set", spec.get("set", "forest_day")); e = ENVS.get(env, ENVS["forest_day"]); o = {}
    shake = 0.0
    if sc.get("shake_at") is not None: shake = 0.1 * ease((t - sc["shake_at"]) / 0.15) * max(0, 1 - (t - sc["shake_at"]) / 1.2) * math.sin(t * 55)
    eye, tgt, fov = camera(sc, env, t, D); eye = (eye[0] + shake, eye[1] + shake, eye[2])
    g.set_light(L=e["L"], col=e.get("Lcol", (1, 0.97, 0.9)), amb=e["amb"], fog=e.get("fog", e["bot"]), fogd=e["fogd"], rim=e.get("rim", (0.15, 0.18, 0.25)))
    g.begin(eye, tgt, fov, e["top"], e["bot"], e["stars"], t)
    if e["ground"] is not None:
        P.ground(g, e["ground"])
        if e.get("water"): g.draw("plane", T(-30, 0.02, 0) @ S(40, 1, 300), (0.1, 0.4, 0.75), spec=1.0)
    props = sc.get("props")
    if props is None: props = [dict(type=a, x=b, z=c) for a, b, c in DEFAULT_PROPS.get(env, [])]
    elif sc.get("keep_decor", True): props = [dict(type=a, x=b, z=c) for a, b, c in DEFAULT_PROPS.get(env, [])] + props
    if env == "space" and not props: props = [dict(type="earth", x=0, y=-0.1, z=0, r=1.0)]
    for pr in props: prop(g, pr, t, D, o)
    heads = draw_figs(g, sc, t, D, env)
    w = sc.get("weather", WEATHER_AUTO.get(env, "none"))
    if w != "none": weather(g, w, t)
    im = Image.fromarray(g.read()).convert("RGBA")
    for q, r, col in o.get("glows", []): glow(im, q, r, col)
    if kind == "hook":
        p = ease(t / 0.35); top, bot = (sc.get("title") or ["", ""])[:2]
        E.text_center(im, top, 300, E.anton(140), scale=.8 + .2 * p, alpha=p); E.text_center(im, bot, 460, E.anton(140), fill=E.YELLOW, scale=.8 + .2 * p, alpha=p)
    elif kind == "cta":
        p = ease(t / 0.35)
        for j, ln in enumerate((sc.get("title") or ["¿QUÉ OTRO TEMA", "QUIERES VER?"])[:3]):
            E.text_center(im, ln, 300 + j * 150, E.anton(130), fill=E.YELLOW if j == 1 else (255, 255, 255), scale=.8 + .2 * p, alpha=p)
        s = 1 + 0.06 * math.sin(t * 6); b = Image.new("RGBA", (300, 280), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([10, 10, 290, 200], 60, fill=(255, 255, 255, 255)); bd.polygon([(80, 190), (60, 270), (150, 195)], fill=(255, 255, 255, 255))
        for k in range(3): bd.ellipse([80 + k * 55, 90, 110 + k * 55, 120], fill=(20, 20, 30, 255))
        E.paste_c(im, b.resize((int(300 * s), int(280 * s))), W * 0.7, 300 + len((sc.get("title") or [1, 2])[:3]) * 150 + 120, ease((t - 0.3) / 0.3))
    else:
        E.chip(im, sc.get("chip", ""), ease(t / 0.3))
        if sc.get("big"):
            p = ease((t - 0.4) / 0.4); E.text_center(im, sc["big"], 360, E.anton(120), fill=E.YELLOW, scale=.8 + .2 * p, alpha=p, maxw=980)
        em = sc.get("emoji") or []
        if isinstance(em, str): em = [em]
        for k, ee in enumerate(em):
            pk = ease((t - 0.3 - k * 0.2) / 0.3)
            if pk > 0: E.paste_c(im, E.emoji_img(ee, 150), W / (len(em) + 1) * (k + 1), 520 + 12 * math.sin(t * 2 + k), pk)
        E.captions(im, words, t, y=1560)
    for fg, J in heads:
        if fg.get("prop"):
            q = g.project(J["rh"])
            if q: E.paste_c(im, E.emoji_img(fg["prop"], 110 if env != "space" else 70), q[0], q[1])
        if fg.get("say") and t > 0.5:
            q = g.project(J["head"] + np.array([0, 0.32 if env != "space" else 0.12, 0], "f4"))
            if q: bubble(im, fg["say"], q[0], q[1])
    E.overlay(im, spec, t)
    im.alpha_composite(E.vig(0.5 if env in ("forest_night", "snow_night", "red", "city_night") else 0.38))
    if i > 0 and t < 0.15: im = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), im, t / 0.15)
    return im

# ------------------------------------------------------------------ audio
def kokoro():
    os.makedirs(KOKORO_DIR, exist_ok=True)
    for u in KOKORO_URLS:
        p = os.path.join(KOKORO_DIR, os.path.basename(u))
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000: subprocess.run(["curl", "-sSL", "-o", p, u], check=True)
    from kokoro_onnx import Kokoro
    return Kokoro(*[os.path.join(KOKORO_DIR, os.path.basename(u)) for u in KOKORO_URLS])

def tts_all(spec, work):
    import soundfile as sf
    k = kokoro(); durs = []
    for i, sc in enumerate(spec["scenes"]):
        s, sr = k.create(sc["line"], voice=spec.get("voice", VOICE), speed=spec.get("speed", SPEED), lang="es"); sf.write(f"{work}/r{i}.wav", s, sr)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{work}/r{i}.wav", "-af", "highpass=f=70,acompressor=threshold=-22dB:ratio=2.5:makeup=3,loudnorm=I=-14:TP=-1",
                        "-ar", "48000", "-ac", "1", f"{work}/l{i}.wav"], check=True)
        durs.append(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", f"{work}/l{i}.wav"])))
    return durs

def render_scenes(args):
    spec, idxs, Ds, durs, starts, work = args
    g = GL(); tex_setup(g); out = []
    for i in idxs:
        f = f"{work}/s{i:02d}.mp4"; tmp = f + ".tmp.mp4"; D = Ds[i]; words = E.chunks_for(spec["scenes"][i]["line"], durs[i] - 0.3, LEAD)
        sp = dict(spec, _start=float(starts[i]))
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for fr in range(int(round(D * FPS))): p.stdin.write(frame(g, sp, i, fr / FPS, D, words).convert("RGB").tobytes())
        p.stdin.close(); p.wait()
        if p.returncode != 0: raise RuntimeError(f"ffmpeg falló en escena {i}")
        os.replace(tmp, f); out.append(f)
    return out

def build(spec_path, out_path):
    from concurrent.futures import ProcessPoolExecutor
    spec = json.load(open(spec_path, encoding="utf8")); work = tempfile.mkdtemp(prefix="v3d_"); SR = 48000
    durs = tts_all(spec, work); Ds = [round((LEAD + d + TAIL) * FPS) / FPS for d in durs]
    starts = np.cumsum([0] + Ds[:-1]); total = sum(Ds); spec["_total"] = total
    n = len(Ds); nw = max(1, min(2, os.cpu_count() or 1)); groups = [list(range(k, n, nw)) for k in range(nw)]
    import multiprocessing as mp
    with ProcessPoolExecutor(max_workers=nw, mp_context=mp.get_context("spawn")) as ex:
        list(ex.map(render_scenes, [(spec, gr, Ds, durs, starts, work) for gr in groups]))
    files = [f"{work}/s{i:02d}.mp4" for i in range(n)]
    voice = np.zeros(int(total * SR) + SR)
    for i, s in enumerate(starts):
        a = np.frombuffer(subprocess.check_output(["ffmpeg", "-v", "error", "-i", f"{work}/l{i}.wav", "-f", "f32le", "-"]), np.float32)
        o = int((s + LEAD) * SR); voice[o:o + len(a)] += a
    m = E.music(len(voice) / SR, spec.get("mood", "bright"), starts) * 0.8
    r = np.random.default_rng(5)
    for i, sc in enumerate(spec["scenes"]):
        if sc.get("shake_at") is not None or sc.get("sfx") == "boom":
            tb = starts[i] + (sc.get("shake_at") or 0.3); nn = int(1.2 * SR); tt = np.arange(nn) / SR
            b = (np.sin(2 * np.pi * 45 * tt) * 0.8 + np.convolve(r.standard_normal(nn), np.ones(60) / 60, "same") * 2) * np.exp(-tt * 3.5) * 0.45
            o = int(tb * SR); m[o:o + nn] += b[:max(0, len(m) - o)]
    voice.astype(np.float32).tofile(f"{work}/voice.f32"); m.astype(np.float32).tofile(f"{work}/music.f32")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", f"{work}/voice.f32", "-f", "f32le", "-ar", "48000", "-ac", "1", "-i", f"{work}/music.f32",
                    "-filter_complex", "[0:a]asplit=2[a1][a2];[1:a][a1]sidechaincompress=threshold=0.02:ratio=6[md];[a2]volume=1.3[a3];[a3][md]amix=inputs=2:normalize=0,loudnorm=I=-14:TP=-1,aresample=48000[out]",
                    "-map", "[out]", "-ac", "2", "-c:a", "aac", "-b:a", "192k", f"{work}/mix.m4a"], check=True)
    open(f"{work}/list.txt", "w").write("".join(f"file '{f}'\n" for f in files))
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", f"{work}/list.txt", "-c", "copy", f"{work}/v.mp4"], check=True)
    tmp = out_path + ".tmp.mp4"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", f"{work}/v.mp4", "-i", f"{work}/mix.m4a", "-map", "0:v", "-map", "1:a", "-c:v", "copy", "-shortest", "-movflags", "+faststart", tmp], check=True)
    os.replace(tmp, out_path); shutil.rmtree(work, ignore_errors=True); print("OK", out_path, round(total, 1), "s")

def preview(spec_path, out_dir):
    spec = json.load(open(spec_path, encoding="utf8")); os.makedirs(out_dir, exist_ok=True)
    g = GL(); tex_setup(g); n = len(spec["scenes"]); spec["_total"] = n * 7.0; th = []
    for i in range(n):
        D = 7.0; words = E.chunks_for(spec["scenes"][i]["line"], D - 1, LEAD)
        th.append(frame(g, dict(spec, _start=i * 7.0), i, 3.0, D, words).convert("RGB").resize((216, 384)))
    cols = 6; sh = Image.new("RGB", (216 * cols, 384 * ((n + cols - 1) // cols)))
    for k, im in enumerate(th): sh.paste(im, ((k % cols) * 216, (k // cols) * 384))
    p = os.path.join(out_dir, "preview3d.jpg"); sh.save(p, quality=85); print(p)

if __name__ == "__main__":
    if sys.argv[1] == "--preview": preview(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else ".")
    else: build(sys.argv[1], sys.argv[2])
