"""Mini motor 3D (OpenGL por software, EGL) para videos verticales 1080x1920."""
import numpy as np, math, moderngl

W, H = 1080, 1920

VS = """
#version 330
uniform mat4 M; uniform mat4 VP;
in vec3 in_pos; in vec3 in_norm; in vec2 in_uv;
out vec3 v_n; out vec3 v_w; out vec2 v_uv;
void main(){ vec4 w = M*vec4(in_pos,1.0); v_w = w.xyz; v_n = mat3(transpose(inverse(M)))*in_norm; v_uv = in_uv; gl_Position = VP*w; }
"""
FS = """
#version 330
uniform vec3 color; uniform vec3 L; uniform vec3 Lcol; uniform vec3 amb; uniform vec3 cam;
uniform float spec; uniform float emis; uniform int use_tex; uniform sampler2D tex; uniform float uoff;
uniform float alpha; uniform vec3 fogc; uniform float fogd; uniform vec3 rimc; uniform float night;
in vec3 v_n; in vec3 v_w; in vec2 v_uv; out vec4 f;
void main(){
  vec3 n = normalize(v_n); vec3 base = color;
  if(use_tex==1) base *= texture(tex, vec2(v_uv.x+uoff, v_uv.y)).rgb;
  vec3 l = normalize(L); float d = max(dot(n,l),0.0);
  vec3 v = normalize(cam - v_w); vec3 h = normalize(l+v);
  float s = pow(max(dot(n,h),0.0), 40.0)*spec*step(0.0, d);
  float rim = pow(1.0-max(dot(n,v),0.0), 3.0);
  vec3 c = base*(amb + Lcol*max(d, night)) + Lcol*s + rimc*rim;
  c = mix(c, base, emis);
  float fd = 1.0 - exp(-fogd*length(cam - v_w));
  c = mix(c, fogc, clamp(fd,0.0,1.0));
  f = vec4(c, alpha);
}
"""
BG_VS = """
#version 330
in vec2 in_pos; out vec2 uv;
void main(){ uv = in_pos*0.5+0.5; gl_Position = vec4(in_pos, 0.999, 1.0); }
"""
BG_FS = """
#version 330
uniform vec3 top; uniform vec3 bot; uniform float stars; uniform float time;
in vec2 uv; out vec4 f;
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
void main(){
  vec3 c = mix(bot, top, uv.y);
  if(stars > 0.0){
    vec2 g = floor(gl_FragCoord.xy/3.0); float h = hash(g);
    if(h > 0.9965){ float tw = 0.6+0.4*sin(time*2.0 + h*80.0); c += vec3(stars*tw*(h-0.9965)/0.0035); }
  }
  f = vec4(c,1.0);
}
"""

# ---------------------------------------------------------------- math
def perspective(fov, aspect, n=0.05, fa=200.0):
    f = 1 / math.tan(math.radians(fov) / 2)
    return np.array([[f / aspect, 0, 0, 0], [0, f, 0, 0], [0, 0, (fa + n) / (n - fa), 2 * fa * n / (n - fa)], [0, 0, -1, 0]], "f4")
def look_at(eye, tgt, up=(0, 1, 0)):
    eye, tgt, up = map(lambda a: np.array(a, "f4"), (eye, tgt, up))
    z = eye - tgt; z /= np.linalg.norm(z); x = np.cross(up, z); x /= np.linalg.norm(x); y = np.cross(z, x)
    m = np.eye(4, dtype="f4"); m[0, :3], m[1, :3], m[2, :3] = x, y, z; m[:3, 3] = -m[:3, :3] @ eye; return m
def T(x, y, z): m = np.eye(4, dtype="f4"); m[:3, 3] = (x, y, z); return m
def S(x, y=None, z=None):
    y = x if y is None else y; z = x if z is None else z; return np.diag([x, y, z, 1]).astype("f4")
def RX(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0, 0], [0, c, -s, 0], [0, s, c, 0], [0, 0, 0, 1]], "f4")
def RY(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s, 0], [0, 1, 0, 0], [-s, 0, c, 0], [0, 0, 0, 1]], "f4")
def RZ(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0, 0], [s, c, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], "f4")
def align_y(d):
    """Rotación que lleva el eje +Y a la dirección d."""
    d = np.array(d, "f4"); n = np.linalg.norm(d)
    if n < 1e-6: return np.eye(4, dtype="f4")
    d /= n; y = np.array([0, 1, 0], "f4"); v = np.cross(y, d); c = float(np.dot(y, d))
    if np.linalg.norm(v) < 1e-6:
        return np.eye(4, dtype="f4") if c > 0 else RX(math.pi)
    if 1 + c < 1e-4: return RX(math.pi)
    vx = np.array([[0, -v[2], v[1]], [v[2], 0, -v[0]], [-v[1], v[0], 0]], "f4")
    r = np.eye(3, dtype="f4") + vx + vx @ vx * (1 / (1 + c)); m = np.eye(4, dtype="f4"); m[:3, :3] = r; return m

