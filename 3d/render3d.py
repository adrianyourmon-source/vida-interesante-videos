import sys, os, json, math, subprocess, numpy as np
sys.path.insert(0, "/home/claude/vida-interesante-videos"); sys.path.insert(0, "/home/claude/v3d")
from PIL import Image, ImageDraw, ImageFilter, ImageFont
import engine as E
from gl3d import GL, W, H
import scenes3d as SC

FPS = 30; LEAD, TAIL = 0.2, 0.45
LINES = json.load(open("/home/claude/v3d/lines2.json")); DURS = json.load(open("/home/claude/v3d/durs2.json"))
Ds = [round((LEAD + d + TAIL) * FPS) / FPS for d in DURS]; STARTS = list(np.cumsum([0] + Ds[:-1])); TOTAL = sum(Ds)

def textures(g):
    tx = E.textures(); e = tx["earth"] * (1 - tx["cloud"][..., None]) + 250 * tx["cloud"][..., None]
    g.texture("earth", e)
    th, tw = E.TH, E.TW; lat = np.linspace(90, -90, th)[:, None] * np.ones((1, tw))
    n = E.value_noise(tw, th, 6, 3); n2 = E.value_noise(tw, th, 5, 17)
    ocean = np.abs(lat) > 38 + 18 * (n - 0.5) * 2
    land = np.stack([120 + 90 * n2, 120 + 40 * n, 60 + 30 * n], -1); land[n2 < 0.45] = np.stack([60 + 60 * n, 120 + 50 * n, 50 + 20 * n], -1)[n2 < 0.45]
    sea = np.stack([15 + 25 * n, 60 + 50 * n, 140 + 60 * n], -1)
    m = np.where(ocean[..., None], sea, land); m[np.abs(lat) > 80] = [235, 240, 245]
    m = m * (1 - tx["cloud"][..., None] * 0.6) + 250 * tx["cloud"][..., None] * 0.6
    g.texture("mega", m)

_bf = None
def bubble(im, txt, x, y):
    global _bf
    if _bf is None: _bf = E.font(46, "Black")
    tw = _bf.getlength(txt); bw, bh = int(tw + 60), 96
    x = min(max(x, bw / 2 + 20), W - bw / 2 - 20)
    bl = Image.new("RGBA", (bw + 10, bh + 50), (0, 0, 0, 0)); d = ImageDraw.Draw(bl)
    d.rounded_rectangle([4, 4, bw + 4, bh + 4], 40, fill=(255, 255, 255, 255), outline=(18, 18, 24, 255), width=5)
    d.polygon([(bw / 2 - 18, bh), (bw / 2 + 18, bh), (bw / 2, bh + 40)], fill=(255, 255, 255, 255))
    d.text((bw / 2 + 4, 4 + bh / 2), txt, font=_bf, fill=(18, 18, 24, 255), anchor="mm")
    im.alpha_composite(bl, (int(x - bl.width / 2), int(y - bl.height)))

def glow(im, pos, r, col):
    (x, y) = pos; s = int(r * 2); gl = Image.new("RGBA", (s, s), (0, 0, 0, 0)); d = ImageDraw.Draw(gl)
    for k in range(12, 0, -1):
        rr = r * k / 12; a = int(110 * (1 - k / 12) ** 1.5); d.ellipse([r - rr, r - rr, r + rr, r + rr], fill=col + (a,))
    im.alpha_composite(gl.filter(ImageFilter.GaussianBlur(r / 8)), (int(x - r), int(y - r)))

