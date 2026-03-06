import unittest
from services.memory_service import MemoryService
import os

class TestStruggleLog(unittest.TestCase):
    def setUp(self):
        self.db_path = "test_struggle.db"
        self.memory = MemoryService(self.db_path)

    def tearDown(self):
        if os.path.exists(self.memory.db_path):
            os.remove(self.memory.db_path)

    def test_record_and_get_struggle(self):
        self.memory.record_struggle("counting", "The child is having trouble counting past 5.", "medium")
        
        struggles = self.memory.get_unresolved_struggles()
        self.assertEqual(len(struggles), 1)
        # SQLite result: (id, timestamp, subject, description, severity, resolved)
        self.assertEqual(struggles[0][2], "counting")
        self.assertEqual(struggles[0][3], "The child is having trouble counting past 5.")
        self.assertEqual(struggles[0][4], "medium")
        self.assertEqual(struggles[0][5], 0)

    def test_resolve_struggle(self):
        self.memory.record_struggle("colors", "Struggling with red vs orange.", "low")
        struggles = self.memory.get_unresolved_struggles()
        struggle_id = struggles[0][0]
        
        self.memory.resolve_struggle(struggle_id)
        
        unresolved = self.memory.get_unresolved_struggles()
        self.assertEqual(len(unresolved), 0)

if __name__ == '__main__':
    unittest.main()
