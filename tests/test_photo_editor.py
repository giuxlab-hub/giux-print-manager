# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive image processing and paper-layout tests (no print jobs)."""
from pathlib import Path
import hashlib
import tempfile
import unittest
from PIL import Image, ImageDraw
from photo_editor import PhotoSettings, magick_command, render_adjusted, render_print_page


class PhotoProcessing(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="giux-photo-test-")
        self.folder = Path(self.temp.name)
        self.source = self.folder / "source image.png"
        im = Image.new("RGB", (90, 60), (180, 180, 180))
        draw = ImageDraw.Draw(im)
        draw.rectangle((0, 0, 28, 25), fill=(255, 0, 0))
        draw.rectangle((61, 34, 89, 59), fill=(0, 0, 255))
        im.save(self.source)
        self.hash = hashlib.sha256(self.source.read_bytes()).hexdigest()

    def tearDown(self):
        self.assertEqual(hashlib.sha256(self.source.read_bytes()).hexdigest(), self.hash)
        self.temp.cleanup()

    def render(self, settings, preview=False):
        dest = self.folder / "output.png"
        render_adjusted(self.source, dest, settings, preview=preview)
        with Image.open(dest) as img:
            return img.convert("RGB").copy()

    def test_unmodified_original(self):
        img = self.render(PhotoSettings())
        self.assertEqual(img.size, (90, 60))
        self.assertEqual(img.getpixel((10, 10)), (255, 0, 0))

    def test_rotation_and_mirrors(self):
        self.assertEqual(self.render(PhotoSettings(turns=1)).size, (60, 90))
        self.assertEqual(self.render(PhotoSettings(angle=18)).size, (106, 86))
        self.assertEqual(self.render(PhotoSettings(mirror_h=True)).getpixel((80, 10)), (255, 0, 0))
        self.assertEqual(self.render(PhotoSettings(mirror_v=True)).getpixel((10, 50)), (255, 0, 0))

    def test_brightness_contrast_and_saturation(self):
        changed = self.render(PhotoSettings(brightness=25, contrast=12, saturation=65))
        original = self.render(PhotoSettings())
        self.assertNotEqual(changed.getpixel((40, 30)), original.getpixel((40, 30)))

    def test_filters(self):
        gray = self.render(PhotoSettings(effect="gray"))
        self.assertEqual(len(set(gray.getpixel((10, 10)))), 1)
        for effect in ("sepia", "auto-level"):
            with self.subTest(effect=effect):
                self.assertEqual(self.render(PhotoSettings(effect=effect)).size, (90, 60))

    def test_blur_and_sharpen(self):
        self.assertEqual(self.render(PhotoSettings(blur=2, sharpness=3)).size, (90, 60))

    def test_validation_and_no_overwrite(self):
        for setting in (PhotoSettings(contrast=80), PhotoSettings(angle=100),
                        PhotoSettings(effect="command")):
            with self.assertRaises(ValueError):
                magick_command(self.source, self.folder / "bad.png", setting)
        with self.assertRaises(ValueError):
            render_adjusted(self.source, self.source, PhotoSettings())
        args = magick_command(self.source, self.folder / "out preview.png", PhotoSettings(), preview=True)
        self.assertEqual(args[0], "magick")
        self.assertIn(str(self.source), args)
        self.assertIn("1600x1200>", args)

    def test_print_image_uses_same_transform(self):
        output = self.folder / "page.png"
        render_print_page(self.source, PhotoSettings(turns=1, effect="gray"), "4x6", "fit", output)
        with Image.open(output) as image:
            self.assertEqual(image.size, (1200, 1800))
            self.assertEqual(image.getpixel((0, 0)), (255, 255, 255))

    def test_paper_rejections(self):
        with self.assertRaises(ValueError):
            render_print_page(self.source, PhotoSettings(), "unsupported", "fit", self.folder / "x.png")


if __name__ == "__main__":
    unittest.main()
