"""Utilería 3D y stickman 3D para engine3d.py."""
import math, random, sys, os, numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

