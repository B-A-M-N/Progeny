import ollama
import yaml
import os
import json

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
                self.child_name = config.get("child", {}).get("name", "Child")
                self.interests = config.get("child", {}).get("interests", [])

    def get_response(self, state_summary, vision_description, brain_context=None, lesson_context=None):
        # Strict instructions for the agent to behave like a finite state machine
        system_prompt = (
            f"You are a local AI companion for {self.child_name}. "
            f"Interests: {', '.join(self.interests)}. "
            "Your goal is to guide learning through 'Cognitive Scaffolding'.\n"
            "STRICT RULES:\n"
            "1. You must choose ONE action from this list: " + ", ".join(self.allowed_actions) + ".\n"
            "2. Output format must be JSON: {\"action\": \"ACTION_NAME\", \"text\": \"YOUR_SHORT_RESPONSE\", \"struggle\": \"OPTIONAL_DESCRIPTION_OF_ANY_DIFFICULTY_DETECTED\"}\n"
            "3. Keep text under 2 sentences. Warm, concrete, encouraging.\n"
            "4. If the child is holding an object, use 'comment_observation' to acknowledge it.\n"
            "5. If the child seems disengaged, use 'offer_choice' or 'suggest_break'.\n"
            "6. If the child is engaged, use 'ask_simple_question' to scaffold learning.\n"
            "7. If the child asks a factual question, use 'retrieve_content' to find the answer.\n"
            "8. If you identify a topic for deep learning or the parent asks, use 'plan_lesson' to research and generate a kid-friendly report.\n"
            "9. If the child is struggling (e.g., can't pick up a block, getting frustrated), describe the struggle in the 'struggle' field so it can be logged."
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
            
            result = json.loads(response['response'])
            
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
