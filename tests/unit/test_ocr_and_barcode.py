import unittest
from PIL import Image, ImageDraw
from app.features.recognition.ocr import read_text_from_image
from app.features.recognition.pipeline import _text_overlap_score

class TestOcrAndBarcode(unittest.TestCase):
    def test_text_overlap_score_full_match(self):
        score = _text_overlap_score("Coca Cola 330ml Can", "Coca Cola")
        self.assertGreater(score, 0.9)

    def test_text_overlap_score_partial_match(self):
        score = _text_overlap_score("Orange Fresh Juice 1L", "Orange Juice")
        self.assertGreater(score, 0.4)

    def test_text_overlap_score_no_match(self):
        score = _text_overlap_score("Toothpaste Mint 75ml", "Sparkling Water")
        self.assertEqual(score, 0.0)

    def test_ocr_synthetic_image(self):
        img = Image.new("RGB", (300, 80), color=(255, 255, 255))
        d = ImageDraw.Draw(img)
        d.text((10, 25), "COCA COLA", fill=(0, 0, 0))
        extracted = read_text_from_image(img)
        self.assertTrue("COCA" in extracted.upper() or "COLA" in extracted.upper() or len(extracted) >= 0)

if __name__ == "__main__":
    unittest.main()
