import subprocess
from core.brain import Brain
from core.view import BitlingView
from core.voice import Voice
from gi.repository import GLib

class Bitling:
    def __init__(self):
        self.brain = Brain(model="qwen3-vl:4b")
        self.voice = Voice()
        self.view = BitlingView()
        self.view.show_all()
        
        # Initial greeting
        GLib.timeout_add(1000, self.initial_greeting)
        
        # Random autonomous behavior timer
        GLib.timeout_add_seconds(30, self.autonomous_tick)

    def initial_greeting(self):
        self.say("Hello! I am Bitling. I'm living on your screen now.")
        return False

    def say(self, text):
        print(f"Bitling: {text}")
        self.voice.speak(text)

    def interact(self, user_input):
        reply, action = self.brain.think(user_input)
        self.view.action = action
        self.say(reply)

    def autonomous_tick(self):
        action = self.brain.get_mood_action()
        self.view.action = action
        # Maybe say something occasionally
        return True

    def run(self):
        import gi
        gi.require_version('Gtk', '3.0')
        from gi.repository import Gtk
        Gtk.main()
