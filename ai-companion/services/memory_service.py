import sqlite3
import os
import json
import time
import numpy as np

class MemoryService:
    def __init__(self, db_path=".gemini_security/second_brain.db", embedding_service=None):
        # Resolve path relative to project root
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.db_path = os.path.join(self.project_root, db_path)
        self.embedding = embedding_service
        
        # Ensure directory exists
        db_dir = os.path.dirname(self.db_path)
        if not os.path.exists(db_dir):
            os.makedirs(db_dir)
            
        self.init_db()

    def init_db(self):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Events table: stores everything that happens (loop history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                event_type TEXT,
                vision_desc TEXT,
                state_snapshot TEXT,
                agent_response TEXT,
                metadata TEXT
            )
        ''')
        
        # Knowledge table: stores long-term facts/interests about the child
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE,
                value TEXT,
                confidence REAL,
                last_updated REAL
            )
        ''')
        
        # Embeddings for knowledge
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_embeddings (
                key TEXT PRIMARY KEY,
                embedding BLOB,
                FOREIGN KEY(key) REFERENCES knowledge(key) ON DELETE CASCADE
            )
        ''')
        
        # Lessons table: stores generated lesson plans/reports
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT UNIQUE,
                report TEXT,
                sources TEXT, -- JSON list of URLs
                created_at REAL
            )
        ''')

        # Struggles table: tracks difficulties the child is having
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS struggles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp REAL,
                subject TEXT,
                description TEXT,
                severity TEXT, -- 'low', 'medium', 'high'
                resolved BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()

    def record_event(self, event_type, vision_desc, state_snapshot, agent_response, metadata=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO events (timestamp, event_type, vision_desc, state_snapshot, agent_response, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            time.time(),
            event_type,
            vision_desc,
            json.dumps(state_snapshot),
            agent_response,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()

    def update_knowledge(self, key, value, confidence=1.0):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO knowledge (key, value, confidence, last_updated)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                confidence = excluded.confidence,
                last_updated = excluded.last_updated
        ''', (key, value, confidence, time.time()))
        
        conn.commit()
        conn.close()

        # Update embedding if service is available
        if self.embedding:
            try:
                emb = self.embedding.embed([value])[0]
                blob = emb.tobytes()
                conn = sqlite3.connect(self.db_path)
                c = conn.cursor()
                c.execute('INSERT OR REPLACE INTO knowledge_embeddings (key, embedding) VALUES (?, ?)', (key, blob))
                conn.commit()
                conn.close()
            except Exception as e:
                print(f"[Memory] Embedding failed for {key}: {e}")

    def get_knowledge(self, key):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT value FROM knowledge WHERE key = ?', (key,))
        result = cursor.fetchone()
        conn.close()
        return result[0] if result else None
        
    def search_knowledge(self, query, top_k=3):
        if not self.embedding:
            print("[Memory] No embedding service available for semantic search")
            return []
        
        try:
            # Embed query
            query_emb = self.embedding.embed([query])[0]
            
            # Fetch all embeddings
            conn = sqlite3.connect(self.db_path)
            c = conn.cursor()
            c.execute('SELECT key, embedding FROM knowledge_embeddings')
            rows = c.fetchall()
            conn.close()
            
            if not rows:
                return []
            
            scores = []
            for key, blob in rows:
                doc_emb = np.frombuffer(blob, dtype=np.float32)
                # Cosine similarity
                norm_product = np.linalg.norm(query_emb) * np.linalg.norm(doc_emb)
                if norm_product == 0:
                    score = 0
                else:
                    score = np.dot(query_emb, doc_emb) / norm_product
                scores.append((score, key))
                
            scores.sort(key=lambda x: x[0], reverse=True)
            
            results = []
            for score, key in scores[:top_k]:
                val = self.get_knowledge(key)
                results.append({"key": key, "value": val, "score": float(score)})
                
            return results
        except Exception as e:
            print(f"[Memory] Semantic search failed: {e}")
            return []

    def get_recent_events(self, limit=5):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM events ORDER BY timestamp DESC LIMIT ?', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def save_lesson(self, subject, report, sources=None):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT OR REPLACE INTO lessons (subject, report, sources, created_at)
            VALUES (?, ?, ?, ?)
        ''', (subject, report, json.dumps(sources) if sources else None, time.time()))
        conn.commit()
        conn.close()

    def get_lesson(self, subject):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT report, sources FROM lessons WHERE subject = ?', (subject,))
        result = cursor.fetchone()
        conn.close()
        if result:
            return {"report": result[0], "sources": json.loads(result[1]) if result[1] else []}
        return None

    def record_struggle(self, subject, description, severity='medium'):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO struggles (timestamp, subject, description, severity)
            VALUES (?, ?, ?, ?)
        ''', (time.time(), subject, description, severity))
        conn.commit()
        conn.close()

    def get_unresolved_struggles(self, limit=5):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM struggles WHERE resolved = 0 ORDER BY timestamp DESC LIMIT ?', (limit,))
        results = cursor.fetchall()
        conn.close()
        return results

    def resolve_struggle(self, struggle_id):
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute('UPDATE struggles SET resolved = 1 WHERE id = ?', (struggle_id,))
        conn.commit()
        conn.close()

if __name__ == "__main__":
    # Dummy embedding service for testing if fastembed not installed
    class DummyEmbedding:
        def embed(self, texts):
            import numpy as np
            return [np.random.rand(384).astype(np.float32) for _ in texts]
            
    memory = MemoryService(embedding_service=DummyEmbedding())
    memory.record_event("test", "A child is playing with a train", {"interest": "trains"}, "Hello, that's a cool train!")
    memory.update_knowledge("favorite_train", "Big Boy Steam Engine")
    
    print("Recent Events:", memory.get_recent_events(1))
    print("Favorite Train:", memory.get_knowledge("favorite_train"))
    print("Semantic Search 'steam engine':", memory.search_knowledge("steam engine"))
