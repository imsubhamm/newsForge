# Bangla News AI Editor

Local-first editor for a Bengali news channel. A reporter uploads a script, a voice-over, and raw footage. The system builds a vertical 1080×1920 news reel for Instagram Reels, Facebook Reels, and YouTube Shorts. **Nothing is published automatically.** A human must preview and approve the result.

This repository currently completes **Milestones 1–2**:

1. Create a news project and store assets on disk.
2. Render one professional sample reel from a static `timeline.json`.

Whisper, footage AI, and automatic editing come next. They are intentionally not implemented yet.

---

## What it does today

- Dashboard for creating a news story (title, location, reporter, Bengali script, voice, multiple clips, optional logo)
- Upload validation and progress
- Job IDs written to `storage/jobs/{job_id}/`
- FastAPI + SQLite job records
- Remotion news template: footage, voice, Bengali captions, headline, location, logo, lower third
- A verified sample 1080×1920 H.264/AAC MP4 from a hand-written timeline

## Architecture

AI reasoning stays separate from video rendering. The model must never cut pixels. It may only emit a validated editing plan.

```
INPUT
  Bengali script
  Bengali voice-over
  Raw footage
        │
        ▼
Transcription Service          (Milestone 3)
        │
        ▼
Script / Whisper alignment     (Milestone 4)
        │
        ▼
Footage preprocessing          (Milestone 5)
        │
        ▼
Footage analysis (vision)      (Milestone 6)
        │
        ▼
AI editor agent                (Milestone 7)
        │
        ▼
timeline.json                  (strict schema)
        │
        ▼
Remotion + FFmpeg
        │
        ▼
Rendered MP4  1080×1920
```

`MOCK_AI=true` keeps the stack runnable without API keys. Provider code lives in `services/api/app/ai/` so OpenAI-compatible APIs can be plugged in later. Keys come only from environment variables.

## Repository layout

```
apps/web/                 Next.js dashboard
services/api/             FastAPI, SQLite, job storage
video/                    Remotion 9:16 news template
storage/jobs/             Per-job assets, analysis, output
data/                     SQLite database
scripts/                  Sample assets + render helpers
docs/
```

Job folder contract:

```
storage/jobs/{job_id}/
  script.txt
  voice.mp3
  footage/clip01.mp4
  metadata.json
  analysis/timeline.json
  output/final.mp4
```

## Prerequisites (macOS)

- macOS with Apple Silicon or Intel
- Node.js 20+
- npm 10+
- Python 3.11+
- FFmpeg and ffprobe (`brew install ffmpeg`)
- Chrome/Chromium is installed automatically by Remotion on first render if needed

### FFmpeg

```bash
brew install ffmpeg
ffmpeg -version
ffprobe -version
```

You need `libx264` and an AAC/MP3 encoder. Homebrew’s ffmpeg formula includes both.

### Node

```bash
node -v
npm -v
```

### Python

```bash
python3 --version
cd services/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Environment variables

Copy the example file. Do not commit a real `.env`.

```bash
cp .env.example .env
```

| Variable | Purpose |
| --- | --- |
| `MOCK_AI` | `true` skips paid AI calls |
| `AI_PROVIDER` | `openai` or `mock` |
| `OPENAI_API_KEY` | Only from the environment, never hardcoded |
| `STORAGE_PATH` | Local job storage, default `./storage` |
| `DATABASE_URL` | SQLite URL, default `sqlite:///./data/news_editor.db` |
| `NEXT_PUBLIC_API_URL` | Frontend → API, default `http://127.0.0.1:8000` |

## Run the backend

```bash
cd services/api
source .venv/bin/activate
python -m uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Health check: http://127.0.0.1:8000/api/health

## Run the frontend

```bash
cd apps/web
npm install
npm run dev
```

Open http://localhost:3000. The homepage is the **Create News Story** form. After upload you land on `/jobs/{id}` with real backend job state.

## Render the sample news reel

This is the Milestone 2 proof: raw footage + voice + captions + branding → 1080×1920 MP4.

```bash
cd apps/web && npm install
cd ../../video && npm install
cd ../..
bash scripts/generate-sample-assets.sh
bash scripts/render-sample.sh
```

Output (verified 1080×1920 H.264 + AAC):

```
/Users/imsub/NewsEditor/storage/jobs/sample-demo/output/final.mp4
```

If `npx remotion` fails with `EILSEQ` or a 404 for footage, set `TMPDIR=/tmp` and keep media under `video/public` (the render script copies the job there).

Preview the template interactively:

```bash
cd video
npm run studio
```

## Tests

```bash
cd services/api
source .venv/bin/activate
pytest
```

Coverage is limited to things that already exist: upload validation, path safety, timeline schema, subtitle chunking, ffprobe metadata, and AI JSON parsing.

## Troubleshooting

**`ffprobe is not installed`**
Install ffmpeg with Homebrew and restart the terminal.

**Upload fails / “Is the API running?”**
Start FastAPI on port 8000. The Next.js app proxies `/api/*` there.

**Remotion render cannot find Chrome**
On first render Remotion downloads a headless browser. Allow network access once. Re-run `bash scripts/render-sample.sh`.

**Bengali glyphs look like tofu**
The render uses bundled `video/public/fonts/NotoSansBengali-*.ttf`. Re-run `bash scripts/generate-sample-assets.sh` if those files are missing.

**Unsupported / empty media**
Only `.mp3/.wav/.m4a` audio and `.mp4/.mov` video are accepted. Empty files are rejected.

**SQLite, npm, or Remotion errors on an external drive**
This repo was started on `/Volumes/Flash/NewsEditor`, but that volume corrupted many ordinary file writes (`EILSEQ`, null-byte files). The verified working copy is:

```
/Users/imsub/NewsEditor
```

If you keep a copy on Flash, run installs and renders with:

```bash
export npm_config_cache="$HOME/.npm"
export TMPDIR="/tmp"
```

Do not use an npm cache or Remotion temp directory on the Flash volume.

**Homebrew FFmpeg has no `drawtext`**
The Homebrew build on this Mac is `ffmpeg 9.0.1` without libfreetype, so sample clips are color plates plus `drawbox`, not burned-in Latin labels.

## Safety / news quality

- The reporter’s script is the source of truth for spelling and facts.
- Whisper (later) is for timing, not for rewriting the story.
- Footage selection may only use uploaded clips.
- Social titles/captions (later) must stay grounded in the script.
- The human approves the final video. There is no auto-publish.

## Next recommended step

**Milestone 3 — transcription.** Run faster-whisper on the uploaded voice-over, write `analysis/transcript.json` with word-level timestamps, then align those times to the original Bengali script without replacing the reporter’s spelling.
