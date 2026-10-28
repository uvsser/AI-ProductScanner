import unittest
from app.core.config import Settings

class TestConfig(unittest.TestCase):
    def test_default_settings(self):
        s = Settings()
        self.assertIsNotNone(s.secret_key)
        self.assertEqual(s.clip_model_name, "ViT-B-32")
        self.assertGreater(s.match_threshold, 0.0)
        self.assertGreater(s.max_upload_mb, 0)

    def test_storage_resolution(self):
        s = Settings()
        self.assertTrue(s.resolved_storage_dir.is_absolute())
        self.assertTrue(s.resolved_uploads_dir.is_absolute())

if __name__ == "__main__":
    unittest.main()
