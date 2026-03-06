#!/bin/bash

# Progeny Bare Metal Service Setup
# This script installs dependencies for SearXNG and Firecrawl without Docker.

echo "--- Starting Bare Metal Service Setup ---"

# 1. Install System Dependencies (Requires sudo)
echo "[1/4] Installing system dependencies (Redis, Node, Go)..."
sudo apt-get update
sudo apt-get install -y redis-server python3-venv python3-dev build-essential libxml2-dev libxslt1-dev zlib1g-dev nodejs npm golang-go

# 2. Setup SearXNG
echo "[2/4] Setting up SearXNG..."
cd ai-companion/searxng_server
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python3 manage.py install
cd ../..

# 3. Setup Firecrawl
echo "[3/4] Setting up Firecrawl (Local Services)..."
cd firecrawl-local
# Firecrawl uses pnpm or npm
npm install
# Note: Firecrawl has multiple sub-apps (api, worker). 
# This script assumes a basic installation of the API.
cd apps/api && npm install
cd ../../..

# 4. Finalizing
echo "[4/4] Services ready."
echo "To run SearXNG: cd ai-companion/searxng_server && source venv/bin/activate && export SEARXNG_SETTINGS_PATH=./settings.yml && python3 searx/webapp.py"
echo "To run Firecrawl: cd firecrawl-local/apps/api && npm start"
echo "Make sure Redis is running: sudo service redis-server start"
