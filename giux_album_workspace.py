# SPDX-License-Identifier: GPL-3.0-or-later
"""GTK3 Album Composer UI. CUPS is used only after an explicit print confirmation."""
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import subprocess
import tempfile

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import GdkPixbuf, GLib, Gtk
from photo_editor import PhotoCanvas
from giux_album_core import (BACKGROUNDS, DECORATIONS, MAX_PAGES, PAPER_MM, TEMPLATES,
                             export_pdf, export_png, load_project, new_page, new_project,
                             render_preview, save_project, set_template)

WORDS = {
    "it": {
        "album": "Album", "new": "Nuovo", "open": "Apri .gpa", "save": "Salva .gpa",
        "page": "Pagina", "previous": "◀", "next": "▶", "add_page": "+ Pagina",
        "remove_page": "− Pagina", "paper": "Carta", "orientation": "Orientamento",
        "portrait": "Verticale", "landscape": "Orizzontale", "template": "Foto/pagina",
        "background": "Sfondo", "decoration": "Decorazione", "title": "Titolo pagina",
        "footer": "Testo finale", "photos": "Immagini e didascalie", "slot": "Riquadro",
        "add_photos": "Aggiungi foto…", "replace": "Sostituisci riquadro",
        "clear": "Svuota riquadro", "caption": "Didascalia", "fit": "Adatta",
        "fill": "Riempi", "photo_layout": "Inquadratura", "preview": "Aggiorna",
        "view_fit": "Adatta vista", "export_png": "Esporta PNG",
        "export_pdf": "Esporta PDF", "print": "Stampa album…",
        "ready": "Anteprima pagina pronta", "working": "Composizione della pagina…",
        "error": "Errore Album", "confirm": "Stampare tutte le pagine dell'album?",
        "missing_printer": "Selezionare una stampante nella scheda Fotografie.",
        "printer": "Stampante", "done": "Operazione completata",
        "new_confirm": "Creare un album nuovo? Le modifiche non salvate andranno perse.",
        "remove_confirm": "Eliminare la pagina attuale?",
        "hint": "Trascina: sposta · Rotella: zoom · Esporta PDF per tutte le pagine",
        "saved": "Progetto salvato", "loaded": "Progetto caricato",
        "overflow": "Le fotografie aggiuntive vengono inserite in nuove pagine",
        "none": "Nessuna", "classic": "Classica", "confetti": "Coriandoli",
        "botanical": "Botanica", "white": "Bianco", "cream": "Crema", "sky": "Cielo",
        "rose": "Rosa", "all": "Tutte le pagine",
    },
    "en": {
        "album": "Album", "new": "New", "open": "Open .gpa", "save": "Save .gpa",
        "page": "Page", "previous": "◀", "next": "▶", "add_page": "+ Page",
        "remove_page": "− Page", "paper": "Paper", "orientation": "Orientation",
        "portrait": "Portrait", "landscape": "Landscape", "template": "Photos/page",
        "background": "Background", "decoration": "Decoration", "title": "Page title",
        "footer": "Footer text", "photos": "Photos and captions", "slot": "Photo slot",
        "add_photos": "Add photos…", "replace": "Replace selected",
        "clear": "Clear selected", "caption": "Caption", "fit": "Fit",
        "fill": "Fill", "photo_layout": "Photo crop", "preview": "Refresh",
        "view_fit": "Fit view", "export_png": "Export PNG",
        "export_pdf": "Export PDF", "print": "Print album…",
        "ready": "Page preview ready", "working": "Rendering page…",
        "error": "Album error", "confirm": "Print every page of this album?",
        "missing_printer": "Select a printer in the Photos tab.",
        "printer": "Printer", "done": "Operation completed",
        "new_confirm": "Create a new album? Unsaved changes will be discarded.",
        "remove_confirm": "Remove this album page?",
        "hint": "Drag to pan · Wheel to zoom · PDF includes every page",
        "saved": "Project saved", "loaded": "Project loaded",
        "overflow": "Additional photos automatically continue onto new pages",
        "none": "None", "classic": "Classic", "confetti": "Confetti",
        "botanical": "Botanical", "white": "White", "cream": "Cream", "sky": "Sky",
        "rose": "Rose", "all": "All pages",
    },
}


