from fastembed import TextEmbedding, TextCrossEncoder
import numpy as np

class EmbeddingService:
    def __init__(self, embed_model="BAAI/bge-small-en-v1.5", rerank_model="jinaai/jina-reranker-v1-turbo-en"):
        print(f"[Embedding] Loading embedding model: {embed_model}")
        self.embedding_model = TextEmbedding(model_name=embed_model)
        
        print(f"[Embedding] Loading Turbo Reranker: {rerank_model}")
        try:
            # Use TextCrossEncoder for optimized CPU reranking
            self.reranker = TextCrossEncoder(model_name=rerank_model)
        except Exception as e:
            print(f"Warning: Turbo Reranker failed to load: {e}. Falling back to embedding similarity.")
            self.reranker = None

    def embed(self, texts):
        """
        Embeds a list of texts.
        Returns a list of numpy arrays.
        """
        # fastembed returns a generator, so we convert to list
        embeddings = list(self.embedding_model.embed(texts))
        return embeddings

    def rerank(self, query, documents, top_k=3):
        """
        Uses a Cross-Encoder (reranker) to accurately rank documents.
        """
        if not documents:
            return []
            
        if self.reranker:
            # fastembed rerank returns a generator of (score, doc) tuples
            results = list(self.reranker.rerank(query, documents))
            # Sort by score descending (it usually returns them sorted but we ensure)
            results.sort(key=lambda x: x[0], reverse=True)
            return [doc for score, doc in results[:top_k]]
        else:
            # Fallback to simple embedding similarity
            return self.rank_sim(query, documents, top_k)

    def rank_sim(self, query, documents, top_k=3):
        """
        Fallback: Ranks documents based on cosine similarity to the query embeddings.
        """
        query_embedding = list(self.embedding_model.embed([query]))[0]
        doc_embeddings = list(self.embedding_model.embed(documents))
        
        scores = []
        for i, doc_emb in enumerate(doc_embeddings):
            # Cosine similarity
            norm_product = np.linalg.norm(query_embedding) * np.linalg.norm(doc_emb)
            if norm_product == 0:
                score = 0
            else:
                score = np.dot(query_embedding, doc_emb) / norm_product
            scores.append((score, documents[i]))
        
        # Sort by score descending
        scores.sort(key=lambda x: x[0], reverse=True)
        
        return [doc for score, doc in scores[:top_k]]

if __name__ == "__main__":
    svc = EmbeddingService()
    docs = ["Trains are fast", "Dinosaurs are big", "Steam engines are railway vehicles", "I like ice cream"]
    
    # Use Cross-Encoder reranking
    ranked = svc.rerank("railway vehicles", docs)
    print(f"Reranked (Cross-Encoder) for 'railway vehicles': {ranked}")
    
    # Use Embedding similarity
    sim_ranked = svc.rank_sim("railway vehicles", docs)
    print(f"Sim-Ranked (Bi-Encoder) for 'railway vehicles': {sim_ranked}")
