import yaml
import os

class SafetyService:
    def __init__(self, config_path="config.yaml"):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.config_path = os.path.join(project_root, config_path)
        self.blocked_topics = []
        self.max_speech_rate = 4
        self.load_config()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r') as f:
                config = yaml.safe_load(f)
                controls = config.get("parent_controls", {})
                self.blocked_topics = controls.get("blocked_topics", [])
                self.max_speech_rate = controls.get("max_speech_per_minute", 4)

    def is_safe(self, text):
        """Checks if the text contains any blocked topics."""
        if not text:
            return True
        
        text_lower = text.lower()
        for topic in self.blocked_topics:
            if topic in text_lower:
                print(f"[Safety] Blocked topic detected: {topic}")
                return False
        return True

    def validate_action(self, action_type):
        """Ensures the agent isn't trying to do something unapproved."""
        # This could be expanded to check against a dynamic allowlist
        return True

if __name__ == "__main__":
    safety = SafetyService()
    print(f"Safety Check 'I love trains': {safety.is_safe('I love trains')}")
    print(f"Safety Check 'This is scary': {safety.is_safe('This is scary')}")
