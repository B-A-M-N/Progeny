#!/bin/bash

# Progeny LoRA Autodetect & Downloader
# Automatically finds your LoRA directory and downloads high-quality children's content styles.

echo "--- Searching for Stable Diffusion LoRA directory ---"

POSSIBLE_PATHS=(
    "/home/bamn/Progeny/services/generator/models/Lora"
    "/home/bamn/stable-diffusion-webui/models/Lora"
    "$HOME/stable-diffusion-webui/models/Lora"
    "$HOME/sd-webui/models/Lora"
)

LORA_DIR=""
for path in "${POSSIBLE_PATHS[@]}"; do
    PARENT_DIR=$(dirname "$path")
    if [ -d "$PARENT_DIR" ]; then
        LORA_DIR="$path"
        mkdir -p "$LORA_DIR"
        echo "Found LoRA target: $LORA_DIR"
        break
    fi
done

if [ -z "$LORA_DIR" ]; then
    echo "Error: Could not find a Stable Diffusion 'models' folder."
    exit 1
fi

echo "--- Starting Downloads (Children's Content Bundle) ---"

# 1. PIXAR 3D
echo "[1/8] Pixar 3D Style..."
wget -q --show-progress -O "$LORA_DIR/pixar_style_sdxl.safetensors" "https://huggingface.co/animte/pixar-sdxl-lora/resolve/main/pixar_style_sdxl.safetensors"

# 2. STUDIO GHIBLI
echo "[2/8] Studio Ghibli Style..."
wget -q --show-progress -O "$LORA_DIR/ghibli_style_sdxl.safetensors" "https://huggingface.co/Kontext-Style/Ghibli_lora/resolve/main/ghibli_style_sdxl.safetensors"

# 3. WATERCOLOR
echo "[3/8] Watercolor Storybook..."
wget -q --show-progress -O "$LORA_DIR/watercolor_style_sdxl.safetensors" "https://huggingface.co/op74185/watercolor-illustration/resolve/main/watercolor_style_sdxl.safetensors"

# 4. CLAYMATION
echo "[4/8] Claymation Style..."
wget -q --show-progress -O "$LORA_DIR/claymation_style_sdxl.safetensors" "https://huggingface.co/bghira/SDXL-Claymation-Style/resolve/main/claymation_style_sdxl.safetensors"

# 5. LEGO (SDXL)
echo "[5/8] LEGO / Plastic Brick Style..."
wget -q --show-progress -O "$LORA_DIR/lego_style_sdxl.safetensors" "https://huggingface.co/lordjia/lelo-lego-lora-for-xl-sd1-5/resolve/main/lelo-lego-style-for-xl.safetensors"

# 6. AMIGURUMI (Crochet/Plush)
echo "[6/8] Amigurumi / Yarn Style..."
wget -q --show-progress -O "$LORA_DIR/amigurumi_style_sdxl.safetensors" "https://huggingface.co/artificialguybr/amigurami-redmond-amigurami-crochet-sd-xl-lora/resolve/main/AmigurumiRedmond-Amigurumi-AmigurumiCrochet.safetensors"

# 7. CRAYON DRAWING
echo "[7/8] Child's Crayon Drawing Style..."
wget -q --show-progress -O "$LORA_DIR/crayon_style_sdxl.safetensors" "https://huggingface.co/artificialguybr/crayon-drawing-redmond-child-crayon-style-lora-for-sdxl/resolve/main/CrayonDrawingRedmond-Crayon-CrayonDrawing.safetensors"

# 8. DISNEY 3D (PonyXL Version - Needs Pony Base Model)
echo "[8/8] Disney 3D Style (PonyXL compatible)..."
wget -q --show-progress -O "$LORA_DIR/disney_style_ponyxl.safetensors" "https://huggingface.co/hhks/PonyXL_Styles_Backup/resolve/main/3Danimation_Disney_1.0/3Danimation_Disney_1.0.safetensors"

echo ""
echo "--- All LoRAs Downloaded to $LORA_DIR ---"
