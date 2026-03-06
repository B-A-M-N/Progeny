import unittest
from unittest.mock import MagicMock
from services.memory_service import MemoryService
import numpy as np
import os
import sqlite3

class TestMemoryService(unittest.TestCase):
    def setUp(self):
        # Use temporary DB
        self.db_path = "test_second_brain.db"
        self.mock_embedding = MagicMock()
        self.memory = MemoryService(self.db_path, self.mock_embedding)

    def tearDown(self):
        if os.path.exists(self.memory.db_path):
            os.remove(self.memory.db_path)

    def test_update_knowledge_with_embedding(self):
        # Mock embed return
        self.mock_embedding.embed.return_value = [np.array([1.0, 0.0], dtype=np.float32)]
        
        self.memory.update_knowledge("key", "value")
        
        # Verify call
        self.mock_embedding.embed.assert_called_with(["value"])
        
        # Verify DB
        conn = sqlite3.connect(self.memory.db_path)
        c = conn.cursor()
        c.execute("SELECT embedding FROM knowledge_embeddings WHERE key='key'")
        row = c.fetchone()
        self.assertIsNotNone(row)
        stored_emb = np.frombuffer(row[0], dtype=np.float32)
        np.testing.assert_array_equal(stored_emb, np.array([1.0, 0.0], dtype=np.float32))
        conn.close()

    def test_search_knowledge(self):
        # Setup data
        # side_effect returns for sequential calls: update(k1), update(k2), search(query)
        self.mock_embedding.embed.side_effect = [
            [np.array([1.0, 0.0], dtype=np.float32)], # for k1 (matches query)
            [np.array([0.0, 1.0], dtype=np.float32)], # for k2 (orthogonal)
            [np.array([1.0, 0.0], dtype=np.float32)]  # for query
        ]
        
        self.memory.update_knowledge("k1", "v1")
        self.memory.update_knowledge("k2", "v2")
        
        results = self.memory.search_knowledge("query")
        
        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]['key'], "k1")
        self.assertAlmostEqual(results[0]['score'], 1.0)
        self.assertEqual(results[1]['key'], "k2")
        self.assertAlmostEqual(results[1]['score'], 0.0)
        
if __name__ == '__main__':
    unittest.main()
