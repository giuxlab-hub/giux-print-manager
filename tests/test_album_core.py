# SPDX-License-Identifier: GPL-3.0-or-later
"""Album document, layout and export regression tests; no printing or scanning."""
from pathlib import Path
import json
import tempfile
import unittest

from PIL import Image
from giux_album_core import (BACKGROUNDS, DECORATIONS, TEMPLATES,
    export_pdf, export_png, layout_regions, load_project, new_page,
    new_project, page_size, render_page, render_preview, save_project,
    set_template, validate)


class AlbumCoreTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="giux-album-tests-")
        self.root = Path(self.temp.name)
        self.images = []
        for n in range(9):
            path = self.root / f"photo_{n}.png"
            Image.new("RGB", (180 + n * 5, 110 + n * 4),
                      (20 * n, 80, 140)).save(path)
            self.images.append(path)

    def tearDown(self):
        self.temp.cleanup()

    def test_paper_orientations(self):
        project = new_project()
        self.assertEqual(page_size(project, 300), (2480, 3508))
        project["orientation"] = "landscape"
        self.assertEqual(page_size(project, 300), (3508, 2480))

    def test_every_template_has_correct_bounds(self):
        for paper in ("A4", "A5", "4x6", "5x7"):
            for orientation in ("portrait", "landscape"):
                for template in TEMPLATES:
                    with self.subTest(paper=paper, orientation=orientation, template=template):
                        doc = new_project(paper, orientation, template)
                        regions = layout_regions(doc, 0, 100)
                        w, h = page_size(doc, 100)
                        self.assertEqual(len(regions), len(doc["pages"][0]["slots"]))
                        for x, y, rw, rh in regions:
                            self.assertTrue(0 <= x < w and 0 <= y < h)
                            self.assertTrue(x + rw <= w and y + rh <= h)

    def test_layout_with_title_footer_decorations(self):
        doc = new_project(template="four")
        page = doc["pages"][0]
        page["title"] = "Summer Trip"
        page["footer"] = "GiuxLab — 2026"
        for i,slot in enumerate(page["slots"]):
            slot["path"] = str(self.images[i])
            slot["caption"] = f"Photo {i + 1}"
        for deco in DECORATIONS:
            with self.subTest(decor=deco):
                page["decoration"] = deco
                image = render_page(doc, 0, 90)
                self.assertEqual(image.size, page_size(doc, 90))
                image.close()

    def test_template_preserves_first_slots(self):
        page = new_page("four")
        page["slots"][0]["path"] = str(self.images[0])
        set_template(page, "nine")
        self.assertEqual(page["slots"][0]["path"], str(self.images[0]))
        self.assertEqual(len(page["slots"]), 9)
        set_template(page, "single")
        self.assertEqual(len(page["slots"]), 1)

    def test_multi_page_pdf_and_png_export(self):
        doc = new_project("A5", "landscape", "duo")
        for i in range(2):
            doc["pages"][0]["slots"][i]["path"] = str(self.images[i])
        doc["pages"].append(new_page("four"))
        doc["pages"][1]["title"] = "Second page"
        for i in range(4):
            doc["pages"][1]["slots"][i]["path"] = str(self.images[i + 2])
        pdf = self.root / "complete-album.pdf"
        png = self.root / "first-page.png"
        export_pdf(doc, pdf)
        export_png(doc, 0, png)
        self.assertTrue(pdf.read_bytes().startswith(b"%PDF-"))
        self.assertGreater(pdf.stat().st_size, 2000)
        with Image.open(png) as image:
            self.assertEqual(image.size, page_size(doc, 300))
        preview = render_preview(doc, 0)
        self.assertTrue(preview.startswith(b"\x89PNG"))
        self.assertLess(len(preview), png.stat().st_size + 100000)

    def test_project_roundtrip_relative_paths_utf8(self):
        doc = new_project()
        page = doc["pages"][0]
        page["title"] = "Vacanze in Sardegna — 2026"
        page["slots"][0].update(path=str(self.images[0]), caption="Spiaggia • serata")
        project_path = self.root / "album.gpa"
        save_project(doc, project_path)
        raw = json.loads(project_path.read_text(encoding="utf8"))
        self.assertEqual(raw["pages"][0]["slots"][0]["path"], "photo_0.png")
        loaded = load_project(project_path)
        self.assertEqual(loaded, doc)
        self.assertNotIn("absolute/image/path", project_path.read_text())

    def test_project_validation_rejects_unsafe_schema(self):
        doc = new_project()
        doc["pages"][0]["template"] = "unknown"
        with self.assertRaises(ValueError):
            validate(doc)
        doc = new_project()
        doc["pages"][0]["slots"].append({"path": "", "caption": ""})
        with self.assertRaises(ValueError):
            validate(doc)
        doc = new_project()
        doc["paper"] = "poster"
        with self.assertRaises(ValueError):
            validate(doc)
        doc = new_project()
        doc["pages"][0]["slots"][0]["path"] = "x"
        doc["pages"][0]["slots"][0]["caption"] = "Y" * 181
        with self.assertRaises(ValueError):
            validate(doc)

    def test_backgrounds_and_missing_image_placeholder(self):
        doc = new_project(template="single")
        doc["pages"][0]["slots"][0]["path"] = str(self.root / "nonexistent.jpg")
        for color in BACKGROUNDS:
            doc["pages"][0]["background"] = color
            result = render_page(doc, 0, 90)
            self.assertTrue(result.getpixel((0, 0)))
            result.close()

    def test_original_photo_not_overwritten(self):
        original = self.images[0].read_bytes()
        doc = new_project()
        doc["pages"][0]["slots"][0]["path"] = str(self.images[0])
        export_png(doc, 0, self.root / "output.png")
        self.assertEqual(self.images[0].read_bytes(), original)


if __name__ == "__main__":
    unittest.main()
