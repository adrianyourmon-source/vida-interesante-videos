"""Escenas 3D: ¿Qué pasaría si la Tierra dejara de girar?"""
import math, random, sys, numpy as np
sys.path.insert(0, "/home/claude/vida-interesante-videos")
import stickman as SM
from gl3d import T, S, RX, RY, RZ, align_y

WHITE = (0.95, 0.95, 0.97); DARK = (0.05, 0.05, 0.07)
SKY_TOP, SKY_BOT = (0.30, 0.55, 0.90), (0.78, 0.88, 0.98)
SPACE_TOP, SPACE_BOT = (0.01, 0.015, 0.05), (0.05, 0.07, 0.16)
def ease(x): x = min(max(x, 0), 1); return x * x * (3 - 2 * x)
def lerp(a, b, t): return a + (b - a) * t
def lerp3(a, b, t): return tuple(lerp(x, y, t) for x, y in zip(a, b))

# ------------------------------------------------------------ stickman 3D
def stick(g, base, action, t, phase=0.0, yaw=0.0, s=0.00313, color=WHITE, face=None, f=1, xf=None, r=0.05):
    p = SM.pose(action, t, phase); face = face or SM.DEFAULT_FACE.get(action, "neutral")
    def pt(x, y, ang, ln): a = math.radians(ang) * f; return (x + ln * math.sin(a), y + ln * math.cos(a))
    lean = p["lean"]
    neck = pt(0, 0, 180 + lean, SM.TORSO); hc = pt(*neck, 180 + lean + p["head"], SM.NECK + SM.HEAD_R); sh = pt(0, 0, 180 + lean, SM.TORSO - 18)
    def limb(b, a1, a2, l1, l2):
        j = pt(*b, a1 + lean * .3, l1); return j, pt(*j, a1 + a2 + lean * .3, l2)
    le, lh = limb(sh, p["ls"], p["le"], SM.UARM, SM.FARM); re, rh = limb(sh, p["rs"], p["re"], SM.UARM, SM.FARM)
    lk, lf = limb((0, 0), p["lh"], p["lk"], SM.THIGH, SM.SHIN); rk, rf = limb((0, 0), p["rh"], p["rk"], SM.THIGH, SM.SHIN)
    hipy = (SM.THIGH + SM.SHIN - p["dy"]) * s; shake = p["shake"] * math.sin(t * 40) * s
    cy, sy = math.cos(yaw), math.sin(yaw)
    def W(q, z=0.0):
        x, y = q[0] * s + shake, -q[1] * s
        wx, wz = x * cy + z * sy, -x * sy + z * cy
        P = np.array([base[0] + wx, base[1] + hipy + y, base[2] + wz], "f4")
        if p["rot"]:
            a = math.radians(p["rot"]); c0 = np.array(base, "f4"); d = P - c0
            P = c0 + np.array([d[0] * math.cos(a) - d[1] * math.sin(a), d[0] * math.sin(a) + d[1] * math.cos(a), d[2]], "f4")
        return xf(P) if xf else P
    J = {k: W(v, z) for k, v, z in [("hip", (0, 0), 0), ("neck", neck, 0), ("head", hc, 0), ("sh", sh, 0), ("le", le, .07), ("lh", lh, .08),
                                     ("re", re, -.07), ("rh", rh, -.08), ("lk", lk, .05), ("lf", lf, .05), ("rk", rk, -.05), ("rf", rf, -.05)]}
    for a, b in [("hip", "neck"), ("sh", "le"), ("le", "lh"), ("sh", "re"), ("re", "rh"), ("hip", "lk"), ("lk", "lf"), ("hip", "rk"), ("rk", "rf")]:
        g.segment(J[a], J[b], r, color, spec=0.5)
    for k in ("hip", "sh", "le", "lh", "re", "rh", "lk", "lf", "rk", "rf"): g.ball(J[k], r * (1.15 if k in ("lf", "rf", "lh", "rh") else 1.0), color, spec=0.5)
    hr = SM.HEAD_R * s; H = J["head"]; g.ball(H, hr, color, mesh="sphere", spec=0.6)
    # cara
    n = np.array([0.38 * f * cy + 0.92 * sy, 0, -0.38 * f * sy + 0.92 * cy], "f4"); n /= np.linalg.norm(n)
    up = np.array([0, 1, 0], "f4"); side = np.cross(up, n)
    B = np.eye(4, dtype="f4"); B[:3, 0], B[:3, 1], B[:3, 2] = side, up, n
    big = face in ("fear", "surprised")
    for sx in (-1, 1):
        e = H + hr * (n * 0.86 + side * sx * 0.32 + up * 0.15)
        if face == "happy": g.draw("lsphere", T(*e) @ B @ S(hr * .15, hr * .07, hr * .07), DARK, spec=.2)
        elif face == "dizzy": g.draw("lsphere", T(*e) @ B @ RZ(.8 * sx) @ S(hr * .16, hr * .04, hr * .05), DARK)
        elif big:
            g.ball(e, hr * 0.2, (1, 1, 1), spec=.4); g.ball(H + hr * (n * 1.0 + side * sx * 0.32 + up * 0.15), hr * 0.1, DARK)
        else:
            blink = (t % 3.3) < 0.12; g.draw("lsphere", T(*e) @ B @ S(hr * .12, hr * (.02 if blink else .13), hr * .07), DARK, spec=.3)
        if face in ("angry", "sad", "fear", "thinking"):
            tilt = {"angry": .35, "sad": -.35, "fear": -.3, "thinking": .2 * sx}[face] * sx
            eb = H + hr * (n * 0.8 + side * sx * 0.33 + up * 0.45)
            g.draw("lsphere", T(*eb) @ B @ RZ(tilt) @ S(hr * .2, hr * .035, hr * .05), DARK)
    m = H + hr * (n * 0.9 - up * 0.38)
    msc = {"happy": (.3, .12, .08), "fear": (.13, .17 + .03 * math.sin(t * 12), .08), "surprised": (.12, .15, .08), "sad": (.22, .04, .06),
           "cold": (.24, .03 + .015 * abs(math.sin(t * 30)), .06), "angry": (.2, .05, .06), "thinking": (.15, .03, .06), "dizzy": (.18, .07, .06)}.get(face, (.2, .035, .06))
    g.draw("lsphere", T(*m) @ B @ S(hr * msc[0], hr * msc[1], hr * msc[2]), DARK, spec=.1)
    if face == "fear" or action in ("scared", "run_away"):
        dy = ((t * 0.6) % 0.25); g.ball(H + hr * (side * -1.15 * f + up * (0.4 - dy * 4)), hr * .1, (0.5, 0.8, 1.0), spec=1)
    return J

