import unittest
import numpy as np
from app.features.recognition.matcher import match_query_to_candidates

class TestMatcher(unittest.TestCase):
    def test_match_empty_candidates(self):
        query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        result = match_query_to_candidates(query, [])
        self.assertIsNone(result)

    def test_match_best_candidate(self):
        query = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        candidates = [
            (1, "Product A", np.array([0.9, 0.1, 0.0], dtype=np.float32)),
            (2, "Product B", np.array([0.1, 0.9, 0.0], dtype=np.float32)),
            (3, "Product C", np.array([-1.0, 0.0, 0.0], dtype=np.float32)),
        ]
        result = match_query_to_candidates(query, candidates)
        self.assertIsNotNone(result)
        self.assertEqual(result["product_id"], 1)
        self.assertEqual(result["title"], "Product A")
        self.assertGreater(result["similarity"], 0.8)

if __name__ == "__main__":
    unittest.main()
