import math, random, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops

import json, glob, os
W, H, FPS, DUR = 720, 1280, 30, 50.0
OUT = sys.argv[1]
AUDIO = sys.argv[2]
TL = json.load(open(sys.argv[3])) if len(sys.argv) > 3 else None
FOTOS = sys.argv[4] if len(sys.argv) > 4 else None
if TL: DUR = TL["dur"]
NF = int(DUR * FPS)
ORANGE = (232, 117, 62)
WHITE = (240, 240, 235)
FB = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
f_sub = ImageFont.truetype(FB, 44)
f_lab = ImageFont.truetype(FB, 22)
f_big = ImageFont.truetype(FB, 78)
f_mid = ImageFont.truetype(FB, 40)
f_small = ImageFont.truetype(FB, 28)
f_tag = ImageFont.truetype(FB, 20)

# ---------- helpers ----------
def lerp(a, b, t): return a + (b - a) * t
def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(t): t = clamp(t); return t * t * (3 - 2 * t)
def mix(c1, c2, t): return tuple(int(lerp(c1[i], c2[i], t)) for i in range(3))

def gradient(top, bot, hor=0.62):
    y = np.linspace(0, 1, H)[:, None]
    t = np.clip(y / hor, 0, 1)
    arr = np.zeros((H, W, 3), np.float32)
    for i in range(3):
        arr[:, :, i] = (top[i] + (bot[i] - top[i]) * t ** 1.4)
    return arr

SKIES = {
    "church": gradient((14, 18, 30), (150, 78, 52)),
    "street": gradient((12, 16, 26), (120, 60, 48)),
    "caribe": gradient((10, 18, 28), (60, 86, 98)),
    "park": gradient((10, 20, 24), (74, 82, 66)),
    "church2": gradient((8, 12, 22), (120, 60, 56)),
    "end": gradient((6, 8, 16), (92, 44, 40)),
}

yy, xx = np.mgrid[0:H, 0:W]
VIG = 1 - 0.45 * (((xx - W / 2) / (W / 2)) ** 2 * 0.6 + ((yy - H / 2) / (H / 2)) ** 2 * 0.7)
VIG = np.clip(VIG, 0.5, 1)[:, :, None].astype(np.float32)
rng = np.random.default_rng(3)

def silhouette_hills(d, base, amp, color, seed, off=0.0):
    r = random.Random(seed)
    ph = [r.random() * 6 for _ in range(4)]
    pts = [(0, H)]
    for x in range(0, W + 20, 20):
        y = base - amp * (0.5 * math.sin(x / 130 + ph[0] + off) + 0.3 * math.sin(x / 55 + ph[1]) + 0.2 * math.sin(x / 27 + ph[2]))
        pts.append((x, y))
    pts.append((W, H))
    d.polygon(pts, fill=color)

def glow_circle(g, x, y, r, color):
    gd = ImageDraw.Draw(g)
    gd.ellipse([x / 4 - r / 4, y / 4 - r / 4, x / 4 + r / 4, y / 4 + r / 4], fill=color)

def church(d, g, cx, base, s, glow=1.0, t=0.0):
    sil = (10, 11, 15)
    # nave
    d.rectangle([cx - 130 * s, base - 210 * s, cx + 150 * s, base], fill=sil)
    d.polygon([(cx - 140 * s, base - 210 * s), (cx + 10 * s, base - 300 * s), (cx + 160 * s, base - 210 * s)], fill=sil)
    # tower
    tx = cx - 150 * s
    d.rectangle([tx - 50 * s, base - 420 * s, tx + 50 * s, base], fill=sil)
    d.polygon([(tx - 58 * s, base - 420 * s), (tx, base - 540 * s), (tx + 58 * s, base - 420 * s)], fill=sil)
    # cross
    d.rectangle([tx - 3 * s, base - 610 * s, tx + 3 * s, base - 540 * s], fill=sil)
    d.rectangle([tx - 20 * s, base - 585 * s, tx + 20 * s, base - 579 * s], fill=sil)
    # glowing door and windows
    warm = (255, 190, 110)
    flick = 0.85 + 0.15 * math.sin(t * 9)
    wc = tuple(int(c * glow * flick) for c in warm)
    d.rounded_rectangle([cx - 30 * s, base - 120 * s, cx + 50 * s, base], radius=int(40 * s), fill=wc)
    for wx in (-90, 90):
        d.rounded_rectangle([cx + wx * s - 14 * s, base - 170 * s, cx + wx * s + 14 * s, base - 110 * s], radius=int(14 * s), fill=wc)
    d.ellipse([tx - 14 * s, base - 360 * s, tx + 14 * s, base - 332 * s], fill=wc)
    glow_circle(g, cx + 10 * s, base - 60 * s, 170 * s * glow, (255, 150, 70))
    glow_circle(g, cx + 10 * s, base - 140 * s, 220 * s * glow, (255, 120, 50))

