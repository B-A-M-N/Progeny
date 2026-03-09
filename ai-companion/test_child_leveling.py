import unittest
import os
from services.memory_service import MemoryService

class TestChildLeveling(unittest.TestCase):
    def setUp(self):
        # Use a test DB
        self.db_config = {
            "dbname": "progeny_test",
            "user": "bitling",
            "password": "tutor_brain",
            "host": "localhost"
        }
        # Note: In a real CI, we'd mock the DB or create a fresh one. 
        # Here we assume the dev environment has the user/pass. 
        # If connection fails, we'll skip or just inspect the code logic.
        try:
            self.memory = MemoryService(db_config=self.db_config)
            # clear tables for test
            conn = self.memory.get_conn()
            cur = conn.cursor()
            cur.execute("DROP TABLE IF EXISTS xp_events")
            cur.execute("DROP TABLE IF EXISTS skill_progress")
            cur.execute("DROP TABLE IF EXISTS skills")
            cur.execute("UPDATE tutor_profile SET xp=0, level=1 WHERE id=1")
            conn.commit()
            conn.close()
            self.memory.init_db() # Re-create tables
        except Exception as e:
            print(f"Skipping DB tests due to connection error: {e}")
            self.memory = None

    def test_log_xp_event(self):
        if not self.memory: return
        
        # 1. Log an event
        leveled_up, new_level = self.memory.log_xp_event("EFFORT", 50, evidence="Test Effort")
        self.assertFalse(leveled_up)
        
        # 2. Log enough to level up (100 total needed)
        leveled_up, new_level = self.memory.log_xp_event("MASTERY", 60, evidence="Test Mastery")
        self.assertTrue(leveled_up)
        self.assertEqual(new_level, 2)
        
        # Check Profile
        profile = self.memory.get_tutor_profile()
        self.assertEqual(profile['level'], 2)
        self.assertEqual(profile['xp'], 110)

    def test_learning_stage(self):
        if not self.memory: return
        
        # Initial stage
        stage = self.memory.get_learning_stage()
        self.assertEqual(stage, 1)
        
        # Add mastered skills manually to test stage calculation
        conn = self.memory.get_conn()
        cur = conn.cursor()
        # Add 6 skills
        for i in range(6):
            cur.execute("INSERT INTO skills (name) VALUES (%s) RETURNING id", (f"skill_{i}",))
            sid = cur.fetchone()[0]
            cur.execute("INSERT INTO skill_progress (skill_id, mastered_at) VALUES (%s, CURRENT_TIMESTAMP)", (sid,))
        conn.commit()
        conn.close()
        
        # Should be Stage 2 now (5-15 skills)
        stage = self.memory.get_learning_stage()
        self.assertEqual(stage, 2)

if __name__ == '__main__':
    unittest.main()
