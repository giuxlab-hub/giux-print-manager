# SPDX-License-Identifier: GPL-3.0-or-later
"""ImageMagick, geometry and interactive image canvas regression tests."""
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from PIL import Image, ImageDraw, ImageFont

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from giux_image_filters import render_filters, transform
from giux_image_canvas import ImageCanvas
from giux_ocr_workspace import OCRWorkspace, ocr_file

class ImageTests(unittest.TestCase):
    def setUp(self):
        self.directory=tempfile.TemporaryDirectory()
        self.root=Path(self.directory.name)
        self.original=self.root/"original.png"
        image=Image.new("RGB",(1400,900),"white")
        draw=ImageDraw.Draw(image)
        font=ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",72)
        draw.text((120,85),"GiuxLab OCR Test 2026",font=font,fill="black")
        draw.text((120,430),"ABC 12345",font=font,fill="black")
        image.save(self.original)

    def tearDown(self):
        self.directory.cleanup()

    def test_filters_and_original_untouched(self):
        filtered=self.root/"filtered.png"
        render_filters(self.original,filtered,20,25,2,70)
        with Image.open(filtered) as image:
            self.assertEqual(image.size,(1400,900))
            self.assertNotEqual(image.getpixel((300,120)),(255,255,255))
        with Image.open(self.original) as image:
            self.assertEqual(image.size,(1400,900))

    def test_transforms(self):
        for operation,dimensions in (("left",(900,1400)),("right",(900,1400)),
                                     ("horizontal",(1400,900)),("vertical",(1400,900))):
            with self.subTest(operation=operation):
                output=self.root/(operation+".png")
                transform(self.original,output,operation)
                with Image.open(output) as image:
                    self.assertEqual(image.size,dimensions)

    def test_handles_and_resize(self):
        canvas=ImageCanvas(self.original)
        canvas.zoom=1.0
        canvas.selection=(100,120,600,520)
        self.assertEqual(len(canvas.handles()),8)
        self.assertEqual(canvas.hit((100,120)),"nw")
        self.assertEqual(canvas.hit((350,120)),"n")
        self.assertEqual(canvas.hit((600,320)),"e")
        self.assertEqual(canvas.hit((350,320)),"move")
        event=lambda x,y:SimpleNamespace(button=1,x=x,y=y)
        canvas.press(canvas,event(600,520))
        canvas.motion(canvas,event(800,660))
        canvas.release(canvas,event(800,660))
        self.assertEqual(canvas.box(),(100,120,800,660))

    def test_zoom_preserves_crop(self):
        canvas=ImageCanvas(self.original)
        canvas.selection=(70,80,900,500)
        before=canvas.box()
        canvas.set_zoom(1.2)
        self.assertEqual(canvas.box(),before)

    def test_ocr_uses_filtered_image(self):
        filtered=self.root/"filtered.png"
        render_filters(self.original,filtered,10,10,1,100)
        text=ocr_file(filtered,(80,60,1300,320),"eng","6")
        self.assertIn("GiuxLab OCR Test 2026",text)
        self.assertNotIn("ABC 12345",text)

if __name__=="__main__":
    unittest.main()