def person(d, x, y, s, color=(8, 8, 10), walk=0.0, hunch=0.0):
    # head, torso, legs (stylised silhouette)
    d.ellipse([x - 9 * s + hunch * 8, y - 70 * s, x + 9 * s + hunch * 8, y - 52 * s], fill=color)
    d.polygon([(x - 13 * s, y - 50 * s), (x + 13 * s, y - 50 * s), (x + 10 * s, y - 20 * s), (x - 10 * s, y - 20 * s)], fill=color)
    sw = math.sin(walk) * 8 * s
    d.line([x - 6 * s, y - 22 * s, x - 6 * s + sw, y], fill=color, width=max(2, int(6 * s)))
    d.line([x + 6 * s, y - 22 * s, x + 6 * s - sw, y], fill=color, width=max(2, int(6 * s)))
    if hunch:  # arms forward (zombie)
        d.line([x, y - 45 * s, x + 24 * s, y - 40 * s], fill=color, width=max(2, int(5 * s)))

def trees(d, seed, y0, n, color, size):
    r = random.Random(seed)
    for _ in range(n):
        x = r.randint(-20, W + 20)
        h = size * r.uniform(0.7, 1.3)
        d.rectangle([x - 4, y0 - h * 0.5, x + 4, y0], fill=color)
        for k in range(4):
            ox, oy = r.uniform(-h * 0.3, h * 0.3), r.uniform(-h * 0.2, h * 0.2)
            rad = h * r.uniform(0.28, 0.42)
            d.ellipse([x + ox - rad, y0 - h * 0.7 + oy - rad, x + ox + rad, y0 - h * 0.7 + oy + rad], fill=color)

# ---------- scenes ----------
def scene_church(img, g, t, key="church", low=False, end=False):
    d = ImageDraw.Draw(img)
    silhouette_hills(d, 700, 90, (26, 24, 30), 1, off=t * 0.05)
    silhouette_hills(d, 760, 60, (16, 16, 20), 2)
    # sun glow
    glow_circle(g, W * 0.7, 640, 520, (255, 120, 60))
    if low:
        p = ease(t / 8.0)
        base = lerp(1520, 1290, p)
        church(d, g, 360, base, 1.7, 1.0, t)
        d.rectangle([0, min(base, H), W, H], fill=(12, 12, 14))
    else:
        church(d, g, 400, 980, 1.0 + 0.05 * (t / 5.0 if not end else 0), 1.0 if not end else 1.25, t)
    if not low:
        d.rectangle([0, 980, W, H], fill=(12, 12, 14))
    if end:
        walk = t * 4
        for i, (px, sc) in enumerate([(120, 1.0), (170, 1.05), (225, 0.95)]):
            xx_ = lerp(px - 40, 395, ease((t - 0.3) / 7.5))
            person(d, xx_ + i * 14, 1070 + i * 4, 2.1 - i * 0.1, walk=walk + i)
        if t > 5:  # zombies in distance on sides
            for zx in (40, 690):
                zz = ease((t - 5) / 3)
                person(d, zx + (-30 if zx > 360 else 30) * zz, 1040, 1.9, (4, 4, 6), walk=walk, hunch=1)
    elif not low:
        # birds / siren hint: a distant zombie shape at last seconds
        if t > 2.5:
            person(d, 620 - (t - 2.5) * 8, 1020, 1.3, (6, 6, 8), walk=t * 3, hunch=1)
    if low:
        person(d, 100, 1250, 3.0, (4, 4, 6), walk=t * 3, hunch=1) if t > 6 else None

