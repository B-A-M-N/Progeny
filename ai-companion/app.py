import time
import os
import asyncio
import json
import yaml
import websockets
from websockets.legacy.server import serve as legacy_ws_serve
from enum import Enum
from services.camera_service import CameraService
from services.vision_service import VisionService
from services.state_service import StateService
from services.agent_service import AgentService
from services.tts_service import TTSService
from services.cast_service import CastService
from services.memory_service import MemoryService
from services.search_service import SearchService
from services.firecrawl_service import FirecrawlService
from services.safety_service import SafetyService
from services.content_service import ContentService
from services.lesson_plan_service import LessonPlanService
from services.creation_service import CreationService
from services.resource_service import ResourceService
from services.onboarding_service import OnboardingService
from utils.local_server import LocalAudioServer
from utils.writing_server import app as writing_app
import threading
import traceback
from collections import deque

# Try to import EmbeddingService (requires fastembed)
try:
    from services.embedding_service import EmbeddingService
except ImportError:
    EmbeddingService = None
    print("Warning: EmbeddingService not available (fastembed/numpy missing). Reranking and semantic search disabled.")

class State(Enum):
    IDLE = "IDLE"
    PERCEIVING = "PERCEIVING"
    ENGAGED = "ENGAGED"
    DECIDING = "DECIDING"
    SPEAKING = "SPEAKING"
    RESEARCHING = "RESEARCHING"
    PLANNING_LESSON = "PLANNING_LESSON"

