#!/bin/bash
# Genera el video "DÍA Z: Castilla" con narrador.
# Uso: ./generar.sh [carpeta_con_fotos]   (por defecto ../../fotos)
# Fotos: 00_iglesia, 01_carrera68, 02_caribe, 03_parque, 04_iglesia_abajo, 05_cierre (.jpg/.png).
# Si falta alguna foto, esa escena usa la ilustración animada.
set -e
cd "$(dirname "$0")"
FOTOS="${1:-../../fotos}"
B=build; mkdir -p $B/tts
pip install -q piper-tts numpy pillow
[ -f $B/tts/es.onnx ] || {
  curl -sSL -o $B/tts/es.onnx      https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx
  curl -sSL -o $B/tts/es.onnx.json https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json
}
python3 tts/narr.py $B
python3 make_audio.py $B/mix.wav $B/timeline.json $B/narr.wav
python3 make_video.py $B/dia_z_narrado.mp4 $B/mix.wav $B/timeline.json "$FOTOS"
ffmpeg -y -v error -i $B/dia_z_narrado.mp4 -c:v libx264 -crf 27 -preset slow -pix_fmt yuv420p -c:a copy -movflags +faststart ../../dia_z_castilla_narrado.mp4
echo "Listo: dia_z_castilla_narrado.mp4"
