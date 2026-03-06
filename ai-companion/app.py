import time
import os
import asyncio
import json
import yaml
from enum import Enum
from services.camera_service import CameraService
from services.vision_service import VisionService
from services.state_service import StateService
from services.agent_service import AgentService
from services.tts_service import TTSService
from services.cast_service import CastService
from services.memory_service import MemoryService
from services.firecrawl_service import FirecrawlService
from services.safety_service import SafetyService
from services.content_service import ContentService
from services.lesson_plan_service import LessonPlanService
from utils.local_server import LocalAudioServer

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
        
        # Initialize Embedding Service first (shared)
        self.embedding = None
        if EmbeddingService:
            try:
                self.embedding = EmbeddingService()
                print("Embedding Service initialized.")
            except Exception as e:
                print(f"Failed to init EmbeddingService: {e}")

        # Initialize services with config
        self.camera = CameraService()
        self.vision = VisionService(model=self.config['models']['vision'])
        self.state_svc = StateService(model=self.config['models']['agent'])
        self.agent = AgentService(config_path=config_path)
        self.tts = TTSService()
        self.memory = MemoryService(embedding_service=self.embedding)
        self.firecrawl = FirecrawlService()
        self.safety = SafetyService(config_path=config_path)
        self.content = ContentService(self.firecrawl, self.safety, embedding_service=self.embedding)
        self.lesson_planner = LessonPlanService(
            self.firecrawl, self.embedding, self.memory, 
            agent_model=self.config['models']['agent']
        )
        self.caster = CastService(host=self.config['cast']['host_ip'])
        self.server = LocalAudioServer(port=self.config['system']['port'])
        
        self.current_state = State.IDLE
        self.is_running = False

    def load_config(self, path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.join(project_root, path)
        if os.path.exists(full_path):
            with open(full_path, 'r') as f:
                self.config = yaml.safe_load(f)
        else:
            print("Config not found, using defaults.")
            self.config = {
                'system': {'port': 8000, 'loop_interval_seconds': 5},
                'models': {'vision': 'qwen3-vl:2b', 'agent': 'qwen2.5:0.5b'},
                'cast': {'host_ip': '10.9.66.93'}
            }

    def change_state(self, new_state, metadata=None):
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

    async def run(self):
        print("--- Starting Progeny Engine (Lesson Planning Enabled) ---")
        self.is_running = True
        self.server.start()
        if not self.camera.start(): return

        interval = self.config['system']['loop_interval_seconds']

        try:
            while self.is_running:
                # 1. Perception
                self.change_state(State.PERCEIVING)
                frame = self.camera.get_frame()
                if frame is None: 
                    await asyncio.sleep(2); continue

                vision_desc = self.vision.analyze(frame)
                self.state_svc.update_from_vision(vision_desc)
                summary = self.state_svc.get_summary()
                
                # 2. Knowledge Extraction
                if summary.get("visible_objects"):
                    for obj in summary["visible_objects"]:
                        self.memory.update_knowledge(f"seen_object_{obj}", "present", confidence=0.8)
                
                self.memory.record_event("perception", vision_desc, summary, None)
# 3. Decision Logic
if summary.get("child_present"):
    self.change_state(State.DECIDING)

    # FETCH OPEN BRAIN CONTEXT (The Semantic Hook)
    interest = summary.get("current_interest", "trains")
    brain_context = self.memory.search_knowledge(interest, top_k=2)
    lesson_context = self.memory.get_lesson(interest)

    # Agent chooses an ACTION and TEXT, informed by the Brain
    decision = self.agent.get_response(summary, vision_desc, brain_context, lesson_context)
    action = decision.get("action", "comment_observation")
    text = decision.get("text", "")

    # LOG STRUGGLES (The Support Hook)
    struggle = decision.get("struggle")
    state_struggles = summary.get("struggles_detected", [])
    if struggle:
        print(f"[Engine] Logging struggle: {struggle}")
        self.memory.record_struggle(interest, struggle)
    elif state_struggles:
        for s in state_struggles:
            print(f"[Engine] Logging vision-detected struggle: {s}")
            self.memory.record_struggle(interest, s, severity="low")

    print(f"[Agent] Action: {action} | Text: {text}")
                    # Validate Safety
                    if not self.safety.is_safe(text):
                        print("[Safety] Response blocked.")
                        text = "I am listening."

                    # Execute Action
                    if action == "retrieve_content":
                        self.change_state(State.RESEARCHING)
                        interest = summary.get("current_interest", "trains")
                        fact = self.content.get_fun_fact(interest)
                        if fact:
                            text = fact
                    
                    elif action == "plan_lesson":
                        self.change_state(State.PLANNING_LESSON)
                        interest = summary.get("current_interest", "trains")
                        print(f"[Action] Planning deep lesson for: {interest}")
                        # Running lesson planning in the main loop for now (blocking)
                        # In production this could be backgrounded
                        report = self.lesson_planner.plan_lesson(interest)
                        text = f"I spent some time learning about {interest}! I have a special report ready for later."
                        print(f"[LessonPlanner] Generated Report: {report[:100]}...")

                    if text:
                        self.change_state(State.SPEAKING)
                        fname = self.tts.generate(text)
                        if fname:
                            self.caster.play_audio(self.server.get_url(fname))
                            self.memory.record_event("interaction", vision_desc, summary, text, metadata={"action": action})
                else:
                    self.change_state(State.IDLE)

                await asyncio.sleep(interval)
        finally:
            self.stop()

    def stop(self):
        self.is_running = False
        self.camera.stop()
        self.server.stop()

if __name__ == "__main__":
    app = ProgenyEngine()
    asyncio.run(app.run())