def scene_street(img, g, t):
    d = ImageDraw.Draw(img)
    vx, vy = 360, 560
    # buildings left/right as perspective slabs
    cols = [(18, 20, 26), (22, 22, 28), (16, 18, 22)]
    for side in (-1, 1):
        for i in range(7):
            z0, z1 = i / 7, (i + 1) / 7
            def sc(z): return 1 / (1 + 4 * z)
            s0, s1 = sc(z0), sc(z1)
            x0 = vx + side * (330) * s0
            x1 = vx + side * (330) * s1
            top0 = vy - 520 * s0 + 40; top1 = vy - 520 * s1 + 40
            bot0 = vy + 380 * s0; bot1 = vy + 380 * s1
            d.polygon([(x0, top0), (x1, top1), (x1, bot1), (x0, bot0)], fill=cols[i % 3])
            # shop signs (commercial street)
            sign = [(255, 90, 60), (70, 200, 255), (255, 210, 60), (120, 255, 150), (255, 120, 220)][(i + (0 if side < 0 else 2)) % 5]
            fl = 0.7 + 0.3 * math.sin(t * 5 + i * 1.7)
            sc_ = tuple(int(c * fl) for c in sign)
            xa = vx + side * 300 * s0; xb = vx + side * 300 * s1
            d.polygon([(xa, vy + 40 * s0), (xb, vy + 40 * s1), (xb, vy + 110 * s1), (xa, vy + 110 * s0)], fill=sc_)
            glow_circle(g, (xa + xb) / 2, vy + 90 * (s0 + s1) / 2, 120 * (s0 + s1), sign)
            # lit windows
            for k in range(3):
                wy0 = vy - 300 * s0 + k * 90 * s0; wy1 = vy - 300 * s1 + k * 90 * s1
                if (i * 3 + k + (side > 0)) % 3 != 0:
                    d.polygon([(xa, wy0), (xb, wy1), (xb, wy1 + 40 * s1), (xa, wy0 + 40 * s0)], fill=(230, 190, 120))
    # road
    d.polygon([(vx - 330, H), (vx + 330, H), (vx + 12, vy + 6), (vx - 12, vy + 6)], fill=(24, 24, 28))
    for i in range(10):
        z = ((i / 10) + t * 0.12) % 1
        s = 1 / (1 + 4 * z)
        yv = vy + 380 * s
        d.polygon([(vx - 6 * s, yv - 18 * s), (vx + 6 * s, yv - 18 * s), (vx + 7 * s, yv), (vx - 7 * s, yv)], fill=(210, 190, 120))
    # cars (traffic jam): slow, brake lights
    r = random.Random(7)
    cars = [(r.choice([-1, 1]) * r.uniform(0.2, 0.85), r.random()) for _ in range(26)]
    cars.sort(key=lambda c: -((c[1] - t * 0.025) % 1))
    for lane, z0 in cars:
        z = (z0 - t * 0.025) % 1
        s = 1 / (1 + 4 * z)
        x = vx + lane * 280 * s
        y = vy + 380 * s
        w_ = 150 * s; h_ = 90 * s
        d.rounded_rectangle([x - w_ / 2, y - h_, x + w_ / 2, y], radius=int(8 * s), fill=(14, 14, 18))
        for sx in (-1, 1):
            cx_ = x + sx * w_ * 0.36
            d.ellipse([cx_ - 8 * s, y - h_ * 0.5 - 8 * s, cx_ + 8 * s, y - h_ * 0.5 + 8 * s], fill=(255, 40, 30))
            glow_circle(g, cx_, y - h_ * 0.5, 90 * s + 20, (255, 30, 20))
    # horn flashes
    if int(t * 3) % 4 == 0:
        glow_circle(g, 360, 640, 400, (255, 60, 40))
    # shadows chasing from edges
    p = ease((t - 5) / 3)
    if p > 0:
        person(d, 30 + 50 * p, 1200, 3.0, (4, 4, 6), walk=t * 3, hunch=1)

