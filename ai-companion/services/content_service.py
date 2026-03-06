import random
from services.firecrawl_service import FirecrawlService
from services.safety_service import SafetyService

class ContentService:
    def __init__(self, firecrawl_service=None, safety_service=None, embedding_service=None):
        self.firecrawl = firecrawl_service or FirecrawlService()
        self.safety = safety_service or SafetyService()
        self.embedding = embedding_service

        # Simple cache to avoid repeated searches in short time
        self.fact_cache = {}

    def get_fun_fact(self, topic):
        """Finds a kid-safe fun fact about the given topic."""
        # check cache first
        if topic in self.fact_cache:
            facts = self.fact_cache[topic]
            if facts:
                return random.choice(facts)

        query = f"fun facts for kids about {topic}"
        print(f"[Content] Searching for: {query}")

        results = self.firecrawl.search(query, limit=3)
        if not results or not results.get('success'):
            return f"Did you know {topic} are amazing? Let's learn more together!"

        facts = []
        for item in results.get('data', []):
            # Extract text snippet from markdown or description
            text = item.get('markdown', '') or item.get('description', '')
            if not text:
                continue

            # Basic cleaning and safety check
            sentences = text.split('. ')
            for s in sentences:
                s = s.strip()
                if len(s) > 20 and len(s) < 150 and self.safety.is_safe(s):
                    facts.append(s)

        if facts:
            # Rerank if embedding service is available
            if self.embedding:
                print(f"[Content] Reranking {len(facts)} facts for topic: {topic}")
                ranked_facts = self.embedding.rerank(f"fun fact about {topic}", facts, top_k=5)
                # Update cache with ranked facts
                self.fact_cache[topic] = ranked_facts
                return ranked_facts[0] if ranked_facts else random.choice(facts)

            self.fact_cache[topic] = facts
            return random.choice(facts)

        return f"I know {topic} are super cool! What do you like about them?"
    def find_video_topic(self, interest):
        """Finds a safe video topic or title (placeholder for real video search)."""
        # In a real implementation, this would query YouTube API or scrape via Firecrawl
        # For now, we return a search query the parent could use or the agent can mention
        return f"educational video about {interest} for kids"

if __name__ == "__main__":
    content = ContentService()
    print("Fact about Trains:", content.get_fun_fact("trains"))
    print("Fact about Dinosaurs:", content.get_fun_fact("dinosaurs"))
