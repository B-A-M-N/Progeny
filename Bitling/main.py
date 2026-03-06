import threading
import sys
from core.bitling import Bitling

def terminal_input_loop(bitling):
    print("Bitling is active! Type your message in the terminal to talk to it.")
    while True:
        try:
            user_input = input("> ")
            if user_input.lower() in ["exit", "quit"]:
                import gi
                gi.require_version('Gtk', '3.0')
                from gi.repository import Gtk
                Gtk.main_quit()
                break
            bitling.interact(user_input)
        except EOFError:
            break

if __name__ == "__main__":
    bitling = Bitling()
    
    # Start terminal input in a separate thread
    input_thread = threading.Thread(target=terminal_input_loop, args=(bitling,), daemon=True)
    input_thread.start()
    
    bitling.run()
