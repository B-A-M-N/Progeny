#!/bin/bash
PROJECT_ROOT=$(pwd)
echo "--- Progeny Launcher (Bare Metal) ---"

# 1. Start Redis (Critical for SearXNG/Firecrawl)
if ! pgrep -x "redis-server" > /dev/null; then
    echo "Starting Redis..."
    sudo service redis-server start
fi

# 2. Start SearXNG
echo "Starting SearXNG..."
cd ai-companion/searxng_server
source venv/bin/activate
export SEARXNG_SETTINGS_PATH=$PROJECT_ROOT/ai-companion/searxng_server/settings.yml
python3 searx/webapp.py > ../../searxng.log 2>&1 &
deactivate
cd "$PROJECT_ROOT"

# 3. Start Firecrawl (Simplified launch)
echo "Starting Firecrawl..."
cd services/firecrawl/apps/api
npm start > ../../../../firecrawl.log 2>&1 &
cd "$PROJECT_ROOT"

echo "Cleaning up old Progeny processes..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8765/tcp 2>/dev/null || true
fuser -k 5000/tcp 2>/dev/null || true

echo "Starting Bitling Brain..."
source ai-companion/venv/bin/activate
PYTHONUNBUFFERED=1 python3 -u ai-companion/app.py > mind.log 2>&1 &
godot --path Bitling
