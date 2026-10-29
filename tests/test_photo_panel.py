# SPDX-License-Identifier: GPL-3.0-or-later
"""GTK3 widget contract tests; skipped when a graphical display is unavailable."""
import unittest
from types import SimpleNamespace

from gi.repository import Gdk, GdkPixbuf, Gtk
from photo_editor import PhotoEditor, PhotoSettings


@unittest.skipIf(Gdk.Display.get_default() is None, "GTK display unavailable")
class PhotoPanelWidgetTests(unittest.TestCase):
    def setUp(self):
        self.editor = PhotoEditor("en")

    def tearDown(self):
        self.editor.close()

    def test_controls_are_slider_or_buttons_no_numeric_entry(self):
        def descend(widget):
            yield widget
            if isinstance(widget, Gtk.Container):
                for child in widget.get_children():
                    yield from descend(child)
        items = list(descend(self.editor))
        self.assertFalse(any(isinstance(w, (Gtk.Entry, Gtk.SpinButton)) for w in items))
        self.assertEqual(len([w for w in items if isinstance(w, Gtk.Scale)]), 6)

    def test_adjustments_reset_and_state_restore(self):
        self.editor.rotate(1)
        self.editor.mirror_h_check.set_active(True)
        self.editor.sliders["brightness"].set_value(22)
        self.editor.effect_combo.set_active_id("sepia")
        self.assertEqual(self.editor.settings.turns, 1)
        self.assertEqual(self.editor.settings.effect, "sepia")
        saved = self.editor.export_state()
        self.editor.reset()
        self.assertEqual(self.editor.settings, PhotoSettings())
        self.editor.restore_state(saved)
        self.assertEqual(self.editor.settings, saved[1])

    def test_cursor_zoom_and_drag_pan(self):
        canvas = self.editor.canvas
        pixels = GdkPixbuf.Pixbuf.new(GdkPixbuf.Colorspace.RGB, False, 8, 80, 60)
        canvas.set_pixbuf(pixels, False)
        canvas.scale = 1.0
        canvas.x = canvas.y = 0.0
        canvas.zoom_at(20, 30, 1.5)
        self.assertAlmostEqual(canvas.scale, 1.5)
        self.assertAlmostEqual(canvas.x, -10)
        self.assertAlmostEqual(canvas.y, -15)
        self.assertTrue(canvas.on_press(None, SimpleNamespace(button=1, x=10, y=10)))
        self.assertTrue(canvas.on_motion(None, SimpleNamespace(x=40, y=35)))
        self.assertAlmostEqual(canvas.x, 20)
        self.assertAlmostEqual(canvas.y, 10)
        self.assertTrue(canvas.on_release(None, SimpleNamespace(button=1)))


if __name__ == "__main__":
    unittest.main()