class AlbumWorkspace(Gtk.Box):
    def __init__(self, language="en", get_printer=None, status=None):
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.language = "it" if language == "it" else "en"
        self.words = WORDS[self.language]
        self.project = new_project()
        self.index = 0
        self.project_file = None
        self.get_printer = get_printer or (lambda: None)
        self.on_status = status or (lambda msg: None)
        self.updating = False
        self.closed = False
        self.preview_generation = 0
        self.preview_source_id = 0
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="giux-album")
        self._build()
        self._load_page()
        self.request_preview()

    @property
    def page(self):
        return self.project["pages"][self.index]

    def _label(self, key):
        return Gtk.Label(label=self.words[key], xalign=0)

    def _button(self, box, key, fn):
        button = Gtk.Button(label=self.words[key])
        button.connect("clicked", fn)
        box.pack_start(button, False, False, 0)
        return button

    def _combo(self, box, key, choices, fn):
        row = Gtk.Box(spacing=8)
        row.pack_start(self._label(key), False, False, 0)
        field = Gtk.ComboBoxText()
        for value, name in choices:
            field.append(value, name)
        field.connect("changed", fn)
        field.set_hexpand(True)
        row.pack_start(field, True, True, 0)
        box.pack_start(row, False, False, 0)
        return field

    def _entry(self, box, key, fn):
        box.pack_start(self._label(key), False, False, 0)
        field = Gtk.Entry()
        field.connect("changed", fn)
        box.pack_start(field, False, False, 0)
        return field

    def _build(self):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_size_request(335, -1)
        self.pack_start(scroll, False, False, 0)
        controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=7)
        controls.set_border_width(8)
        scroll.add(controls)

        head = Gtk.Box(spacing=4)
        self._button(head, "new", self.new)
        self._button(head, "open", self.open)
        self._button(head, "save", self.save)
        controls.pack_start(head, False, False, 0)

        pager = Gtk.Box(spacing=5)
        self._button(pager, "previous", lambda *_: self.switch_page(-1))
        self.page_count = Gtk.Label(label="", xalign=0.5)
        pager.pack_start(self.page_count, True, True, 0)
        self._button(pager, "next", lambda *_: self.switch_page(1))
        controls.pack_start(pager, False, False, 0)
        page_actions = Gtk.Box(spacing=4)
        self._button(page_actions, "add_page", self.add_page)
        self._button(page_actions, "remove_page", self.remove_page)
        controls.pack_start(page_actions, False, False, 0)

        self.paper = self._combo(controls, "paper", [(p, p) for p in PAPER_MM], self.changed_paper)
        self.orientation = self._combo(controls, "orientation",
                                       [(p, self.words[p]) for p in ("portrait", "landscape")],
                                       self.changed_paper)
        self.template = self._combo(controls, "template",
                                    [(name, str(cols * rows)) for name, (cols, rows) in TEMPLATES.items()],
                                    self.changed_template)
        self.background = self._combo(controls, "background",
                                      [(p, self.words[p]) for p in BACKGROUNDS], self.changed_page)
        self.decoration = self._combo(controls, "decoration",
                                      [(p, self.words[p]) for p in DECORATIONS], self.changed_page)
        self.title = self._entry(controls, "title", self.changed_page)
        self.footer = self._entry(controls, "footer", self.changed_page)
        self.photo_layout = self._combo(controls, "photo_layout",
                                        [(m, self.words[m]) for m in ("fit", "fill")],
                                        self.changed_page)

        controls.pack_start(Gtk.Separator(), False, False, 4)
        controls.pack_start(self._label("photos"), False, False, 0)
        self.selected_slot = self._combo(controls, "slot", [], self.changed_slot)
        choices = Gtk.Box(spacing=3)
        self._button(choices, "add_photos", self.add_photos)
        self._button(choices, "replace", self.replace_photo)
        controls.pack_start(choices, False, False, 0)
        self._button(controls, "clear", self.clear_photo)
        self.caption = self._entry(controls, "caption", self.changed_caption)
        note = self._label("overflow")
        note.set_line_wrap(True)
        controls.pack_start(note, False, False, 0)

        controls.pack_start(Gtk.Separator(), False, False, 3)
        self._button(controls, "export_png", self.export_current_png)
        self._button(controls, "export_pdf", self.export_all_pdf)
        self._button(controls, "print", self.print_album)

        side = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        self.pack_start(side, True, True, 0)
        heading = Gtk.Box(spacing=5)
        self._button(heading, "view_fit", lambda *_: self.canvas.fit())
        self._button(heading, "preview", lambda *_: self.request_preview())
        heading.pack_start(self._label("page"), False, False, 0)
        side.pack_start(heading, False, False, 0)
        self.canvas = PhotoCanvas()
        side.pack_start(self.canvas, True, True, 0)
        hint = self._label("hint")
        hint.set_line_wrap(True)
        side.pack_start(hint, False, False, 0)

    def _load_page(self):
        self.updating = True
        try:
            self.paper.set_active_id(self.project["paper"])
            self.orientation.set_active_id(self.project["orientation"])
            self.template.set_active_id(self.page["template"])
            self.background.set_active_id(self.page["background"])
            self.decoration.set_active_id(self.page["decoration"])
            self.photo_layout.set_active_id(self.page.get("fit", "fill"))
            self.title.set_text(self.page["title"])
            self.footer.set_text(self.page["footer"])
            self.page_count.set_text(f"{self.words['page']} {self.index + 1} / {len(self.project['pages'])}")
            self._refresh_slots()
        finally:
            self.updating = False

    def _refresh_slots(self):
        current = self.selected_slot.get_active_id()
        self.selected_slot.remove_all()
        for i, slot in enumerate(self.page["slots"]):
            label = Path(slot["path"]).name if slot["path"] else "—"
            self.selected_slot.append(str(i), f"{i + 1}. {label[:26]}")
        self.selected_slot.set_active_id(current if current is not None
                                         and int(current) < len(self.page["slots"]) else "0")
        self._load_caption()

    def _load_caption(self):
        item = self.selected_slot.get_active_id()
        self.caption.set_text(self.page["slots"][int(item)]["caption"] if item is not None else "")

    def changed_paper(self, *_):
        if self.updating:
            return
        paper, orientation = self.paper.get_active_id(), self.orientation.get_active_id()
        if paper and orientation:
            self.project["paper"] = paper
            self.project["orientation"] = orientation
            self.request_preview()

    def changed_template(self, *_):
        if self.updating:
            return
        choice = self.template.get_active_id()
        if choice:
            set_template(self.page, choice)
            self.updating = True
            self._refresh_slots()
            self.updating = False
            self.request_preview()

    def changed_page(self, *_):
        if self.updating:
            return
        choice = self.background.get_active_id()
        if choice:
            self.page["background"] = choice
        choice = self.decoration.get_active_id()
        if choice:
            self.page["decoration"] = choice
        choice = self.photo_layout.get_active_id()
        if choice:
            self.page["fit"] = choice
        self.page["title"] = self.title.get_text()[:300]
        self.page["footer"] = self.footer.get_text()[:300]
        self.request_preview()

    def changed_slot(self, *_):
        if not self.updating:
            self.updating = True
            self._load_caption()
            self.updating = False

    def changed_caption(self, *_):
        if self.updating:
            return
        slot = self.selected_slot.get_active_id()
        if slot is not None:
            self.page["slots"][int(slot)]["caption"] = self.caption.get_text()[:180]
            self.request_preview()

    def request_preview(self):
        if self.closed:
            return
        self.preview_generation += 1
        if self.preview_source_id:
            GLib.source_remove(self.preview_source_id)
        self.preview_source_id = GLib.timeout_add(300, self._render_preview)

    def _render_preview(self):
        self.preview_source_id = 0
        if self.closed:
            return False
        ticket = self.preview_generation
        document, index = deepcopy(self.project), self.index
        self.on_status(self.words["working"])
        def work():
            if self.closed or ticket != self.preview_generation:
                return
            try:
                result = True, render_preview(document, index)
            except Exception as exc:
                result = False, str(exc)
            GLib.idle_add(self._receive_preview, ticket, result)
        self.executor.submit(work)
        return False

    def _receive_preview(self, ticket, result):
        if self.closed or ticket != self.preview_generation:
            return False
        success, data = result
        if not success:
            self.on_status(self.words["error"] + ": " + data[:180])
            return False
        try:
            loader = GdkPixbuf.PixbufLoader.new_with_type("png")
            loader.write(data)
            loader.close()
            pixbuf = loader.get_pixbuf()
            if pixbuf is None:
                raise ValueError("No preview pixels")
            self.canvas.set_pixbuf(pixbuf, True)
            self.on_status(self.words["ready"])
        except Exception as exc:
            self.on_status(self.words["error"] + ": " + str(exc))
        return False

    def _error(self, message):
        dlg = Gtk.MessageDialog(transient_for=self.get_toplevel(), flags=0,
                                message_type=Gtk.MessageType.ERROR,
                                buttons=Gtk.ButtonsType.OK, text=self.words["error"])
        dlg.format_secondary_text(str(message))
        dlg.run()
        dlg.destroy()

    def _confirm(self, message):
        dlg = Gtk.MessageDialog(transient_for=self.get_toplevel(), flags=0,
                                message_type=Gtk.MessageType.QUESTION,
                                buttons=Gtk.ButtonsType.OK_CANCEL, text=message)
        accepted = dlg.run() == Gtk.ResponseType.OK
        dlg.destroy()
        return accepted

    def _choose(self, action, name, multiple=False):
        dialog = Gtk.FileChooserDialog(title=name, transient_for=self.get_toplevel(),
                                       action=action)
        dialog.add_buttons(self.words["save"] if action==Gtk.FileChooserAction.SAVE else self.words["open"],
                           Gtk.ResponseType.OK, "Cancel", Gtk.ResponseType.CANCEL)
        if action == Gtk.FileChooserAction.SAVE:
            dialog.set_do_overwrite_confirmation(True)
            dialog.set_current_name(name)
        else:
            dialog.set_select_multiple(multiple)
        ok = dialog.run() == Gtk.ResponseType.OK
        result = (dialog.get_filenames() if multiple else dialog.get_filename()) if ok else None
        dialog.destroy()
        return result

    def new(self, *_):
        if not self._confirm(self.words["new_confirm"]):
            return
        self.project = new_project()
        self.project_file = None
        self.index = 0
        self._load_page()
        self.request_preview()

    def open(self, *_):
        filename = self._choose(Gtk.FileChooserAction.OPEN, self.words["open"])
        if not filename:
            return
        try:
            loaded = load_project(filename)
            self.project, self.project_file, self.index = loaded, Path(filename), 0
            self._load_page()
            self.request_preview()
            self.on_status(self.words["loaded"])
        except Exception as exc:
            self._error(exc)

    def save(self, *_):
        filename = str(self.project_file) if self.project_file else self._choose(
            Gtk.FileChooserAction.SAVE, "photo-album.gpa")
        if not filename:
            return
        if not filename.endswith(".gpa"):
            filename += ".gpa"
        try:
            self.project_file = save_project(self.project, filename)
            self.on_status(self.words["saved"] + ": " + str(self.project_file))
        except Exception as exc:
            self._error(exc)

    def switch_page(self, step):
        new_index = self.index + step
        if 0 <= new_index < len(self.project["pages"]):
            self.index = new_index
            self._load_page()
            self.request_preview()

    def add_page(self, *_):
        if len(self.project["pages"]) >= MAX_PAGES:
            self._error("Maximum page count reached")
            return
        self.project["pages"].insert(self.index + 1, new_page(self.page["template"]))
        self.switch_page(1)

    def remove_page(self, *_):
        if len(self.project["pages"]) <= 1:
            return
        if not self._confirm(self.words["remove_confirm"]):
            return
        self.project["pages"].pop(self.index)
        self.index = min(self.index, len(self.project["pages"]) - 1)
        self._load_page()
        self.request_preview()

    def add_photos(self, *_):
        photos = self._choose(Gtk.FileChooserAction.OPEN, self.words["add_photos"], multiple=True)
        if not photos:
            return
        try:
            for filename in photos:
                if not Path(filename).is_file():
                    continue
                page = self.page
                target = next((slot for slot in page["slots"] if not slot["path"]), None)
                if target is None:
                    if len(self.project["pages"]) >= MAX_PAGES:
                        raise ValueError("Maximum album page count reached")
                    self.project["pages"].insert(self.index + 1, new_page(page["template"]))
                    self.index += 1
                    target = self.page["slots"][0]
                target["path"] = str(Path(filename).resolve())
            self._load_page()
            self.request_preview()
        except Exception as exc:
            self._error(exc)

    def replace_photo(self, *_):
        slot = self.selected_slot.get_active_id()
        if slot is None:
            return
        filename = self._choose(Gtk.FileChooserAction.OPEN, self.words["replace"])
        if filename:
            self.page["slots"][int(slot)]["path"] = str(Path(filename).resolve())
            self._refresh_slots()
            self.request_preview()

    def clear_photo(self, *_):
        slot = self.selected_slot.get_active_id()
        if slot is not None:
            self.page["slots"][int(slot)] = {"path": "", "caption": ""}
            self.updating = True
            self._refresh_slots()
            self.updating = False
            self.request_preview()

    def export_state(self):
        return deepcopy(self.project), self.index, self.project_file

    def restore_state(self, state):
        self.project, self.index, self.project_file = deepcopy(state[0]), state[1], state[2]
        self._load_page()
        self.request_preview()

    def _background(self, fn):
        self.on_status(self.words["working"])
        def work():
            try:
                success, message = True, str(fn())
            except Exception as exc:
                success, message = False, str(exc)
            GLib.idle_add(self._finished, success, message)
        self.executor.submit(work)

    def _finished(self, success, message):
        if not self.closed:
            self.on_status((self.words["done"] if success else self.words["error"]) + ": " + message[:200])
            if not success:
                self._error(message)
        return False

    def export_current_png(self, *_):
        filename = self._choose(Gtk.FileChooserAction.SAVE, "album-page.png")
        if filename:
            if not filename.lower().endswith(".png"):
                filename += ".png"
            project, index = deepcopy(self.project), self.index
            self._background(lambda: export_png(project, index, filename))

    def export_all_pdf(self, *_):
        filename = self._choose(Gtk.FileChooserAction.SAVE, "photo-album.pdf")
        if filename:
            if not filename.lower().endswith(".pdf"):
                filename += ".pdf"
            project = deepcopy(self.project)
            self._background(lambda: export_pdf(project, filename))

    def print_album(self, *_):
        queue = self.get_printer()
        if not queue:
            self._error(self.words["missing_printer"])
            return
        if not self._confirm(self.words["confirm"] + "\n" + self.words["printer"] + ": " + queue):
            return
        project = deepcopy(self.project)
        def job():
            with tempfile.TemporaryDirectory(prefix="giux-album-print-") as folder:
                pdf = Path(folder) / "album.pdf"
                export_pdf(project, pdf)
                process = subprocess.run(["lp", "-d", queue, "-o", "fit-to-page", str(pdf)],
                                         capture_output=True, text=True, timeout=90, check=False)
                if process.returncode:
                    raise RuntimeError(process.stderr.strip() or "CUPS print failed")
                return process.stdout.strip() or "CUPS job submitted"
        self._background(job)

    def close(self):
        self.closed = True
        self.preview_generation += 1
        if self.preview_source_id:
            GLib.source_remove(self.preview_source_id)
            self.preview_source_id = 0
        self.executor.shutdown(wait=False, cancel_futures=True)