def scene_caribe(img, g, t):
    d = ImageDraw.Draw(img)
    silhouette_hills(d, 560, 100, (24, 30, 34), 5)
    # metro viaduct + train
    d.rectangle([0, 560, W, 600], fill=(30, 34, 38))
    for px in range(40, W, 160):
        d.rectangle([px, 600, px + 26, 800], fill=(24, 26, 30))
    tx = (t * 140) % (W + 500) - 400
    d.rectangle([tx, 500, tx + 400, 560], fill=(210, 220, 215))
    d.rectangle([tx, 540, tx + 400, 548], fill=(40, 160, 90))
    for k in range(8):
        d.rectangle([tx + 12 + k * 48, 512, tx + 40 + k * 48, 530], fill=(255, 220, 140))
    # station canopy & bridge
    d.polygon([(0, 380), (W, 330), (W, 400), (0, 440)], fill=(14, 16, 20))
    for k in range(6):
        d.rectangle([60 + k * 120, 405 - k * 8, 70 + k * 120, 560], fill=(14, 16, 20))
        d.rectangle([40 + k * 120, 392 - k * 8, 100 + k * 120, 398 - k * 8], fill=(220, 235, 255))
        glow_circle(g, 70 + k * 120, 396 - k * 8, 100, (170, 210, 255))
    # terminal building with sign
    d.rectangle([0, 800, W, 1000], fill=(16, 18, 22))
    d.rectangle([60, 830, 660, 880], fill=(35, 90, 70))
    d.text((90, 838), "TERMINAL DEL NORTE", font=f_mid, fill=(220, 240, 230))
    for k in range(10):
        lit = (k * 3 + int(t * 2)) % 5 != 0
        d.rectangle([60 + k * 60, 910, 100 + k * 60, 960], fill=(255, 210, 130) if lit else (30, 30, 36))
    # buses with orange lights
    for i in range(4):
        bx = (i * 230 + 20 - t * 14) % (W + 300) - 150
        d.rounded_rectangle([bx, 1010, bx + 180, 1110], radius=10, fill=(190, 60, 40))
        d.rectangle([bx + 10, 1025, bx + 170, 1060], fill=(255, 220, 150))
        d.ellipse([bx + 8, 1090, bx + 36, 1118], fill=(10, 10, 12)); d.ellipse([bx + 144, 1090, bx + 172, 1118], fill=(10, 10, 12))
        glow_circle(g, bx + 180, 1090, 100, (255, 140, 40))
    d.rectangle([0, 1120, W, H], fill=(14, 14, 16))
    # crowd (packed) + roadworks lights
    r = random.Random(11)
    for i in range(46):
        x = r.randint(10, W - 10); y = r.randint(1135, 1270)
        person(d, x + math.sin(t * 2 + i) * 6, y, 1.5 + (y - 1135) / 130, (6, 6, 8), walk=t * 3 + i)
    for k in range(3):
        cx_ = 120 + k * 240
        if int(t * 2 + k) % 2 == 0:
            glow_circle(g, cx_, 1000, 100, (255, 160, 30))
            d.ellipse([cx_ - 8, 992, cx_ + 8, 1008], fill=(255, 190, 40))
    if t > 6:
        person(d, 700 - ease((t - 6) / 4) * 60, 1150, 2.6, (4, 4, 6), walk=t * 3, hunch=1)

