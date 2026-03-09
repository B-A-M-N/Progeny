import os
import sys
import json
import torch
import numpy as np

# Add ai-companion to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "ai-companion"))

def sync_voices():
    print("--- 🔄 BITLING VOICE SYNC ---")
    
    # Paths
    voices_dir = os.path.join(project_root, "services/Kokoro-82M/voices")
    target_json = os.path.join(project_root, "ai-companion/data/assets/voices.json")
    target_npy = os.path.join(project_root, "ai-companion/data/assets/voices.npy")
    
    if not os.path.exists(voices_dir):
        print(f"❌ Error: Source voices directory not found at {voices_dir}")
        return

    all_voices = {}
    print(f"Scanning {voices_dir} for new personalities...")
    
    for filename in os.listdir(voices_dir):
        if filename.endswith(".pt"):
            voice_id = filename.replace(".pt", "")
            try:
                # Load the PyTorch tensor (weights_only=True for security)
                weights = torch.load(os.path.join(voices_dir, filename), weights_only=True)
                # Convert to numpy for the ONNX engine
                if isinstance(weights, torch.Tensor):
                    all_voices[voice_id] = weights.cpu().numpy()
                else:
                    all_voices[voice_id] = weights
                print(f"  + Added: {voice_id}")
            except Exception as e:
                print(f"  ! Skipped {voice_id}: {e}")

    if all_voices:
        # Save as NPY (The format Bitling's engine prefers for speed)
        np.save(target_npy, all_voices)
        
        # Also update the JSON for human reading/debugging
        # (Converting numpy arrays back to lists for JSON)
        json_friendly = {k: v.tolist() if isinstance(v, np.ndarray) else v for k, v in all_voices.items()}
        with open(target_json, 'w') as f:
            json.dump(json_friendly, f)
            
        print(f"\n✅ SUCCESS! {len(all_voices)} voices are now available to Bitling.")
        print(f"Updated: {target_npy}")
    else:
        print("❌ No voices found to sync.")

if __name__ == "__main__":
    sync_voices()
