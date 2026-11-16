import sys, wave, json
import numpy as np

TL = json.load(open(sys.argv[2]))
DUR = TL['dur']
SR = 44100
N = int(SR * DUR)
t = np.arange(N) / SR
r = np.random.default_rng(5)

def env(x, a, d):  # one-shot decaying envelope
    return np.where(x >= 0, np.exp(-x / d) * np.minimum(1, x / a), 0)

# dark drone, slowly evolving
lfo = 0.5 + 0.5 * np.sin(2 * np.pi * 0.08 * t)
drone = (np.sin(2 * np.pi * 55 * t) * 0.35 + np.sin(2 * np.pi * 82.4 * t + 1) * 0.2 * lfo
         + np.sin(2 * np.pi * 110.7 * t) * 0.1 * (1 - lfo))
# tension pad (minor second)
pad = (np.sin(2 * np.pi * 220 * t) + np.sin(2 * np.pi * 233.1 * t)) * 0.04 * (0.4 + 0.6 * np.sin(2 * np.pi * 0.05 * t) ** 2)
mix = drone * 0.6 + pad

# heartbeat that speeds up, until 33s
hb = np.zeros(N)
tt = 0.0
while tt < TL['scene_starts'][4]:
    for off, amp in ((0, 1.0), (0.22, 0.7)):
        x = t - (tt + off)
        hb += amp * np.sin(2 * np.pi * 52 * x) * env(x, 0.005, 0.09)
    tt += 1.1 - 0.45 * (tt / TL['scene_starts'][4])
mix += hb * 0.5

# distant siren (0-5s), very quiet
sir = np.sin(2 * np.pi * np.cumsum(700 + 220 * np.sin(2 * np.pi * 0.35 * t)) / SR)
mix += sir * 0.035 * np.clip(1 - np.abs(t - 2.5) / 3, 0, 1)

# whoosh + hit at each scene change
for tc in TL['scene_starts'][1:]:
    x = t - tc
    noise = r.normal(0, 1, N)
    wh = noise * np.exp(-((x + 0.25) / 0.2) ** 2) * 0.12
    hit = np.sin(2 * np.pi * 45 * x) * env(x, 0.003, 0.35) * 0.8
    mix += wh + hit

# traffic horns (scene 1)
s1 = TL['scene_starts'][1]
for th in (s1 + 1.2, s1 + 2.0, s1 + 4.4, s1 + 7.1):
    x = t - th
    mix += (np.sin(2 * np.pi * 420 * x) + np.sin(2 * np.pi * 530 * x)) * env(x, 0.01, 0.12) * 0.05 * (x > 0)

# church bells (scene 4 and 5): inharmonic partials
def bell(t0, f=330, amp=0.22):
    x = t - t0
    out = np.zeros(N)
    for ratio, a in ((1, 1), (2.01, 0.5), (2.76, 0.4), (4.07, 0.25), (5.4, 0.15)):
        out += a * np.sin(2 * np.pi * f * ratio * x) * env(x, 0.003, 2.2 / ratio ** 0.5)
    return out * amp * (x > 0)
s4 = TL['scene_starts'][4]
for tb in [s4 + 1.5 + 2.4 * k for k in range(int((DUR - s4 - 2) // 2.4))]:
    mix += bell(tb)

# zombie growl at the end
x = t - (DUR - 1.2)
g = r.normal(0, 1, N)
low = np.convolve(g, np.ones(60) / 60, mode="same")
growl = low * (1 + 0.8 * np.sin(2 * np.pi * 28 * x)) * np.exp(-((x - 0.45) / 0.35) ** 2) * (x > -0.1) * 2.2
mix += growl * 0.8

# duck volume for the 1s pause (37-38) except bell


mix = mix * 0.55   # música más baja: va debajo de la voz
mix = np.tanh(mix * 1.2)
mix /= np.max(np.abs(mix))
mix *= 0.8
import wave as _w
with _w.open(sys.argv[3]) as nw:
    nv = np.frombuffer(nw.readframes(nw.getnframes()), np.int16).astype(np.float32) / 32768
    nsr = nw.getframerate()
nv = np.interp(np.arange(N) / SR, np.arange(len(nv)) / nsr, nv)
# la música baja mientras habla el narrador
envv = np.convolve(np.abs(nv), np.ones(int(SR * 0.25)) / int(SR * 0.25), mode='same')
duck = 1 - 0.55 * np.clip(envv * 8, 0, 1)
mix = mix * duck * 0.6 + nv * 0.95
mix /= max(1.0, np.abs(mix).max())
fade = np.clip((DUR - t) / 0.4, 0, 1) * np.clip(t / 0.3, 0, 1)
mix *= fade
pcm = (mix * 32767).astype(np.int16)
with wave.open(sys.argv[1], "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())
print("audio ok")