def scene_park(img, g, t):
    d = ImageDraw.Draw(img)
    silhouette_hills(d, 520, 90, (28, 34, 30), 9)
    trees(d, 21, 760, 9, (16, 24, 20), 360)
    d.rectangle([0, 760, W, H], fill=(18, 24, 20))
    trees(d, 33, 900, 7, (10, 16, 14), 520)
    # paths
    d.polygon([(250, 800), (470, 800), (700, H), (20, H)], fill=(34, 34, 36))
    # lamp posts
    for lx, ly, ls in [(160, 900, 1.0), (560, 900, 1.0), (330, 810, 0.55), (440, 810, 0.55)]:
        d.rectangle([lx - 4 * ls, ly - 300 * ls, lx + 4 * ls, ly], fill=(8, 8, 10))
        fl = 0.6 + 0.4 * (1 if (int(t * 6 + lx) % 9) else 0.15)
        d.ellipse([lx - 14 * ls, ly - 320 * ls, lx + 14 * ls, ly - 292 * ls], fill=tuple(int(c * fl) for c in (255, 230, 160)))
        glow_circle(g, lx, ly - 306 * ls, 260 * ls * fl, (255, 200, 110))
    # bench
    d.rectangle([420, 1010, 600, 1024], fill=(8, 8, 10))
    d.rectangle([425, 1024, 435, 1060], fill=(8, 8, 10)); d.rectangle([585, 1024, 595, 1060], fill=(8, 8, 10))
    d.rectangle([420, 985, 600, 995], fill=(8, 8, 10))
    # slow zombie approaching along path
    p = clamp((t - 2) / 6.5)
    zy = lerp(820, 1230, ease(p)); zs = lerp(1.0, 4.2, ease(p))
    person(d, 360 + math.sin(t * 2) * 6, zy, zs, (4, 4, 6), walk=t * 2.5, hunch=1)
    # fog
    fog = Image.new("RGB", (W, H), (0, 0, 0))
    fd = ImageDraw.Draw(fog)
    for k in range(5):
        ox = (t * 18 + k * 160) % (W + 400) - 200
        fd.ellipse([ox - 260, 760 + k * 55, ox + 260, 860 + k * 55], fill=(24, 30, 30))
    fog = fog.filter(ImageFilter.GaussianBlur(40))
    img.paste(ImageChops.add(img, fog))

_proc = [
    (lambda i, g, t: scene_church(i, g, t), "church", "DÍA Z  |  IGLESIA SAN JUDAS, CASTILLA"),
    (scene_street, "street", "01  |  LA CARRERA 68"),
    (scene_caribe, "caribe", "02  |  ESTACIÓN CARIBE Y TERMINAL DEL NORTE"),
    (scene_park, "park", "03  |  PARQUE DE JUANES"),
    (lambda i, g, t: scene_church(i, g, t, low=True), "church2", "04  |  ¿Y ENTONCES?"),
    (lambda i, g, t: scene_church(i, g, t, end=True), "end", "DÍA Z  ·  CASTILLA"),
]

_photo_cache = {}
def find_photo(idx):
    if not FOTOS: return None
    for ext in ("jpg", "jpeg", "png", "webp", "JPG", "JPEG", "PNG"):
        m = sorted(glob.glob(os.path.join(FOTOS, f"{idx:02d}*.{ext}")))
        if m: return m[0]
    return None

def photo_scene(img, g, t, idx, dur, path):
    if path not in _photo_cache:
        im = Image.open(path).convert("RGB")
        sc = max(W * 1.3 / im.width, H * 1.3 / im.height)
        _photo_cache[path] = im.resize((int(im.width * sc), int(im.height * sc)), Image.LANCZOS)
    base = _photo_cache[path]
    p = clamp(t / max(dur, 0.1))
    direction = [1, -1, 1, -1, 1, -1][idx % 6]
    if idx == 4:  # contrapicado: la cámara sube
        zoom0, zoom1 = 1.0, 0.86
    else:
        zoom0, zoom1 = 1.0, 0.82
    vw = min(base.width, W * 1.25 * lerp(zoom0, zoom1, ease(p)))
    vh = vw * H / W
    if vh > base.height:
        vh = base.height; vw = vh * W / H
    cx = base.width / 2 + direction * (p - 0.5) * (base.width - vw) * 0.8
    cy = base.height / 2 + (-(p - 0.5) * (base.height - vh) * 0.8 if idx == 4 else (p - 0.5) * (base.height - vh) * 0.3)
    cx = clamp(cx, vw / 2, base.width - vw / 2); cy = clamp(cy, vh / 2, base.height - vh / 2)
    # leve temblor de cámara
    cx += math.sin(t * 2.3) * 2; cy += math.cos(t * 1.9) * 2
    crop = base.resize((W, H), Image.BICUBIC, box=(cx - vw / 2, cy - vh / 2, cx + vw / 2, cy + vh / 2))
    # look nocturno: baja saturación y luz, tinte cálido arriba / frío abajo
    arr = np.asarray(crop).astype(np.float32)
    gray = arr.mean(axis=2, keepdims=True)
    arr = gray + (arr - gray) * 0.65
    arr *= 0.62
    ramp = np.linspace(1, 0, H)[:, None, None]
    arr = arr * (np.array([1.0, 0.82, 0.7]) * ramp + np.array([0.75, 0.9, 1.1]) * (1 - ramp))
    img.paste(Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8)))
    d = ImageDraw.Draw(img)
    # zombi lejano que se acerca (siluetas) en las rutas
    if idx in (1, 2, 3):
        z = ease((t - 1.0) / max(dur - 1.5, 1))
        person(d, lerp(660, 560, z), lerp(1010, 1180, z), lerp(1.2, 3.2, z), (4, 4, 6), walk=t * 3, hunch=1)
    if idx == 5:
        for zx, dr in ((40, 1), (690, -1)):
            zz = ease((t - 3) / 4)
            person(d, zx + dr * 40 * zz, 1060, 2.0, (4, 4, 6), walk=t * 3, hunch=1)

