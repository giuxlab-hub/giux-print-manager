# SPDX-License-Identifier: GPL-3.0-or-later
"""Non-destructive ImageMagick photo adjustments and interactive GTK3 preview.

The same transform pipeline is used for previews and full-resolution print output.
No source file is overwritten, and no printer operation is performed by this module.
"""
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path
import subprocess
import tempfile

import gi
gi.require_version("Gdk", "3.0")
gi.require_version("Gtk", "3.0")
from gi.repository import Gdk, GdkPixbuf, GLib, Gtk
from PIL import Image, ImageOps


@dataclass(frozen=True)
class PhotoSettings:
    turns: int = 0
    angle: int = 0
    mirror_h: bool = False
    mirror_v: bool = False
    brightness: int = 0
    contrast: int = 0
    saturation: int = 100
    sharpness: int = 0
    blur: int = 0
    effect: str = "normal"


EFFECTS = ("normal", "gray", "sepia", "auto-level")
CAPTIONS = {
    "it": {
        "editor": "Regolazioni immagine",
        "rotate_left": "Ruota 90° ↶",
        "rotate_right": "Ruota 90° ↷",
        "mirror_h": "Rifletti orizz.",
        "mirror_v": "Rifletti vert.",
        "angle": "Inclinazione",
        "brightness": "Luminosità",
        "contrast": "Contrasto",
        "saturation": "Saturazione",
        "sharpness": "Nitidezza",
        "blur": "Sfocatura",
        "effect": "Filtro",
        "normal": "Originale",
        "gray": "Bianco e nero",
        "sepia": "Seppia",
        "auto-level": "Livelli automatici",
        "reset": "Ripristina",
        "fit": "Adatta",
        "help": "Trascina per spostare · Rotella per zoom",
        "choose": "Apri un'immagine per iniziare",
        "working": "Elaborazione anteprima…",
        "ready": "Anteprima aggiornata",
        "error": "Errore anteprima",
    },
    "en": {
        "editor": "Image adjustments",
        "rotate_left": "Rotate 90° ↶",
        "rotate_right": "Rotate 90° ↷",
        "mirror_h": "Flip horizontal",
        "mirror_v": "Flip vertical",
        "angle": "Fine rotation",
        "brightness": "Brightness",
        "contrast": "Contrast",
        "saturation": "Saturation",
        "sharpness": "Sharpen",
        "blur": "Blur",
        "effect": "Filter",
        "normal": "Original",
        "gray": "Grayscale",
        "sepia": "Sepia",
        "auto-level": "Auto levels",
        "reset": "Reset edits",
        "fit": "Fit view",
        "help": "Drag to pan · Mouse wheel to zoom",
        "choose": "Open an image to begin",
        "working": "Rendering preview…",
        "ready": "Preview updated",
        "error": "Preview error",
    },
}


def magick_command(source, target, settings, preview=False):
    """Construct a shell-free ImageMagick argument vector."""
    if not isinstance(settings, PhotoSettings):
        raise TypeError("settings must be PhotoSettings")
    if not 0 <= settings.turns <= 3:
        raise ValueError("Invalid quarter-turn count")
    for key, lower, upper in (
        ("angle", -45, 45),
        ("brightness", -50, 50),
        ("contrast", -60, 60),
        ("saturation", 0, 200),
        ("sharpness", 0, 5),
        ("blur", 0, 5),
    ):
        if not lower <= getattr(settings, key) <= upper:
            raise ValueError("Invalid photo adjustment: " + key)
    if settings.effect not in EFFECTS:
        raise ValueError("Invalid photo filter")

    cmd = [
        "magick",
        "-limit", "memory", "256MiB",
        "-limit", "map", "1GiB",
        str(Path(source).resolve()),
        "-auto-orient",
        "-background", "white",
        "-alpha", "remove",
        "-alpha", "off",
    ]
    if settings.turns:
        cmd += ["-rotate", str(settings.turns * 90)]
    if settings.mirror_h:
        cmd.append("-flop")
    if settings.mirror_v:
        cmd.append("-flip")
    if settings.angle:
        cmd += ["-rotate", str(settings.angle)]
    if settings.brightness or settings.contrast:
        cmd += ["-brightness-contrast", f"{settings.brightness}x{settings.contrast}"]
    if settings.saturation != 100:
        cmd += ["-modulate", f"100,100,{settings.saturation}"]
    if settings.sharpness:
        cmd += ["-sharpen", f"0x{settings.sharpness * 0.45:.2f}"]
    if settings.blur:
        cmd += ["-blur", f"0x{settings.blur * 0.65:.2f}"]
    if settings.effect == "gray":
        cmd += ["-colorspace", "Gray"]
    elif settings.effect == "sepia":
        cmd += ["-sepia-tone", "80%"]
    elif settings.effect == "auto-level":
        cmd.append("-auto-level")
    if preview:
        # Keep preview memory bounded, but transform before reducing the image.
        cmd += ["-resize", "1600x1200>"]
    return cmd + ["-strip", str(Path(target).resolve())]