def shadow(g, x, z, r=0.5, a=0.25):
    g.draw("sphere", T(x, 0.005, z) @ S(r, 0.002, r * 0.6), (0, 0, 0), alpha=a, rim=False)

# ------------------------------------------------------------ props
def ground(g, color=(0.45, 0.62, 0.32), y=0.0, size=300):
    g.draw("plane", T(0, y, 0) @ S(size, 1, size), color, spec=0.0, rim=False)
def tree(g, x, z, h=2.2, sway=0.0, lean=0.0, col=(0.2, 0.55, 0.25)):
    M = T(x, 0, z) @ RZ(lean + sway)
    g.draw("cyl", M @ S(0.09, h * 0.35, 0.09), (0.42, 0.28, 0.16), spec=0)
    g.draw("cone", M @ T(0, h * 0.25, 0) @ S(h * 0.33, h * 0.5, h * 0.33), col, spec=0.1)
    g.draw("cone", M @ T(0, h * 0.5, 0) @ S(h * 0.25, h * 0.45, h * 0.25), tuple(c * 1.12 for c in col), spec=0.1)
def house(g, x, z, w=1.3, h=1.1, col=(0.92, 0.85, 0.72), roof=(0.75, 0.25, 0.2), M=None):
    M = (M if M is not None else T(x, 0, z))
    g.draw("box", M @ T(0, h / 2, 0) @ S(w, h, w), col, spec=0.1)
    g.draw("pyr", M @ T(0, h, 0) @ RY(math.pi / 4) @ S(w * 0.78, w * 0.55, w * 0.78), roof, spec=0.1)
    g.draw("box", M @ T(0, h * 0.35, w / 2 + 0.01) @ S(w * 0.22, h * 0.45, 0.02), (0.35, 0.22, 0.12))
    for sx in (-1, 1): g.draw("box", M @ T(sx * w * 0.28, h * 0.62, w / 2 + 0.01) @ S(w * 0.18, w * 0.18, 0.02), (0.55, 0.8, 0.95), emis=0.3)
