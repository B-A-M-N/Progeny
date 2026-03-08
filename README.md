# Progeny (Bitling)

Progeny is an AI learning companion built for real kids, real families, and real everyday struggles.

Implementation spec: [Bitling Runtime Architecture](docs/bitling_runtime_architecture.md)

## Our Mission

Kids are growing up in a world where AI is part of learning whether we like it or not.
The question is not "should AI exist in education".
The real question is:

- can AI help children feel capable,
- can it support curiosity without pressure,
- can it meet neurodivergent kids where they are instead of forcing them into a rigid mold?

Progeny exists to answer yes.

This is not meant to be another app that drills kids, scores them, and calls it learning.
It is meant to be a supportive companion that helps a child keep going, especially when learning gets hard.

## What We Care About

- Interest-first learning: start from what the child already loves.
- Regulated persistence over perfect correctness.
- Tiny wins, low pressure, and steady growth.
- Parent visibility without shaming or clinical coldness.
- Neurodivergent-aware support that adapts in real time.

## Who This Is For

- Children who learn best through interaction, play, and visual companionship.
- Parents who want support tools, not judgment tools.
- Neurodivergent families (Autism/ADHD/AuDHD) who need adaptable pacing and communication.
- Builders/educators who want a local-first, modifiable tutor stack.

## How Progeny Is Meant To Feel

For a child:

- "Bitling gets me."
- "I can try again without being pushed too hard."
- "Learning feels like building something together."

For a parent:

- "I can see what helps my child, what stresses them, and what restores them."
- "This supports my child’s growth without turning home into a testing center."

## Product Experience

## 1) Create A Companion

The child/family creates Bitling’s avatar and style in Godot.
This gives ownership and emotional buy-in from day one.

## 2) First Meeting (Onboarding)

The first session is designed as a relationship-building flow, not an assessment.

- Parent can optionally provide baseline context.
- Child goes through playful world-building prompts.
- Signals are collected quietly (latency, writing pressure, pauses, retries, etc.).
- The system builds an adaptive baseline from behavior patterns, not labels.

## 3) Live Neuroadaptive Teaching

Bitling continuously adapts to the child’s *current* state.
It does not only ask "what topic?" — it asks "what is this child ready for right now, and what keeps them regulated?"

Three cooperating engines run together:

- Interest Engine (motivation and topic anchoring)
- Regulation Engine (overload detection + pacing/sensory shifts)
- Learning Engine (challenge and scaffolding)

Teaching modes:

- `explore`
- `engage`
- `advance`
- `practice`
- `stabilize`
- `repair`
- `recover`
- `rest`
- `co_play`

So when overload rises, Bitling reduces demand instead of pushing harder.

## 4) Dynamic Lessons

Lessons are generated live from:

- child interests,
- recent behavior,
- current adaptive state,
- prior struggles and what helped recovery.

The content is dynamic, but internally structured so the app stays reliable.

## 5) Persistent World + Trust Growth

Bitling is not meant to feel like opening a blank worksheet every time.
It keeps a persistent world with places, companions, objects, events, and missions.
It also tracks trust stages over time:

- `safety`
- `familiarity`
- `rapport`
- `collaboration`
- `attachment`

This makes sessions feel like "welcome back to *our* world" rather than "start another task."

## 6) Writing + Fine-Motor Support

The writing pad/tablet server lets kids draw/write in a low-pressure way.
It tracks pressure/motor patterns and turns those into support signals.

This helps detect not just "can they do it," but "what made it harder" and "what helped them recover."

## 7) Media + Attention Loop

Watching content is optional, but tracked as an attention/comprehension signal.
Short post-watch probes (choice/drawing/co-play prompts) help estimate:

- comprehension,
- retention,
- regulation effect,
- whether that kind of media helps this specific child.

## What’s Working Right Now

- Creator + avatar generation flow
- Onboarding scene in Godot
- Adaptive profile persistence and live updates
- Trust-stage updates and persistent world anchors
- Dynamic lesson generation with adaptive context
- Writing telemetry feeding adaptation
- Optional media session/probe tracking
- Open Brain memory persistence (Postgres + pgvector)
- Kokoro speech with caching and fallback support

## Tech Stack (Short Version)

- Godot client (`Bitling/`)
- Python brain (`ai-companion/`)
- Postgres + pgvector memory
- SearXNG + Firecrawl research pipeline
- Ollama local models
- Kokoro ONNX speech

## Dependencies

System packages (Ubuntu/Pop):

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

Python setup:

```bash
python3 -m venv ai-companion/venv
source ai-companion/venv/bin/activate
pip install --upgrade pip
pip install -r ai-companion/requirements.txt
```

Node/PNPM (Firecrawl):

```bash
curl -fsSL https://get.pnpm.io/install.sh | sh
export PATH="$HOME/.local/share/pnpm:$PATH"
```

Also required:

- Godot 4.x
- Ollama (`moondream`, `qwen2.5:0.5b`)
- PostgreSQL + pgvector
- Redis
- SearXNG
- Firecrawl API

Optional:

- Automatic1111 local SD API
- Piper fallback (`PROGENY_PIPER_MODEL`, `PROGENY_PIPER_BIN`)

## Setup & Run

Setup:

```bash
chmod +x setup_all.sh
./setup_all.sh
```

Run:

```bash
PROGENY_FORCE_LOCAL=0 ./run_progeny.sh
```

## STT Direction (Target Machine)

Recommended local STT path:

- `whisper.cpp` + Distil-Whisper Large v3 (or quantized medium/large variant)
