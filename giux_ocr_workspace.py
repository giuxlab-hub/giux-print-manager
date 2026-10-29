# SPDX-License-Identifier: GPL-3.0-or-later
"""Independent acquired-image canvas and Tesseract OCR workspace."""
import os
import re
import subprocess
import tempfile
import threading
from pathlib import Path

import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk, GdkPixbuf
from PIL import Image
from giux_image_canvas import ImageCanvas
from giux_image_filters import render_filters, transform

LANG = {
    "it": {
        "title":"Immagine acquisita — OCR", "source":"Immagine originale",
        "region":"Trascina sull'immagine per selezionare un'area. Senza selezione: intera pagina.",
        "language":"Lingue OCR (es. eng+ita)", "psm":"Impaginazione",
        "ocr":"OCR selezione", "reset":"Cancella selezione",
        "export":"Salva area PNG", "copy":"Copia testo", "save":"Salva testo UTF-8",
        "pdf":"Salva PDF ricercabile", "result":"Testo riconosciuto",
        "no_lang":"Tesseract non ha restituito lingue disponibili",
        "error":"Errore", "busy":"Elaborazione OCR in corso…", "done":"OCR completato",
        "save_title":"Salva output", "selection":"Selezione", "full":"Immagine intera",
        "zoom":"Zoom", "cancel":"Annulla", "ok":"Salva",
        "rotateleft":"Ruota ↶", "rotateright":"Ruota ↷",
        "mirrorh":"Rifletti orizz.", "mirrorv":"Rifletti vert.",
        "brightness":"Luminosità", "contrast":"Contrasto",
        "sharpness":"Nitidezza", "saturation":"Saturazione",
        "filtersreset":"Azzera filtri", "filtertitle":"Filtri ImageMagick",
        "panhelp":"Rotellina: zoom • Tasto centrale: sposta canvas • 8 maniglie: ridimensiona",
        "saveimage":"Salva immagine elaborata"
    },
    "en": {
        "title":"Acquired image — OCR", "source":"Original image",
        "region":"Drag over the image to select an area. No selection: full page.",
        "language":"OCR languages (e.g. eng+ita)", "psm":"Page segmentation",
        "ocr":"OCR selection", "reset":"Clear selection",
        "export":"Save region PNG", "copy":"Copy text", "save":"Save UTF-8 text",
        "pdf":"Save searchable PDF", "result":"Recognized text",
        "no_lang":"Tesseract returned no available languages",
        "error":"Error", "busy":"Running OCR…", "done":"OCR complete",
        "save_title":"Save output", "selection":"Selection", "full":"Full image",
        "zoom":"Zoom", "cancel":"Cancel", "ok":"Save",
        "rotateleft":"Rotate ↶", "rotateright":"Rotate ↷",
        "mirrorh":"Flip horizontally", "mirrorv":"Flip vertically",
        "brightness":"Brightness", "contrast":"Contrast",
        "sharpness":"Sharpness", "saturation":"Saturation",
        "filtersreset":"Reset filters", "filtertitle":"ImageMagick filters",
        "panhelp":"Wheel: zoom • Middle drag: pan • 8 handles: resize",
        "saveimage":"Save edited image"
    }
}

def installed_languages():
    p=subprocess.run(["tesseract","--list-langs"],capture_output=True,
                     text=True,timeout=12,check=False)
    if p.returncode:
        raise RuntimeError((p.stderr or p.stdout).strip())
    names=[x.strip() for x in (p.stdout+"\n"+p.stderr).splitlines()]
    return sorted(x for x in names if x != "osd" and re.fullmatch(r"[A-Za-z][A-Za-z0-9_-]*",x))

def crop_image(image_path,box,target):
    with Image.open(image_path) as image:
        if box:
            image=image.crop(box)
        image.convert("RGB").save(target)

def ocr_file(image_path,box,languages,psm,fmt="txt"):
    installed=set(installed_languages())
    requested=languages.split("+")
    if not requested or any(l not in installed for l in requested):
        raise ValueError("Language model is not installed: "+languages)
    if psm not in ("3","6","7","11"):
        raise ValueError("Unsupported PSM")
    with tempfile.TemporaryDirectory(prefix="giux-ocr-") as folder:
        cropped=Path(folder)/"input.png"
        crop_image(image_path,box,cropped)
        if fmt=="pdf":
            dest=Path(folder)/"result"
            args=["tesseract",str(cropped),str(dest),"-l",languages,
                  "--psm",psm,"pdf"]
            p=subprocess.run(args,capture_output=True,text=True,timeout=180)
            if p.returncode:
                raise RuntimeError(p.stderr[:1200])
            return (dest.with_suffix(".pdf")).read_bytes()
        args=["tesseract",str(cropped),"stdout","-l",languages,"--psm",psm]
        p=subprocess.run(args,capture_output=True,timeout=180)
        if p.returncode:
            raise RuntimeError(p.stderr.decode("utf-8","replace")[:1200])
        return p.stdout.decode("utf-8","replace")

