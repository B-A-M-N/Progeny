import subprocess
import os
import time
import requests
import signal

class SearchService:
    def __init__(self, port=8080):
        self.port = port
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.searx_dir = os.path.join(self.project_root, "searxng_server")
        self.process = None

    def start(self):
        env = os.environ.copy()
        env["SEARXNG_SETTINGS_PATH"] = os.path.join(self.searx_dir, "searx/settings_local.yml")
        env["PYTHONPATH"] = f"{env.get('PYTHONPATH', '')}:{self.searx_dir}"
        
        # Command to run SearxNG from its virtualenv
        cmd = [os.path.join(self.searx_dir, "venv/bin/python"), 
               os.path.join(self.searx_dir, "searx/webapp.py")]
        
        print(f"Starting SearxNG on port {self.port}...")
        self.process = subprocess.Popen(
            cmd, 
            cwd=self.searx_dir, 
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )
        
        # Wait for the server to be ready
        max_retries = 10
        for i in range(max_retries):
            try:
                response = requests.get(f"http://127.0.0.1:{self.port}/status", timeout=2)
                if response.status_code == 200:
                    print("SearxNG is ready.")
                    return True
            except:
                pass
            time.sleep(1)
        
        print("SearxNG failed to start in time.")
        return False

    def search(self, query, engines=["google", "youtube"]):
        url = f"http://127.0.0.1:{self.port}/search"
        params = {
            "q": query,
            "format": "json",
            "engines": ",".join(engines),
            "safesearch": "2"
        }
        try:
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                return response.json()
        except Exception as e:
            print(f"Search error: {e}")
        return None

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait()
            print("SearxNG stopped.")

if __name__ == "__main__":
    search_service = SearchService()
    if search_service.start():
        print("Testing search for 'trains'...")
        results = search_service.search("steam engines for kids")
        if results and 'results' in results:
            for res in results['results'][:3]:
                print(f"- {res['title']} ({res['url']})")
        search_service.stop()