def building(g, M, w, h, col=(0.7, 0.72, 0.78)):
    g.draw("box", M @ T(0, h / 2, 0) @ S(w, h, w), col, spec=0.3)
    for k in range(int(h / 0.5)):
        g.draw("box", M @ T(0, 0.3 + k * 0.5, w / 2 + 0.01) @ S(w * 0.8, 0.12, 0.02), (0.35, 0.55, 0.75), emis=0.2)
def earth(g, c, r, rot, tex="earth", obl=1.0, tilt=0.41, halo=True, night=0.04):
    M = T(*c) @ RZ(tilt) @ RY(rot) @ S(r, r * obl, r)
    g.draw("sphere", M, (1, 1, 1), tex=tex, spec=0.35, night=night)
    if halo: g.draw("sphere", T(*c) @ RZ(tilt) @ S(r * 1.035, r * obl * 1.035, r * 1.035), (0.35, 0.6, 1.0), alpha=0.16, emis=1.0, rim=False)
    return M

# ------------------------------------------------------------ scenes
RNG = random.Random(3)
TREES = [(RNG.uniform(-14, 14), RNG.uniform(-25, -2.5), RNG.uniform(1.6, 3.0)) for _ in range(40)]
HOUSES = [(-3.2, -3.0), (3.4, -4.0), (-6.5, -7), (6.0, -9), (0.5, -11)]
STREAKS = [(RNG.uniform(-10, 10), RNG.uniform(0.2, 5), RNG.uniform(-12, 2), RNG.uniform(0.5, 1.5)) for _ in range(70)]

def day(g, eye, tgt, t, fov=38, fogd=0.025):
    g.set_light(L=(-0.5, 0.8, 0.6), amb=(0.38, 0.4, 0.46), fog=SKY_BOT, fogd=fogd, rim=(0.15, 0.18, 0.25))
    g.begin(eye, tgt, fov, SKY_TOP, SKY_BOT, 0, t)

def space(g, eye, tgt, t, fov=38, L=(-0.7, 0.3, 0.6)):
    g.set_light(L=L, amb=(0.06, 0.07, 0.1), fog=(0, 0, 0), fogd=0.0, rim=(0.2, 0.35, 0.7))
    g.begin(eye, tgt, fov, SPACE_TOP, SPACE_BOT, 1.0, t)

def landscape(g, t, scroll=0.0, wind=0.0, jolt=0.0):
    ground(g)
    for i, (x, z, h) in enumerate(TREES):
        xx = ((x - scroll + 14) % 28) - 14
        tree(g, xx + jolt * 0.0, z, h, sway=0.04 * math.sin(t * 2 + i) - wind * (0.35 + 0.1 * math.sin(t * 9 + i)))
    for i, (x, z) in enumerate(HOUSES):
        xx = ((x - scroll + 14) % 28) - 14; house(g, xx, z)

def sc_hook(g, t, D, o):
    stop = ease((t - (D - 1.2)) / 0.25)
    rot = t * 0.9 if stop == 0 else (D - 1.2) * 0.9 + 0.02 * (1 - stop)
    zoom = lerp(8.0, 6.6, ease(t / D)); sh = 0.05 * stop * math.sin(t * 60) * (1 - ease((t - (D - 0.9)) / 0.6))
    space(g, (sh, 0.5, zoom), (0, 0.1, 0), t)
    earth(g, (0, -0.55, 0), 1.0, rot, tilt=0)
    fly = ease((t - (D - 1.0)) / 0.9)
    base = np.array([0 + fly * 2.4, 0.45 + fly * 1.6, 0], "f4")
    xf = (lambda P: base + (P - base) @ np.array([[math.cos(fly * 4), math.sin(fly * 4), 0], [-math.sin(fly * 4), math.cos(fly * 4), 0], [0, 0, 1]], "f4")) if fly > 0 else None
    stick(g, base, "scared" if fly > 0 else "cheer", t, s=0.0009, r=0.014, xf=xf)

