# Progeny (Bitling)

Desktop tutor companion stack:

- `Bitling/` = Godot 4 client (Creator + overlay companion)
- `ai-companion/` = Python brain (WebSocket + agent loop + memory + TTS)
- `services/` = local infra/tooling (Firecrawl, SearXNG, Kokoro assets, optional local SD)

## What This Is Right Now

This is a **local-first tutor system** with:

- Character creation in Godot.
- Remote generation via AI Horde/ArtBot path (for low-power dev machines).
- Open Brain memory in PostgreSQL/pgvector.
- Overlay companion window (Clippy-style) after character finalize.
- Kokoro TTS with cache + lightweight post-processing + optional Piper fallback.

## Working Status (Current)

### Working

- WebSocket handshake between Godot and brain (`ws://<host>:9001`).
- Creator remote generation requests (construct/tweak over WS).
- LoRA browse and selection flow (catalog -> field -> request payload).
- Generated image save/load from `Bitling/assets/generated/`.
- Main overlay scene connection + action/speech reactions.
- Open Brain status surfaced in init payload (`connected` + detail).
- Event/knowledge/struggle/XP logging hooks wired in backend loop.
- Kokoro TTS generation and serving through local audio server.
- TTS cache (`ai-companion/data/tts_cache/*.wav`) enabled.

### Expected Constraints

- If PostgreSQL/pgvector is down, memory logging won’t work.
- If Firecrawl/SearXNG are down, research features degrade.
- If `PROGENY_PIPER_MODEL` is not set, Piper fallback is skipped.
- Local SD path requires Automatic1111 API and capable hardware.

## Full Dependencies

## 1) System Packages (Ubuntu/Pop)

```bash
sudo apt update
sudo apt install -y \
  wget git curl unzip openssl \
  python3 python3-venv \
  libgl1 libglib2.0-0 \
  redis-server \
  rustc cargo \
  git-lfs espeak-ng
```

Install Godot 4.x (project currently run with 4.3 in local logs).

## 2) Python Dependencies (`ai-companion`)

Install:

```bash
python3 -m venv ai-companion/venv
source ai-companion/venv/bin/activate
pip install --upgrade pip
pip install -r ai-companion/requirements.txt
```

Current required Python packages:

- `requests`
- `pyyaml`
- `websockets`
- `flask`
- `transitions`
- `psutil`
- `opencv-python`
- `numpy`
- `ollama`
- `fastembed`
- `pydantic`
- `json-repair`
- `kokoro-onnx`
- `soundfile`
- `pychromecast<14.0.0`
- `psycopg2-binary`
- `pgvector`

## 3) Node/PNPM Dependencies (Firecrawl)

Install PNPM:

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
export PATH="$HOME/.local/share/pnpm:$PATH"
```

Firecrawl app deps are installed inside `services/firecrawl` via `pnpm install`.

## 4) Runtime Services Needed

- Redis
- PostgreSQL + pgvector extension
- SearXNG (`ai-companion/searxng_server`)
- Firecrawl API (`services/firecrawl/apps/api`)
- Ollama with models:
  - `moondream`
  - `qwen2.5:0.5b`

## 5) TTS Assets

Kokoro model/voices are expected under repo data paths used by `TTSService`.

Optional Piper fallback env vars:

- `PROGENY_PIPER_MODEL=/absolute/path/to/piper_model.onnx`
- `PROGENY_PIPER_BIN=piper` (optional override)

## 6) Optional Local Image Generation

Automatic1111 API at:

- `http://127.0.0.1:7860` (configurable in `ai-companion/config.yaml`)

Used only when local generation is enabled and available.

## Setup Paths

## Full bootstrap

```bash
chmod +x setup_all.sh
./setup_all.sh
```

## Focused scripts

- `./setup_tutor.sh`
- `./setup_services.sh`
- `./setup_postgres_bare_metal.sh`

## Run

```bash
PROGENY_FORCE_LOCAL=0 ./run_progeny.sh
```

Mode toggles:

- `PROGENY_FORCE_LOCAL=0` => force remote generation.
- `PROGENY_FORCE_LOCAL=1` => prefer local generation when local SD API is reachable.

`run_progeny.sh` starts Redis/SearXNG/Firecrawl, then brain + Godot.

## Core Ports

- Brain WebSocket: `9001`
- Audio HTTP server: `8000`
- Writing pad Flask: `5000`
- SearXNG: local app default in `searxng_server`
- Firecrawl API: service-managed (see app config/start logs)

## Open Brain Logging (Auto)

Memory schema and logging hooks are in `ai-companion/services/memory_service.py` and used from `ai-companion/app.py`.

Auto-logged during runtime loop:

- state transitions
- perception snapshots
- interaction responses
- struggle detections
- XP events
- knowledge updates

## STT Recommendation (Target Machine)

Recommended local STT stack:

- `whisper.cpp` + Distil-Whisper Large v3 (or quantized medium/large variant)

Rationale: good quality/latency/resource balance compared with heavier full Whisper Python runtime.
