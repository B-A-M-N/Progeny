# Bitling Runtime Architecture (Local-First)

This document turns Progeny's mission into a concrete runtime architecture.

## Goals

- Keep children regulated and curious, not pressured.
- Preserve autonomy and trust while still progressing skills.
- Keep memory/state durable in DB, not trapped in model context.

## System Components

```text
Godot Client (Bitling UI)
  - avatar/world rendering
  - writing pad + UI telemetry
  - camera/mic capture
  - websocket bridge to brain

Python Brain (Session Orchestrator)
  - turn manager + demand shaping
  - 3-engine adaptive loop
  - trust/world state transitions
  - lesson + probe orchestration

Inference Workers
  - STT (whisper.cpp target path)
  - TTS (Kokoro)
  - LLM roles (playmate/researcher/state_extractor)
  - vision cues

Memory Layer
  - Postgres (canonical truth)
  - pgvector (semantic retrieval)
  - graph memory (interest/regulation/world relationships)

Research Layer
  - SearXNG search
  - Firecrawl extraction
```

## Adaptive Control Model

The orchestrator runs three cooperating engines:

1. Interest Engine: topic anchoring and novelty.
2. Regulation Engine: overload/strain detection.
3. Learning Engine: pacing, challenge, and scaffolding.

Trust and world continuity are persistent cross-cutting systems:

- Trust stages: `safety`, `familiarity`, `rapport`, `collaboration`, `attachment`
- World anchors: location, companions, objects, events, missions.

## Runtime Loop

Cadence:

- `1-2s`: ingest signals (`onboarding_event`, writing telemetry, probe events, regulation signals)
- `5-10s`: infer live state and escalation profile
- `10-20s`: pick mode/policy and render response

Internal modes:

- `explore`, `engage`, `advance`, `practice`, `stabilize`, `repair`, `recover`, `rest`, `co_play`

## WebSocket Contract (current + required)

Client -> Brain:

- `get_onboarding_script`
- `set_parent_baseline`
- `onboarding_event`
- `finish_onboarding`
- `start_media_session`
- `media_probe_event`
- `end_media_session`
- `get_media_insights`
- `get_media_probe_pack`
- `regulation_signal`
- `get_world_state`
- `get_writing_pad_url`
- `world_action`

Brain -> Client:

- `init`
- `onboarding_script`
- `onboarding_profile_updated`
- `onboarding_runtime_update`
- `onboarding_summary`
- `media_session_started`
- `media_probe_recorded`
- `media_session_ended`
- `media_insights`
- `media_probe_pack`
- `adaptive_state`
- `trust_stage_update`
- `world_state`
- `writing_pad_info`
- `lesson_plan`
- `speak`

Writing pad convenience:

- `init` includes `writing_pad_url` and `writing_pad_qr_url`
- `world_state` includes `writing_pad_url` and `writing_pad_qr_url`
- Writing server QR endpoint: `/api/writing/qr?target=<url>`

Schema files (source of truth for inbound message validation):

- `ai-companion/contracts/ws/*.schema.json`
- Runtime validator: `ai-companion/utils/ws_contracts.py`

## Canonical Event Shapes

### `onboarding_event`

```json
{
  "type": "onboarding_event",
  "session_id": "first_run",
  "event": {
    "metric_key": "latency_to_choice",
    "metric_value": 1.8,
    "metadata": {
      "step": 2,
      "signals": {
        "response_latency_spike": 0.35
      }
    }
  }
}
```

### `regulation_signal`

```json
{
  "type": "regulation_signal",
  "signals": {
    "movement_acceleration": 0.62,
    "micro_frustration": 0.54,
    "silence_withdrawal": 0.28
  }
}
```

### `world_action`

```json
{
  "type": "world_action",
  "action": "collect_item",
  "payload": {
    "item": "space_crystal",
    "quantity": 1
  }
}
```

### `adaptive_state` payload

```json
{
  "type": "adaptive_state",
  "state": {
    "engagement": "steady",
    "cognitive_load": "workable",
    "frustration": "mild",
    "regulation": "wobbling",
    "challenge_readiness": "hold_steady",
    "escalation_score": 0.31,
    "escalation_band": "rising",
    "phase": "engage",
    "trust_stage": "rapport",
    "trust_score": 0.58
  },
  "policy": {
    "mode": "stabilize",
    "prompt_style": "co_play",
    "prompt_length": "short",
    "sensory_density": "moderate",
    "task_granularity": "small_steps",
    "modality": "current"
  },
  "world_anchor": {
    "location": "space_station",
    "companions": ["bitling", "dragon_helper"]
  }
}
```

## Data Ownership Rules

- Postgres is source-of-truth for profiles, sessions, events, probes, and world/trust state.
- Model context is ephemeral; never rely on it for continuity.
- Only orchestrator emits child-facing actions; workers do not directly talk to child UI.

## Rollout Phases

1. Stability pass: WS reliability, mode transitions, trust/world updates.
2. Sensor pass: richer writing + voice + camera signal normalization.
3. Learning pass: lesson/probe effectiveness feedback into planning.
4. Parent pass: clear insight summaries and controls/guardrails.

## Acceptance Criteria

- Child can return and receive world-aware greeting + continuity.
- Adaptive mode changes when escalation rises (without forcing tasks).
- Lessons reflect current mode and world anchor.
- Media probe results influence subsequent lesson shaping.
- Trust stage changes are visible and persisted.