def sc_equator(g, t, D, o):
    space(g, (0, 0.6, 6.6), (0, -0.1, 0), t, L=(-0.8, 0.4, 0.5))
    rot = t * 0.8; earth(g, (0, -0.1, 0), 1.0, rot, tilt=0)
    pulse = 0.6 + 0.4 * math.sin(t * 5)
    g.draw("torus", T(0, -0.1, 0) @ S(1.02, 0.5, 1.02), (1.0, 0.8, 0.15), emis=0.6 + 0.4 * pulse)
    for k in range(6):
        a = rot + k * math.pi / 3; p = (math.cos(a) * 1.05, -0.1, -math.sin(a) * 1.05)
        if p[2] > -0.2: g.ball(p, 0.03, (1.0, 0.85, 0.2), emis=1.0)
    o["big"] = "1.670 KM/H"

def sc_sound(g, t, D, o):
    sc = t * 9; day(g, (0, 1.5, 7), (0, 1.1, 0), t); landscape(g, t, scroll=sc)
    stick(g, (0, 0, 0), "run", t, yaw=0.0); shadow(g, 0, 0)
    # ondas de sonido quedándose atrás
    for k in range(3):
        rr = ((t * 1.2 + k * 0.33) % 1.0); g.draw("ring", T(-0.6 - rr * 3.0, 1.2, 0) @ RZ(math.pi / 2) @ S(0.3 + rr * 0.9), (1, 1, 1), emis=1, alpha=max(0.0, 0.8 - rr))
    o["big"] = "MÁS RÁPIDO QUE EL SONIDO"; o["emoji"] = ["✈️", "🔊"]

def sc_feel(g, t, D, o):
    day(g, (math.sin(t * 0.3) * 1.5, 1.6, 7), (0, 1.1, 0), t); landscape(g, t, scroll=0)
    stick(g, (0.3, 0, 0), "idle", t, face="happy", yaw=-0.2); shadow(g, 0.3, 0)
    o["say"] = ("NO SIENTO NADA", "head"); o["emoji"] = ["✈️", "🌍"]

def sc_brake(g, t, D, o):
    j = ease((t - 1.6) / 0.25); shk = 0.12 * j * math.sin(t * 55) * max(0, 1 - (t - 1.6) / 1.5)
    day(g, (shk, 1.6 + shk, 7.5), (0, 1.1, 0), t)
    landscape(g, t, scroll=t * 0.0, wind=j * 0.8)
    fly = ease((t - 1.7) / 1.6); bx = fly * 7; by = math.sin(min(fly, 1) * math.pi) * 1.6
    base = np.array([-0.5 + bx, by, 0], "f4"); ang = fly * 6
    R = np.array([[math.cos(ang), math.sin(ang), 0], [-math.sin(ang), math.cos(ang), 0], [0, 0, 1]], "f4")
    stick(g, base, "scared" if j > 0 else "talk", t, xf=(lambda P: base + (P - base - np.array([0, 0.9, 0], "f4")) @ R + np.array([0, 0.9, 0], "f4")) if fly > 0 else None,
          face="fear" if j > 0 else "neutral")
    shadow(g, base[0], 0, 0.5, 0.25 * (1 - min(1, by / 2)))
    o["emoji"] = ["➡️"] if j > 0 else []; o["say"] = ("¡¿QUÉ PASA?!", "head") if j > 0 else None

def sc_wind(g, t, D, o):
    day(g, (0.05 * math.sin(t * 40), 1.6, 7.5), (0, 1.2, 0), t, fogd=0.04); ground(g, (0.55, 0.55, 0.4))
    for i, (x, z, h) in enumerate(TREES[:20]): tree(g, x, z, h, lean=-0.9 - 0.15 * math.sin(t * 8 + i), col=(0.35, 0.5, 0.25))
    for i, (x, y, z, l) in enumerate(STREAKS):
        xx = ((x + t * 26 * l) % 24) - 12; g.draw("box", T(xx, y, z) @ S(1.2 * l, 0.025, 0.025), (1, 1, 1), emis=1, alpha=0.55, rim=False)
    sp = ((t * 0.9) % 1.0); base = np.array([lerp(-4, 4, ease(t / D)), 1.2 + 0.4 * math.sin(t * 3), 0.5], "f4"); ang = t * 5
    R = np.array([[math.cos(ang), math.sin(ang), 0], [-math.sin(ang), math.cos(ang), 0], [0, 0, 1]], "f4")
    stick(g, base, "dizzy", t, xf=lambda P: base + (P - base - np.array([0, 0.9, 0], "f4")) @ R)
    o["big"] = "+1.600 KM/H"; o["emoji"] = ["🌪️", "💨"]

