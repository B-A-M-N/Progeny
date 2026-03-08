# Progeny (Bitling)

## Why This Exists

AI is becoming a core part of how kids will learn. Progeny is being built around one premise:

- children can learn faster and stay engaged longer when learning is interactive, personalized, and tied to their interests.

There are very few tools that are explicitly built for **neurodivergent kids** while also being useful for all children.  
Progeny is meant to be:

- an educational companion for any child,
- plus a practical support tool for parents of neurodivergent children (Autism/ADHD/AuDHD),
- by connecting learning goals to the child’s real interests and sensory/communication needs.

## What Progeny Is

Local-first tutor companion stack:

- `Bitling/` = Godot 4 client (character creator + overlay companion)
- `ai-companion/` = Python brain (WebSocket orchestration + memory + safety + TTS + writing server)
- `services/` = supporting local infrastructure (SearXNG, Firecrawl, Kokoro assets, optional local generator)

## Core Product Features

## 1) Tutor Avatar Creator (Godot)

- Create/regenerate/tweak a tutor avatar from natural language.
- Remote generation path (AI Horde/ArtBot style) for weaker dev hardware.
- LoRA browsing/selection flow with runnable payload mapping.
- Output preview is stored in `Bitling/assets/generated/`.

## 2) Desktop Companion Overlay

- Borderless transparent “clippy-style” always-on-top companion.
- Drag/move, context menu, chat panel, click-through pin mode.
- Reacts to backend action/speak events.

## 3) Open Brain Memory System

PostgreSQL + pgvector-backed long-term memory:

- events
- semantic knowledge
- lessons
- struggles
- XP ledger + level progression
- graph nodes/edges for related concepts

Open Brain connection status is sent in WS init and surfaced in Godot UI.

## 4) Writing Pad / Tablet Server (Important)

This is already in the stack and runs as a Flask app on port `5000`.

- Writing canvas endpoint: `/`
- Parent dashboard endpoint: `/dashboard`
- API:
  - `/api/submit_writing`
  - `/api/struggles`
  - `/api/graph_stats`

Writing flow captures stroke pressure and logs:

- effort XP
- mastery XP when regulation is good
- struggle events when pressure is too heavy/light

This is intended for stylus/tablet writing and fine-motor support.

## 5) Speech Pipeline

- Kokoro ONNX TTS primary.
- Cached audio for repeated phrases (`ai-companion/data/tts_cache/*.wav`).
- Lightweight post-processing for cleaner speech.
- Optional Piper fallback when configured.

## Current Status

### Working now

- Godot <-> brain WebSocket connection and init payload.
- Creator remote generation request path.
- LoRA browse + selection flow.
- Generated image save/load pathing.
- Overlay companion scene and interaction controls.
- Open Brain status handshake (`connected` + detail).
- Writing Pad server endpoints and persistence hooks.
- Memory logging hooks (state/perception/interaction/struggle/XP/knowledge).
- Kokoro TTS generation + local audio serving.

### Known constraints

- If PostgreSQL/pgvector is unavailable, Open Brain logging fails.
- If Firecrawl/SearXNG is down, research quality drops.
- Piper fallback only runs when `PROGENY_PIPER_MODEL` is set.
- Local SD path needs Automatic1111 API + capable hardware.

## Dependencies (Actual)

## 1) System packages (Ubuntu/Pop)

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

Also required:

- Godot 4.x (project currently run/tested with 4.3 in logs)
- Ollama
- PostgreSQL + pgvector extension

## 2) Python dependencies (`ai-companion`)

```bash
python3 -m venv ai-companion/venv
source ai-companion/venv/bin/activate
pip install --upgrade pip
pip install -r ai-companion/requirements.txt
```

Current required packages:

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

## 3) Node/PNPM (Firecrawl)

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
export PATH="$HOME/.local/share/pnpm:$PATH"
```

Then install Firecrawl deps inside `services/firecrawl` with `pnpm install`.

## 4) Required runtime services

- Redis
- PostgreSQL + pgvector
- SearXNG (`ai-companion/searxng_server`)
- Firecrawl API (`services/firecrawl/apps/api`)
- Ollama models:
  - `moondream`
  - `qwen2.5:0.5b`

## 5) Optional extras

- Automatic1111 local SD API (`http://127.0.0.1:7860`)
- Piper fallback:
  - `PROGENY_PIPER_MODEL=/absolute/path/to/model.onnx`
  - optional `PROGENY_PIPER_BIN=piper`

## Setup

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

- `PROGENY_FORCE_LOCAL=0` -> force remote generation.
- `PROGENY_FORCE_LOCAL=1` -> prefer local generation when local SD API is reachable.

## Ports

- Brain WebSocket: `9001`
- Audio HTTP server: `8000`
- Writing Pad Flask: `5000`

## STT Direction (Target Machine)

Recommended local STT path:

- `whisper.cpp` + Distil-Whisper Large v3 (or quantized medium/large variant)
