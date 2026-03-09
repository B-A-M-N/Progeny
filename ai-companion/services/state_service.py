import json
import os
import time
import ollama
from typing import List, Optional
from pydantic import BaseModel, Field, field_validator
from utils.json_enforcer import JsonEnforcer, fuzzy_enum_match

class VisionState(BaseModel):
    child_present: bool = False
    visible_objects: List[str] = Field(default_factory=list)
    engagement_level: str = "none"
    emotion: str = "calm"
    activity: str = "idle"
    current_interest: str = "unknown"
    struggles_detected: List[str] = Field(default_factory=list)

    @field_validator("engagement_level")
    @classmethod
    def validate_engagement(cls, v):
        return fuzzy_enum_match(v, ["high", "medium", "low", "none"], "none")

    @field_validator("emotion")
    @classmethod
    def validate_emotion(cls, v):
        return fuzzy_enum_match(v, ["happy", "sad", "frustrated", "excited", "calm", "bored"], "calm")

class StateService:
    def __init__(self, history_file="data/session_state.json", model="qwen2.5:0.5b"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.history_file = os.path.join(project_root, history_file)
        self.model = model
        self.current_state = {
            "child_present": False,
            "last_interaction": 0,
            "visible_objects": [],
            "engagement_level": "none",
            "current_interest": "trains", 
            "emotion": "calm",
            "activity": "idle",
            "last_agent_response": ""
        }
        self.load_state()

    def load_state(self):
        if os.path.exists(self.history_file):
            try:
                with open(self.history_file, 'r') as f:
                    self.current_state.update(json.load(f))
            except Exception as e:
                print(f"Error loading state: {e}")

    def save_state(self):
        try:
            with open(self.history_file, 'w') as f:
                json.dump(self.current_state, f, indent=4)
        except Exception as e:
            print(f"Error saving state: {e}")

    def update_from_vision(self, vision_description):
        if not vision_description:
            return

        # Use a tiny LLM to extract structured state from the vision description
        # This keeps the logic robust while staying local and fast
        prompt = (
            "SYSTEM: You are a structural state extractor. You convert vision descriptions into JSON.\n"
            "EXAMPLE 1:\n"
            "Description: 'A child is laughing and holding a red toy train.'\n"
            "JSON: {\"child_present\": true, \"visible_objects\": [\"red toy train\"], \"engagement_level\": \"high\", \"emotion\": \"happy\", \"activity\": \"playing\", \"current_interest\": \"trains\", \"struggles_detected\": []}\n"
            "EXAMPLE 2:\n"
            "Description: 'The room is empty. A cat is on the sofa.'\n"
            "JSON: {\"child_present\": false, \"visible_objects\": [\"cat\", \"sofa\"], \"engagement_level\": \"none\", \"emotion\": \"calm\", \"activity\": \"idle\", \"current_interest\": \"unknown\", \"struggles_detected\": []}\n"
            f"NOW: Description: '{vision_description}'\n"
            "Return ONLY the raw JSON."
        )

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                stream=False
            )
            
            # Use JsonEnforcer for "Bare Metal" reliability
            structured_data = JsonEnforcer.enforce(
                response['response'], 
                VisionState,
                default_factory=lambda: VisionState(child_present="child" in vision_description.lower())
            )
            
            self.current_state.update(structured_data.model_dump())
        except Exception as e:
            print(f"State extraction error: {e}")
            # Fallback to simple heuristic if everything fails
            self.current_state["child_present"] = "child" in vision_description.lower()

        self.current_state["last_observation_time"] = time.time()
        self.save_state()

    def get_summary(self):
        return self.current_state

if __name__ == "__main__":
    state = StateService()
    print("Testing intelligent state extraction...")
    test_desc = "A child is laughing and holding a red toy train with 4 wheels."
    state.update_from_vision(test_desc)
    print("Extracted State:", json.dumps(state.get_summary(), indent=2))