_starts = TL["scene_starts"] if TL else [0, 5, 14, 24, 33, 42]
_ends = _starts[1:] + [DUR]
SCENES = []
for _i, (_fn, _key, _label) in enumerate(_proc):
    _ph = find_photo(_i)
    if _ph:
        _fn2 = (lambda i_, g_, t_, _i=_i, _d=_ends[_i] - _starts[_i], _p=_ph: photo_scene(i_, g_, t_, _i, _d, _p))
    else:
        _fn2 = _fn
    SCENES.append((_starts[_i], _ends[_i], _key, _fn2, _label))
SKIES["church2"] = SKIES["church2"]

SUBS = [tuple(x) for x in TL["subs"]] if TL else []
CARD_T = TL["card_t"] if TL else 46.0
def _line_t(prefix, default):
    if TL:
        for a, b, say in TL["lines"]:
            if say.startswith(prefix): return a - 0.1
    return default
CARR_T = _line_t("Carrera sesenta", CARD_T + 2.7)
ETIQ_T = _line_t("Etiqueta", CARD_T + 5.5)

def rich_lines(text, font, maxw):
    toks, on, prev = [], False, " "
    for part in text.split("*"):
        first = True
        for w in part.split(" "):
            if w:
                glue = first and len(toks) > 0 and part[:1] != " " and not prev.endswith(" ")
                toks.append((w, on, glue))
            first = False
        if part: prev = part
        on = not on
    lines, line, wid = [], [], 0
    sp = font.getlength(" ")
    for w, o, gl in toks:
        wl = font.getlength(w)
        gap = 0 if (gl or not line) else sp
        if line and wid + gap + wl > maxw:
            lines.append(line); line, wid, gap = [], 0, 0
        wid += gap + wl
        line.append((w, o, wl, gl))
    if line: lines.append(line)
    return lines

def draw_rich(ui, text, font, cy, alpha, maxw=620, lh=58):
    d = ImageDraw.Draw(ui)
    lines = rich_lines(text, font, maxw)
    sp = font.getlength(" ")
    y = cy - lh * len(lines) / 2
    a = int(255 * alpha)
    for ln in lines:
        total = sum(e[2] for e in ln) + sum(sp for k, e in enumerate(ln) if k and not e[3])
        x = W / 2 - total / 2
        for k, (w, o, wl, gl) in enumerate(ln):
            if k and not gl: x += sp
            col = (*(ORANGE if o else WHITE), a)
            d.text((x + 2, y + 3), w, font=font, fill=(0, 0, 0, int(a * 0.8)))
            d.text((x, y), w, font=font, fill=col)
            x += wl
        y += lh

def centered(ui, text, font, y, color, alpha):
    d = ImageDraw.Draw(ui)
    w = font.getlength(text)
    a = int(255 * alpha)
    d.text((W / 2 - w / 2 + 2, y + 3), text, font=font, fill=(0, 0, 0, int(a * .8)))
    d.text((W / 2 - w / 2, y), text, font=font, fill=(*color, a))