def frame(g, i, t):
    sc = SC.SCENES[i]; D = Ds[i]; o = {}
    g.last_head = None
    _stick = SC.stick
    def stick_wrap(gg, base, *a, **k):
        J = _stick(gg, base, *a, **k); gg.last_head = J["head"]; return J
    SC.stick = stick_wrap
    try: sc["fn"](g, t, D, o)
    finally: SC.stick = _stick
    head = g.project(g.last_head + np.array([0, 0.32, 0], "f4")) if g.last_head is not None else None
    im = Image.fromarray(g.read()).convert("RGBA")
    if o.get("glow"): glow(im, *o["glow"])
    kind = sc.get("kind", "body")
    if kind == "hook":
        p = E.ease(t / 0.35); top, bot = sc["title"]
        E.text_center(im, top, 300, E.anton(140), scale=.8 + .2 * p, alpha=p); E.text_center(im, bot, 460, E.anton(140), fill=E.YELLOW, scale=.8 + .2 * p, alpha=p)
    elif kind == "cta":
        p = E.ease(t / 0.35)
        for j, ln in enumerate(sc["title"]): E.text_center(im, ln, 300 + j * 150, E.anton(130), fill=E.YELLOW if j == 1 else (255, 255, 255), scale=.8 + .2 * p, alpha=p)
        s = 1 + 0.06 * math.sin(t * 6); b = Image.new("RGBA", (300, 280), (0, 0, 0, 0)); bd = ImageDraw.Draw(b)
        bd.rounded_rectangle([10, 10, 290, 200], 60, fill=(255, 255, 255, 255)); bd.polygon([(80, 190), (60, 270), (150, 195)], fill=(255, 255, 255, 255))
        for k in range(3): bd.ellipse([80 + k * 55, 90, 110 + k * 55, 120], fill=(20, 20, 30, 255))
        E.paste_c(im, b.resize((int(300 * s), int(280 * s))), W * 0.68, 860, E.ease((t - 0.3) / 0.3))
    else:
        E.chip(im, sc.get("chip", ""), E.ease(t / 0.3))
        if o.get("big"):
            p = E.ease((t - 0.4) / 0.4); E.text_center(im, o["big"], 360, E.anton(120), fill=E.YELLOW, scale=.8 + .2 * p, alpha=p, maxw=980)
        em = o.get("emoji") or []
        for k, e in enumerate(em):
            pk = E.ease((t - 0.3 - k * 0.2) / 0.3)
            if pk > 0: E.paste_c(im, E.emoji_img(e, 150), W / (len(em) + 1) * (k + 1), 520 + 12 * math.sin(t * 2 + k), pk)
        if o.get("say") and head and t > 0.5: bubble(im, o["say"][0], head[0], head[1])
        for txt, wp in o.get("say2") or []:
            q = g.project(np.array(wp, "f4"))
            if q and t > 0.5: bubble(im, txt, q[0], q[1])
        words = E.chunks_for(LINES[i], DURS[i] - 0.3, LEAD); E.captions(im, words, t, y=1560)
    E.overlay(im, {"_start": STARTS[i], "_total": TOTAL}, t)
    im.alpha_composite(E.vig(0.4))
    if i > 0 and t < 0.15: im = Image.blend(Image.new("RGBA", (W, H), (0, 0, 0, 255)), im, t / 0.15)
    return im

def render(idx_list):
    g = GL(); textures(g)
    for i in idx_list:
        out = f"/home/claude/v3d/scenes/s{i:02d}.mp4"
        if os.path.exists(out): continue
        tmp = out.replace(".mp4", ".tmp.mp4"); nf = int(round(Ds[i] * FPS))
        p = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "21", "-maxrate", "7M", "-bufsize", "14M", "-pix_fmt", "yuv420p", tmp], stdin=subprocess.PIPE)
        for fr in range(nf): p.stdin.write(frame(g, i, fr / FPS).convert("RGB").tobytes())
        p.stdin.close(); p.wait()
        if p.returncode == 0: os.replace(tmp, out)
        print("scene", i, "ok", flush=True)

def preview(times, out):
    g = GL(); textures(g); th = []
    for i in range(len(SC.SCENES)):
        t = min(Ds[i] - 0.1, times.get(i, Ds[i] * 0.6)); th.append(frame(g, i, t).convert("RGB").resize((216, 384)))
    sh = Image.new("RGB", (216 * 6, 384 * 3))
    for k, im in enumerate(th): sh.paste(im, ((k % 6) * 216, (k // 6) * 384))
    sh.save(out, quality=85)

if __name__ == "__main__":
    os.makedirs("/home/claude/v3d/scenes", exist_ok=True)
    if sys.argv[1] == "preview": preview({}, sys.argv[2])
    elif sys.argv[1] == "frame":
        g = GL(); textures(g); frame(g, int(sys.argv[2]), float(sys.argv[3])).convert("RGB").save(sys.argv[4], quality=90)
    else: render([int(x) for x in sys.argv[1].split(",")])
