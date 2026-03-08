import json
import ollama
from pydantic import BaseModel, Field
from utils.json_enforcer import JsonEnforcer


class LessonPlanSchema(BaseModel):
    hook: str = "Wow, let's learn something amazing together."
    facts: list[str] = Field(default_factory=lambda: ["Fact 1", "Fact 2", "Fact 3"])
    activity: str = "Let's do one tiny activity together."
    media_followup: str = "Optional: watch one short kid-safe clip about this topic."
    adaptation_note: str = "If overload appears, reduce prompt length and switch to drawing-choice mode."
    next_probe: str = "Pick one: what was this mostly about?"
    mode: str = "stabilize"

class LessonPlanService:
    def __init__(self, firecrawl_service, search_service, embedding_service, memory_service, agent_model="qwen2.5:0.5b"):
        self.firecrawl = firecrawl_service
        self.search_service = search_service
        self.embedding = embedding_service
        self.memory = memory_service
        self.agent_model = agent_model

    def plan_lesson_dynamic(self, subject, quality="high", live_state=None, adaptive_policy=None):
        """Researches a subject and generates a structured dynamic lesson step."""
        print(f"[LessonPlanner] Starting {quality} quality research on '{subject}'...")
        media_insight = self.memory.get_media_effectiveness(topic=subject) if self.memory else {}
        learning_ctx = self.memory.get_recent_learning_context(subject=subject, window_seconds=7200) if self.memory else {}
        adaptation = self.memory.get_adaptation_profile() if self.memory else {}
        world_anchor = (adaptation or {}).get("world_anchor", {})
        trust_model = (adaptation or {}).get("trust", {})
        
        # 1. Scaled Search (Adjust limits based on quality)
        search_limit = 3 if quality == "high" else (1 if quality == "medium" else 0)
        
        results = []
        if search_limit > 0:
            query = f"educational facts about {subject} for 5 year olds"
            results = self.firecrawl.search_integrated(query, self.search_service, limit=search_limit)
        
        # 2. Extract and Rank Fragments (Scaled intensity)
        fragments = []
        sources = []
        
        if results:
            for item in results:
                sources.append(item.get('url'))
                text = item.get('markdown', '')
                if text:
                    # Split into chunks
                    chunks = [s.strip() for s in text.split('\n') if len(s.strip()) > 50]
                    fragments.extend(chunks)
        
        # 3. Handle 'Low' Quality (Snippet-only mode)
        if quality == "low" or not fragments:
            print("[LessonPlanner] Low quality fallback - using search snippets only.")
            search_data = self.search_service.search(f"simple facts about {subject} for kids")
            if search_data and 'results' in search_data:
                fragments = [res['content'] for res in search_data['results'][:3]]
                sources = [res['url'] for res in search_data['results'][:3]]

        if not fragments:
            return "I tried to find some info, but my library is a bit dusty today!"

        # 4. Scaled Reranking
        if self.embedding and quality == "high":
            print(f"[LessonPlanner] High-quality ranking of {len(fragments)} fragments...")
            ranked = self.embedding.rerank(f"simple educational facts about {subject}", fragments, top_k=10)
        else:
            # Medium/Low skip heavy reranking
            ranked = fragments[:5]

        # 5. Synthesis: Generate the Report
        context_text = "\n---\n".join(ranked)
        
        # Neurodiversity adjustments for the report
        neuro_rules = (
            "The child is autistic and a Gestalt Language Processor. "
            "Use DECLARATIVE statements. Avoid direct questions. "
            "Focus heavily on the child's high-interest triggers (trains, dinosaurs). "
            "Explain concepts using 'chunks' of related info."
        )

        mode = str((adaptive_policy or {}).get("mode", "stabilize"))
        prompt = (
            f"Subject: {subject}\n"
            f"Context from research:\n{context_text}\n\n"
            f"MEDIA EFFECTIVENESS (optional): {json.dumps(media_insight)}\n\n"
            f"RECENT LEARNING CONTEXT (important): {json.dumps(learning_ctx)}\n\n"
            f"LIVE STATE: {json.dumps(live_state or {})}\n"
            f"ADAPTIVE POLICY: {json.dumps(adaptive_policy or {})}\n"
            f"TRUST MODEL: {json.dumps(trust_model)}\n"
            f"WORLD ANCHOR: {json.dumps(world_anchor)}\n"
            f"CURRENT MODE: {mode}\n\n"
            f"NEURODIVERSITY RULES: {neuro_rules}\n\n"
            "TASK: Return ONLY JSON with keys:\n"
            "{\n"
            "  \"hook\": string,\n"
            "  \"facts\": [string, string, string],\n"
            "  \"activity\": string,\n"
            "  \"media_followup\": string,\n"
            "  \"adaptation_note\": string,\n"
            "  \"next_probe\": string,\n"
            "  \"mode\": string\n"
            "}\n"
            "Behavior rules:\n"
            "- Keep language simple and short.\n"
            "- Respect CURRENT MODE when choosing activity/demand.\n"
            "- If WORLD ANCHOR has a location/companions, frame hook/activity inside that world.\n"
            "- If TRUST MODEL stage is safety/familiarity, use lower-demand co-play language.\n"
            "- facts must be exactly 3 entries.\n"
            "- next_probe must be optional and low-pressure.\n"
            "- Avoid clinical/diagnostic language."
        )

        print("[LessonPlanner] Synthesizing report...")
        try:
            response = ollama.generate(
                model=self.agent_model,
                prompt=prompt,
                stream=False
            )
            structured = JsonEnforcer.enforce(
                response['response'],
                LessonPlanSchema,
                default_factory=lambda: LessonPlanSchema(mode=mode)
            )
            lesson_obj = structured.model_dump()
            # Save structured report
            self.memory.save_lesson(subject, json.dumps(lesson_obj), sources=sources)
            print(f"[LessonPlanner] Lesson on '{subject}' saved.")
            return lesson_obj
            
        except Exception as e:
            print(f"[LessonPlanner] Error during synthesis: {e}")
            return LessonPlanSchema(
                hook=f"I found cool things about {subject}. Let's try one tiny step together.",
                facts=[
                    f"{subject.title()} can be learned one small piece at a time.",
                    "Short practice works better than long pressure.",
                    "You can skip and still keep learning."
                ],
                activity=f"Draw one simple thing related to {subject}.",
                mode=mode
            ).model_dump()

    def plan_lesson(self, subject, quality="high"):
        """Backward-compatible text report built from structured dynamic lesson."""
        obj = self.plan_lesson_dynamic(subject, quality=quality)
        facts = obj.get("facts", [])
        return (
            f"{obj.get('hook', '')}\n"
            f"- {facts[0] if len(facts) > 0 else ''}\n"
            f"- {facts[1] if len(facts) > 1 else ''}\n"
            f"- {facts[2] if len(facts) > 2 else ''}\n"
            f"Activity: {obj.get('activity', '')}\n"
            f"Media: {obj.get('media_followup', '')}\n"
            f"Adaptation: {obj.get('adaptation_note', '')}"
        )

if __name__ == "__main__":
    # Test script would go here
    pass
