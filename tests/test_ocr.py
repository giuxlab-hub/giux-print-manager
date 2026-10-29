"""Integration tests for Tesseract OCR and pixel-coordinate cropping."""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from giux_ocr_workspace import installed_languages, ocr_file, crop_image
from PIL import Image, ImageDraw, ImageFont


class OCRTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.input = Path(self.temp.name) / "test.png"
        image = Image.new("RGB", (1400, 700), "white")
        draw = ImageDraw.Draw(image)
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 70)
        draw.text((80, 50), "GiuxLab OCR Test 2026", fill="black", font=font)
        draw.text((80, 350), "ABC 12345", fill="black", font=font)
        image.save(self.input)

    def tearDown(self):
        self.temp.cleanup()

    def test_crop(self):
        out = Path(self.temp.name) / "region.png"
        crop_image(self.input, (25, 40, 425, 280), out)
        with Image.open(out) as img:
            self.assertEqual(img.size, (400, 240))

    def test_language_discovery(self):
        self.assertIn("eng", installed_languages())

    def test_ocr_full(self):
        result = ocr_file(self.input, None, "eng", "6")
        self.assertIn("GiuxLab OCR Test 2026", result)
        self.assertIn("ABC 12345", result)

    def test_ocr_selection(self):
        result = ocr_file(self.input, (50, 25, 1300, 230), "eng", "6")
        self.assertIn("GiuxLab OCR Test 2026", result)
        self.assertNotIn("ABC 12345", result)

    def test_searchable_pdf(self):
        data = ocr_file(self.input, None, "eng", "6", fmt="pdf")
        self.assertTrue(data.startswith(b"%PDF-"))

    def test_missing_language(self):
        with self.assertRaises(ValueError):
            ocr_file(self.input, None, "never_installed_model", "6")


if __name__ == "__main__":
    unittest.main()
