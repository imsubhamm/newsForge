#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
JOB_DIR="$ROOT/storage/jobs/sample-demo"
FOOTAGE="$JOB_DIR/footage"
ANALYSIS="$JOB_DIR/analysis"
OUTPUT="$JOB_DIR/output"
FONT_DIR="$ROOT/video/public/fonts"
mkdir -p "$FOOTAGE" "$ANALYSIS" "$OUTPUT" "$FONT_DIR"

if [[ ! -f "$FONT_DIR/NotoSansBengali-Regular.ttf" ]]; then
  curl -L --fail --retry 3 -o "$FONT_DIR/NotoSansBengali-Regular.ttf" \
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Regular.ttf"
fi
if [[ ! -f "$FONT_DIR/NotoSansBengali-Bold.ttf" ]]; then
  curl -L --fail --retry 3 -o "$FONT_DIR/NotoSansBengali-Bold.ttf" \
    "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansBengali/NotoSansBengali-Bold.ttf"
fi

make_clip() {
  local name="$1"
  local color="$2"
  local label="$3"
  local accent="$4"
  ffmpeg -y -hide_banner -loglevel error \
    -f lavfi -i "color=c=${color}:s=1920x1080:d=6:r=30" \
    -vf "drawbox=x=0:y=900:w=1920:h=180:color=${accent}@0.88:t=fill" \
    -c:v libx264 -pix_fmt yuv420p -preset fast -crf 20 \
    "$FOOTAGE/$name"
}

make_clip "clip01.mp4" "0x17375E" "MALL EXTERIOR" "0xC41E3A"
make_clip "clip02.mp4" "0x2B2118" "CROWD / INSIDE MALL" "0x8A6A2F"
make_clip "clip03.mp4" "0x1C2B24" "SECURITY RESPONSE" "0x2F6B4F"

ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "aevalsrc=0.12*sin(2*PI*220*t)+0.06*sin(2*PI*330*t):s=44100:d=8" \
  -c:a libmp3lame -b:a 160k "$JOB_DIR/voice.mp3"

ffmpeg -y -hide_banner -loglevel error \
  -f lavfi -i "color=c=0xC41E3A:s=384x384:d=1:r=1" \
  -vf "drawbox=x=42:y=42:w=300:h=300:color=0xF4D35E@1:t=14,drawbox=x=132:y=132:w=120:h=120:color=0xF6F1E8@1:t=fill" \
  -frames:v 1 "$JOB_DIR/logo.png"

cat > "$JOB_DIR/script.txt" <<'EOF'
পুজোর বাজারে ঘটল এক অদ্ভুত ঘটনা। দুর্গাপুরের একটি ব্যস্ত শপিং মলে হঠাৎ হনুমান উঠে পড়ে। কেনাকাটা থেমে যায়, মানুষ ভিড় জমায়। পুলিশ ও মল কর্তৃপক্ষ ঘটনাস্থলে পৌঁছায়।
EOF

cat > "$JOB_DIR/metadata.json" <<'EOF'
{
  "id": "sample-demo",
  "title": "দুর্গাপুরের মলে হঠাৎ হনুমান",
  "location": "দুর্গাপুর",
  "reporter_name": "রিয়া সেন",
  "status": "UPLOADED",
  "crop_mode": "blur-background",
  "voice": "voice.mp3",
  "logo": "logo.png",
  "script_path": "script.txt",
  "footage": [
    {"id": "clip01", "filename": "clip01.mp4"},
    {"id": "clip02", "filename": "clip02.mp4"},
    {"id": "clip03", "filename": "clip03.mp4"}
  ]
}
EOF

python3 - "$JOB_DIR" <<'PY'
import json
import sys
from pathlib import Path

job = Path(sys.argv[1])
plan = {
  "headline": "দুর্গাপুরের মলে হঠাৎ হনুমান",
  "location": "দুর্গাপুর",
  "reporter_name": "রিয়া সেন",
  "duration": 8.0,
  "crop_mode": "blur-background",
  "footage_warning": None,
  "timeline": [
    {
      "start": 0.0,
      "end": 3.2,
      "source": "clip01.mp4",
      "source_start": 1.0,
      "source_end": 4.2,
      "reason": "Mall exterior establishes the location."
    },
    {
      "start": 3.2,
      "end": 6.2,
      "source": "clip02.mp4",
      "source_start": 0.4,
      "source_end": 3.4,
      "reason": "Crowd and interior context for the incident."
    },
    {
      "start": 6.2,
      "end": 8.0,
      "source": "clip03.mp4",
      "source_start": 1.0,
      "source_end": 2.8,
      "reason": "Security presence closes the story."
    }
  ],
  "captions": [
    {"start": 0.0, "end": 2.0, "text": "পুজোর বাজারে ঘটল"},
    {"start": 2.0, "end": 3.6, "text": "এক অদ্ভুত ঘটনা"},
    {"start": 3.6, "end": 5.4, "text": "মলে হঠাৎ হনুমান"},
    {"start": 5.4, "end": 6.8, "text": "কেনাকাটা থেমে যায়"},
    {"start": 6.8, "end": 8.0, "text": "কর্তৃপক্ষ পৌঁছায়"}
  ]
}
(job / "analysis" / "timeline.json").write_text(
    json.dumps(plan, ensure_ascii=False, indent=2) + "\n",
    encoding="utf-8",
)
print("timeline written")
PY

echo "Sample job ready at $JOB_DIR"
