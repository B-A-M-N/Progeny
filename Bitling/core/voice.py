from kokoro_onnx import Kokoro
import sounddevice as sd
import os

class Voice:
    def __init__(self, model_path="assets/kokoro.onnx", voices_path="assets/voices.json"):
        self.kokoro = Kokoro(model_path, voices_path)
        self.voice_name = "af_sky" # A nice female voice

    def speak(self, text):
        if not text:
            return
        samples, sample_rate = self.kokoro.create(
            text, 
            voice=self.voice_name, 
            speed=1.1, 
            lang="en-us"
        )
        sd.play(samples, sample_rate)
        # We don't wait for audio to finish here so it's non-blocking for the UI
        # But for Bitling, we might want to know when it finishes if we do lip sync later
