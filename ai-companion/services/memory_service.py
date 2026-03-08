import psycopg2
from psycopg2.extras import RealDictCursor
import os
import json
import time
import numpy as np
from pgvector.psycopg2 import register_vector

class MemoryService:
    def __init__(self, db_config=None, embedding_service=None):
        self.embedding = embedding_service
        self.db_config = db_config or {
            "dbname": "progeny_brain",
            "user": "bitling",
            "password": "tutor_brain",
            "host": "localhost"
        }
        self.init_db()

    def get_conn(self):
        conn = psycopg2.connect(**self.db_config)
        register_vector(conn)
        return conn

    def health_check(self):
        """Returns (ok: bool, detail: str) for Open Brain database connectivity."""
        try:
            conn = self.get_conn()
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.fetchone()
            cursor.close()
            conn.close()
            return True, "connected"
        except Exception as e:
            return False, f"{type(e).__name__}: {e}"

    def init_db(self):
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # 1. Facts & Semantic Memory (Using pgvector)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS knowledge (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE,
                content TEXT,
                embedding vector(384), -- Dimension for fastembed default
                metadata JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 2. Events Log
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS events (
                id SERIAL PRIMARY KEY,
                timestamp REAL,
                event_type TEXT,
                vision_desc TEXT,
                state_snapshot JSONB,
                agent_response TEXT,
                metadata JSONB
            )
        ''')

        # 3. Lessons Archive
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS lessons (
                id SERIAL PRIMARY KEY,
                subject TEXT UNIQUE,
                report TEXT,
                sources JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 4. Struggles (Scaffolding Support)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS struggles (
                id SERIAL PRIMARY KEY,
                timestamp REAL,
                subject TEXT,
                description TEXT,
                severity TEXT,
                resolved BOOLEAN DEFAULT FALSE
            )
        ''')

        # 5. Tutor Profile (RPG Evolution)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tutor_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT DEFAULT 'Bitling',
                appearance TEXT DEFAULT 'default',
                attitude TEXT DEFAULT 'helpful',
                level INTEGER DEFAULT 1,
                xp INTEGER DEFAULT 0
            )
        ''')

        # 6. XP Events (Child-Centered Progress Ledger)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS xp_events (
                id SERIAL PRIMARY KEY,
                event_type TEXT, -- 'MASTERY', 'EFFORT', 'SELF_ADVOCACY', 'STRUGGLE_RESOLVED'
                amount INTEGER,
                skill_id INTEGER,
                evidence TEXT,
                timestamp REAL
            )
        ''')

        # 7. Skills & Progress (Learning Stage Tracking)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skills (
                id SERIAL PRIMARY KEY,
                name TEXT UNIQUE,
                domain TEXT, -- 'academic', 'social', 'regulation'
                criteria TEXT
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS skill_progress (
                skill_id INTEGER REFERENCES skills(id),
                attempts INTEGER DEFAULT 0,
                successes INTEGER DEFAULT 0,
                mastered_at TIMESTAMP
            )
        ''')

        # 8. Knowledge Graph (Interest-to-Concept Relationships)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id SERIAL PRIMARY KEY,
                key TEXT UNIQUE,
                label TEXT, -- 'interest', 'concept', 'skill'
                metadata JSONB
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS edges (
                id SERIAL PRIMARY KEY,
                source_id INTEGER REFERENCES nodes(id),
                target_id INTEGER REFERENCES nodes(id),
                rel_type TEXT, -- 'causes', 'related_to', 'part_of', 'bridged_by'
                metadata JSONB,
                UNIQUE(source_id, target_id, rel_type)
            )
        ''')

        # 9. Neuroadaptive Onboarding / Runtime Adaptation Profile
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS adaptation_profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                profile JSONB NOT NULL,
                source TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

        # 10. Onboarding Session Metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS onboarding_metrics (
                id SERIAL PRIMARY KEY,
                timestamp REAL,
                session_id TEXT,
                metric_key TEXT,
                metric_value DOUBLE PRECISION,
                metadata JSONB
            )
        ''')

        # 11. Media Session Tracking (watch + behavior context)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_sessions (
                id SERIAL PRIMARY KEY,
                session_id TEXT UNIQUE,
                topic TEXT,
                title TEXT,
                url TEXT,
                started_at REAL,
                ended_at REAL,
                watched_seconds DOUBLE PRECISION DEFAULT 0,
                completed BOOLEAN DEFAULT FALSE,
                baseline_state JSONB,
                end_state JSONB,
                behavior_delta JSONB,
                metadata JSONB
            )
        ''')

        # 12. Post-watch probes (optional, low-pressure)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS media_probes (
                id SERIAL PRIMARY KEY,
                timestamp REAL,
                session_id TEXT,
                probe_type TEXT,
                response_mode TEXT,
                response_latency DOUBLE PRECISION,
                success_score DOUBLE PRECISION,
                metadata JSONB
            )
        ''')
        
        cursor.execute('''
            INSERT INTO tutor_profile (id, name, appearance, attitude, level, xp)
            VALUES (1, 'Bitling', 'default', 'helpful', 1, 0)
            ON CONFLICT (id) DO NOTHING;
        ''')
        
        conn.commit()
        cursor.close()
        conn.close()

    def update_knowledge(self, key, content, confidence=1.0):
        embedding = self.embedding.embed(content) if self.embedding else None
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO knowledge (key, content, embedding, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET 
                content = EXCLUDED.content,
                embedding = EXCLUDED.embedding,
                metadata = EXCLUDED.metadata,
                updated_at = CURRENT_TIMESTAMP
        ''', (key, content, embedding, json.dumps({"confidence": confidence})))
        conn.commit()
        cursor.close()
        conn.close()

    def search_knowledge(self, query, top_k=3):
        if not self.embedding: return []
        query_vec = self.embedding.embed(query)
        
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        # Use pgvector's cosine distance operator (<=>)
        cursor.execute('''
            SELECT key, content, metadata
            FROM knowledge
            ORDER BY embedding <=> %s
            LIMIT %s
        ''', (query_vec, top_k))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results

    def get_tutor_profile(self):
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM tutor_profile WHERE id = 1')
        res = cursor.fetchone()
        cursor.close()
        conn.close()
        return res

    def log_xp_event(self, event_type, amount, skill_id=None, evidence=None):
        """
        Logs a child-centered XP event and updates the Bond Level.
        Returns: (leveled_up: bool, new_level: int)
        """
        profile = self.get_tutor_profile()
        new_xp = profile['xp'] + amount
        # Bond Level formula: (XP // 100) + 1
        new_level = (new_xp // 100) + 1
        
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # 1. Log the event
        cursor.execute('''
            INSERT INTO xp_events (event_type, amount, skill_id, evidence, timestamp)
            VALUES (%s, %s, %s, %s, %s)
        ''', (event_type, amount, skill_id, evidence, time.time()))
        
        # 2. Update Profile
        cursor.execute('UPDATE tutor_profile SET xp = %s, level = %s WHERE id = 1', (new_xp, new_level))
        
        conn.commit()
        cursor.close()
        conn.close()
        
        return new_level > profile['level'], new_level

    def resolve_struggle(self, struggle_id):
        """
        Marks a struggle as resolved and awards a major XP milestone.
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('UPDATE struggles SET resolved = TRUE WHERE id = %s', (struggle_id,))
        conn.commit()
        cursor.close()
        conn.close()
        
        # Award Major Milestone XP
        return self.log_xp_event('STRUGGLE_RESOLVED', 50, evidence=f"Resolved struggle ID {struggle_id}")

    def get_learning_stage(self):
        """
        Calculates Readiness Stage (1-3) based on mastered skills.
        Stage 1 (Foundational): < 5 mastered
        Stage 2 (Emerging): 5-15 mastered
        Stage 3 (Fluent): > 15 mastered
        """
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('SELECT COUNT(*) FROM skill_progress WHERE mastered_at IS NOT NULL')
        mastered_count = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        if mastered_count < 5: return 1
        if mastered_count <= 15: return 2
        return 3

    def record_event(self, event_type, vision_desc, state_snapshot, agent_response, metadata=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO events (timestamp, event_type, vision_desc, state_snapshot, agent_response, metadata)
            VALUES (%s, %s, %s, %s, %s, %s)
        ''', (time.time(), event_type, vision_desc, json.dumps(state_snapshot), agent_response, json.dumps(metadata)))
        conn.commit()
        cursor.close()
        conn.close()

    def get_lesson(self, subject):
        """Retrieves a previously planned lesson from the database."""
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute("SELECT report FROM lessons WHERE subject = %s", (subject,))
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        return row['report'] if row else None

    def save_lesson(self, subject, report, sources=None):
        """Saves a new lesson report."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO lessons (subject, report, sources) 
            VALUES (%s, %s, %s)
            ON CONFLICT (subject) DO UPDATE SET 
                report = EXCLUDED.report,
                sources = EXCLUDED.sources,
                created_at = CURRENT_TIMESTAMP
        ''', (subject, report, json.dumps(sources) if sources else "[]"))
        conn.commit()
        cursor.close()
        conn.close()

    def record_struggle(self, subject, description, severity="medium"):
        """Records a new learning or developmental struggle."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO struggles (timestamp, subject, description, severity)
            VALUES (%s, %s, %s, %s)
        ''', (time.time(), subject, description, severity))
        conn.commit()
        cursor.close()
        conn.close()

    def get_unresolved_struggles(self):
        """Returns all struggles that haven't been resolved yet."""
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT * FROM struggles WHERE resolved = FALSE ORDER BY timestamp DESC')
        res = cursor.fetchall()
        cursor.close()
        conn.close()
        return res

    def upsert_adaptation_profile(self, profile, source="unknown"):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO adaptation_profile (id, profile, source, updated_at)
            VALUES (1, %s, %s, CURRENT_TIMESTAMP)
            ON CONFLICT (id) DO UPDATE SET
                profile = EXCLUDED.profile,
                source = EXCLUDED.source,
                updated_at = CURRENT_TIMESTAMP
        ''', (json.dumps(profile or {}), source))
        conn.commit()
        cursor.close()
        conn.close()

    def get_adaptation_profile(self):
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('SELECT profile FROM adaptation_profile WHERE id = 1')
        row = cursor.fetchone()
        cursor.close()
        conn.close()
        if not row:
            return None
        return row.get("profile")

    def record_onboarding_metric(self, session_id, metric_key, metric_value, metadata=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO onboarding_metrics (timestamp, session_id, metric_key, metric_value, metadata)
            VALUES (%s, %s, %s, %s, %s)
        ''', (
            time.time(),
            str(session_id or ""),
            str(metric_key or ""),
            float(metric_value or 0.0),
            json.dumps(metadata or {})
        ))
        conn.commit()
        cursor.close()
        conn.close()

    def start_media_session(self, session_id, topic, title="", url="", baseline_state=None, metadata=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO media_sessions (
                session_id, topic, title, url, started_at, baseline_state, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (session_id) DO UPDATE SET
                topic = EXCLUDED.topic,
                title = EXCLUDED.title,
                url = EXCLUDED.url,
                started_at = EXCLUDED.started_at,
                baseline_state = EXCLUDED.baseline_state,
                metadata = EXCLUDED.metadata
        ''', (
            str(session_id or ""),
            str(topic or ""),
            str(title or ""),
            str(url or ""),
            time.time(),
            json.dumps(baseline_state or {}),
            json.dumps(metadata or {})
        ))
        conn.commit()
        cursor.close()
        conn.close()

    def end_media_session(self, session_id, watched_seconds=0.0, completed=False, end_state=None, behavior_delta=None, metadata=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            UPDATE media_sessions
            SET ended_at = %s,
                watched_seconds = %s,
                completed = %s,
                end_state = %s,
                behavior_delta = %s,
                metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
            WHERE session_id = %s
        ''', (
            time.time(),
            float(watched_seconds or 0.0),
            bool(completed),
            json.dumps(end_state or {}),
            json.dumps(behavior_delta or {}),
            json.dumps(metadata or {}),
            str(session_id or "")
        ))
        conn.commit()
        cursor.close()
        conn.close()

    def record_media_probe(self, session_id, probe_type, response_mode="choice", response_latency=0.0, success_score=0.5, metadata=None):
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO media_probes (
                timestamp, session_id, probe_type, response_mode, response_latency, success_score, metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        ''', (
            time.time(),
            str(session_id or ""),
            str(probe_type or ""),
            str(response_mode or "choice"),
            float(response_latency or 0.0),
            float(success_score or 0.0),
            json.dumps(metadata or {})
        ))
        conn.commit()
        cursor.close()
        conn.close()

    def get_media_effectiveness(self, topic=None, limit=20):
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        if topic:
            cursor.execute('''
                SELECT
                    ms.topic,
                    count(*) AS sessions,
                    avg(ms.watched_seconds) AS avg_watched_seconds,
                    avg(CASE WHEN ms.completed THEN 1 ELSE 0 END) AS completion_rate,
                    avg(mp.success_score) AS avg_probe_score,
                    avg(mp.response_latency) AS avg_probe_latency
                FROM media_sessions ms
                LEFT JOIN media_probes mp ON mp.session_id = ms.session_id
                WHERE ms.topic = %s
                GROUP BY ms.topic
                LIMIT 1
            ''', (str(topic),))
            row = cursor.fetchone()
            cursor.close()
            conn.close()
            return row or {}
        cursor.execute('''
            SELECT
                ms.topic,
                count(*) AS sessions,
                avg(ms.watched_seconds) AS avg_watched_seconds,
                avg(CASE WHEN ms.completed THEN 1 ELSE 0 END) AS completion_rate,
                avg(mp.success_score) AS avg_probe_score,
                avg(mp.response_latency) AS avg_probe_latency
            FROM media_sessions ms
            LEFT JOIN media_probes mp ON mp.session_id = ms.session_id
            GROUP BY ms.topic
            ORDER BY sessions DESC, avg_probe_score DESC NULLS LAST
            LIMIT %s
        ''', (int(limit),))
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows

    def get_recent_learning_context(self, subject=None, window_seconds=3600):
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        since_ts = time.time() - float(window_seconds)

        # Recent struggles
        if subject:
            cursor.execute('''
                SELECT description, severity, timestamp
                FROM struggles
                WHERE timestamp >= %s AND (subject = %s OR subject = 'general')
                ORDER BY timestamp DESC
                LIMIT 20
            ''', (since_ts, str(subject)))
        else:
            cursor.execute('''
                SELECT description, severity, timestamp
                FROM struggles
                WHERE timestamp >= %s
                ORDER BY timestamp DESC
                LIMIT 20
            ''', (since_ts,))
        struggles = cursor.fetchall()

        # Recent onboarding/interaction metrics
        cursor.execute('''
            SELECT metric_key, avg(metric_value) AS avg_value, count(*) AS n
            FROM onboarding_metrics
            WHERE timestamp >= %s
            GROUP BY metric_key
            ORDER BY n DESC
            LIMIT 20
        ''', (since_ts,))
        onboarding_metrics = cursor.fetchall()

        # Recent event stats
        cursor.execute('''
            SELECT event_type, count(*) AS n
            FROM events
            WHERE timestamp >= %s
            GROUP BY event_type
            ORDER BY n DESC
            LIMIT 20
        ''', (since_ts,))
        event_counts = cursor.fetchall()

        # Adaptation profile snapshot
        cursor.execute('SELECT profile FROM adaptation_profile WHERE id = 1')
        row = cursor.fetchone()
        adaptation = row.get("profile") if row else {}

        cursor.close()
        conn.close()
        return {
            "since_ts": since_ts,
            "subject": subject,
            "recent_struggles": struggles or [],
            "onboarding_metrics": onboarding_metrics or [],
            "recent_event_counts": event_counts or [],
            "adaptation_profile": adaptation or {}
        }

    # --- Knowledge Graph Methods ---

    def add_node(self, key, label, metadata=None):
        """Adds or updates a node in the knowledge graph."""
        conn = self.get_conn()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO nodes (key, label, metadata)
            VALUES (%s, %s, %s)
            ON CONFLICT (key) DO UPDATE SET
                label = EXCLUDED.label,
                metadata = EXCLUDED.metadata
            RETURNING id
        ''', (key, label, json.dumps(metadata) if metadata else "{}"))
        node_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return node_id

    def add_edge(self, source_key, target_key, rel_type, metadata=None):
        """Creates a relationship between two nodes."""
        conn = self.get_conn()
        cursor = conn.cursor()
        
        # Get Node IDs (Ensure they exist)
        cursor.execute('SELECT id FROM nodes WHERE key = %s', (source_key,))
        src_row = cursor.fetchone()
        cursor.execute('SELECT id FROM nodes WHERE key = %s', (target_key,))
        tgt_row = cursor.fetchone()

        if not src_row or not tgt_row:
            cursor.close()
            conn.close()
            return None # Or handle error

        cursor.execute('''
            INSERT INTO edges (source_id, target_id, rel_type, metadata)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (source_id, target_id, rel_type) DO UPDATE SET
                metadata = EXCLUDED.metadata
        ''', (src_row[0], tgt_row[0], rel_type, json.dumps(metadata) if metadata else "{}"))
        
        conn.commit()
        cursor.close()
        conn.close()

    def get_related_nodes(self, key):
        """Retrieves nodes connected to the given node key."""
        conn = self.get_conn()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute('''
            SELECT n2.key, n2.label, e.rel_type, e.metadata
            FROM nodes n1
            JOIN edges e ON n1.id = e.source_id
            JOIN nodes n2 ON e.target_id = n2.id
            WHERE n1.key = %s
            UNION
            SELECT n1.key, n1.label, e.rel_type, e.metadata
            FROM nodes n2
            JOIN edges e ON n2.id = e.target_id
            JOIN nodes n1 ON e.source_id = n1.id
            WHERE n2.key = %s
        ''', (key, key))
        results = cursor.fetchall()
        cursor.close()
        conn.close()
        return results

    def hybrid_retrieval(self, query, top_k=3):
        """
        Combines vector similarity with graph traversal for deep context.
        """
        # 1. Vector Search
        vector_results = self.search_knowledge(query, top_k=top_k)
        
        # 2. Graph Expansion
        graph_context = []
        seen_keys = set()
        
        for res in vector_results:
            key = res['key']
            seen_keys.add(key)
            related = self.get_related_nodes(key)
            for r in related:
                if r['key'] not in seen_keys:
                    graph_context.append(r)
                    seen_keys.add(r['key'])
        
        return {
            "semantic_matches": vector_results,
            "related_concepts": graph_context
        }
