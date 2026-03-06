import unittest
from unittest.mock import MagicMock, patch
from services.lesson_plan_service import LessonPlanService

class TestLessonPlanService(unittest.TestCase):
    def setUp(self):
        self.mock_firecrawl = MagicMock()
        self.mock_embedding = MagicMock()
        self.mock_memory = MagicMock()
        self.planner = LessonPlanService(self.mock_firecrawl, self.mock_embedding, self.mock_memory)

    @patch('ollama.generate')
    def test_plan_lesson_success(self, mock_ollama):
        # Setup mocks
        fact = "Steam engines work by boiling water to create steam which then pushes pistons to move the giant heavy wheels of the locomotive."
        self.mock_firecrawl.search.return_value = {
            'success': True,
            'data': [{'url': 'http://test.com', 'markdown': fact}]
        }
        self.mock_embedding.rerank.return_value = [fact]
        mock_ollama.return_value = {'response': 'Mocked Report'}

        # Run
        report = self.planner.plan_lesson("trains")
        
        # Verify
        self.assertEqual(report, "Mocked Report")
        self.mock_memory.save_lesson.assert_called_with("trains", "Mocked Report", sources=['http://test.com'])
        mock_ollama.assert_called()

    def test_plan_lesson_search_fail(self):
        self.mock_firecrawl.search.return_value = {'success': False}
        report = self.planner.plan_lesson("cars")
        self.assertTrue("library is a bit dusty" in report)

if __name__ == '__main__':
    unittest.main()
