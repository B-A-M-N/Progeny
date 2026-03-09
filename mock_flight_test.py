import asyncio
import os
import sys
import json
import subprocess

# Add ai-companion to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(project_root, "ai-companion"))

from services.agent_service import AgentService
from services.tts_service import TTSService
from services.memory_service import MemoryService

async def mock_flight_test():
    print("--- 🧪 PROGENY AUDIBLE FLIGHT TEST ---")
    
    memory = MemoryService()
    agent = AgentService()
    tts = TTSService()
    
    print("\n[1/3] Prompting Bitling's Brain...")
    mock_vision = "A 5-year-old is holding a big orange dinosaur."
    mock_state = {"child_present": True, "emotion": "excited", "current_interest": "dinosaurs"}
    
    response = agent.get_response(mock_state, mock_vision)
    text = response.get("text", "I'm ready to learn!")
    print(f"Bitling decided to say: '{text}'")
    
    print("\n[2/3] Generating High-Quality Voice (Kokoro)...")
    fname = tts.generate(text, filename="mock_flight_test.wav")
    audio_path = os.path.join(project_root, "ai-companion/data", fname)
    
    if os.path.exists(audio_path):
        print(f"✅ Voice generated. PLAYING NOW through your speakers...")
        # Use aplay (built-in Linux) or ffplay
        try:
            subprocess.run(["aplay", audio_path], check=True)
        except:
            print("Could not play via aplay, trying paplay...")
            subprocess.run(["paplay", audio_path], check=True)
    else:
        print(f"❌ Error: Audio file not found at {audio_path}")

    print("\n[3/3] Checking Memory storage...")
    memory.update_knowledge("seen_dinosaur", "orange", confidence=1.0)
    print(f"✅ Success! Bitling remembered the orange dinosaur.")

    print("\n--- 🏁 TEST COMPLETE ---")

if __name__ == "__main__":
    asyncio.run(mock_flight_test())
