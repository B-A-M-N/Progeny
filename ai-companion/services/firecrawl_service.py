import requests
import json
import time

class FirecrawlService:
    def __init__(self, base_url="http://localhost:3002/v1"):
        self.base_url = base_url
        self.headers = {
            "Authorization": "Bearer local-test-key", # Dummy key for local mode
            "Content-Type": "application/json"
        }

    def scrape_url(self, url, formats=["markdown"]):
        endpoint = f"{self.base_url}/scrape"
        payload = {
            "url": url,
            "formats": formats,
            "onlyMainContent": True
        }
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=30)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Firecrawl scrape error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Firecrawl connection error: {e}")
        return None

    def search(self, query, limit=5, scrape_options={"formats": ["markdown"]}):
        endpoint = f"{self.base_url}/search"
        payload = {
            "query": query,
            "limit": limit,
            "scrapeOptions": scrape_options
        }
        try:
            response = requests.post(endpoint, headers=self.headers, json=payload, timeout=60)
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Firecrawl search error {response.status_code}: {response.text}")
        except Exception as e:
            print(f"Firecrawl connection error: {e}")
        return None

if __name__ == "__main__":
    fc = FirecrawlService()
    print("Testing Firecrawl search for 'trains for kids'...")
    results = fc.search("best trains for kids learning")
    if results and results.get('success'):
        for res in results.get('data', [])[:2]:
            print(f"- {res.get('url')} (Content length: {len(res.get('markdown', ''))})")
    else:
        print("Search failed or returned no results.")