def sc_fly(g, t, D, o):
    day(g, (0.04 * math.sin(t * 37), 1.8, 8), (0, 1.3, 0), t, fogd=0.04); ground(g, (0.55, 0.55, 0.4))
    for i, (x, y, z, l) in enumerate(STREAKS[:40]):
        xx = ((x + t * 26 * l) % 24) - 12; g.draw("box", T(xx, y, z) @ S(1.2 * l, 0.025, 0.025), (1, 1, 1), emis=1, alpha=0.5, rim=False)
    for k in range(4):
        tt = max(0, t - k * 0.7); x = -6 + tt * 3.5; y = max(0, tt * tt * 0.5 - 0.2)
        house(g, 0, 0, M=T(x, y, -2 - k * 1.5) @ RZ(-tt * 1.2) @ RY(tt))
    for k in range(5):
        tt = max(0, t - 0.3 - k * 0.5); tree(g, -7 + tt * 4.5, -1 - k, 2.0, lean=-1.2 - tt * 2)
    g.draw("lsphere", T(0.9, 0.2, 0.4) @ S(0.7, 0.45, 0.6), (0.45, 0.43, 0.42), spec=0.2)
    stick(g, (0.1, 0, 0.6), "scared", t, yaw=0.3); o["say"] = ("¡AGÁRRATE!", "head"); o["emoji"] = ["🏠", "🌳"]

def wave(g, x, h, col=(0.15, 0.45, 0.85)):
    g.draw("cyl", T(x, 0, 0) @ RX(math.pi / 2) @ T(0, -18, 0) @ S(h, 20, h), col, spec=1.0, alpha=0.92)
def sc_ocean(g, t, D, o):
    day(g, (0, 1.8, 8.5), (0, 1.4, 0), t); ground(g, (0.85, 0.78, 0.55))
    g.draw("plane", T(-30, 0.02, 0) @ S(40, 1, 300), (0.1, 0.4, 0.75), spec=1.0)
    for i, (x, z) in enumerate(HOUSES[:3]): house(g, x + 4, z)
    wx = lerp(-12, 0.5, ease(t / D)); wave(g, wx, lerp(1.5, 2.8, ease(t / D)))
    for k in range(25):
        a = k * 0.25; g.ball((wx + 3.4 * math.cos(a) * 0.95, 3.4 * math.sin(a) * 0.95 + 0.2 * math.sin(t * 9 + k), RNG.uniform(-4, 2) if False else -2 + (k % 5)), 0.12, (1, 1, 1), emis=0.6)
    stick(g, (lerp(1.0, 4.5, ease(t / D)), 0, 0.8), "run", t, face="fear"); o["emoji"] = ["🌊", "😱"]; o["say"] = ("¡CORRAN!", "head")

def sc_slow(g, t, D, o):
    space(g, (0, 0.5, 6.8), (0, 0.0, 0), t)
    spd = 1.6 * math.exp(-t * 0.5); rot = (1.6 / 0.5) * (1 - math.exp(-t * 0.5))
    earth(g, (0, -0.4, 0), 1.0, rot, tilt=0)
    stick(g, np.array([0, 0.6, 0], "f4"), "think", t, s=0.0009, r=0.014)
    o["emoji"] = ["⏳"]; o["big"] = "MILES DE AÑOS"

def sc_bulge(g, t, D, o):
    space(g, (0, 0.6, 6.6), (0, 0, 0), t)
    k = ease((t - 1.0) / (D - 2)); obl = lerp(0.8, 1.0, k)
    earth(g, (0, 0, 0), 1.0, t * 0.4, obl=obl, tilt=0)
    # agua: anillo ancho en el ecuador que se mueve a los polos
    for sgn in (-1, 1):
        y = sgn * lerp(0.0, 0.82, k); rr = math.sqrt(max(0.0001, 1 - (y / obl) ** 2))
        g.draw("torus", T(0, y * obl, 0) @ S(rr * 1.03, 1.0, rr * 1.03), (0.2, 0.55, 1.0), emis=0.3, alpha=0.7)
    o["emoji"] = ["💧", "🧭"]

