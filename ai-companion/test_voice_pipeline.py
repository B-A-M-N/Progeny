import time
import os
import yaml
from utils.local_server import LocalAudioServer
from services.tts_service import TTSService
from services.cast_service import CastService

def load_config(path="config.yaml"):
    project_root = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(project_root, path)
    if os.path.exists(full_path):
        with open(full_path, 'r') as f:
            return yaml.safe_load(f)
    return {}

def test_pipeline():
    config = load_config()
    host_ip = config.get('cast', {}).get('host_ip', '10.9.66.93')
    
    print(f"Testing pipeline with Cast IP: {host_ip}")

    # 1. Start the HTTP server
    print("Step 1: Starting local audio server...")
    server = LocalAudioServer(port=8000, directory="data")
    server.start()
    
    try:
        # 2. Generate the TTS audio
        print("Step 2: Generating speech...")
        tts = TTSService()
        filename = tts.generate("Hello! This is a test of the Progeny voice pipeline. If you hear this, the system is working.")
        
        if not filename:
            print("TTS generation failed.")
            return

        # 3. Get the URL
        url = server.get_url(filename)
        print(f"Audio available at: {url}")

        # 4. Cast it to the Home Mini
        print("Step 3: Casting to Google Home Mini...")
        caster = CastService(host=host_ip)
        if caster.play_audio(url):
            print("SUCCESS: Pipeline test complete.")
            time.sleep(10)
        else:
            print("FAILURE: Casting failed.")

    finally:
        print("Cleaning up...")
        server.stop()

if __name__ == "__main__":
    test_pipeline()
