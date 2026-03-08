# Progeny (Bitling)

An AI learning companion built for real kids in real homes, not a demo.

## Why This Exists

As AI becomes more relevant to education, kids are increasingly learning *with* AI, not just from static apps.  
Progeny was created to make that useful, safe, and human-centered.

Most children’s apps are either:

- generic drill tools with no personalization, or
- “AI toys” that are flashy but not built around real developmental needs.

There are also almost no systems designed specifically for neurodivergent learners while still working for all kids.

Progeny’s purpose:

- help children learn faster by linking new skills to their actual interests,
- support neurodivergent learning needs (Autism/ADHD/AuDHD),
- give parents practical visibility into effort, struggles, and progress,
- stay local-first so families keep control of their child’s data and workflow.

## Who This Is For

- Children who learn better through interaction and character-based guidance.
- Parents who want to scaffold learning at home without guesswork.
- Neurodivergent families needing adaptable sensory/communication support.
- Builders/educators who want a customizable local tutor stack.

## Design Principles

- Interest-first: connect lessons to what the child already cares about.
- Scaffold, don’t overwhelm: small wins, clear feedback, repeatable routine.
- Local-first by default: keep core data and behaviors on-device.
- Parent visibility: progress and friction should be observable, not hidden.
- Practical over hype: if it doesn’t improve daily learning, it doesn’t ship.

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

## New: Neuroadaptive Onboarding + Live Teaching Engine

This stack now includes a trait + state + micro-signal adaptation system.

How it works:

1. Trait Layer (slow-changing baseline)
- Parent baseline is captured and mapped into a multidimensional profile (not a diagnosis preset).
- Stored in Open Brain `adaptation_profile`.

2. Session State Layer (updates every loop)
- Inferred dimensions:
  - engagement
  - cognitive_load
  - frustration
  - regulation
  - confidence
  - challenge_readiness

3. Micro-Signal Layer (fast events)
- Feeds state inference from onboarding events + writing telemetry:
  - pressure variance
  - pressure spike frequency
  - micro pauses
  - fragmentation
  - engagement duration

4. Teaching Mode Policy (live control)
- System selects one mode each cycle:
  - `advance`
  - `stabilize`
  - `repair`
  - `recover`
- Mode drives prompt style, demand level, modality, and pacing.

## New: Godot Onboarding UI

The Godot flow now routes:

`Creator -> Onboarding -> Main`

Added files:

- `Bitling/Onboarding.tscn`
- `Bitling/Onboarding.gd`

Current onboarding UI includes:

- Parent baseline capture (optional)
- Child world-building session prompt flow
- Metric events sent to backend over WS
- Parent-facing session summary + starter plan

## New: Dynamic Structured Lessons (Not Static Lessons)

Lessons are generated dynamically from live state, but emitted in a strict schema for deterministic rendering.

Lesson schema fields:

- `hook`
- `facts` (exactly 3)
- `activity`
- `media_followup`
- `adaptation_note`
- `next_probe`
- `mode`

Why this design:

- Dynamic generation keeps retention optimized to current state.
- Structured output prevents brittle UI/runtime behavior.

Backend now broadcasts `lesson_plan` packets with this schema so Godot can render sections consistently.

## New: Media + Attention Loop (Optional, Tracked)

Media tracking is now wired so watched content can be evaluated against behavior/comprehension.

Database additions:

- `media_sessions`
- `media_probes`

What is tracked:

- session metadata (`topic/title/url/start/end/watched_seconds/completed`)
- baseline vs end adaptive state
- behavior delta (`engagement/frustration/regulation`)
- post-watch probe events (`probe_type/response_mode/latency/success_score`)

This powers per-topic `media_effectiveness` and is fed back into lesson planning prompts.

## New WebSocket Messages

Onboarding + adaptation:

- `get_onboarding_script`
- `set_parent_baseline`
- `onboarding_event`
- `finish_onboarding`
- `adaptive_state` (broadcast)

Media loop:

- `start_media_session`
- `media_probe_event`
- `end_media_session`
- `get_media_insights`
- `get_media_probe_pack`

Lesson output:

- `lesson_plan` (broadcast with structured lesson object)

## New HTTP Endpoints (Writing/Tablet Server)

Onboarding:

- `POST /api/onboarding/baseline`

Media tracking:

- `POST /api/media/start`
- `POST /api/media/probe`
- `POST /api/media/end`
- `GET /api/media/insights`

Writing endpoint now also returns adaptation context:

- `POST /api/submit_writing` -> includes `metrics` + `adaptation_profile`

## Operational Notes

- If Postgres is down, adaptive profile/media/session persistence will fail.
- Godot headless check can crash on some hosts; validate scene flow with normal runtime when needed.
- Media probes are intentionally optional and low-pressure; they should never block lesson flow.
