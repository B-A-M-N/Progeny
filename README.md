# Progeny Engine (Bitling)

Local-first tutor companion with:

- Godot client: `Bitling/`
- Python brain: `ai-companion/`
- Local support services: SearXNG, Firecrawl, Redis, Postgres/pgvector, Kokoro TTS

## What Is Working Now

- Creator connects to brain over WebSocket (`:9001`).
- Remote image generation uses AI Horde / ArtBot-style API.
- LoRA browser returns Horde-runnable entries, and selected IDs are sent in generation payload.
- Generated previews are saved to `Bitling/assets/generated/tutor_preview.<ext>`.
- Main companion scene runs as a borderless, transparent desktop overlay.

## Full Dependency Setup

### System Packages (Ubuntu/Pop)

```bash
sudo apt update
sudo apt install -y \
  wget git curl unzip openssl \
  python3 python3-venv \
  libgl1 libglib2.0-0 \
  redis-server \
  rustc cargo
```

### Python Dependencies

```bash
python3 -m venv ai-companion/venv
source ai-companion/venv/bin/activate
pip install --upgrade pip
pip install -r ai-companion/requirements.txt
```

### Node/PNPM (Firecrawl)

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh -
export PATH="$HOME/.local/share/pnpm:$PATH"
```

### Required Runtime Services

- Ollama models:
  - `ollama pull moondream`
  - `ollama pull qwen2.5:0.5b`
- Redis
- PostgreSQL + `pgvector`
- SearXNG
- Firecrawl API
- Kokoro voice assets

## Setup Scripts In This Repo

- Full bootstrap: `./setup_all.sh`
- Tutor-focused setup: `./setup_tutor.sh`
- Service-only setup: `./setup_services.sh`
- Postgres setup: `./setup_postgres_bare_metal.sh`

Use executable bit first if needed:

```bash
chmod +x setup_all.sh run_progeny.sh
```

## Run

```bash
./run_progeny.sh
```

This starts Redis/SearXNG/Firecrawl, launches `ai-companion/app.py`, then opens Godot (`Bitling`).

## Generation Mode Controls

- Remote-first (recommended on low-power dev laptop):
  - `PROGENY_FORCE_LOCAL=0 ./run_progeny.sh`
- Local-only when local SD API is reachable:
  - `PROGENY_FORCE_LOCAL=1 ./run_progeny.sh`

## Creator + LoRAs

1. Open Creator.
2. Enter description and select style/model.
3. Click `Browse LoRAs` and pick entries.
4. Click `Generate` / `Regenerate`.

LoRA field formats:

- `name:weight`
- `name|id:weight` (preferred; added automatically from catalog)

Weight range is clamped to `0.0..2.0`.

## Overlay Interaction Features

- Drag-to-move avatar
- Right-click context menu (`Talk`, `Regenerate Avatar`, `Pin/Unpin click-through`, `Hide Chat`, `Quit`)
- Mini chat panel
- Click-through pin mode

## STT Path For Target Machine

Recommended local STT stack for your eventual stronger host:

- `whisper.cpp` + Distil-Whisper Large v3 (or quantized Medium/Large variant)

This gives better quality/stability than Vosk while staying lighter than full Whisper Python runtime.
