import json
import os
import time
import ollama

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
            f"Based on this vision description: '{vision_description}'\n"
            "Extract the following JSON state:\n"
            "{\n"
            "  \"child_present\": boolean,\n"
            "  \"visible_objects\": [string],\n"
            "  \"engagement_level\": \"high\"|\"medium\"|\"low\"|\"none\",\n"
            "  \"emotion\": \"happy\"|\"sad\"|\"frustrated\"|\"excited\"|\"calm\"|\"bored\",\n"
            "  \"activity\": string,\n"
            "  \"current_interest\": string,\n"
            "  \"struggles_detected\": [string] -- list of any difficulties like 'motor skills', 'counting', 'frustration'\n"
            "}\n"
            "Return ONLY the raw JSON."
        )

        try:
            response = ollama.generate(
                model=self.model,
                prompt=prompt,
                format="json",
                stream=False
            )
            structured_data = json.loads(response['response'])
            self.current_state.update(structured_data)
        except Exception as e:
            print(f"State extraction error: {e}")
            # Fallback to simple heuristic if LLM fails
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