def sc_esri(g, t, D, o):
    space(g, (0, 0.8, 6.4), (0, 0, 0), t); earth(g, (0, -0.05, 0), 1.0, t * 0.35, tex="mega", tilt=0.2)
    o["big"] = "1 SUPERCONTINENTE"

def sc_flood(g, t, D, o):
    day(g, (math.sin(t * 0.25) * 2, 2.0, 8), (0, 1.0, 0), t)
    lvl = lerp(-0.2, 0.25, ease(t / 2.5))
    g.draw("plane", T(0, lvl, 0) @ S(300, 1, 300), (0.12, 0.42, 0.72), spec=1.2)
    g.draw("lsphere", T(0, -0.6, 0) @ S(1.4, 0.75, 1.2), (0.55, 0.5, 0.4))
    building(g, T(-3.5, lvl - 2.2, -3), 1.2, 3.2); building(g, T(3.3, lvl - 2.6, -5), 1.4, 3.6, (0.8, 0.7, 0.6)); building(g, T(5.5, lvl - 2, -2), 1.0, 2.6)
    tree(g, -1.0, -0.3, 1.2)
    stick(g, (0.25, 0.15, 0.2), "sad", t); o["emoji"] = ["🌊", "🏙️"]

def sc_daynight(g, t, D, o):
    space(g, (0, 5.5, 6.0), (0, -0.3, 0), t, L=(1, 0, 0))
    g.ball((0, 0, 0), 0.55, (1.0, 0.75, 0.25), mesh="sphere", emis=1.0)
    g.draw("ring", S(1.55, 1, 1.55), (1, 1, 1), emis=1.0, alpha=0.3)
    a = 0.6 + t * 0.35; ex, ez = 1.55 * math.cos(a), -1.55 * math.sin(a)
    g.prog["L"].value = (-ex, 0.0, -ez)
    earth(g, (ex, 0, ez), 0.3, 0.0, tilt=0.41, night=0.02)
    sp = g.project((0, 0, 0)); o["glow"] = (sp, 300, (255, 190, 80)) if sp else None
    o["big"] = "1 DÍA = 1 AÑO"

def sc_split(g, t, D, o):
    cx = lerp(-1.6, 1.6, ease((t - 0.3) / (D - 0.8)))
    g.set_light(L=(-0.3, 0.7, 0.6), amb=(0.35, 0.3, 0.3), fog=(0.8, 0.6, 0.5), fogd=0.0)
    g.begin((cx, 1.7, 8.5), (cx, 1.1, 0), 40, (0.9, 0.55, 0.3), (0.98, 0.85, 0.6), 0, t)
    g.draw("plane", T(-15, 0, 0) @ S(30, 1, 300), (0.9, 0.62, 0.3), spec=0)
    g.draw("plane", T(15, 0.001, 0) @ S(30, 1, 300), (0.9, 0.95, 1.0), spec=0.4)
    g.draw("box", T(15.0, 6, -12) @ S(30, 30, 0.1), (0.04, 0.06, 0.16), emis=1.0)  # cielo nocturno
    g.ball((-3.5, 4.2, -6), 0.9, (1.0, 0.8, 0.3), emis=1.0)
    for k in range(4): tree(g, 2.5 + k * 1.3, -2.5 - k, 1.8, col=(0.85, 0.92, 0.98))
    for k in range(4): g.draw("cone", T(-2.8 - k * 1.2, 0, -2.5 - k) @ S(0.25, 1.0, 0.25), (0.3, 0.6, 0.3))
    stick(g, (-1.6, 0, 0), "sad", t, face="sad", color=(1.0, 0.85, 0.75)); stick(g, (1.6, 0, 0), "shiver", t, color=(0.85, 0.92, 1.0))
    for k in range(40):
        x = 0.3 + (k * 0.37) % 5; y = 5 - ((t * 0.8 + k * 0.29) % 5); g.ball((x, y, (k % 4) * 0.5), 0.035, (1, 1, 1), emis=1)
    o["say2"] = [("¡QUÉ CALOR!", (-1.6, 2.1, 0)), ("¡QUÉ FRÍO!", (1.6, 2.1, 0))]

