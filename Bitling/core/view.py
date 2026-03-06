import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib, Cairo
import math

class BitlingView(Gtk.Window):
    def __init__(self):
        super().__init__(type=Gtk.WindowType.POPUP)
        self.set_title("Bitling")
        self.set_keep_above(True)
        self.set_app_paintable(True)
        self.set_visual(self.get_screen().get_rgba_visual())
        
        # Initial size and position
        self.width, self.height = 120, 120
        self.set_size_request(self.width, self.height)
        
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_button_press)
        self.connect("button-release-event", self.on_button_release)
        self.connect("motion-notify-event", self.on_motion_notify)
        
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK |
                        Gdk.EventMask.BUTTON_RELEASE_MASK |
                        Gdk.EventMask.POINTER_MOTION_MASK)

        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        self.frame = 0
        self.action = "[IDLE]"
        self.target_x = 0
        self.velocity_x = 0
        self.velocity_y = 0
        
        # Screen dimensions
        self.screen_width = Gdk.Screen.get_default().get_width()
        self.screen_height = Gdk.Screen.get_default().get_height()
        
        self.sprites = {}
        self.load_sprites()
        
        # Position at bottom right initially
        self.move(self.screen_width - 200, self.screen_height - 200)

        # Animation timer
        GLib.timeout_add(150, self.update_animation)

    def load_sprites(self):
        try:
            from gi.repository import GdkPixbuf
            
            def load(name):
                pb = GdkPixbuf.Pixbuf.new_from_file(f"assets/{name}.png")
                # Scale down if too big (robot is ~100px usually, let's make it 80px)
                w, h = pb.get_width(), pb.get_height()
                scale = 80 / max(w, h)
                return pb.scale_simple(int(w * scale), int(h * scale), GdkPixbuf.InterpType.BILINEAR)

            self.sprites["idle"] = [load("idle1"), load("idle2")]
            self.sprites["walk"] = [load("walk1"), load("walk2")]
            self.sprites["jump"] = [load("idle2")] # Use open eyes/up pose for jump
            self.sprites["sleep"] = [load("idle1")] # Close enough for now
            
            # Update window size to match sprite
            w = self.sprites["idle"][0].get_width()
            h = self.sprites["idle"][0].get_height()
            self.resize(w + 20, h + 20)
            
        except Exception as e:
            print(f"Failed to load sprites: {e}")
            self.sprites = None

    def on_draw(self, widget, cr):
        cr.set_source_rgba(0, 0, 0, 0)
        cr.set_operator(Cairo.OPERATOR_SOURCE)
        cr.paint()
        cr.set_operator(Cairo.OPERATOR_OVER)

        if not self.sprites:
            # Fallback drawing
            self.draw_fallback(cr)
            return

        # Determine sprite frame
        current_sprites = self.sprites.get("idle")
        if self.action == "[WALK]": current_sprites = self.sprites["walk"]
        elif self.action == "[JUMP]": current_sprites = self.sprites["jump"]
        
        frame_idx = (self.frame // 2) % len(current_sprites)
        pixbuf = current_sprites[frame_idx]
        
        Gdk.cairo_set_source_pixbuf(cr, pixbuf, 10, 10)
        cr.paint()

    def draw_fallback(self, cr):
        # Draw Bitling Body (Placeholder)
        bounce = math.sin(self.frame * 0.5) * 5
        # ... (Previous drawing code truncated for brevity, but we just draw a circle)
        cr.set_source_rgb(0.4, 0.7, 1.0)
        cr.arc(60, 60 + bounce, 40, 0, 2 * math.pi)
        cr.fill()

    def update_animation(self):
        self.frame += 1
        
        if self.action == "[WALK]":
            x, y = self.get_position()
            # Move towards a target or just wander
            step = 2
            if x < 50: self.velocity_x = step
            elif x > self.screen_width - 150: self.velocity_x = -step
            
            if self.velocity_x == 0: self.velocity_x = step
            
            self.move(x + self.velocity_x, y)
        
        elif self.action == "[JUMP]":
            x, y = self.get_position()
            # Simple jump arc
            self.velocity_y += 2 # Gravity
            self.move(x, y + self.velocity_y)
            
            if y > self.screen_height - 200: # Ground
                self.action = "[IDLE]"
                self.velocity_y = 0

        self.queue_draw()
        return True

    def on_button_press(self, widget, event):
        if event.button == 1:
            self.drag_data["x"] = event.x
            self.drag_data["y"] = event.y
            self.drag_data["dragging"] = True
            self.action = "[JUMP]" # Look surprised/held
            self.velocity_y = 0
        elif event.button == 3:
            Gtk.main_quit()

    def on_button_release(self, widget, event):
        if event.button == 1:
            self.drag_data["dragging"] = False
            # Toss effect
            self.velocity_y = -10 

    def on_motion_notify(self, widget, event):
        if self.drag_data["dragging"]:
            x, y = self.get_position()
            self.move(int(x + event.x - self.drag_data["x"]), 
                      int(y + event.y - self.drag_data["y"]))