# ---------------------------------------------------------------- meshes
def _sphere(nl=48, nm=96):
    v = []
    for i in range(nl + 1):
        lat = -math.pi / 2 + math.pi * i / nl
        for j in range(nm + 1):
            lon = 2 * math.pi * j / nm
            p = (math.cos(lat) * math.cos(lon), math.sin(lat), -math.cos(lat) * math.sin(lon))
            v.append((*p, *p, j / nm, 0.5 - lat / math.pi))
    v = np.array(v, "f4"); idx = []
    for i in range(nl):
        for j in range(nm):
            a = i * (nm + 1) + j; b = a + nm + 1; idx += [a, b, a + 1, a + 1, b, b + 1]
    return v[np.array(idx)]
def _cyl(n=24, r0=1.0, r1=1.0, cap=True):
    tri = []
    for j in range(n):
        a0, a1 = 2 * math.pi * j / n, 2 * math.pi * (j + 1) / n
        p = lambda a, y, r: (r * math.cos(a), y, r * math.sin(a))
        nrm = lambda a: (math.cos(a), (r0 - r1), math.sin(a))
        q = [(p(a0, 0, r0), nrm(a0)), (p(a1, 0, r0), nrm(a1)), (p(a1, 1, r1), nrm(a1)), (p(a0, 1, r1), nrm(a0))]
        for k in (0, 1, 2, 0, 2, 3): tri.append((*q[k][0], *q[k][1], 0, 0))
        if cap:
            tri += [(0, 0, 0, 0, -1, 0, 0, 0), (*p(a1, 0, r0), 0, -1, 0, 0, 0), (*p(a0, 0, r0), 0, -1, 0, 0, 0)]
            if r1 > 0: tri += [(0, 1, 0, 0, 1, 0, 0, 0), (*p(a0, 1, r1), 0, 1, 0, 0, 0), (*p(a1, 1, r1), 0, 1, 0, 0, 0)]
    return np.array(tri, "f4")
def _box():
    t = []
    for ax in range(3):
        for sgn in (-1, 1):
            n = [0, 0, 0]; n[ax] = sgn; u, v = [(1, 2), (2, 0), (0, 1)][ax]
            corners = []
            for a, b in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
                p = [0, 0, 0]; p[ax] = sgn * 0.5; p[u] = a * 0.5; p[v] = b * 0.5; corners.append(p)
            for k in (0, 1, 2, 0, 2, 3): t.append((*corners[k], *n, 0, 0))
    return np.array(t, "f4")
def _plane(n=1):
    t = []
    for i in range(n):
        for j in range(n):
            x0, x1, z0, z1 = -0.5 + i / n, -0.5 + (i + 1) / n, -0.5 + j / n, -0.5 + (j + 1) / n
            q = [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]
            for k in (0, 2, 1, 0, 3, 2): t.append((q[k][0], 0, q[k][1], 0, 1, 0, q[k][0] + .5, q[k][1] + .5))
    return np.array(t, "f4")
def _torus(R=1.0, r=0.05, n=96, m=12):
    t = []
    def P(i, j):
        u, v = 2 * math.pi * i / n, 2 * math.pi * j / m
        c = (R + r * math.cos(v)); p = (c * math.cos(u), r * math.sin(v), c * math.sin(u))
        nn = (math.cos(v) * math.cos(u), math.sin(v), math.cos(v) * math.sin(u)); return (*p, *nn, i / n, j / m)
    for i in range(n):
        for j in range(m):
            a, b, c, d = P(i, j), P(i + 1, j), P(i + 1, j + 1), P(i, j + 1); t += [a, b, c, a, c, d]
    return np.array(t, "f4")

