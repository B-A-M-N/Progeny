import ollama
import json

class Brain:
    def __init__(self, model="qwen3-vl:4b"):
        self.model = model
        self.context = [
            {"role": "system", "content": "You are Bitling, a small, curious, and helpful desktop pet. You are expressive, slightly mischievous, and very friendly. Keep your responses short and punchy (max 1-2 sentences). You can also suggest an action for your body: [IDLE], [WALK], [JUMP], [SLEEP], [GREET]."}
        ]

    def think(self, user_input):
        self.context.append({"role": "user", "content": user_input})
        
        try:
            response = ollama.chat(
                model=self.model,
                messages=self.context,
            )
            
            reply = response['message']['content']
            self.context.append({"role": "assistant", "content": reply})
            
            # Basic parsing for actions in brackets
            action = "[IDLE]"
            for a in ["[WALK]", "[JUMP]", "[SLEEP]", "[GREET]", "[IDLE]"]:
                if a in reply:
                    action = a
                    break
            
            clean_reply = reply.replace(action, "").strip()
            return clean_reply, action
        except Exception as e:
            return f"My brain fuzzy... ({str(e)})", "[IDLE]"

    def get_mood_action(self):
        # Autonomous action decision
        prompt = "Decide your next autonomous action based on your mood. Return ONLY the action tag: [IDLE], [WALK], [JUMP], [SLEEP]."
        try:
            response = ollama.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            action = response['message']['content'].strip()
            return action if action in ["[IDLE]", "[WALK]", "[JUMP]", "[SLEEP]"] else "[IDLE]"
        except:
            return "[IDLE]"
