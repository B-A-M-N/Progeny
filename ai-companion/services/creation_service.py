import os
import json
import base64
import time
import imghdr
import ollama
import requests

class CreationService:
    def __init__(self, config, agent_model="qwen2.5:0.5b"):
        self.config = config
        self.agent_model = agent_model
        app_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))  # .../ai-companion
        repo_root = os.path.dirname(app_root)  # .../Progeny
        self.repo_root = repo_root
        self.output_dir = os.path.join(repo_root, "Bitling/assets/generated")
        os.makedirs(self.output_dir, exist_ok=True)
        
        self.local_api_url = self.config.get('generation', {}).get('local_api_url', "http://127.0.0.1:7860")
        self.horde_default_loras_url = "https://raw.githubusercontent.com/Haidra-Org/AI-Horde-image-model-reference/main/lora.json"

    def is_local_available(self):
        """Checks if a local SD API (like Automatic1111) is reachable."""
        try:
            # Check for standard WebUI API endpoint
            response = requests.get(f"{self.local_api_url}/sdapi/v1/options", timeout=2)
            return response.status_code == 200
        except:
            return False

    def refine_description(self, child_description):
        """Turns a kid's simple description into a professional artistic prompt."""
        style = self.config.get('generation', {}).get('style_preset', '3d-render')
        prompt = (
            f"The child wants a tutor that looks like: '{child_description}'.\n"
            f"STYLE PRESET: {style}\n"
            "TASK: Create a detailed artistic prompt for a character generator. "
            "The character should be: Friendly, high-quality, clear silhouette, centered, on a solid white background. "
            "Return ONLY the refined prompt text."
        )
        
        try:
            response = ollama.generate(model=self.agent_model, prompt=prompt, stream=False)
            return response['response'].strip()
        except Exception as e:
            print(f"[CreationService] Error refining prompt: {e}")
            return f"A friendly character based on {child_description}, high quality."

    def generate_local(self, prompt, use_upscale=True):
        # ... (existing code)
        return self._send_sd_request(prompt, use_upscale=use_upscale)

    def generate_remote(self, description, style, model="turbo", width=384, height=384, enhance_prompt=False, seed="", loras=None):
        """Remote generation via ArtBot/AI Horde."""
        base_description = description
        if enhance_prompt:
            try:
                base_description = self.refine_description(description)
            except Exception:
                base_description = description

        prompt = (
            f"{style} of a friendly character, {base_description}, "
            "full body, centered, standing, white background, high quality, 3D render"
        )
        api_key = self.config.get("generation", {}).get("horde_api_key", "0000000000")
        submit_url = "https://aihorde.net/api/v2/generate/async"
        headers = {
            "apikey": api_key,
            "Client-Agent": "progeny:0.1:github.com/bamn/Progeny",
            "accept": "application/json",
            "content-type": "application/json"
        }
        params = {
            "width": int(width),
            "height": int(height),
            "steps": 20 if model == "turbo" else 28,
            "cfg_scale": 7,
            "sampler_name": "k_euler_a",
            "n": 1
        }
        if seed:
            params["seed"] = str(seed)
        clean_loras = self._sanitize_horde_loras(loras or [])
        if clean_loras:
            params["loras"] = clean_loras

        payload = {
            "prompt": prompt,
            "params": params,
            "nsfw": False,
            "censor_nsfw": True,
            "trusted_workers": False,
            "r2": True
        }
        print(f"[CreationService] ArtBot/Horde request submitted. model={model} loras={len(clean_loras)} seed={'set' if seed else 'auto'} enhance={enhance_prompt}")

        try:
            submit = requests.post(
                submit_url,
                json=payload,
                headers=headers,
                timeout=(8, 30)
            )
            submit.raise_for_status()
            req_id = submit.json().get("id")
            if not req_id:
                print(f"[CreationService] ArtBot/Horde missing request id: {submit.text[:220]}")
                return None

            check_url = f"https://aihorde.net/api/v2/generate/check/{req_id}"
            status_url = f"https://aihorde.net/api/v2/generate/status/{req_id}"

            deadline = time.time() + 120
            while time.time() < deadline:
                chk = requests.get(check_url, headers=headers, timeout=(8, 20))
                chk.raise_for_status()
                cj = chk.json()
                if cj.get("faulted"):
                    print(f"[CreationService] ArtBot/Horde faulted: {str(cj)[:220]}")
                    return None
                if cj.get("done"):
                    break
                time.sleep(2)
            else:
                print("[CreationService] ArtBot/Horde timed out waiting for generation.")
                return None

            st = requests.get(status_url, headers=headers, timeout=(8, 20))
            st.raise_for_status()
            sj = st.json()
            gens = sj.get("generations") or []
            if not gens:
                print(f"[CreationService] ArtBot/Horde no generations: {str(sj)[:220]}")
                return None

            image_ref = gens[0].get("img") or gens[0].get("image")
            if not image_ref:
                print(f"[CreationService] ArtBot/Horde generation missing img: {str(gens[0])[:220]}")
                return None

            image_bytes = self._load_image_ref_bytes(image_ref)
            if not image_bytes:
                print("[CreationService] ArtBot/Horde image fetch/decode failed.")
                return None

            return self._write_generated_image(image_bytes)
        except Exception as e:
            print(f"[CreationService] ArtBot/Horde failed ({type(e).__name__}): {e}")
            return None

    # Backward-compat shim for old call sites.
    def generate_pollinations(self, description, style, model="turbo", width=384, height=384):
        return self.generate_remote(description, style, model=model, width=width, height=height)

    def _sanitize_horde_loras(self, loras):
        out = []
        for item in loras:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).strip()
            if not name:
                continue
            try:
                model_w = float(item.get("model", 0.8))
            except Exception:
                model_w = 0.8
            try:
                clip_w = float(item.get("clip", 1.0))
            except Exception:
                clip_w = 1.0
            payload = {
                "name": name,
                "model": max(0.0, min(2.0, model_w)),
                "clip": max(0.0, min(2.0, clip_w))
            }
            lora_id = str(item.get("id", "")).strip()
            if lora_id:
                payload["id"] = lora_id
            out.append(payload)
        return out

    def list_remote_loras(self, query="", limit=30):
        """Fetches Horde-runnable LoRAs only (Horde default allowlist + Civitai metadata)."""
        q = (query or "").strip()
        lim = max(1, min(int(limit or 30), 100))
        try:
            ids_resp = requests.get(self.horde_default_loras_url, timeout=(8, 20))
            ids_resp.raise_for_status()
            raw_ids = ids_resp.json()
            id_list = []
            if isinstance(raw_ids, list):
                id_list = [str(i).strip() for i in raw_ids if str(i).strip()]
            elif isinstance(raw_ids, dict):
                for k, v in raw_ids.items():
                    key = str(k).strip()
                    if key:
                        id_list.append(key)
                    if isinstance(v, dict):
                        for field in ("id", "modelId", "civitai_id", "version_id"):
                            fv = str(v.get(field, "")).strip()
                            if fv:
                                id_list.append(fv)
            else:
                print(f"[CreationService] Unexpected Horde default lora payload type: {type(raw_ids)}")
                return []
            id_list = list(dict.fromkeys(id_list))
            if not id_list:
                return []

            # Civitai accepts repeated ids query params.
            civitai_url = "https://civitai.com/api/v1/models"
            params = [("limit", str(min(100, len(id_list))))]
            for i in id_list[:1000]:
                params.append(("ids", i))
            resp = requests.get(civitai_url, params=params, timeout=(8, 30))
            resp.raise_for_status()
            data = resp.json()
            items = data.get("items", []) if isinstance(data, dict) else []
            out = []
            for it in items:
                if not isinstance(it, dict):
                    continue
                name = str(it.get("name", "")).strip()
                if not name:
                    continue
                desc = str(it.get("description", "") or "").strip()
                model_versions = it.get("modelVersions", []) or []
                trigger_words = []
                version_name = ""
                version_id = ""
                if model_versions and isinstance(model_versions[0], dict):
                    mv = model_versions[0]
                    version_name = str(mv.get("name", "") or "")
                    version_id = str(mv.get("id", "") or "")
                    trigger_words = [str(w) for w in (mv.get("trainedWords", []) or []) if str(w).strip()]
                searchable = " ".join([name, desc, " ".join(trigger_words)]).lower()
                if q and q.lower() not in searchable:
                    continue
                model_id = str(it.get("id", "") or "").strip()
                best_id = version_id or model_id
                out.append({
                    "name": name,
                    "description": desc[:400],
                    "trigger_words": trigger_words[:6],
                    "version": version_name,
                    "version_id": version_id,
                    "model_id": model_id,
                    "id": best_id,
                })
                if len(out) >= lim:
                    break
            return out[:lim]
        except Exception as e:
            print(f"[CreationService] LoRA catalog fetch failed ({type(e).__name__}): {e}")
            return []

    def _load_image_ref_bytes(self, candidate):
        if not isinstance(candidate, str) or not candidate:
            return None
        if candidate.startswith(("http://", "https://")):
            try:
                r = requests.get(candidate, timeout=(8, 20))
                r.raise_for_status()
                return r.content
            except Exception:
                return None
        if candidate.startswith("data:image/"):
            try:
                _, b64 = candidate.split(",", 1)
                return base64.b64decode(b64)
            except Exception:
                return None
        try:
            return base64.b64decode(candidate)
        except Exception:
            return None

    def _write_generated_image(self, image_bytes):
        kind = imghdr.what(None, h=image_bytes) or "png"
        if kind == "jpeg":
            ext = "jpg"
        elif kind in ("png", "webp", "gif", "bmp"):
            ext = kind
        else:
            ext = "png"
        filename = f"tutor_preview.{ext}"
        output_path = os.path.join(self.output_dir, filename)
        with open(output_path, "wb") as f:
            f.write(image_bytes)
        return f"assets/generated/{filename}"

    def tweak_local(self, base_image_path, tweak_description, strength=0.4):
        """Refines an existing image using img2img."""
        print(f"[CreationService] Tweaking image with: {tweak_description} (Strength: {strength})")
        
        # Load and encode base image
        import base64
        full_path = os.path.join(self.repo_root, "Bitling", base_image_path)
        with open(full_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')

        payload = {
            "init_images": [encoded_string],
            "prompt": tweak_description,
            "negative_prompt": "ugly, blurry, low quality",
            "denoising_strength": strength,
            "steps": 20,
            "cfg_scale": 7
        }
        
        try:
            response = requests.post(url=f'{self.local_api_url}/sdapi/v1/img2img', json=payload)
            r = response.json()
            img_data = r['images'][0]
            output_path = os.path.join(self.output_dir, "tutor_preview.png")
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            return "assets/generated/tutor_preview.png"
        except Exception as e:
            print(f"[CreationService] Tweak failed: {e}")
            return None

    def _send_sd_request(self, prompt, use_upscale=True):
        # Inject LoRAs from config if available
        loras = self.config.get('generation', {}).get('loras', [])
        lora_prompt = ""
        for lora in loras:
            name = lora.get('name')
            weight = lora.get('weight', 1.0)
            trigger = lora.get('trigger_word', '')
            if name:
                lora_prompt += f" {trigger} <lora:{name}:{weight}>"
        
        final_prompt = prompt + lora_prompt
        print(f"[CreationService] Local Prompt with LoRAs: {final_prompt}")

        payload = {
            "prompt": final_prompt,
            "negative_prompt": "ugly, blurry, low quality, text, watermark",
            "steps": 25,
            "width": 512,
            "height": 512,
            "cfg_scale": 7.5,
            "enable_hr": use_upscale,
            "hr_scale": 1.5,
            "hr_upscaler": "R-ESRGAN 4x+",
            "sampler_name": "Euler a",
            "alwayson_scripts": {
                "ADetailer": {
                    "args": [True, {"ad_model": "face_yolov8n.pt"}]
                }
            }
        }
        try:
            response = requests.post(url=f'{self.local_api_url}/sdapi/v1/txt2img', json=payload)
            r = response.json()
            import base64
            img_data = r['images'][0]
            output_path = os.path.join(self.output_dir, "tutor_preview.png")
            with open(output_path, "wb") as f:
                f.write(base64.b64decode(img_data))
            return "assets/generated/tutor_preview.png"
        except: return None
