import unittest
from unittest.mock import MagicMock
from services.content_service import ContentService

class TestContentService(unittest.TestCase):
    def setUp(self):
        self.mock_firecrawl = MagicMock()
        self.mock_safety = MagicMock()
        # Initialize without embedding first, add in specific tests if needed
        self.content_service = ContentService(self.mock_firecrawl, self.mock_safety)

    def test_get_fun_fact_success(self):
        # Setup mock return
        self.mock_firecrawl.search.return_value = {
            'success': True,
            'data': [
                {'markdown': 'Dinosaurs were big. Some dinosaurs ate plants.'},
                {'description': 'Tyrannosaurus Rex had small arms.'}
            ]
        }
        self.mock_safety.is_safe.return_value = True

        # Run method
        fact = self.content_service.get_fun_fact("dinosaurs")
        
        # Verify
        print(f"Test Success Fact: {fact}")
        self.assertTrue(fact in ['Dinosaurs were big.', 'Some dinosaurs ate plants.', 'Tyrannosaurus Rex had small arms.'])
        self.mock_firecrawl.search.assert_called_with("fun facts for kids about dinosaurs", limit=3)

    def test_get_fun_fact_safety_filter(self):
        self.mock_firecrawl.search.return_value = {
            'success': True,
            'data': [{'markdown': 'This is a very safe fact about trains that is long enough.'}]
        }
        
        # Mock safety to reject it
        self.mock_safety.is_safe.return_value = False
        
        fact = self.content_service.get_fun_fact("trains")
        
        # Should return fallback because safety said no
        self.assertTrue("What do you like about them?" in fact or "amazing" in fact)

    def test_get_fun_fact_cache(self):
        # Setup cache
        self.content_service.fact_cache["cached_topic"] = ["Cached fact."]
        
        fact = self.content_service.get_fun_fact("cached_topic")
        self.assertEqual(fact, "Cached fact.")
        self.mock_firecrawl.search.assert_not_called()

    def test_get_fun_fact_rerank(self):
        # Setup mock embedding
        mock_embedding = MagicMock()
        self.content_service.embedding = mock_embedding
        
        # Setup facts in firecrawl return
        # Needs to be long enough > 20 chars
        fact1 = "This is fact A about the topic."
        fact2 = "This is fact B about the topic."
        
        self.mock_firecrawl.search.return_value = {
            'success': True,
            'data': [{'markdown': f"{fact1} {fact2}"}]
        }
        self.mock_safety.is_safe.return_value = True
        
        # Setup rank return to flip order
        mock_embedding.rerank.return_value = [fact2, fact1]
        
        fact = self.content_service.get_fun_fact("topic")
        
        mock_embedding.rerank.assert_called()
        # Should return the first one from ranked list
        self.assertEqual(fact, fact2)

if __name__ == '__main__':
    unittest.main()
