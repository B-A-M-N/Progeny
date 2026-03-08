import ollama
import yaml
import os
import json
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from utils.json_enforcer import JsonEnforcer

class AgentResponse(BaseModel):
    action: str = "comment_observation"
    text: str = ""
    struggle: Optional[str] = None

class AgentService:
    def __init__(self, config_path="config.yaml"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(project_root, config_path)
        
        self.model = "qwen2.5:0.5b" # Default fallback
        self.allowed_actions = []
        self.child_name = "Child"
        self.interests = []
        
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                self.model = config.get("models", {}).get("agent", "qwen2.5:0.5b")
                self.allowed_actions = config.get("allowed_actions", [])
                self.child_data = config.get("child", {})
                self.child_name = self.child_data.get("name", "Child")
                self.interests = self.child_data.get("interests", [])
                # Handle both legacy and new spectrum profile
                self.neuro = self.child_data.get("neurodiversity_profile", {})
                if not self.neuro: # Fallback to old key if exists
                    self.neuro = self.child_data.get("neurodiversity", {})

    def get_response(self, state_summary, vision_description, brain_context=None, lesson_context=None, tutor_profile=None, learning_stage=1, neuro_profile=None):
        # Default profile if none provided
        level = tutor_profile.get('level', 1) if tutor_profile else 1
        attitude = tutor_profile.get('attitude', 'helpful') if tutor_profile else 'helpful'
        tutor_name = tutor_profile.get('name', 'Bitling') if tutor_profile else 'Bitling'

        # Spectrum Profile Extraction
        active_neuro = neuro_profile if isinstance(neuro_profile, dict) and neuro_profile else self.neuro
        comm = active_neuro.get("communication", {})
        sensory = active_neuro.get("sensory", {})
        engagement = active_neuro.get("engagement", {})
        ef = active_neuro.get("executive_function", {})

        # 1. Complexity Rules (Learning Stage Based - Child Centered)
        # Stage 1 (Foundational): < 5 mastered skills
        # Stage 2 (Emerging): 5-15 mastered skills
        # Stage 3 (Fluent): > 15 mastered skills
        
        complexity_rule = "Stage 1: Keep language extremely simple and short (2-4 words). Focus on core vocabulary. No questions."
        if learning_stage == 2:
            complexity_rule = "Stage 2: Use simple sentences (4-6 words). Introduce simple analogies. Use 'first-then' structure."
        elif learning_stage >= 3:
            complexity_rule = "Stage 3: You can use slightly more advanced vocabulary and longer sentences (full thoughts)."

        # 2. Communication Rules
        comm_processing = comm.get("processing_type", "gestalt")
        comm_style = comm.get("style", "declarative")
        literalness = comm.get("literalness", "high")

        comm_rules = []
        if comm_style == "declarative":
            comm_rules.append("Use DECLARATIVE MODELING. Instead of asking questions, make statements about what you see or feel.")
        else:
            comm_rules.append("Use simple, direct questions to engage.")

        if comm_processing == "gestalt":
            comm_rules.append("The child is a Gestalt Language Processor (GLP). Validate and acknowledge any 'scripts' or echolalia as meaningful communication.")
        
        if literalness == "high":
            comm_rules.append("BE EXTREMELY LITERAL. Avoid metaphors, idioms, sarcasm, or complex figures of speech.")

        # 3. Social/Engagement Rules
        freq = engagement.get("interaction_frequency", "medium")
        routine = engagement.get("routine_strictness", "high")
        
        engagement_rules = []
        if freq == "low":
            engagement_rules.append("Speak less. Be patient and give the child significant time to process and respond.")

        # 4. Sensory Awareness (Influences tone)
        vibe = sensory.get("preferred_visual_vibe", "calm")
        vibe_rule = "Use a calm, steady, and melodic tone." if vibe == "calm" else "Be energetic and high-contrast in your verbal delivery."

        # 5. Executive Function & ADHD/AuDHD Rules
        is_adhd = ef.get("is_adhd", False)
        is_audhd = ef.get("is_audhd", False)
        dopamine = ef.get("dopamine_optimized", False)

        adhd_rules = []
        if is_adhd or is_audhd:
            adhd_rules.append("The child has ADHD/AuDHD. Break complex tasks into tiny MICRO-TASKS. Provide immediate feedback.")
            if dopamine:
                adhd_rules.append("PRIORITIZE DOPAMINE. Lead with the child's special interests (trains, dinosaurs). Celebrate small wins frequently.")
            if ef.get("body_doubling_mode"):
                adhd_rules.append("ACT AS A BODY DOUBLE. Use your presence to provide a sense of calm and accountability without pressure.")

        adaptive_policy = state_summary.get("adaptive_policy", {}) if isinstance(state_summary, dict) else {}
        adaptive_mode = str(adaptive_policy.get("mode", "stabilize"))
        mode_rules = []
        if adaptive_mode == "recover":
            mode_rules.append("MODE=RECOVER. Stop teaching pressure. Prioritize regulation and low-demand co-play.")
            mode_rules.append("Use very short prompts. Offer choice-based or drawing-first interaction.")
        elif adaptive_mode == "rest":
            mode_rules.append("MODE=REST. Pause active teaching. Use calm, low-demand, restorative interaction only.")
        elif adaptive_mode == "co_play":
            mode_rules.append("MODE=CO_PLAY. Join the child's play and curiosity. No direct demands.")
        elif adaptive_mode == "explore":
            mode_rules.append("MODE=EXPLORE. Offer playful discovery choices. Help child lead topic selection.")
        elif adaptive_mode == "engage":
            mode_rules.append("MODE=ENGAGE. Keep attention warm with short, interactive co-activity.")
        elif adaptive_mode == "practice":
            mode_rules.append("MODE=PRACTICE. Reinforce mastery with repetition games and tiny wins.")
        elif adaptive_mode == "repair":
            mode_rules.append("MODE=REPAIR. Reduce demand and break tasks into tiny steps.")
            mode_rules.append("Use declarative language and guided success.")
        elif adaptive_mode == "stabilize":
            mode_rules.append("MODE=STABILIZE. Keep difficulty steady, maintain momentum, avoid abrupt challenge jumps.")
        else:
            mode_rules.append("MODE=ADVANCE. Introduce slight novelty and one-step challenge increases.")

        # Strict instructions for the agent to behave like a finite state machine
        system_prompt = (
            f"You are {tutor_name}, a local AI companion and tutor for {self.child_name}. "
            f"Interests: {', '.join(self.interests)}. "
            f"Your level is {level}. Personality: {attitude}.\n"
            "STRICT OPERATING RULES:\n"
            f"- {complexity_rule}\n"
            f"- {vibe_rule}\n"
            + "\n".join([f"- {r}" for r in comm_rules]) + "\n"
            + "\n".join([f"- {r}" for r in engagement_rules]) + "\n"
            + "\n".join([f"- {r}" for r in adhd_rules]) + "\n"
            + "\n".join([f"- {r}" for r in mode_rules]) + "\n"
            "3. Choose ONE action: " + ", ".join(self.allowed_actions) + ".\n"
            "4. Output ONLY raw JSON.\n"
            "EXAMPLE 1 (Happy playing):\n"
            "Vision: Child is building a tower.\n"
            "JSON: {\"action\": \"comment_observation\", \"text\": \"You are building a tall tower!\", \"struggle\": null}\n"
            "EXAMPLE 2 (Frustrated):\n"
            "Vision: Child is crying and throwing a block.\n"
            "JSON: {\"action\": \"provide_comfort\", \"text\": \"Blocks are hard sometimes. I am here.\", \"struggle\": \"frustrated with blocks\"}\n"
        )

        context_parts = [
            f"Vision: {vision_description}",
            f"State: {json.dumps(state_summary)}"
        ]

        if brain_context:
            context_parts.append(f"Memory (Open Brain): {json.dumps(brain_context)}")
        
        if lesson_context:
            context_parts.append(f"Prepared Lesson Report: {lesson_context.get('report')}")

        context = "\n".join(context_parts)

        try:
            response = ollama.generate(
                model=self.model,
                prompt=f"{system_prompt}\n\nContext:\n{context}",
                format="json",
                stream=False
            )
            
            # Use JsonEnforcer for "Bare Metal" reliability
            result_obj = JsonEnforcer.enforce(
                response['response'],
                AgentResponse,
                default_factory=lambda: AgentResponse(text="I see you! What are you playing with?")
            )
            
            result = result_obj.model_dump()
            
            # Fallback if model hallucinates an invalid action
            if result.get("action") not in self.allowed_actions:
                print(f"[Agent] Invalid action '{result.get('action')}' replaced with 'comment_observation'")
                result["action"] = "comment_observation"
                
            return result
        except Exception as e:
            print(f"[Agent] Error: {e}")
            # Fail safe response
            return {"action": "comment_observation", "text": "I see you! What are you playing with?"}

if __name__ == "__main__":
    agent = AgentService()
    test_state = {"child_present": True, "emotion": "happy"}
    test_vision = "The child is holding a green dinosaur toy."
    print(agent.get_response(test_state, test_vision))
