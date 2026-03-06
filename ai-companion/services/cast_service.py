import pychromecast
import time

class CastService:
    def __init__(self, target_name=None, host=None):
        self.target_name = target_name
        self.host = host
        self.cast = None

    def discover(self, timeout=5):
        if self.host:
            print(f"Connecting to host: {self.host}")
            # get_chromecast_from_host expects (ip, port, uuid, model, friendly)
            host_tuple = (self.host, 8009, None, "Google Home Mini", "Portal speaker")
            self.cast = pychromecast.get_chromecast_from_host(host_tuple)
            self.cast.wait()
            return True

        print("Discovering Chromecasts...")
        chromecasts, browser = pychromecast.get_chromecasts(timeout=timeout)
        
        if not chromecasts:
            print("No Chromecasts found.")
            return False

        if self.target_name:
            self.cast = next((c for c in chromecasts if c.name == self.target_name), None)
        else:
            self.cast = next((c for c in chromecasts if "Home Mini" in c.model_name or "Google Home" in c.model_name), chromecasts[0])
        
        if self.cast:
            print(f"Found cast device: {self.cast.name}")
            self.cast.wait()
            return True
        return False

    def play_audio(self, url):
        if not self.cast:
            if not self.discover():
                return False

        print(f"Playing audio: {url}")
        mc = self.cast.media_controller
        mc.play_media(url, 'audio/wav')
        mc.block_until_active()
        print("Audio cast successfully.")
        return True

if __name__ == "__main__":
    caster = CastService()
    if caster.discover():
        print(f"Ready to cast to {caster.cast.name}")
    else:
        print("Discovery failed.")
