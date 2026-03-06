# Progeny Engine: Local AI Educational Companion

**⚠️ VERY EXPERIMENTAL ⚠️**
**Note: This is a side project because I'm a dad!**

The **Progeny Engine** is a local-first, agentic AI designed for early childhood cognitive scaffolding. It uses visual perception, semantic memory, and autonomous research to guide a child's learning based on their intrinsic interests.

## Features
- **Semantic Memory (FastEmbed):** Vector-based "Open Brain" to track child interactions.
- **Autonomous Lesson Planner:** Deep research via Firecrawl/SearXNG with Cross-Encoder reranking.
- **Struggle Logging:** Proactively identifies and logs developmental difficulties.
- **Privacy-First:** All data, including vision and voice, is processed locally.

## Prerequisite: Hardware & Host Services

### 1. Ollama (Host Machine)
You must have [Ollama](https://ollama.com/) installed and running. Pull the required models:
```bash
ollama pull moondream   # Vision model
ollama pull qwen2.5:0.5b # Agent/Logic model
```

### 2. Redis (Host Machine)
SearXNG and Firecrawl require a local Redis server.
```bash
sudo apt-get install redis-server
sudo service redis-server start
```

## Installation (Bare Metal)

### 1. Setup Support Services
This script will initialize the local SearXNG (`ai-companion/searxng_server/`) and Firecrawl (`firecrawl-local/`) instances from their source.
```bash
chmod +x setup_services.sh
./setup_services.sh
```

### 2. Setup Progeny Engine
```bash
cd ai-companion
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## Running the System

To run the full suite without Docker, you will need to start three processes:

1.  **SearXNG:**
    ```bash
    cd ai-companion/searxng_server && source venv/bin/activate && export SEARXNG_SETTINGS_PATH=./settings.yml && python3 searx/webapp.py
    ```
2.  **Firecrawl API:**
    ```bash
    cd firecrawl-local/apps/api && npm start
    ```
3.  **Progeny Engine:**
    ```bash
    cd ai-companion && source venv/bin/activate && python3 app.py
    ```

## Architecture
- **State Machine:** Manages the cycle of Perceive -> Decide -> Research -> Speak.
- **Open Brain:** SQLite-backed vector storage for knowledge and struggles.
- **Cognitive Scaffolding:** Rule-based and LLM-guided interaction logic.

## Safety & Privacy
- **Strict Controls:** Blocks topics defined in `config.yaml`.
- **Local-Only:** No data is sent to external clouds (Ollama, Firecrawl, and SearXNG all run locally).