def render(t):
    si = next(i for i, s in enumerate(SCENES) if s[0] <= t < s[1]) if t < DUR else len(SCENES) - 1
    s0, s1, key, fn, label = SCENES[si]
    lt = t - s0
    img = Image.new("RGB", (W, H))
    img.paste(Image.fromarray(SKIES[key].astype(np.uint8)))
    g = Image.new("RGB", (W // 4, H // 4), (0, 0, 0))
    fn(img, g, lt)
    g = g.filter(ImageFilter.GaussianBlur(10)).resize((W, H))
    img = ImageChops.add(img, g.point(lambda v: int(v * 0.4)))
    arr = np.asarray(img).astype(np.float32)
    # grade: darker, slight teal, vignette, grain
    arr = arr * np.array([0.95, 0.93, 1.0], np.float32)
    arr = arr * VIG
    arr += rng.normal(0, 5, (H, W, 1)).astype(np.float32)
    # transitions: quick dip to black + flash
    dip = min(lt / 0.35, (s1 - t) / 0.35, 1.0)
    dip = clamp(dip)
    arr *= (0.25 + 0.75 * dip) if si > 0 or lt < 0.0 else (0.25 + 0.75 * clamp(lt / 0.6))
    if lt < 0.12 and si > 0:
        arr += 40 * (1 - lt / 0.12)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # slow push-in
    z = 1 + 0.05 * (lt / (s1 - s0))
    cw, ch = W / z, H / z
    img = img.resize((W, H), Image.BILINEAR, box=((W - cw) / 2, (H - ch) / 2, (W + cw) / 2, (H + ch) / 2))
    # UI layer
    ui = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    la = ease(lt / 0.5)
    if si != 5:
        centered(ui, label, f_lab, 70, (200, 200, 195), la * 0.9)
    band = Image.new("L", (1, H), 0)
    for yb in range(880, H):
        band.putpixel((0, yb), int(150 * min(1, (yb - 880) / 120)))
    if si != 5:
        ui.paste((0, 0, 0, 255), (0, 0), band.resize((W, H)))
    d = ImageDraw.Draw(ui)
    if si != 5:
        d.rectangle([W / 2 - 40, 108, W / 2 + 40, 111], fill=(*ORANGE, int(255 * la)))
    for a0, a1, txt in SUBS:
        if a0 <= t < a1:
            al = min(ease((t - a0) / 0.25), ease((a1 - t) / 0.2))
            draw_rich(ui, txt, f_sub, 1010 if si != 5 else 520, al)
    if si == 0 and t < 3.0:
        centered(ui, "DÍA Z", f_big, 420, ORANGE, ease(t / 0.6) * (1 - ease((t - 2.4) / 0.6)))
    if t >= CARD_T:
        p = ease((t - CARD_T) / 0.6)
        centered(ui, "¿TÚ POR DÓNDE SALES?", f_lab, 360, (200, 200, 195), p)
        pc = ease((t - CARR_T) / 0.5)
        centered(ui, "CARRERA 68", f_big, 410, WHITE, pc)
        centered(ui, "o", f_mid, 505, (180, 180, 175), pc)
        centered(ui, "SAN JUDAS", f_big, 560, ORANGE, ease((t - CARR_T - 1.2) / 0.5))
        centered(ui, "Etiqueta al que ya está rezando.", f_small, 700, WHITE, ease((t - ETIQ_T) / 0.6))
        centered(ui, "DÍA Z  ·  CASTILLA", f_tag, 1180, (170, 170, 165), ease((t - ETIQ_T - 0.8) / 0.6))
    # fade to black the last 0.4s
    out = img.convert("RGBA")
    out.alpha_composite(ui)
    out = out.convert("RGB")
    if t > DUR - 0.4:
        out = Image.eval(out, lambda v: int(v * clamp((DUR - t) / 0.4)))
    return out

if __name__ == "__main__":
    cmd = ["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS),
           "-i", "-", "-i", AUDIO, "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
           "-c:a", "aac", "-b:a", "160k", "-shortest", OUT]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    for i in range(NF):
        p.stdin.write(render(i / FPS).tobytes())
        if i % 150 == 0: print("frame", i, flush=True)
    p.stdin.close(); p.wait()
    print("done")