class ProgenyEngine:
    def __init__(self, config_path="config.yaml"):
        self.load_config(config_path)
        
        # Architecture Role Mapping (Environment Overrides)
        # Allows swapping models for specific roles without touching config.yaml
        self.role_models = {
            "vision": os.getenv("PROGENY_MODEL_VISION", self.config['models'].get('vision', 'moondream:latest')),
            "playmate": os.getenv("PROGENY_MODEL_PLAYMATE", self.config['models'].get('agent', 'qwen2.5:0.5b')),
            "researcher": os.getenv("PROGENY_MODEL_RESEARCHER", os.getenv("PROGENY_MODEL_PLAYMATE", self.config['models'].get('agent', 'qwen2.5:0.5b'))),
            "state_extractor": os.getenv("PROGENY_MODEL_STATE", os.getenv("PROGENY_MODEL_PLAYMATE", self.config['models'].get('agent', 'qwen2.5:0.5b')))
        }
        
        print(f"[Engine] Architecture Roles: {json.dumps(self.role_models, indent=2)}")

        # Initialize Embedding Service first (shared)
        self.embedding = None
        if EmbeddingService:
            try:
                self.embedding = EmbeddingService()
                print("Embedding Service initialized.")
            except Exception as e:
                print(f"Failed to init EmbeddingService: {e}")

        # Initialize services with mapped roles
        self.camera = CameraService()
        self.vision = None # LAZY LOADING: Don't init until creation is done
        self.vision_model = self.role_models['vision']
        self.state_svc = StateService(model=self.role_models['state_extractor'])
        self.agent = AgentService(config_path=config_path)
        # Override agent internal model if env/config role is set
        self.agent.model = self.role_models['playmate']
        
        self.tts = TTSService()
        self.memory = MemoryService(embedding_service=self.embedding)
        self.resources = ResourceService(self.config)
        self.search_svc = SearchService()
        self.firecrawl = FirecrawlService()
        self.safety = SafetyService(config_path=config_path)
        self.content = ContentService(self.firecrawl, self.safety, embedding_service=self.embedding)
        self.lesson_planner = LessonPlanService(
            self.firecrawl, self.search_svc, self.embedding, self.memory, 
            agent_model=self.role_models['researcher']
        )
        self.creation_svc = CreationService(self.config, agent_model=self.role_models['playmate'])
        self.onboarding = OnboardingService(self.memory, self.config)
        self.caster = CastService(host=self.config['cast']['host_ip'])
        self.server = LocalAudioServer(port=self.config['system']['port'])
        self.writing_server_port = self.config['system'].get('writing_port', 5000)
        
        self.current_state = State.IDLE
        self.is_running = False

        
        # WebSocket clients (Godot UI)
        self.connected_clients = set()
        self.current_onboarding_session = {}
        self.recent_adaptive_signals = {}
        self.active_media_sessions = {}
        self.signal_alpha = 0.25
        self.interest_history = deque(maxlen=12)
        self.last_trust_stage = ""

    def get_active_neuro_profile(self):
        adapted = self.onboarding.get_or_init_profile()
        neuro = adapted.get("neurodiversity_profile", {})
        if neuro:
            return neuro
        return self.config.get('child', {}).get('neurodiversity_profile', {})

    def _update_adaptive_signal(self, key, value):
        # Accept normalized signals [0..1] and smooth with EMA.
        k = str(key or "").strip()
        if not k:
            return
        try:
            v = float(value)
        except Exception:
            return
        if v < 0.0:
            v = 0.0
        if v > 1.0:
            v = 1.0
        old = float(self.recent_adaptive_signals.get(k, 0.0))
        self.recent_adaptive_signals[k] = (1.0 - self.signal_alpha) * old + self.signal_alpha * v

    def _map_metric_to_signals(self, metric_key, metric_value):
        k = str(metric_key or "").strip()
        try:
            v = float(metric_value)
        except Exception:
            v = 0.0
        # Canonical 12-channel mappings
        if k in ("response_latency_spike", "rapid_topic_switching", "vocal_intensity", "repetitive_language_looping",
                 "movement_acceleration", "micro_frustration", "interruptions", "humor_deflection",
                 "silence_withdrawal", "task_abandonment", "facial_regulation_changes", "breathing_pattern_shift"):
            self._update_adaptive_signal(k, v)
            return
        # Aliases and derived mappings from existing metrics
        if k in ("latency_to_choice", "latency_to_start", "response_latency"):
            self._update_adaptive_signal("response_latency_spike", min(1.0, max(0.0, v / 8.0)))
        elif k in ("topic_switch_rate",):
            self._update_adaptive_signal("rapid_topic_switching", v)
        elif k in ("pressure_spike_frequency",):
            self._update_adaptive_signal("micro_frustration", v)
        elif k in ("partial_attempt_rate", "task_abandonment"):
            self._update_adaptive_signal("task_abandonment", v)
        elif k in ("interruption_rate",):
            self._update_adaptive_signal("interruptions", v)
        elif k in ("facial_tension",):
            self._update_adaptive_signal("facial_regulation_changes", v)
        elif k in ("breathing_shift",):
            self._update_adaptive_signal("breathing_pattern_shift", v)

    def load_config(self, path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(project_root, path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            print("Config not found, using defaults.")
            self.config = {
                'system': {'port': 8000, 'loop_interval_seconds': 5, 'ws_port': 9001},
                'models': {'vision': 'qwen3-vl:2b', 'agent': 'qwen2.5:0.5b'},
                'cast': {'host_ip': '10.9.66.93'},
                'generation': {'prefer_local': False}
            }

    async def broadcast(self, message_dict):
        """Sends a message to all connected Godot clients."""
        if not self.connected_clients:
            return
        msg = json.dumps(message_dict)
        tasks = [asyncio.create_task(client.send(msg)) for client in self.connected_clients]
        await asyncio.gather(*tasks, return_exceptions=True)

    async def ws_handler(self, websocket, path=None):
        """Handles incoming WebSocket connections from Godot."""
        client_addr = getattr(websocket, "remote_address", "unknown")
        print(f"[WebSocket] Client connected: {client_addr}")
        self.connected_clients.add(websocket)
        try:
            # Send initial profile and capability state
            open_brain_ok, open_brain_detail = self.memory.health_check()
            profile = {"name": "Bitling", "appearance": "default", "attitude": "helpful", "level": 1, "xp": 0}
            if open_brain_ok:
                try:
                    db_profile = self.memory.get_tutor_profile()
                    if db_profile:
                        profile = db_profile
                except Exception as e:
                    open_brain_ok = False
                    open_brain_detail = f"profile_load_failed: {type(e).__name__}: {e}"
            gen_config = self.config.get('generation', {})
            neuro_profile = self.get_active_neuro_profile()
            adaptation = self.onboarding.get_or_init_profile()
            world_anchor = adaptation.get("world_anchor", {})
            trust_model = adaptation.get("trust", {})
            
            # Auto-detect if local is actually available
            is_local = self.creation_svc.is_local_available()
            prefer_local = gen_config.get('prefer_local', False) and is_local
            force_local_env = os.getenv("PROGENY_FORCE_LOCAL", "").strip().lower()
            if force_local_env in ("1", "true", "yes", "on"):
                prefer_local = is_local
            elif force_local_env in ("0", "false", "no", "off"):
                prefer_local = False
            
            await websocket.send(json.dumps({
                "type": "init", 
                "profile": profile,
                "neurodiversity": neuro_profile,
                "adaptation_profile": adaptation,
                "open_brain": {
                    "connected": open_brain_ok,
                    "detail": open_brain_detail
                },
                "generation": {
                    "prefer_local": prefer_local,
                    "pollinations_active": not prefer_local
                },
                "world_anchor": world_anchor,
                "trust_model": trust_model,
                "return_greeting": self.onboarding.get_return_greeting(),
            }))
            
            async for message in websocket:
                data = json.loads(message)
                msg_type = data.get("type")

                if msg_type == "construct_tutor_local":
                    description = data.get("description", "A friendly robot.")
                    print(f"[Creation] construct_tutor_local received. desc_len={len(description)}")
                    refined_prompt = self.creation_svc.refine_description(description)
                    img_path = self.creation_svc.generate_local(refined_prompt)
                    
                    if img_path:
                        await websocket.send(json.dumps({
                            "type": "tutor_constructed",
                            "image_url": img_path
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Local generation failed. Fallback to Pollinations."
                        }))

                elif msg_type in ("construct_tutor_remote", "construct_tutor_pollinations"):
                    description = data.get("description", "A friendly robot.")
                    style = data.get("style", "3D Animated Movie")
                    model = data.get("model", "turbo")
                    enhance_prompt = bool(data.get("enhance_prompt", False))
                    seed = data.get("seed", "")
                    loras = data.get("loras", [])
                    print(f"[Creation] construct_tutor_remote received. model={model}, style={style}, desc_len={len(description)}, loras={len(loras)}")
                    img_path = self.creation_svc.generate_remote(
                        description, style, model=model, width=384, height=384,
                        enhance_prompt=enhance_prompt, seed=seed, loras=loras
                    )

                    if img_path:
                        await websocket.send(json.dumps({
                            "type": "tutor_constructed",
                            "image_url": img_path
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Remote generation failed. Retry, switch model, or use local mode on capable machine."
                        }))

                elif msg_type in ("tweak_tutor_remote", "tweak_tutor_pollinations"):
                    base_description = data.get("description", "A friendly robot.")
                    tweak_description = data.get("tweak_description", "")
                    style = data.get("style", "3D Animated Movie")
                    model = data.get("model", "turbo")
                    enhance_prompt = bool(data.get("enhance_prompt", False))
                    seed = data.get("seed", "")
                    loras = data.get("loras", [])
                    print(f"[Creation] tweak_tutor_remote received. model={model}, style={style}, tweak_len={len(tweak_description)}, loras={len(loras)}")
                    combined = f"A {tweak_description} version of {base_description}".strip()
                    img_path = self.creation_svc.generate_remote(
                        combined, style, model=model, width=384, height=384,
                        enhance_prompt=enhance_prompt, seed=seed, loras=loras
                    )

                    if img_path:
                        await websocket.send(json.dumps({
                            "type": "tutor_constructed",
                            "image_url": img_path
                        }))
                    else:
                        await websocket.send(json.dumps({
                            "type": "error",
                            "message": "Remote tweak failed. Retry, switch model, or use local mode on capable machine."
                        }))

                elif msg_type == "finalize_tutor":
                    self.memory.update_tutor_profile(appearance=data.get("appearance", "generated/tutor_preview.png"))
                    print("[Creation] Tutor finalized.")

                elif msg_type == "list_remote_loras":
                    query = data.get("query", "")
                    limit = data.get("limit", 30)
                    print(f"[Creation] list_remote_loras received. query='{query}' limit={limit}")
                    loras = self.creation_svc.list_remote_loras(query=query, limit=limit)
                    await websocket.send(json.dumps({
                        "type": "remote_loras",
                        "items": loras,
                        "query": query
                    }))

                elif data.get("type") == "update_profile":
                    self.memory.update_tutor_profile(
                        name=data.get("name"),
                        appearance=data.get("appearance"),
                        attitude=data.get("attitude")
                    )
                elif msg_type == "get_onboarding_script":
                    await websocket.send(json.dumps({
                        "type": "onboarding_script",
                        "items": self.onboarding.get_session_script(),
                        "profile": self.onboarding.get_or_init_profile()
                    }))
                elif msg_type == "get_world_state":
                    profile = self.onboarding.get_or_init_profile()
                    await websocket.send(json.dumps({
                        "type": "world_state",
                        "world_anchor": profile.get("world_anchor", {}),
                        "trust_model": profile.get("trust", {}),
                        "return_greeting": self.onboarding.get_return_greeting()
                    }))
                elif msg_type == "world_action":
                    action = data.get("action", "")
                    payload = data.get("payload", {})
                    updated = self.onboarding.apply_world_action(action, payload)
                    await websocket.send(json.dumps({
                        "type": "world_state",
                        "world_anchor": updated.get("world_anchor", {}),
                        "trust_model": updated.get("trust", {}),
                        "return_greeting": self.onboarding.get_return_greeting()
                    }))
                elif msg_type == "set_parent_baseline":
                    baseline = data.get("baseline", {})
                    profile = self.onboarding.apply_parent_baseline(baseline)
                    await websocket.send(json.dumps({
                        "type": "onboarding_profile_updated",
                        "profile": profile,
                        "neurodiversity": profile.get("neurodiversity_profile", {})
                    }))
                elif msg_type == "onboarding_event":
                    session_id = str(data.get("session_id", "default"))
                    event = data.get("event", {})
                    metric_key = str(event.get("metric_key", "")).strip()
                    metric_value = event.get("metric_value", 0.0)
                    if metric_key:
                        self.memory.record_onboarding_metric(
                            session_id=session_id,
                            metric_key=metric_key,
                            metric_value=metric_value,
                            metadata=event.get("metadata", {})
                        )
                    self.current_onboarding_session.setdefault(session_id, {})
                    if metric_key:
                        self.current_onboarding_session[session_id][metric_key] = float(metric_value or 0.0)
                        self._map_metric_to_signals(metric_key, metric_value)
                    metadata = event.get("metadata", {})
                    if isinstance(metadata, dict):
                        sig = metadata.get("signals", {})
                        if isinstance(sig, dict):
                            for sk, sv in sig.items():
                                self._map_metric_to_signals(sk, sv)
                    updated = self.onboarding.apply_runtime_metrics(self.current_onboarding_session[session_id])
                    await websocket.send(json.dumps({
                        "type": "onboarding_runtime_update",
                        "profile": updated,
                        "neurodiversity": updated.get("neurodiversity_profile", {})
                    }))
                elif msg_type == "finish_onboarding":
                    session_id = str(data.get("session_id", "default"))
                    metrics = self.current_onboarding_session.get(session_id, {})
                    summary = self.onboarding.summarize_for_parent(metrics)
                    profile = self.onboarding.get_or_init_profile()
                    await websocket.send(json.dumps({
                        "type": "onboarding_summary",
                        "session_id": session_id,
                        "summary": summary,
                        "profile": profile,
                        "world_anchor": profile.get("world_anchor", {}),
                        "trust_model": profile.get("trust", {}),
                    }))
                elif msg_type == "start_media_session":
                    session_id = str(data.get("session_id", f"media_{int(time.time())}"))
                    topic = str(data.get("topic", "general"))
                    title = str(data.get("title", ""))
                    url = str(data.get("url", ""))
                    baseline_state = self.onboarding.estimate_live_state(self.state_svc.get_summary(), self.recent_adaptive_signals)
                    self.active_media_sessions[session_id] = {
                        "started_at": time.time(),
                        "baseline_state": baseline_state,
                        "topic": topic,
                        "title": title,
                        "url": url,
                    }
                    self.memory.start_media_session(
                        session_id=session_id,
                        topic=topic,
                        title=title,
                        url=url,
                        baseline_state=baseline_state,
                        metadata=data.get("metadata", {})
                    )
                    await websocket.send(json.dumps({
                        "type": "media_session_started",
                        "session_id": session_id,
                        "topic": topic
                    }))
                elif msg_type == "media_probe_event":
                    session_id = str(data.get("session_id", ""))
                    probe_type = str(data.get("probe_type", "choice_recall"))
                    response_mode = str(data.get("response_mode", "choice"))
                    response_latency = float(data.get("response_latency", 0.0) or 0.0)
                    success_score = float(data.get("success_score", 0.5) or 0.5)
                    self.memory.record_media_probe(
                        session_id=session_id,
                        probe_type=probe_type,
                        response_mode=response_mode,
                        response_latency=response_latency,
                        success_score=success_score,
                        metadata=data.get("metadata", {})
                    )
                    # Probe latency is a useful escalation indicator.
                    self._map_metric_to_signals("response_latency", min(1.0, response_latency / 8.0))
                    await websocket.send(json.dumps({
                        "type": "media_probe_recorded",
                        "session_id": session_id,
                        "probe_type": probe_type
                    }))
                elif msg_type == "end_media_session":
                    session_id = str(data.get("session_id", ""))
                    live = self.active_media_sessions.get(session_id, {})
                    baseline_state = live.get("baseline_state", {})
                    end_state = self.onboarding.estimate_live_state(self.state_svc.get_summary(), self.recent_adaptive_signals)
                    behavior_delta = {
                        "frustration": [baseline_state.get("frustration", "none"), end_state.get("frustration", "none")],
                        "engagement": [baseline_state.get("engagement", "none"), end_state.get("engagement", "none")],
                        "regulation": [baseline_state.get("regulation", "regulated"), end_state.get("regulation", "regulated")]
                    }
                    watched_seconds = float(data.get("watched_seconds", 0.0) or 0.0)
                    if watched_seconds <= 0 and live.get("started_at"):
                        watched_seconds = max(0.0, time.time() - float(live.get("started_at")))
                    completed = bool(data.get("completed", False))
                    self.memory.end_media_session(
                        session_id=session_id,
                        watched_seconds=watched_seconds,
                        completed=completed,
                        end_state=end_state,
                        behavior_delta=behavior_delta,
                        metadata=data.get("metadata", {})
                    )
                    topic = live.get("topic") or data.get("topic")
                    insight = self.memory.get_media_effectiveness(topic=topic) if topic else {}
                    await websocket.send(json.dumps({
                        "type": "media_session_ended",
                        "session_id": session_id,
                        "behavior_delta": behavior_delta,
                        "effectiveness": insight
                    }))
                    if session_id in self.active_media_sessions:
                        del self.active_media_sessions[session_id]
                elif msg_type == "get_media_insights":
                    topic = data.get("topic")
                    if topic:
                        insight = self.memory.get_media_effectiveness(topic=topic)
                    else:
                        insight = self.memory.get_media_effectiveness(limit=20)
                    await websocket.send(json.dumps({
                        "type": "media_insights",
                        "topic": topic,
                        "insights": insight
                    }))
                elif msg_type == "get_media_probe_pack":
                    await websocket.send(json.dumps({
                        "type": "media_probe_pack",
                        "items": [
                            {"id": "choice_recall", "prompt": "Pick one: what was this mostly about?", "mode": "choice"},
                            {"id": "draw_recall", "prompt": "Show me the part you remember best.", "mode": "drawing"},
                            {"id": "order_check", "prompt": "What happened first?", "mode": "choice"},
                            {"id": "tiny_transfer", "prompt": "Want to try one tiny thing from that video?", "mode": "choice"}
                        ]
                    }))
                elif msg_type == "regulation_signal":
                    # Direct signal channel for sensors/UI (0..1 normalized preferred).
                    signals = data.get("signals", {})
                    if isinstance(signals, dict):
                        for sk, sv in signals.items():
                            self._map_metric_to_signals(sk, sv)
                    await websocket.send(json.dumps({
                        "type": "regulation_signal_ack",
                        "signals": self.recent_adaptive_signals
                    }))
        except websockets.exceptions.ConnectionClosed as e:
            print(f"[WebSocket] ConnectionClosed: {e}")
        except Exception as e:
            print(f"[WebSocket] Handler exception: {type(e).__name__}: {e}")
            traceback.print_exc()
        finally:
            print(f"[WebSocket] Client disconnected: {client_addr}")
            if websocket in self.connected_clients:
                self.connected_clients.remove(websocket)

    async def change_state(self, new_state, metadata=None):
        old_state = self.current_state
        self.current_state = new_state
        print(f"[Engine] {old_state.value} -> {new_state.value}")
        
        self.memory.record_event(
            event_type="state_transition",
            vision_desc=None,
            state_snapshot=self.state_svc.get_summary(),
            agent_response=None,
            metadata={"old": old_state.value, "new": new_state.value, "context": metadata}
        )
        await self.broadcast({"type": "state_change", "state": new_state.value})

    async def run(self):
        print("--- Starting Progeny Engine (Hybrid Evo Enabled) ---")
        self.is_running = True
        
        # 1. Start Servers (WebSocket first for UI responsiveness)
        ws_port = self.config['system'].get('ws_port', 9001)
        ws_host = self.config['system'].get('ip_address', '0.0.0.0')
        print(f"[WebSocket] Starting server on {ws_host}:{ws_port}...")
        ws_server = await legacy_ws_serve(self.ws_handler, ws_host, ws_port, origins=None)
        print("[WebSocket] Server READY. Godot can connect now.")

        self.server.start()
        
        # Start Writing Server in a separate thread
        writing_thread = threading.Thread(
            target=writing_app.run, 
            kwargs={'host': '0.0.0.0', 'port': self.writing_server_port, 'debug': False, 'use_reloader': False}
        )
        writing_thread.daemon = True
        writing_thread.start()
        print(f"[Engine] Writing Pad active on port {self.writing_server_port}")

        if not self.camera.start(): 
            print("[Camera] Failed to start camera.")
            return

        interval = self.config['system'].get('loop_interval_seconds', 5)

        try:
            while self.is_running:
                # 0. System Resource Check & Dynamic Interval
                resource_stats = self.resources.get_system_stats()
                multiplier = self.resources.get_priority_multiplier(self.current_state.value)
                current_loop_interval = interval * multiplier
                
                # Broadcast resources to Dashboard/Godot
                await self.broadcast({
                    "type": "resource_update", 
                    "stats": resource_stats,
                    "is_throttling": multiplier > 1.0
                })

                # Skip heavy processing if we are still in character creation
                profile = self.memory.get_tutor_profile()
                if profile and profile.get('appearance') == 'default':
                    # Character creation is active, don't hog CPU with Vision
                    await asyncio.sleep(2)
                    continue
                
                # LAZY VISION INIT: Only fire up Ollama Vision after profile is set
                if self.vision is None:
                    print("[Engine] Profile finalized! Initializing Vision Module (CPU mode)...")
                    self.vision = VisionService(model=self.vision_model)

                await self.change_state(State.PERCEIVING)
                frame = self.camera.get_frame()
                if frame is None: 
                    await asyncio.sleep(2); continue

                vision_desc = self.vision.analyze(frame)
                
                if hasattr(self, 'last_vision_desc') and self.last_vision_desc == vision_desc:
                    await asyncio.sleep(current_loop_interval)
                    continue
                self.last_vision_desc = vision_desc

                self.state_svc.update_from_vision(vision_desc)
                summary = self.state_svc.get_summary()
                self.interest_history.append(str(summary.get("current_interest", "unknown")))
                if len(self.interest_history) >= 4:
                    switches = 0
                    for i in range(1, len(self.interest_history)):
                        if self.interest_history[i] != self.interest_history[i - 1]:
                            switches += 1
                    switch_rate = switches / max(1, len(self.interest_history) - 1)
                    self._update_adaptive_signal("rapid_topic_switching", switch_rate)
                live_state = self.onboarding.estimate_live_state(summary, self.recent_adaptive_signals)
                trust_profile = self.onboarding.update_trust_from_live_state(live_state)
                trust_model = trust_profile.get("trust", {})
                world_anchor = trust_profile.get("world_anchor", {})
                live_state["trust_stage"] = trust_model.get("stage", "safety")
                live_state["trust_score"] = trust_model.get("score", 0.0)
                adaptive_policy = self.onboarding.render_adaptive_policy(live_state)
                summary_for_agent = dict(summary)
                summary_for_agent["adaptive_state"] = live_state
                summary_for_agent["adaptive_policy"] = adaptive_policy
                summary_for_agent["trust_model"] = trust_model
                summary_for_agent["world_anchor"] = world_anchor
                await self.broadcast({
                    "type": "adaptive_state",
                    "state": live_state,
                    "policy": adaptive_policy,
                    "trust_model": trust_model,
                    "world_anchor": world_anchor
                })
                stage = str(trust_model.get("stage", ""))
                if stage and stage != self.last_trust_stage:
                    self.last_trust_stage = stage
                    await self.broadcast({
                        "type": "trust_stage_update",
                        "trust_model": trust_model
                    })
                
                if summary.get("visible_objects"):
                    for obj in summary["visible_objects"]:
                        self.memory.update_knowledge(f"seen_object_{obj}", "present", confidence=0.8)
                
                self.memory.record_event("perception", vision_desc, summary, None)
                
                if summary.get("child_present"):
                    await self.change_state(State.DECIDING)
                    interest = summary.get("current_interest", "trains")
                    brain_context = self.memory.search_knowledge(interest, top_k=2)
                    lesson_context = self.memory.get_lesson(interest)
                    profile = self.memory.get_tutor_profile()
                    learning_stage = self.memory.get_learning_stage()

                    active_neuro = self.get_active_neuro_profile()
                    decision = self.agent.get_response(
                        summary_for_agent,
                        vision_desc,
                        brain_context,
                        lesson_context,
                        tutor_profile=profile,
                        learning_stage=learning_stage,
                        neuro_profile=active_neuro
                    )
                    action = decision.get("action", "comment_observation")
                    text = decision.get("text", "")

                    await self.broadcast({"type": "action", "action": action})

                    struggle = decision.get("struggle")
                    state_struggles = summary.get("struggles_detected", [])
                    if struggle:
                        self.memory.record_struggle(interest, struggle)
                    elif state_struggles:
                        for s in state_struggles:
                            self.memory.record_struggle(interest, s, severity="low")

                    if not self.safety.is_safe(text):
                        text = "I am listening."

                    if action == "retrieve_content":
                        await self.change_state(State.RESEARCHING)
                        interest = summary.get("current_interest", "trains")
                        fact = self.content.get_fun_fact(interest)
                        if fact:
                            text = fact
                    
                    elif action == "plan_lesson":
                        # BARE METAL GATE: Adjust research depth based on resources
                        quality = self.resources.get_quality_mode()
                        
                        # We only block completely if quality is 'low' AND system is super pegged
                        # Otherwise, we just 'scale down' the research.
                        if quality != "low" or self.resources.can_run_background_task():
                            await self.change_state(State.PLANNING_LESSON)
                            interest = summary.get("current_interest", "trains")
                            lesson_obj = self.lesson_planner.plan_lesson_dynamic(
                                interest,
                                quality=quality,
                                live_state=live_state,
                                adaptive_policy=adaptive_policy
                            )
                            await self.broadcast({
                                "type": "lesson_plan",
                                "subject": interest,
                                "lesson": lesson_obj
                            })
                            text = str(lesson_obj.get("hook", f"Let's learn about {interest} together."))
                        else:
                            print("[Engine] Throttling Lesson Plan - System Pegged")
                            text = "I'm looking forward to learning more about that soon!"

                    elif action in ["ask_simple_question", "praise_attempt"]:
                         pass 

                    # --- Child-Centered XP Hooks ---
                    
                    # 1. Self-Advocacy Check (Simple keyword heuristic for now)
                    if vision_desc and any(k in vision_desc.lower() for k in ["asking for help", "needs a break", "gesturing stop"]):
                        leveled_up, new_level = self.memory.log_xp_event("SELF_ADVOCACY", 10, evidence="Detected request for help/break")
                        if leveled_up:
                            await self.broadcast({"type": "level_up", "level": new_level})
                    
                    # 2. Sustained Engagement (Using state summary)
                    if summary.get("engagement_level") == "high":
                         # Rate limit this in production to avoid spamming XP every loop
                         leveled_up, new_level = self.memory.log_xp_event("EFFORT", 2, evidence="High engagement detected")
                         if leveled_up:
                            await self.broadcast({"type": "level_up", "level": new_level})
                    
                    # -------------------------------

                    if text:
                        await self.change_state(State.SPEAKING)
                        fname = self.tts.generate(text, tutor_profile=profile, learning_stage=learning_stage)
                        if fname:
                            audio_url = self.server.get_url(fname)
                            self.caster.play_audio(audio_url)
                            await self.broadcast({"type": "speak", "text": text, "audio_url": audio_url})
                            self.memory.record_event("interaction", vision_desc, summary, text, metadata={"action": action})
                else:
                    await self.change_state(State.IDLE)

                await asyncio.sleep(interval)
        finally:
            ws_server.close()
            await ws_server.wait_closed()
            self.stop()

    def stop(self):
        self.is_running = False
        self.camera.stop()
        self.server.stop()

if __name__ == "__main__":
    app = ProgenyEngine()
    asyncio.run(app.run())
