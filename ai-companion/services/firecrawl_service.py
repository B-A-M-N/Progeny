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

    def search_integrated(self, query, search_service, limit=3):
        """
        1. Uses SearXNG to find the best URLs (more reliable local search).
        2. Uses Firecrawl to scrape and turn them into clean Markdown.
        """
        print(f"[FirecrawlService] Starting integrated search for: {query}")
        search_results = search_service.search(query)
        
        if not search_results or 'results' not in search_results:
            print("[FirecrawlService] SearXNG returned no results.")
            return []

        scraped_data = []
        # Take the top URLs from SearXNG
        urls = [res['url'] for res in search_results['results'][:limit]]
        
        for url in urls:
            print(f"[FirecrawlService] Deep scraping: {url}")
            data = self.scrape_url(url)
            if data and data.get('success'):
                scraped_data.append({
                    "url": url,
                    "markdown": data.get('data', {}).get('markdown', ''),
                    "title": data.get('data', {}).get('metadata', {}).get('title', 'Unknown')
                })
        
        return scraped_data

if __name__ == "__main__":
    from search_service import SearchService
    search_service = SearchService()
    # Assume SearXNG is already running or start it here for testing
    fc = FirecrawlService()
    print("Testing Integrated Search...")
    # This requires SearXNG to be active on 8080
    results = fc.search_integrated("best educational trains for kids", search_service)
    for res in results:
        print(f"FOUND: {res['title']} - {len(res['markdown'])} chars")