class GL:
    def __init__(self):
        self.ctx = ctx = moderngl.create_context(standalone=True, backend="egl")
        self.prog = ctx.program(vertex_shader=VS, fragment_shader=FS)
        self.bg = ctx.program(vertex_shader=BG_VS, fragment_shader=BG_FS)
        self.bg_vao = ctx.vertex_array(self.bg, [(ctx.buffer(np.array([-1, -1, 3, -1, -1, 3], "f4")), "2f", "in_pos")])
        self.meshes = {}
        for name, data in [("sphere", _sphere()), ("lsphere", _sphere(14, 24)), ("cyl", _cyl()), ("cone", _cyl(24, 1, 0)),
                           ("pyr", _cyl(4, 1, 0)), ("box", _box()), ("plane", _plane(1)), ("torus", _torus()), ("ring", _torus(1.0, 0.012, 128, 8))]:
            buf = ctx.buffer(data.tobytes())
            self.meshes[name] = ctx.vertex_array(self.prog, [(buf, "3f 3f 2f", "in_pos", "in_norm", "in_uv")])
        self.ms = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4, samples=4)], depth_attachment=ctx.depth_renderbuffer((W, H), samples=4))
        self.out = ctx.framebuffer(color_attachments=[ctx.renderbuffer((W, H), 4)])
        self.tex = {}
        self.set_light()

    def texture(self, name, arr):
        a = np.ascontiguousarray(np.clip(arr, 0, 255).astype("u1"))
        t = self.ctx.texture((a.shape[1], a.shape[0]), 3, a.tobytes()); t.repeat_x = True; t.repeat_y = False
        t.build_mipmaps(); t.filter = (moderngl.LINEAR_MIPMAP_LINEAR, moderngl.LINEAR); self.tex[name] = t

    def set_light(self, L=(-0.5, 0.6, 0.7), col=(1.0, 0.97, 0.9), amb=(0.28, 0.3, 0.38), fog=(0.6, 0.75, 0.9), fogd=0.0, rim=(0.15, 0.2, 0.3)):
        self.L, self.Lcol, self.amb, self.fogc, self.fogd, self.rim = L, col, amb, fog, fogd, rim

    def begin(self, eye, tgt, fov=38, top=(0.02, 0.03, 0.08), bot=(0.06, 0.08, 0.18), stars=0.0, time=0.0, up=(0, 1, 0)):
        self.ms.use(); self.ctx.clear(0, 0, 0, 1); self.ctx.disable(moderngl.DEPTH_TEST); self.ctx.disable(moderngl.BLEND)
        self.bg["top"].value, self.bg["bot"].value, self.bg["stars"].value, self.bg["time"].value = top, bot, stars, time
        self.bg_vao.render(); self.ctx.enable(moderngl.DEPTH_TEST)
        self.V = look_at(eye, tgt, up); self.P = perspective(fov, W / H); self.VP = self.P @ self.V; self.eye = eye
        p = self.prog
        p["VP"].write(self.VP.T.copy().tobytes()); p["L"].value = tuple(self.L); p["Lcol"].value = tuple(self.Lcol); p["amb"].value = tuple(self.amb)
        p["cam"].value = tuple(float(x) for x in eye); p["fogc"].value = tuple(self.fogc); p["fogd"].value = self.fogd; p["rimc"].value = tuple(self.rim)

    def draw(self, mesh, M, color=(1, 1, 1), spec=0.3, emis=0.0, tex=None, uoff=0.0, alpha=1.0, night=0.0, rim=True):
        p = self.prog; p["M"].write(M.T.copy().tobytes()); p["color"].value = tuple(float(c) for c in color)
        p["spec"].value = spec; p["emis"].value = emis; p["alpha"].value = alpha; p["night"].value = night
        p["rimc"].value = tuple(self.rim) if rim else (0, 0, 0)
        if tex: self.tex[tex].use(0); p["tex"].value = 0; p["use_tex"].value = 1; p["uoff"].value = uoff
        else: p["use_tex"].value = 0
        if alpha < 1:
            self.ctx.enable(moderngl.BLEND); self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA; self.ctx.depth_mask = False
        self.meshes[mesh].render()
        if alpha < 1: self.ctx.disable(moderngl.BLEND); self.ctx.depth_mask = True

    def segment(self, a, b, r, color, **k):
        a, b = np.array(a, "f4"), np.array(b, "f4"); d = b - a; ln = float(np.linalg.norm(d))
        self.draw("cyl", T(*a) @ align_y(d) @ S(r, ln, r), color, **k)

    def ball(self, p, r, color, mesh="lsphere", **k):
        self.draw(mesh, T(*p) @ S(r), color, **k)

    def project(self, p):
        v = self.VP @ np.array([*p, 1.0], "f4")
        if v[3] <= 0: return None
        x, y = v[0] / v[3], v[1] / v[3]; return ((x * 0.5 + 0.5) * W, (1 - (y * 0.5 + 0.5)) * H)

    def read(self):
        self.ctx.copy_framebuffer(self.out, self.ms)
        data = self.out.read(components=3)
        return np.frombuffer(data, "u1").reshape(H, W, 3)[::-1]
