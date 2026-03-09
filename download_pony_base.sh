#!/bin/bash

# Progeny PonyXL Base Model Downloader
# Hardware Note: You have an R9 5900 (Excellent) but a 1050 Ti (4GB VRAM).
# This script downloads the PRUNED version to save space and help with VRAM.

MODEL_DIR="/home/bamn/Progeny/services/generator/models/Stable-diffusion"
mkdir -p "$MODEL_DIR"

echo "--- Starting PonyXL Base Model Download ---"
echo "Target: $MODEL_DIR"
echo "Note: PonyXL is ~6.5GB. With a 1050 Ti, you MUST use --lowvram in your WebUI args."

# Pony Diffusion V6 XL (Pruned Version)
wget -q --show-progress -O "$MODEL_DIR/ponyDiffusionV6XL_v6StartWithThisOne.safetensors" "https://huggingface.co/Linaqruf/pony-diffusion-v6-xl/resolve/main/ponyDiffusionV6XL_v6StartWithThisOne.safetensors"

echo ""
echo "--- Download Complete! ---"
echo "To run this on your 1050 Ti, make sure your launch command includes: --lowvram --xformers"