def sc_hurricane(g, t, D, o):
    space(g, (0, 0.2, 6.2), (0, 0, 0), t)
    earth(g, (0, 0, 0), 1.0, 0.6 + t * 0.05, tilt=0.0)
    k = ease((t - D * 0.55) / (D * 0.3))
    for i in range(160):
        a = i * 0.21; rr = 0.04 + i * 0.0026; ang = a - t * 2.0 * (1 - k)
        x = rr * math.cos(ang) * (1 - k) + (((i * 37) % 160) / 160 - 0.5) * 1.1 * k; yv = rr * math.sin(ang) * (1 - k) + (((i * 91) % 160) / 160 - 0.5) * 0.9 * k
        p = np.array([x - 0.1, yv + 0.25, 0], "f4"); n = math.sqrt(max(0, 1 - p[0] ** 2 - p[1] ** 2))
        g.ball((p[0], p[1], n * 1.03), 0.022, (1, 1, 1), emis=0.5, alpha=0.85)
    o["emoji"] = ["🌀", "❌"]

def sc_magnet(g, t, D, o):
    space(g, (0, 0.3, 8.2), (0, 0, 0), t)
    earth(g, (0, 0, 0), 0.8, t * 0.3, tilt=0.2)
    fade = 1 - ease((t - 1.5) / 2.0)
    if fade > 0.02:
        for k in range(6):
            for sgn in (-1, 1):
                g.draw("ring", RY(k * math.pi / 6) @ T(sgn * 1.35, 0, 0) @ RX(math.pi / 2) @ S(1.35, 1, 1.35), (0.4, 0.8, 1.0), emis=1, alpha=0.6 * fade)
    for i in range(30):
        ph = (t * 0.7 + i * 0.13) % 1.0
        if t > 2.0:
            g.ball((3.2 - ph * 2.3, -0.8 + (i % 7) * 0.27, 0.3), 0.03, (1.0, 0.3, 0.2), emis=1.0)
    o["emoji"] = ["🧲", "☢️"]

def sc_good(g, t, D, o):
    space(g, (0, 0.6, 6.8), (0, 0.1, 0), t)
    earth(g, (0, -0.55, 0), 1.0, t * 0.6, tilt=0)
    stick(g, np.array([0, 0.45, 0], "f4"), "cheer", t, s=0.0009, r=0.014)
    o["big"] = "2 MS POR SIGLO"

def sc_cta(g, t, D, o):
    space(g, (0, 0.3, 4.2), (0, -0.6, 0), t)
    earth(g, (0, -1.9, 0), 1.3, t * 0.5, tilt=0)
    stick(g, np.array([-0.15, -0.6, 0.3], "f4"), "wave", t, s=0.0009, r=0.016, face="happy")

SCENES = [
    dict(fn=sc_hook, kind="hook", title=["¿Y SI LA TIERRA", "DEJARA DE GIRAR?"]),
    dict(fn=sc_equator, chip="1 · YA ESTÁS GIRANDO"),
    dict(fn=sc_sound, chip="2 · MÁS QUE EL SONIDO"),
    dict(fn=sc_feel, chip="3 · NO LO SIENTES"),
    dict(fn=sc_brake, chip="4 · EL FRENAZO"),
    dict(fn=sc_wind, chip="5 · VIENTOS EXTREMOS"),
    dict(fn=sc_fly, chip="6 · TODO SALE VOLANDO"),
    dict(fn=sc_ocean, chip="7 · TSUNAMIS GIGANTES"),
    dict(fn=sc_slow, chip="8 · ¿Y SI FRENA DESPACIO?"),
    dict(fn=sc_bulge, chip="9 · EL AGUA SE MUEVE"),
    dict(fn=sc_esri, chip="10 · UN NUEVO MAPA"),
    dict(fn=sc_flood, chip="11 · BAJO EL AGUA"),
    dict(fn=sc_daynight, chip="12 · DÍAS ETERNOS"),
    dict(fn=sc_split, chip="13 · CALOR Y HIELO"),
    dict(fn=sc_hurricane, chip="14 · SIN HURACANES"),
    dict(fn=sc_magnet, chip="15 · SIN ESCUDO"),
    dict(fn=sc_good, chip="TRANQUILO"),
    dict(fn=sc_cta, kind="cta", title=["¿QUÉ OTRO", "\"QUÉ PASARÍA SI\"", "QUIERES VER?"]),
]
