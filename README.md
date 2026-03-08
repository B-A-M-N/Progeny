# Progeny Engine (Bitling)

Local-first tutor companion with a Godot desktop avatar (`Bitling/`) and a Python brain (`ai-companion/`).

## Current Generation Pipeline

- `Creator` uses WebSocket to `ai-companion` on port `9001`.
- Remote image generation uses AI Horde / ArtBot-compatible API.
- LoRA browser returns Horde-runnable LoRAs only (from Horde default list + metadata).
- Generated preview is saved to `Bitling/assets/generated/tutor_preview.<ext>`.
- On low-power dev machines, keep remote generation enabled.

## Run

```bash
./run_progeny.sh
```

This launcher starts supporting services and launches the Godot client.

## Generation Mode Controls

- `PROGENY_FORCE_LOCAL=0 ./run_progeny.sh`
  - Forces remote generation path.
- `PROGENY_FORCE_LOCAL=1 ./run_progeny.sh`
  - Forces local generation only when local SD API is reachable.

## Creator Usage (Remote + LoRAs)

1. Open Creator.
2. Enter description and style/model.
3. Click `Browse LoRAs` and select entries.
4. Click `Generate` or `Regenerate`.

LoRA text format supports:

- `name:weight`
- `name|id:weight` (preferred when selected from catalog)

Weights are clamped to `[0.0, 2.0]`.

## Overlay / Desktop Companion

Main scene is configured as a borderless, transparent, always-on-top overlay.

Implemented interaction features:

- Drag avatar window.
- Right-click menu (`Talk`, `Regenerate Avatar`, `Pin/Unpin click-through`, `Hide Chat`, `Quit`).
- Mini chat panel.
- Click-through toggle.

## Dependencies

Install Python deps:

```bash
pip install -r ai-companion/requirements.txt
```

Key runtime deps include: `websockets`, `flask`, `requests`, `ollama`, `opencv-python`, `numpy`, `kokoro-onnx`, `psycopg2-binary`, `pgvector`.

## STT Recommendation For Target Machine

For local STT on the future stronger machine:

- `whisper.cpp` + Distil-Whisper large-v3 (or quantized medium/large variant)

This keeps better accuracy/stability than Vosk while staying lighter than the full Whisper Python stack.