class OCRWorkspace(Gtk.Window):
    def __init__(self, image_path, lang="it"):
        super().__init__(title=LANG.get(lang,LANG["en"])["title"])
        self.text=LANG.get(lang,LANG["en"])
        self.original_path=str(Path(image_path).resolve())
        self.image_path=self.original_path
        self.temp_workspace=tempfile.TemporaryDirectory(prefix="giux-image-work-")
        self.work_dir=Path(self.temp_workspace.name)
        self.base_path=self.original_path
        self.generation=0
        self.filter_timer=None
        self.render_busy=False
        self.render_pending=False
        self.pending_geometry=None
        self.destroyed=False
        self.connect("destroy",self.dispose)
        self.set_default_size(1100,780)
        self.set_border_width(10)
        self.busy=False
        self.canvas=ImageCanvas(self.image_path)
        root=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=8)
        self.add(root)
        header=Gtk.Label(label=self.text["source"]+": "+Path(self.image_path).name,xalign=0)
        root.pack_start(header,False,False,0)
        tools=Gtk.Box(spacing=8)
        root.pack_start(tools,False,False,0)
        tools.pack_start(Gtk.Label(label=self.text["zoom"]),False,False,0)
        zoom=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,20,180,10)
        zoom.set_value(55);zoom.set_size_request(135,-1)
        zoom.connect("value-changed",self.zoom_adjustment)
        tools.pack_start(zoom,False,False,0)
        self.zoom_slider=zoom
        self.canvas.on_zoom=self.sync_zoom
        self.button(tools,"saveimage",self.save_edited_image)
        self.button(tools,"reset",lambda *_:self.canvas.clear())
        self.button(tools,"export",self.save_region)
        geometry_buttons=Gtk.Box(spacing=8)
        root.pack_start(geometry_buttons,False,False,0)
        for key,action in (("rotateleft","left"),("rotateright","right"),
                           ("mirrorh","horizontal"),("mirrorv","vertical")):
            self.button(geometry_buttons,key,lambda _w,op=action:self.geometry(op))
        root.pack_start(Gtk.Label(label=self.text["region"],xalign=0),False,False,0)
        pane=Gtk.Paned(orientation=Gtk.Orientation.VERTICAL)
        root.pack_start(pane,True,True,0)
        scroll=Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.AUTOMATIC,Gtk.PolicyType.AUTOMATIC)
        scroll.add(self.canvas)
        self.canvas.scroller=scroll
        pane.pack1(scroll,resize=True,shrink=False)
        bottom=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=7)
        pane.pack2(bottom,resize=True,shrink=False)
        pane.set_position(450)
        helptext=Gtk.Label(label=self.text["panhelp"],xalign=0)
        bottom.pack_start(helptext,False,False,0)
        adjustment=Gtk.Box(spacing=12)
        bottom.pack_start(adjustment,False,False,0)
        self.filter_scales={}
        for key,minimum,maximum,default in (("brightness",-80,80,0),
                                             ("contrast",-80,80,0),
                                             ("sharpness",0,5,0),
                                             ("saturation",0,200,100)):
            panel=Gtk.Box(orientation=Gtk.Orientation.VERTICAL,spacing=2)
            panel.pack_start(Gtk.Label(label=self.text[key]),False,False,0)
            scale=Gtk.Scale.new_with_range(Gtk.Orientation.HORIZONTAL,minimum,maximum,1)
            scale.set_digits(0)
            scale.set_draw_value(False)
            scale.set_value(default)
            scale.set_size_request(115,-1)
            scale.connect("value-changed",self.filter_changed)
            panel.pack_start(scale,False,False,0)
            adjustment.pack_start(panel,True,True,0)
            self.filter_scales[key]=scale
        self.button(adjustment,"filtersreset",self.reset_filters)
        controls=Gtk.Box(spacing=8)
        bottom.pack_start(controls,False,False,0)
        controls.pack_start(Gtk.Label(label=self.text["language"]),False,False,0)
        self.languages=Gtk.ComboBoxText.new_with_entry()
        self.languages.set_size_request(170,-1)
        controls.pack_start(self.languages,False,False,0)
        controls.pack_start(Gtk.Label(label=self.text["psm"]),False,False,0)
        self.psm=Gtk.ComboBoxText()
        for key,desc in (("3","Auto"),("6","Block"),("7","Single line"),("11","Sparse text")):
            self.psm.append(key,desc)
        self.psm.set_active_id("6")
        controls.pack_start(self.psm,False,False,0)
        self.button(controls,"ocr",self.perform_ocr)
        self.result=Gtk.TextView()
        self.result.set_wrap_mode(Gtk.WrapMode.WORD_CHAR)
        result_scroll=Gtk.ScrolledWindow()
        result_scroll.add(self.result)
        bottom.pack_start(result_scroll,True,True,0)
        actions=Gtk.Box(spacing=8)
        bottom.pack_start(actions,False,False,0)
        self.button(actions,"copy",self.copy_text)
        self.button(actions,"save",self.save_text)
        self.button(actions,"pdf",self.save_pdf)
        self.status=Gtk.Label(xalign=0)
        bottom.pack_start(self.status,False,False,0)
        self.show_all()
        self.fetch_languages()

    def dispose(self,*_):
        self.destroyed=True
        if self.filter_timer is not None:
            GLib.source_remove(self.filter_timer)
            self.filter_timer=None
        # Workers may still be writing intermediate files; do not delete while busy.
        if not self.render_busy and not self.busy:
            self.temp_workspace.cleanup()

    def sync_zoom(self,value):
        self.zoom_slider.handler_block_by_func(self.zoom_adjustment)
        self.zoom_slider.set_value(value*100)
        self.zoom_slider.handler_unblock_by_func(self.zoom_adjustment)

    def zoom_adjustment(self,slider):
        self.canvas.set_zoom(slider.get_value()/100)

    def filter_values(self):
        return {key:int(scale.get_value()) for key,scale in self.filter_scales.items()}

    def filter_changed(self,*_):
        self.generation+=1
        if self.filter_timer is not None:
            GLib.source_remove(self.filter_timer)
        self.filter_timer=GLib.timeout_add(400,self.begin_filter_render)

    def begin_filter_render(self):
        self.filter_timer=None
        if self.destroyed:return False
        if self.render_busy:
            self.render_pending=True
            return False
        values=self.filter_values()
        src=self.base_path
        sequence=self.generation
        output=self.work_dir / f"filter-{sequence}.png"
        self.render_busy=True
        self.status.set_text(self.text["busy"])
        def worker():
            try:
                render_filters(src,output,**values)
                result=(True,str(output),sequence)
            except Exception as exc:
                result=(False,str(exc),sequence)
            GLib.idle_add(self.filter_rendered,result)
        threading.Thread(target=worker,daemon=True).start()
        return False

    def filter_rendered(self,result):
        self.render_busy=False
        ok,output,sequence=result
        if self.destroyed:
            self.temp_workspace.cleanup()
            return False
        if ok and sequence==self.generation:
            self.image_path=output
            self.canvas.load_image(output,preserve=True)
            self.status.set_text(self.text["done"])
        elif not ok and sequence==self.generation:
            self.message(output)
        if self.render_pending or sequence!=self.generation:
            self.render_pending=False
            self.begin_filter_render()
        elif self.pending_geometry:
            operation=self.pending_geometry
            self.pending_geometry=None
            self.geometry(operation)
        return False

    def reset_filter_sliders(self):
        for key,scale in self.filter_scales.items():
            scale.handler_block_by_func(self.filter_changed)
            scale.set_value(100 if key=="saturation" else 0)
            scale.handler_unblock_by_func(self.filter_changed)

    def reset_filters(self,*_):
        self.generation+=1
        if self.filter_timer is not None:
            GLib.source_remove(self.filter_timer)
            self.filter_timer=None
        self.reset_filter_sliders()
        if self.render_busy:
            self.render_pending=True
        else:
            self.image_path=self.base_path
            self.canvas.load_image(self.base_path,preserve=True)
            self.status.set_text(self.text["done"])

    def geometry(self,operation):
        if self.busy:
            self.status.set_text(self.text["busy"])
            return
        if self.render_busy:
            self.pending_geometry=operation
            self.status.set_text(self.text["busy"])
            return
        if self.filter_timer is not None:
            GLib.source_remove(self.filter_timer)
            self.filter_timer=None
            self.pending_geometry=operation
            self.begin_filter_render()
            return
        self.generation+=1
        src=self.image_path
        output=self.work_dir / f"geometry-{self.generation}.png"
        self.render_busy=True
        def worker():
            try:result=(True,transform(src,output,operation))
            except Exception as exc:result=(False,str(exc))
            GLib.idle_add(self.geometry_done,result)
        threading.Thread(target=worker,daemon=True).start()

    def geometry_done(self,result):
        self.render_busy=False
        if self.destroyed:
            self.temp_workspace.cleanup()
            return False
        if result[0]:
            self.base_path=self.image_path=result[1]
            self.reset_filter_sliders()
            self.canvas.load_image(self.image_path,preserve=False)
            self.status.set_text(self.text["done"])
        else:self.message(result[1])
        return False

    def save_edited_image(self,*_):
        path=self.save_dialog(Path(self.original_path).stem+"_edited.png")
        if path:
            try:
                with Image.open(self.image_path) as img:
                    img.save(path)
            except Exception as exc:self.message(exc)

    def button(self,container,key,callback):
        b=Gtk.Button(label=self.text[key]);b.connect("clicked",callback)
        container.pack_start(b,False,False,0)

    def message(self,s):
        d=Gtk.MessageDialog(transient_for=self,flags=0,message_type=Gtk.MessageType.ERROR,
                            buttons=Gtk.ButtonsType.OK,text=self.text["error"])
        d.format_secondary_text(str(s))
        d.run();d.destroy()

    def asynchronous(self,operation,done):
        if self.busy:return
        self.busy=True;self.status.set_text(self.text["busy"])
        def task():
            try:result=(True,operation())
            except Exception as e:result=(False,str(e))
            GLib.idle_add(self.finished,done,result)
        threading.Thread(target=task,daemon=True).start()

    def finished(self,done,result):
        self.busy=False
        if result[0]:
            done(result[1])
            self.status.set_text(self.text["done"])
        else:
            self.status.set_text(str(result[1])[:180])
            self.message(result[1])
        return False

    def fetch_languages(self):
        self.asynchronous(installed_languages,self.display_languages)

    def display_languages(self,languages):
        self.languages.remove_all()
        for code in languages:self.languages.append(code,code)
        preferred="ita" if self.text==LANG["it"] else "eng"
        self.languages.set_active_id(preferred if preferred in languages else ("eng" if "eng" in languages else languages[0] if languages else None))

    def selected_languages(self):
        text=self.languages.get_child().get_text().strip()
        if not re.fullmatch(r"[A-Za-z0-9_-]+(?:\+[A-Za-z0-9_-]+)*",text):
            raise ValueError("Invalid Tesseract language expression")
        return text

    def perform_ocr(self,*_):
        if self.render_busy or self.filter_timer is not None:
            self.status.set_text(self.text["busy"])
            return
        try:language=self.selected_languages()
        except Exception as exc:self.message(exc);return
        box=self.canvas.box()
        psm=self.psm.get_active_id()
        self.asynchronous(lambda:ocr_file(self.image_path,box,language,psm),self.display_text)

    def display_text(self,result):
        self.result.get_buffer().set_text(result)

    def get_text(self):
        b=self.result.get_buffer()
        return b.get_text(b.get_start_iter(),b.get_end_iter(),True)

    def copy_text(self,*_):
        Gtk.Clipboard.get(Gdk.SELECTION_CLIPBOARD).set_text(self.get_text(),-1)
        self.status.set_text("Copied / Copiato")

    def save_dialog(self,default_name):
        chooser=Gtk.FileChooserDialog(title=self.text["save_title"],transient_for=self,
                                      action=Gtk.FileChooserAction.SAVE)
        chooser.add_buttons(self.text["cancel"],Gtk.ResponseType.CANCEL,
                            self.text["ok"],Gtk.ResponseType.OK)
        chooser.set_current_name(default_name)
        chooser.set_do_overwrite_confirmation(True)
        answer=chooser.get_filename() if chooser.run()==Gtk.ResponseType.OK else None
        chooser.destroy()
        return answer

    def save_text(self,*_):
        path=self.save_dialog(Path(self.image_path).stem+"_ocr.txt")
        if path:
            try:Path(path).write_text(self.get_text(),encoding="utf-8")
            except Exception as e:self.message(e)

    def save_region(self,*_):
        if self.render_busy or self.filter_timer is not None:return
        path=self.save_dialog(Path(self.image_path).stem+"_crop.png")
        if path:
            try:crop_image(self.image_path,self.canvas.box(),path)
            except Exception as e:self.message(e)

    def save_pdf(self,*_):
        if self.render_busy or self.filter_timer is not None:return
        path=self.save_dialog(Path(self.image_path).stem+"_ocr.pdf")
        if not path:return
        try:lang=self.selected_languages()
        except Exception as e:self.message(e);return
        box=self.canvas.box();psm=self.psm.get_active_id()
        self.asynchronous(lambda:ocr_file(self.image_path,box,lang,psm,fmt="pdf"),
                          lambda content:Path(path).write_bytes(content))
