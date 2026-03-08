import hashlib
import os
import shutil
import subprocess
import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

# Monkeypatch np.load because kokoro-onnx 0.4.9 calls np.load(voices_path)
# without allow_pickle=True, which is required for object array voices format.
_original_np_load = np.load


def _patched_np_load(*args, **kwargs):
    if "allow_pickle" not in kwargs:
        kwargs["allow_pickle"] = True
    return _original_np_load(*args, **kwargs)


np.load = _patched_np_load


class TTSService:
    def __init__(self, model_path="data/assets/kokoro.onnx", voices_path="data/assets/voices.npy", output_dir="data"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.output_dir = os.path.join(project_root, output_dir)
        self.cache_dir = os.path.join(self.output_dir, "tts_cache")
        os.makedirs(self.output_dir, exist_ok=True)
        os.makedirs(self.cache_dir, exist_ok=True)

        full_repo_model = os.path.join(project_root, "../services/Kokoro-82M/kokoro.onnx")
        if os.path.exists(full_repo_model):
            self.model_path = full_repo_model
            print(f"[TTS] Using full repo model: {full_repo_model}")
        else:
            self.model_path = os.path.join(project_root, model_path)

        self.voices_path = os.path.join(project_root, voices_path)
        self.kokoro = Kokoro(self.model_path, self.voices_path)
        if isinstance(self.kokoro.voices, np.ndarray) and self.kokoro.voices.dtype == "O":
            self.kokoro.voices = self.kokoro.voices.item()

        self.voice_name = "af_sky"
        self.sample_rate_default = 24000
        self.piper_model_path = os.getenv("PROGENY_PIPER_MODEL", "").strip()
        self.piper_bin = os.getenv("PROGENY_PIPER_BIN", "piper").strip() or "piper"

    def generate(self, text, filename="response.wav", tutor_profile=None, learning_stage=1):
        if not text:
            return None

        cleaned = self._prepare_text(text)
        speed = self._compute_speed(tutor_profile=tutor_profile, learning_stage=learning_stage)
        cache_rel = self._cache_relpath(cleaned, speed, self.voice_name, learning_stage)
        cache_abs = os.path.join(self.output_dir, cache_rel)
        target_abs = os.path.join(self.output_dir, filename)
        os.makedirs(os.path.dirname(target_abs), exist_ok=True)

        if os.path.exists(cache_abs):
            if cache_abs != target_abs:
                try:
                    shutil.copy2(cache_abs, target_abs)
                except Exception:
                    pass
            return cache_rel

        samples = None
        sample_rate = self.sample_rate_default

        # Primary engine: Kokoro
        try:
            samples, sample_rate = self.kokoro.create(
                cleaned,
                voice=self.voice_name,
                speed=speed,
                lang="en-us"
            )
        except Exception as e:
            print(f"[TTS] Kokoro failed ({type(e).__name__}): {e}. Trying Piper fallback...")

        # Fallback engine: Piper
        if samples is None:
            piper_ok = self._generate_with_piper(cleaned, cache_abs)
            if piper_ok:
                if cache_abs != target_abs:
                    try:
                        shutil.copy2(cache_abs, target_abs)
                    except Exception:
                        pass
                return cache_rel
            print("[TTS] Piper fallback failed. No audio generated.")
            return None

        processed = self._post_process_audio(samples)
        sf.write(cache_abs, processed, sample_rate)
        if cache_abs != target_abs:
            try:
                shutil.copy2(cache_abs, target_abs)
            except Exception:
                pass
        return cache_rel

    def _compute_speed(self, tutor_profile=None, learning_stage=1):
        level = tutor_profile.get("level", 1) if tutor_profile else 1
        raw_speed = 0.8 + (level * 0.02)
        stage_caps = {1: 0.90, 2: 1.00, 3: 1.08}
        cap = stage_caps.get(learning_stage, 1.08)
        return min(raw_speed, cap, 1.2)

    def _prepare_text(self, text):
        cleaned = " ".join(str(text).split())
        if len(cleaned) > 600:
            cleaned = cleaned[:600].rstrip() + "..."
        # Light prosody shaping for teaching voice
        cleaned = cleaned.replace(" - ", ", ")
        cleaned = cleaned.replace(";", ". ")
        cleaned = cleaned.replace(":", ", ")
        if cleaned and cleaned[-1] not in ".!?":
            cleaned += "."
        return cleaned

    def _cache_relpath(self, text, speed, voice, stage):
        key = f"{voice}|{stage}|{speed:.3f}|{text}"
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()[:24]
        return f"tts_cache/{digest}.wav"

    def _post_process_audio(self, samples):
        arr = np.asarray(samples, dtype=np.float32)
        if arr.ndim > 1:
            arr = np.mean(arr, axis=1)
        peak = float(np.max(np.abs(arr))) if arr.size else 0.0
        if peak > 0:
            arr = arr * (0.92 / peak)
        threshold = 0.55
        ratio = 3.0
        abs_arr = np.abs(arr)
        over = abs_arr > threshold
        arr[over] = np.sign(arr[over]) * (threshold + (abs_arr[over] - threshold) / ratio)
        arr = np.clip(arr, -0.95, 0.95)
        return arr.astype(np.float32)

    def _generate_with_piper(self, text, output_path):
        if not self.piper_model_path:
            print("[TTS] PROGENY_PIPER_MODEL not set; skipping Piper fallback.")
            return False
        if not os.path.exists(self.piper_model_path):
            print(f"[TTS] Piper model not found: {self.piper_model_path}")
            return False
        cmd = [self.piper_bin, "--model", self.piper_model_path, "--output_file", output_path]
        try:
            proc = subprocess.run(
                cmd,
                input=text,
                text=True,
                capture_output=True,
                timeout=25,
                check=False
            )
            if proc.returncode != 0:
                err = (proc.stderr or "").strip()
                print(f"[TTS] Piper failed (code={proc.returncode}): {err[:240]}")
                return False
            return os.path.exists(output_path) and os.path.getsize(output_path) > 0
        except Exception as e:
            print(f"[TTS] Piper invocation error ({type(e).__name__}): {e}")
            return False


if __name__ == "__main__":
    tts = TTSService()
    print("Generating audio...")
    fname = tts.generate("Hello, I am your local AI companion. Let's learn together!")
    print(f"Generated: {fname}")
