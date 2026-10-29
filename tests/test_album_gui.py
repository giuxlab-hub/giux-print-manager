# SPDX-License-Identifier: GPL-3.0-or-later
"""Album GTK3 contract tests: no CUPS jobs, no real printer or scanner."""
from pathlib import Path
from tempfile import TemporaryDirectory
from time import monotonic, sleep
import unittest

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GLib
from PIL import Image

from giux_album_workspace import AlbumWorkspace
from giux_album_core import new_project


@unittest.skipIf(Gdk.Display.get_default() is None, "GTK display unavailable")
class AlbumGtkTests(unittest.TestCase):
    def setUp(self):
        self.messages = []
        self.album = AlbumWorkspace(
            language="it", get_printer=lambda: "synthetic_queue",
            status=self.messages.append,
        )

    def tearDown(self):
        self.album.close()

    def wait_for_preview(self):
        ctx = GLib.MainContext.default()
        deadline = monotonic() + 7
        while monotonic() < deadline:
            while ctx.pending():
                ctx.iteration(False)
            if self.album.canvas.pixbuf is not None and self.messages and self.messages[-1] == "Anteprima pagina pronta":
                return
            sleep(0.025)
        self.fail("Album preview did not render")

    def test_starts_with_blank_page_and_preview(self):
        self.assertEqual(self.album.page["template"], "four")
        self.wait_for_preview()
        self.assertIsNotNone(self.album.canvas.pixbuf)

    def test_user_controls_and_caption(self):
        self.album.paper.set_active_id("A5")
        self.album.orientation.set_active_id("landscape")
        self.album.template.set_active_id("nine")
        self.album.decoration.set_active_id("confetti")
        self.album.background.set_active_id("sky")
        self.album.title.set_text("Vacanze")
        self.album.footer.set_text("2026")
        self.album.selected_slot.set_active_id("3")
        self.album.caption.set_text("Spiaggia")
        self.assertEqual(self.album.project["paper"], "A5")
        self.assertEqual(self.album.project["orientation"], "landscape")
        self.assertEqual(len(self.album.page["slots"]), 9)
        self.assertEqual(self.album.page["slots"][3]["caption"], "Spiaggia")

    def test_page_add_navigation_and_state(self):
        first = self.album.project["pages"][0]
        first["title"] = "Primo"
        self.album.add_page()
        self.assertEqual(len(self.album.project["pages"]), 2)
        self.assertEqual(self.album.index, 1)
        self.album.switch_page(-1)
        self.assertEqual(self.album.page["title"], "Primo")
        saved = self.album.export_state()
        self.album.project = new_project()
        self.album.restore_state(saved)
        self.assertEqual(self.album.project["pages"][0]["title"], "Primo")

    def test_printer_confirmation_cancellation(self):
        """Never send a printer job in a test."""
        self.album._confirm = lambda _msg: False
        self.album._background = lambda _work: self.fail("Printed despite cancellation")
        self.album.print_album()

    def test_preview_with_sample_photos(self):
        with TemporaryDirectory(prefix="giux-album-gui-") as folder:
            p = Path(folder) / "example.png"
            Image.new("RGB", (150, 100), "#4088ac").save(p)
            self.album.page["slots"][0]["path"] = str(p)
            self.album.page["slots"][0]["caption"] = "Example"
            self.album._load_page()
            self.album.request_preview()
            self.wait_for_preview()
            self.assertGreater(self.album.canvas.pixbuf.get_width(), 150)


if __name__ == "__main__":
    unittest.main()
