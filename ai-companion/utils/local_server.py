import http.server
import socketserver
import threading
import os
import socket
from functools import partial

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except Exception:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

class LocalAudioServer:
    def __init__(self, port=8000, directory="data"):
        self.port = port
        # Resolve the directory relative to the project root
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.directory = os.path.join(project_root, directory)
        self.ip = get_local_ip()
        self.httpd = None
        self.thread = None

    def start(self):
        if not os.path.exists(self.directory):
            os.makedirs(self.directory)

        # In Python 3.7+, SimpleHTTPRequestHandler supports the 'directory' argument in its constructor.
        # We use partial to pass this argument when the server instantiates the handler.
        handler_factory = partial(http.server.SimpleHTTPRequestHandler, directory=self.directory)

        # Allow address reuse to prevent hanging if port is in TIME_WAIT
        socketserver.TCPServer.allow_reuse_address = True
        self.httpd = socketserver.TCPServer(("", self.port), handler_factory)
        self.thread = threading.Thread(target=self.httpd.serve_forever)
        self.thread.daemon = True
        self.thread.start()
        print(f"Serving audio at http://{self.ip}:{self.port} (root: {self.directory})")

    def stop(self):
        if self.httpd:
            self.httpd.shutdown()
            self.httpd.server_close()
            print("Audio server stopped.")

    def get_url(self, filename):
        return f"http://{self.ip}:{self.port}/{filename}"

if __name__ == "__main__":
    import time
    server = LocalAudioServer(port=8000, directory="data")
    server.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