def render_adjusted(source, target, settings, preview=False, timeout=None):
    """Render to a new target file; source is never modified."""
    source, target = Path(source), Path(target)
    if not source.is_file():
        raise FileNotFoundError(str(source))
    if source.resolve() == target.resolve():
        raise ValueError("Refusing to overwrite the input image")
    cmd = magick_command(source, target, settings, preview=preview)
    result = subprocess.run(
        cmd, shell=False, capture_output=True, timeout=timeout or (40 if preview else 180),
        check=False,
    )
    if result.returncode:
        message = result.stderr.decode("utf-8", "replace").strip()
        raise RuntimeError("ImageMagick: " + message[-600:])
    if not target.is_file() or not target.stat().st_size:
        raise RuntimeError("ImageMagick did not produce an image")
    return target


def render_print_page(source, settings, paper, layout, destination):
    """Use identical adjustments at original resolution, then layout at 300 DPI."""
    paper_sizes = {
        "A4": (210, 297), "A5": (148, 210),
        "4x6": (101.6, 152.4), "5x7": (127, 177.8),
    }
    if paper not in paper_sizes or layout not in ("fit", "fill"):
        raise ValueError("Unsupported paper or print layout")
    with tempfile.TemporaryDirectory(prefix="giux-print-processing-") as folder:
        adjusted = Path(folder) / "adjusted.png"
        render_adjusted(source, adjusted, settings, preview=False)
        width, height = paper_sizes[paper]
        W, H = round(width * 300 / 25.4), round(height * 300 / 25.4)
        with Image.open(adjusted) as original:
            with original.convert("RGB") as converted:
                im = converted.copy()
        if (im.width > im.height) != (W > H):
            W, H = H, W
        margin = round(3 * 300 / 25.4)
        frame = (W - 2 * margin, H - 2 * margin)
        if layout == "fill":
            im = ImageOps.fit(im, frame, method=Image.Resampling.LANCZOS)
        else:
            im.thumbnail(frame, Image.Resampling.LANCZOS)
        page = Image.new("RGB", (W, H), "white")
        page.paste(im, ((W - im.width) // 2, (H - im.height) // 2))
        page.save(destination, format="PNG")
        page.close()
        im.close()
    return destination


class PhotoCanvas(Gtk.DrawingArea):
    """Zoomable preview pixbuf with left/middle-button panning."""
    def __init__(self):
        super().__init__()
        self.set_size_request(340, 280)
        self.set_hexpand(True)
        self.set_vexpand(True)
        self.pixbuf = None
        self.scale = 1.0
        self.x = 0.0
        self.y = 0.0
        self.drag = None
        self.add_events(
            Gdk.EventMask.BUTTON_PRESS_MASK | Gdk.EventMask.BUTTON_RELEASE_MASK
            | Gdk.EventMask.POINTER_MOTION_MASK | Gdk.EventMask.SCROLL_MASK
            | Gdk.EventMask.SMOOTH_SCROLL_MASK
        )
        self.connect("draw", self.on_draw)
        self.connect("button-press-event", self.on_press)
        self.connect("motion-notify-event", self.on_motion)
        self.connect("button-release-event", self.on_release)
        self.connect("scroll-event", self.on_scroll)
        self.connect("size-allocate", self.on_allocate)

    def on_draw(self, _widget, cr):
        cr.set_source_rgb(0.17, 0.18, 0.20)
        cr.paint()
        if self.pixbuf is not None:
            cr.save()
            cr.translate(self.x, self.y)
            cr.scale(self.scale, self.scale)
            Gdk.cairo_set_source_pixbuf(cr, self.pixbuf, 0, 0)
            cr.paint()
            cr.restore()
        return False

    def fit(self):
        if self.pixbuf is None:
            return
        w, h = self.get_allocated_width(), self.get_allocated_height()
        if w <= 1 or h <= 1:
            return
        pw, ph = self.pixbuf.get_width(), self.pixbuf.get_height()
        self.scale = min(w / pw, h / ph, 8)
        self.x = (w - pw * self.scale) / 2
        self.y = (h - ph * self.scale) / 2
        self.queue_draw()

    def set_pixbuf(self, pixbuf, fit):
        self.pixbuf = pixbuf
        if fit:
            self.fit()
        else:
            self.queue_draw()

    def zoom_at(self, mx, my, factor):
        if self.pixbuf is None:
            return
        new_scale = max(0.08, min(12.0, self.scale * factor))
        ratio = new_scale / self.scale
        self.x = mx - (mx - self.x) * ratio
        self.y = my - (my - self.y) * ratio
        self.scale = new_scale
        self.queue_draw()

    def on_scroll(self, _widget, event):
        if event.direction == Gdk.ScrollDirection.UP:
            self.zoom_at(event.x, event.y, 1.16)
        elif event.direction == Gdk.ScrollDirection.DOWN:
            self.zoom_at(event.x, event.y, 1 / 1.16)
        elif event.direction == Gdk.ScrollDirection.SMOOTH:
            ok, _dx, dy = event.get_scroll_deltas()
            if ok and dy:
                self.zoom_at(event.x, event.y, 1.16 ** (-dy))
        return True

    def on_press(self, _widget, event):
        if event.button in (1, 2) and self.pixbuf is not None:
            self.drag = (event.button, event.x, event.y, self.x, self.y)
            return True
        return False

    def on_motion(self, _widget, event):
        if self.drag:
            _button, start_x, start_y, offset_x, offset_y = self.drag
            self.x = offset_x + event.x - start_x
            self.y = offset_y + event.y - start_y
            self.queue_draw()
            return True
        return False

    def on_release(self, _widget, event):
        if self.drag and event.button == self.drag[0]:
            self.drag = None
            return True
        return False

    def on_allocate(self, _widget, allocation):
        if self.pixbuf is not None and self.scale == 1 and self.x == 0 and self.y == 0:
            self.fit()


class PhotoEditor(Gtk.Box):
    """Controls are sliders/buttons only: no editable numeric input fields."""
    def __init__(self, language="en", status=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        self.language = language if language in CAPTIONS else "en"
        self.words = CAPTIONS[self.language]
        self.on_status = status or (lambda _message: None)
        self.settings = PhotoSettings()
        self.source = None
        self.canvas = PhotoCanvas()
        self.pack_start(self.canvas, True, True, 0)
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="giux-photo")
        self.generation = 0
        self.timer_id = 0
        self.disposed = False
        self.preview_current = False
        self.fit_next = True
        self.sliders = {}
        self._build_panel()

    def _build_panel(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(240, 0)
        scroll.set_hexpand(False)
        self.pack_start(scroll, False, False, 0)
        panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        panel.set_border_width(8)
        scroll.add(panel)
        title = Gtk.Label(label=self.words["editor"], xalign=0)
        panel.pack_start(title, False, False, 0)

        row = Gtk.Box(spacing=4)
        for key, action in (
            ("rotate_left", lambda *_: self.rotate(-1)),
            ("rotate_right", lambda *_: self.rotate(1)),
        ):
            button = Gtk.Button(label=self.words[key])
            button.connect("clicked", action)
            row.pack_start(button, True, True, 0)
        panel.pack_start(row, False, False, 0)

        for key, attr in (("mirror_h", "mirror_h"), ("mirror_v", "mirror_v")):
            check = Gtk.CheckButton(label=self.words[key])
            check.connect("toggled", self.toggle, attr)
            panel.pack_start(check, False, False, 0)
            setattr(self, key+"_check", check)

        sliders = (
            ("angle", -45, 45, 1),
            ("brightness", -50, 50, 1),
            ("contrast", -60, 60, 1),
            ("saturation", 0, 200, 1),
            ("sharpness", 0, 5, 1),
            ("blur", 0, 5, 1),
        )
        for key, minimum, maximum, step in sliders:
            panel.pack_start(Gtk.Label(label=self.words[key], xalign=0), False, False, 0)
            slider = Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL, minimum, maximum, step)
            slider.set_draw_value(False)
            slider.set_value(getattr(self.settings, key))
            slider.connect("value-changed", self.slide, key)
            self.sliders[key] = slider
            panel.pack_start(slider, False, False, 0)

        panel.pack_start(Gtk.Label(label=self.words["effect"], xalign=0), False, False, 0)
        self.effect_combo = Gtk.ComboBoxText()
        for key in EFFECTS:
            self.effect_combo.append(key, self.words[key])
        self.effect_combo.set_active_id("normal")
        self.effect_combo.connect("changed", self.choose_effect)
        panel.pack_start(self.effect_combo, False, False, 0)

        row = Gtk.Box(spacing=4)
        for key, action in (("fit", lambda *_: self.canvas.fit()),
                            ("reset", lambda *_: self.reset())):
            button = Gtk.Button(label=self.words[key])
            button.connect("clicked", action)
            row.pack_start(button, True, True, 0)
        panel.pack_start(row, False, False, 0)
        panel.pack_start(Gtk.Label(label=self.words["help"], xalign=0, wrap=True),
                         False, False, 0)

    def slide(self, slider, key):
        self.settings = replace(self.settings, **{key: int(round(slider.get_value()))})
        self.request_preview()

    def toggle(self, checkbox, attr):
        self.settings = replace(self.settings, **{attr: checkbox.get_active()})
        self.request_preview()

    def rotate(self, direction):
        self.settings = replace(self.settings, turns=(self.settings.turns+direction) % 4)
        self.request_preview(refit=True)

    def choose_effect(self, combo):
        effect = combo.get_active_id()
        if effect in EFFECTS:
            self.settings = replace(self.settings, effect=effect)
            self.request_preview()

    def reset(self):
        self.settings = PhotoSettings()
        self._sync_controls()
        self.request_preview(refit=True)

    def _sync_controls(self):
        for key, slider in self.sliders.items():
            slider.handler_block_by_func(self.slide)
            slider.set_value(getattr(self.settings, key))
            slider.handler_unblock_by_func(self.slide)
        for key, attr in (("mirror_h", "mirror_h"), ("mirror_v", "mirror_v")):
            check = getattr(self, key+"_check")
            check.handler_block_by_func(self.toggle)
            check.set_active(getattr(self.settings, attr))
            check.handler_unblock_by_func(self.toggle)
        self.effect_combo.handler_block_by_func(self.choose_effect)
        self.effect_combo.set_active_id(self.settings.effect)
        self.effect_combo.handler_unblock_by_func(self.choose_effect)

    def open_image(self, path):
        source = Path(path).expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(str(source))
        self.source = source
        self.canvas.set_pixbuf(None, False)
        self.request_preview(refit=True)

    def export_state(self):
        return self.source, self.settings

    def restore_state(self, saved):
        source, settings = saved
        self.settings = settings
        self._sync_controls()
        if source is not None:
            self.open_image(source)

    def request_preview(self, refit=False):
        if self.disposed:
            return
        self.generation += 1
        self.preview_current = False
        self.fit_next = self.fit_next or refit
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = 0
        if self.source is not None:
            self.timer_id = GLib.timeout_add(260, self._start_preview)

    def _start_preview(self):
        self.timer_id = 0
        if self.disposed or self.source is None:
            return False
        generation = self.generation
        settings = self.settings
        source = self.source
        self.on_status(self.words["working"])

        def work():
            # Coalesce rapid slider updates: skip queued renders that are already stale.
            if self.disposed or generation != self.generation:
                return
            try:
                with tempfile.TemporaryDirectory(prefix="giux-photo-preview-") as directory:
                    target = Path(directory) / "preview.png"
                    render_adjusted(source, target, settings, preview=True)
                    data = target.read_bytes()
                result = (True, data)
            except Exception as exc:
                result = (False, str(exc))
            GLib.idle_add(self._receive_preview, generation, result)
        self.executor.submit(work)
        return False

    def _receive_preview(self, generation, result):
        if self.disposed or generation != self.generation:
            return False
        ok, value = result
        if not ok:
            self.on_status(self.words["error"] + ": " + value[:180])
            return False
        try:
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(value)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf is None:
                raise RuntimeError("Missing preview pixels")
            self.canvas.set_pixbuf(pixbuf, self.fit_next)
            self.fit_next = False
            self.preview_current = True
            self.on_status(self.words["ready"])
        except Exception as exc:
            self.on_status(self.words["error"] + ": " + str(exc))
        return False

    def close(self):
        self.disposed = True
        self.generation += 1
        if self.timer_id:
            GLib.source_remove(self.timer_id)
            self.timer_id = 0
        self.executor.shutdown(wait=False, cancel_futures=True)
