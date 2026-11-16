"""Genera la voz del narrador (Piper, español) y una línea de tiempo (timeline.json)
para que el video siga a la voz: cada frase define cuándo cambia la escena y el subtítulo."""
import json, sys, wave
import numpy as np
from piper import PiperVoice
try:
    from piper import SynthesisConfig
    CFG = SynthesisConfig(length_scale=0.93)
except Exception:
    CFG = None

OUTDIR = sys.argv[1]
v = PiperVoice.load(f"{OUTDIR}/tts/es.onnx")
SR = v.config.sample_rate

# (escena, texto hablado, subtítulo con *naranja* o None, pausa antes en segundos)
LINES = [
    (0, "Empezó el apocalipsis zombi.", "Empezó el apocalipsis *zombi*.", 0.5),
    (0, "Estás en San Judas, sobre la sesenta y ocho.", "Estás en *San Judas*, sobre la 68.", 0.3),
    (0, "Tienes que salir de Castilla.", "Tienes que salir de *Castilla*.", 0.3),
    (1, "Opción uno: la carrera sesenta y ocho.", "Opción uno: la *Carrera 68*.", 0.5),
    (1, "La calle más comercial de Castilla.", "La calle más comercial de *Castilla*.", 0.3),
    (1, "Todo el mundo va para allá.", "Todo el mundo va para allá.", 0.3),
    (1, "Ya estaba así antes.", "Ya estaba así *antes*.", 0.4),
    (2, "Opción dos: la estación Caribe y la Terminal del Norte.", "Opción dos: estación *Caribe* y Terminal del Norte.", 0.5),
    (2, "Todos piensan: me voy en bus o en metro.", "Todos piensan: «me voy en bus o en metro».", 0.3),
    (2, "Nadie sale.", "*Nadie* sale.", 0.5),
    (3, "Opción tres: el Parque de Juanes.", "Opción tres: el *Parque de Juanes*.", 0.5),
    (3, "Parece refugio.", "Parece *refugio*.", 0.3),
    (3, "Es el primer lugar donde te buscan.", "Es el primer lugar donde te *buscan*.", 0.4),
    (4, "Entonces... hiciste todo el recorrido.", "Hiciste todo el recorrido…", 0.5),
    (4, "Y la mejor salida, estaba donde empezaste.", "Y la mejor salida estaba donde *empezaste*.", 1.2),
    (5, "San Judas: patrono de las causas difíciles.", "*San Judas*: patrono de las causas difíciles.", 0.5),
    (5, "¿Tú por dónde sales?", None, 1.0),
    (5, "Carrera sesenta y ocho... o San Judas.", None, 0.3),
    (5, "Etiqueta al que ya está rezando.", None, 0.4),
]

TAIL = 0.7          # aire al final de cada escena
t = 0.0
tl_subs, scene_start, card_t, lines_t = [], {}, None, []
audio_parts = []   # (t0, samples)
for i, (sc, say, sub, pause) in enumerate(LINES):
    if sc not in scene_start:
        if sc > 0:
            t += TAIL
        scene_start[sc] = t
        t += 0.35 if sc else 0.0
    t += pause if not (i and LINES[i - 1][0] != sc) else 0.25
    kw = {"syn_config": CFG} if CFG else {}
    a = np.concatenate([np.frombuffer(c.audio_int16_bytes, np.int16) for c in v.synthesize(say, **kw)]).astype(np.float32) / 32768
    d = len(a) / SR
    audio_parts.append((t, a))
    if sub:
        tl_subs.append([round(t - 0.1, 2), round(t + d + 0.25, 2), sub])
    if say.startswith("¿Tú por dónde"):
        card_t = round(t - 0.1, 2)
    lines_t.append((round(t, 2), round(t + d, 2), say))
    t += d
DUR = round(t + 1.6, 2)

out = np.zeros(int(DUR * SR) + SR, np.float32)
for t0, a in audio_parts:
    i = int(t0 * SR)
    out[i:i + len(a)] += a
# un poco de eco para dar clima
echo = np.zeros_like(out)
dl = int(0.13 * SR)
echo[dl:] = out[:-dl] * 0.22
out = out + echo
out = out[: int(DUR * SR)]
out /= max(1e-6, np.abs(out).max())
out *= 0.95
with wave.open(f"{OUTDIR}/narr.wav", "w") as w:
    w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes((out * 32767).astype(np.int16).tobytes())

starts = [scene_start[k] for k in sorted(scene_start)]
tl = {"dur": DUR, "scene_starts": [round(s, 2) for s in starts], "subs": tl_subs, "card_t": card_t, "lines": lines_t}
json.dump(tl, open(f"{OUTDIR}/timeline.json", "w"), ensure_ascii=False, indent=1)
print("dur", DUR, "scenes", tl["scene_starts"], "card", card_t)
