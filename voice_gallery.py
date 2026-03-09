import os
import sys
import subprocess
import json

# Add ai-companion to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "ai-companion"))

from services.tts_service import TTSService

def play_audio(path):
    try:
        subprocess.run(["aplay", path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except:
        subprocess.run(["paplay", path], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def interactive_gallery():
    print("--- 🎹 THE BITLING VOICE JUKEBOX ---")
    tts = TTSService()
    
    voices_json_path = os.path.join(project_root, "ai-companion/data/assets/voices.json")
    try:
        with open(voices_json_path, 'r') as f:
            all_voices = json.load(f)
            voice_list = sorted(all_voices.keys())
    except:
        print("❌ Sync voices first!")
        return

    print(f"\nAVAILABLE VOICES ({len(voice_list)}):")
    # Print in columns for readability
    for i in range(0, len(voice_list), 4):
        print("{:<20} {:<20} {:<20} {:<20}".format(*voice_list[i:i+4] + [""]*(4-len(voice_list[i:i+4]))))

    print("\n--- INSTRUCTIONS ---")
    print("Type a voice name to hear it, or 'exit' to quit.")
    
    while True:
        choice = input("\nVoice Name > ").strip().lower()
        if choice == 'exit': break
        
        if choice in voice_list:
            print(f"Playing {choice}...")
            tts.voice_name = choice
            fname = tts.generate("I am Bitling! How do I sound in this voice?", filename=f"test_{choice}.wav")
            play_audio(os.path.join(project_root, "ai-companion/data", fname))
        else:
            print(f"'{choice}' not found. Check the list above!")

if __name__ == "__main__":
    interactive_gallery()
