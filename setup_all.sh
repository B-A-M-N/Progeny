#!/bin/bash
# Progeny Unified Project Setup - Fully Automated & Resilient
set -e

PROJECT_ROOT=$(pwd)
echo "--- Initializing Progeny Project Stack in $PROJECT_ROOT ---"

# 1. System Dependencies (Requires Sudo)
echo "[1/9] Installing system libraries..."
sudo apt update
sudo apt install wget git python3 python3-venv libgl1 libglib2.0-0 unzip git-lfs espeak-ng curl rustc cargo redis-server openssl -y

# 2. Node.js & PNPM (For Firecrawl)
if ! command -v pnpm &> /dev/null; then
    echo "[2/9] Installing pnpm..."
    curl -fsSL https://get.pnpm.io/install.sh | sh -
    export PATH="$HOME/.local/share/pnpm:$PATH"
else
    echo "[2/9] pnpm already installed."
fi

# 3. Python Backend Environment
echo "[3/9] Setting up internal Python environment..."
cd ai-companion
[ ! -d "venv" ] && python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install websockets requests torch pollinations
deactivate
cd "$PROJECT_ROOT"

# 4. Firecrawl Submodule & Dependencies
echo "[4/9] Setting up Firecrawl submodule and Node dependencies..."
if [ ! -d "services/firecrawl/.git" ]; then
    mkdir -p services
    if ! git submodule status services/firecrawl >/dev/null 2>&1; then
        git submodule add https://github.com/B-A-M-N/firecrawl-local services/firecrawl
    fi
    git submodule update --init --recursive services/firecrawl
fi

cd services/firecrawl
if [ -f "pnpm-lock.yaml" ]; then
    pnpm install --ignore-scripts=false
fi

# Enable new high-reliability flags for the updated Firecrawl V2 bridge
touch apps/api/.env
echo "PDF_RUST_EXTRACT_ENABLE=true" >> apps/api/.env
echo "PDF_SHADOW_COMPARISON_ENABLE=true" >> apps/api/.env
echo "SELF_HOSTED=true" >> apps/api/.env

if [ -d "apps/playwright-service-ts" ]; then
    cd apps/playwright-service-ts
    pnpm install --ignore-scripts=false
    # Ensure all system dependencies for Playwright are met
    npx playwright install-deps
    npx playwright install --with-deps
    cd ../..
fi
cd "$PROJECT_ROOT"

# 5. SearXNG (Local Search Engine)
echo "[5/9] Setting up SearXNG (Local Search Engine)..."
if [ ! -d "ai-companion/searxng_server" ]; then
    cd ai-companion
    git clone https://github.com/searxng/searxng searxng_server
    cd searxng_server
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    cp searx/settings.yml settings.yml
    sed -i "s/secret_key: \"\"/secret_key: \"$(openssl rand -hex 16)\"/" settings.yml
    deactivate
    cd "$PROJECT_ROOT"
else
    echo "SearXNG already exists."
fi

# 6. Kokoro-82M Code & Weights
echo "[6/9] Integrating Kokoro TTS codebase and weights..."
mkdir -p services
if [ ! -d "services/kokoro-code" ]; then
    cd services
    git clone https://github.com/hexgrad/kokoro kokoro-code
    git clone https://huggingface.co/hexgrad/Kokoro-82M kokoro-weights
    cd "$PROJECT_ROOT"
else
    echo "Kokoro already exists."
fi

# 7. Local Generator (Stable Diffusion)
echo "[7/9] Setting up local image generator..."
if [ ! -d "services/generator" ]; then
    cd services
    git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git generator
    cd generator
    cat <<EOF > start_internal.sh
#!/bin/bash
# Optimized for 4GB VRAM 1050 Ti + 64GB System RAM
./webui.sh --lowvram --xformers --opt-split-attention --api --skip-torch-cuda-test --precision full --no-half --listen --port 7860
EOF
    chmod +x start_internal.sh
    cd "$PROJECT_ROOT"
fi

# 8. PostgreSQL Database (Bare Metal)
echo "[8/9] Setting up PostgreSQL and pgvector..."
chmod +x setup_postgres_bare_metal.sh
./setup_postgres_bare_metal.sh

# 9. Final Open Brain & Launcher Prep
echo "[9/9] Finalizing Open Brain and Launcher..."
mkdir -p .gemini_security
touch .gemini_security/second_brain.db
chmod 666 .gemini_security/second_brain.db

cat <<EOF > run_progeny.sh
#!/bin/bash
PROJECT_ROOT=\$(pwd)
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
export SEARXNG_SETTINGS_PATH=\$PROJECT_ROOT/ai-companion/searxng_server/settings.yml
python3 searx/webapp.py > ../../searxng.log 2>&1 &
deactivate
cd "\$PROJECT_ROOT"

# 3. Start Firecrawl (Simplified launch)
echo "Starting Firecrawl..."
cd services/firecrawl/apps/api
npm start > ../../../../firecrawl.log 2>&1 &
cd "\$PROJECT_ROOT"

echo "Cleaning up old Progeny processes..."
fuser -k 8000/tcp 2>/dev/null || true
fuser -k 8765/tcp 2>/dev/null || true

echo "Starting Bitling Brain..."
source ai-companion/venv/bin/activate
python3 ai-companion/app.py > mind.log 2>&1 &
godot --path Bitling
EOF
chmod +x run_progeny.sh

echo "--- Setup Complete! Everything is ready. ---"
echo "Use ./run_progeny.sh to start Bitling."
