import json
import ollama

class LessonPlanService:
    def __init__(self, firecrawl_service, embedding_service, memory_service, agent_model="qwen2.5:0.5b"):
        self.firecrawl = firecrawl_service
        self.embedding = embedding_service
        self.memory = memory_service
        self.agent_model = agent_model

    def plan_lesson(self, subject):
        """Researches a subject and generates a lesson report for the kid."""
        print(f"[LessonPlanner] Starting deep research on '{subject}'...")
        
        # 1. Broad Search
        query = f"educational facts about {subject} for 5 year olds"
        results = self.firecrawl.search(query, limit=5)
        
        if not results or not results.get('success'):
            return "I tried to find some info, but my library is a bit dusty today!"

        # 2. Extract and Rank Fragments
        fragments = []
        sources = []
        for item in results.get('data', []):
            sources.append(item.get('url'))
            text = item.get('markdown', '') or item.get('description', '')
            if text:
                # Split into chunks (roughly paragraphs or sentences)
                chunks = [s.strip() for s in text.split('\n') if len(s.strip()) > 50]
                fragments.extend(chunks)

        if not fragments:
            return f"I found some pages about {subject}, but they were a bit too complicated!"

        # Rank fragments by relevance to 'educational facts for kids'
        if self.embedding:
            print(f"[LessonPlanner] Ranking {len(fragments)} fragments...")
            ranked = self.embedding.rerank(f"simple educational facts about {subject}", fragments, top_k=10)
        else:
            ranked = fragments[:10]

        # 3. Synthesis: Generate the Report using the LLM
        context_text = "\n---\n".join(ranked)
        prompt = (
            f"Subject: {subject}\n"
            f"Context from research:\n{context_text}\n\n"
            "TASK: Write a 'Lesson Report' for a 5-year-old child. "
            "Structure it with:\n"
            "1. A hook (Wow factor!)\n"
            "2. Three simple but amazing facts (explained with analogies a child understands)\n"
            "3. One interactive question to ask the child later.\n"
            "Tone: Enthusiastic, clear, very simple language. Avoid jargon."
        )

        print("[LessonPlanner] Synthesizing report...")
        try:
            response = ollama.generate(
                model=self.agent_model,
                prompt=prompt,
                stream=False
            )
            report = response['response']
            
            # 4. Save to Memory
            self.memory.save_lesson(subject, report, sources=sources)
            print(f"[LessonPlanner] Lesson on '{subject}' saved.")
            return report
            
        except Exception as e:
            print(f"[LessonPlanner] Error during synthesis: {e}")
            return f"I learned a lot about {subject}, but I'm still organizing my thoughts!"

if __name__ == "__main__":
    # Test script would go here
    pass
