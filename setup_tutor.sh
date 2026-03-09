#!/bin/bash
# Progeny Interactive Tutor - Core Setup Script
echo "--- Starting Progeny Core Setup ---"

# 1. Python Backend Dependencies
echo "[1/3] Installing Python dependencies..."
cd ai-companion
pip install -r requirements.txt
pip install websockets requests
cd ..

# 2. Godot Addon Verification
echo "[2/3] Verifying Godot AI Horde Addon..."
if [ ! -d "Bitling/godot_client/addons/stable_horde_client" ]; then
    mkdir -p Bitling/godot_client/addons
    cd Bitling/godot_client/addons
    wget https://github.com/Haidra-Org/AI-Horde-Godot-Addon/archive/refs/heads/main.zip -O addon.zip
    unzip addon.zip
    mv AI-Horde-Godot-Addon-main/addons/stable_horde_client .
    rm -rf AI-Horde-Godot-Addon-main addon.zip
    cd ../../../
    echo "Addon installed."
else
    echo "Addon already present."
fi

# 3. Environment Check
echo "[3/3] Checking API Keys..."
if grep -q "GEMINI_API_KEY" ~/.bashrc; then
    echo "GEMINI_API_KEY found in .bashrc"
else
    echo "WARNING: GEMINI_API_KEY not found in .bashrc. Please add it for generative features."
fi

echo "--- Core Setup Complete! ---"
echo "To start the tutor:"
echo "1. Run: python3 ai-companion/app.py"
echo "2. Run: godot --path Bitling/godot_client"
