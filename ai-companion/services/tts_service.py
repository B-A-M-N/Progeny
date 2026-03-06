import os
import soundfile as sf
import numpy as np
from kokoro_onnx import Kokoro

# Monkeypatch np.load because kokoro-onnx 0.4.9 calls np.load(voices_path)
# but doesn't set allow_pickle=True, which is required for the object array format.
original_load = np.load
def patched_load(*args, **kwargs):
    if 'allow_pickle' not in kwargs:
        kwargs['allow_pickle'] = True
    return original_load(*args, **kwargs)
np.load = patched_load

class TTSService:
    def __init__(self, model_path="data/assets/kokoro.onnx", voices_path="data/assets/voices.npy", output_dir="data"):
        # Resolve paths relative to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.model_path = os.path.join(project_root, model_path)
        self.voices_path = os.path.join(project_root, voices_path)
        self.output_dir = os.path.join(project_root, output_dir)
        
        self.kokoro = Kokoro(self.model_path, self.voices_path)
        if isinstance(self.kokoro.voices, np.ndarray) and self.kokoro.voices.dtype == 'O':
             self.kokoro.voices = self.kokoro.voices.item()
        self.voice_name = "af_sky" # Parent can change this later

    def generate(self, text, filename="response.wav"):
        if not text:
            return None
        
        filepath = os.path.join(self.output_dir, filename)
        
        samples, sample_rate = self.kokoro.create(
            text, 
            voice=self.voice_name, 
            speed=1.0, 
            lang="en-us"
        )
        
        sf.write(filepath, samples, sample_rate)
        return filename

if __name__ == "__main__":
    tts = TTSService()
    print("Generating audio...")
    fname = tts.generate("Hello, I am your local AI companion. Let's learn together!")
    print(f"Generated: {fname}")
