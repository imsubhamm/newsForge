#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
export TMPDIR="${TMPDIR:-/tmp}"
export npm_config_cache="${npm_config_cache:-$HOME/.npm}"
JOB_DIR="${1:-$ROOT/storage/jobs/sample-demo}"
PROPS="$JOB_DIR/analysis/remotion-props.json"
OUTPUT="$JOB_DIR/output/final.mp4"

if [[ ! -f "$JOB_DIR/analysis/timeline.json" ]]; then
  echo "Missing timeline.json. Run: bash scripts/generate-sample-assets.sh" >&2
  exit 1
fi

mkdir -p "$JOB_DIR/output" "$ROOT/video/public/jobs"
# Remotion can only serve media from video/public during render.
PUBLIC_JOB="$ROOT/video/public/jobs/$(basename "$JOB_DIR")"
rm -rf "$PUBLIC_JOB"
mkdir -p "$PUBLIC_JOB"
cp -R "$JOB_DIR/footage" "$PUBLIC_JOB/footage"
cp "$JOB_DIR/voice.mp3" "$PUBLIC_JOB/voice.mp3"
if [[ -f "$JOB_DIR/logo.png" ]]; then
  cp "$JOB_DIR/logo.png" "$PUBLIC_JOB/logo.png"
fi
PUBLIC_PREFIX="/jobs/$(basename "$JOB_DIR")"

python3 - "$JOB_DIR" "$PROPS" "$PUBLIC_PREFIX" <<'PY'
import json
import sys
from pathlib import Path

job = Path(sys.argv[1]).resolve()
out = Path(sys.argv[2])
prefix = sys.argv[3]
plan = json.loads((job / "analysis" / "timeline.json").read_text(encoding="utf-8"))
props = {
    "headline": plan["headline"],
    "location": plan.get("location", ""),
    "reporterName": plan.get("reporter_name", ""),
    "duration": plan["duration"],
    "cropMode": plan.get("crop_mode", "center-crop"),
    "audioSrc": f"{prefix}/voice.mp3",
    "bedSrc": "/audio/news-bed.mp3",
    "logoSrc": f"{prefix}/logo.png" if (job / "logo.png").exists() else None,
    "clips": [
        {
            "start": clip["start"],
            "end": clip["end"],
            "src": f"{prefix}/footage/{clip['source']}",
            "sourceStart": clip["source_start"],
            "sourceEnd": clip["source_end"],
            "cropMode": clip.get("crop_mode") or plan.get("crop_mode", "center-crop"),
        }
        for clip in plan["timeline"]
    ],
    "captions": plan.get("captions", []),
}
out.write_text(json.dumps(props, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(out)
PY

cd "$ROOT/video"
npx remotion render src/index.ts NewsVideo "$OUTPUT" \
  --props="$PROPS" \
  --public-dir="$ROOT/video/public" \
  --codec=h264 \
  --pixel-format=yuv420p \
  --image-format=jpeg \
  --overwrite

ffprobe -v error -select_streams v:0 -show_entries stream=width,height,codec_name,avg_frame_rate \
  -show_entries format=duration \
  -of default=noprint_wrappers=1 "$OUTPUT"

echo "Rendered: $OUTPUT"
