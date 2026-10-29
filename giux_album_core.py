# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable, non-destructive multi-page photo album model and rendering engine.

All printed pixels, preview pixels and PDF pages come from render_page().
A .gpa project is UTF-8 JSON with relative image references wherever possible.
No CUPS calls, GTK dependencies or printer configuration changes belong here.
"""
from copy import deepcopy
from io import BytesIO
from pathlib import Path
import json
import math
import os
import tempfile

from PIL import Image, ImageDraw, ImageFont, ImageOps

VERSION = 1
PAPER_MM = {"A4": (210.0, 297.0), "A5": (148.0, 210.0),
            "4x6": (101.6, 152.4), "5x7": (127.0, 177.8)}
TEMPLATES = {"single": (1, 1), "duo": (2, 1), "four": (2, 2),
             "six": (3, 2), "nine": (3, 3)}
BACKGROUNDS = {"white": "#ffffff", "cream": "#fff6e7",
               "sky": "#eaf5fa", "rose": "#fff0f1"}
DECORATIONS = ("none", "classic", "confetti", "botanical")
FONT_REGULAR = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
FONT_BOLD = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf")
MAX_PAGES = 60
MAX_IMAGES = 540


def new_page(template="four"):
    if template not in TEMPLATES:
        raise ValueError("Unknown album template")
    count = TEMPLATES[template][0] * TEMPLATES[template][1]
    return {"template": template, "title": "", "footer": "", "background": "white",
            "decoration": "classic", "slots": [{"path": "", "caption": ""} for _ in range(count)]}


def new_project(paper="A4", orientation="portrait", template="four"):
    if paper not in PAPER_MM or orientation not in ("portrait", "landscape"):
        raise ValueError("Invalid paper or orientation")
    return {"format": "giux-photo-album", "version": VERSION,
            "paper": paper, "orientation": orientation, "pages": [new_page(template)]}


def validate(project):
    if not isinstance(project, dict) or project.get("format") != "giux-photo-album" or project.get("version") != VERSION:
        raise ValueError("Not a supported Giux Photo Album project")
    if project.get("paper") not in PAPER_MM or project.get("orientation") not in ("portrait", "landscape"):
        raise ValueError("Unsupported paper/orientation")
    pages = project.get("pages")
    if not isinstance(pages, list) or not 1 <= len(pages) <= MAX_PAGES:
        raise ValueError("Invalid album page count")
    for page in pages:
        if not isinstance(page, dict) or page.get("template") not in TEMPLATES:
            raise ValueError("Invalid album template")
        if page.get("background") not in BACKGROUNDS or page.get("decoration") not in DECORATIONS:
            raise ValueError("Unknown background or decoration")
        for key in ("title", "footer"):
            if not isinstance(page.get(key), str) or len(page[key]) > 300:
                raise ValueError("Invalid page text")
        slots = page.get("slots")
        columns, rows = TEMPLATES[page["template"]]
        if not isinstance(slots, list) or len(slots) != columns * rows:
            raise ValueError("Wrong photo slot count")
        for slot in slots:
            if not isinstance(slot, dict):
                raise ValueError("Invalid photo slot")
            for key, limit in (("path", 4096), ("caption", 180)):
                if not isinstance(slot.get(key), str) or len(slot[key]) > limit:
                    raise ValueError("Invalid photo field")
    return project


def set_template(page, template):
    if template not in TEMPLATES:
        raise ValueError("Unknown template")
    existing = page["slots"]
    n = math.prod(TEMPLATES[template])
    page["template"] = template
    page["slots"] = (existing[:n] + [{"path": "", "caption": ""} for _ in range(max(n - len(existing), 0))])


def page_size(project, dpi=300):
    w, h = PAPER_MM[project["paper"]]
    if project["orientation"] == "landscape":
        w, h = h, w
    return round(w * dpi / 25.4), round(h * dpi / 25.4)


def layout_regions(project, index, dpi=300):
    """Return exact page-space rectangles for all photo slots."""
    page = project["pages"][index]
    width, height = page_size(project, dpi)
    scale = dpi / 25.4
    margin = 7.0 * scale
    gap = 3.5 * scale
    title_height = 18.0 * scale if page["title"] else 7.0 * scale
    footer_height = 12.0 * scale if page["footer"] else 5.0 * scale
    columns, rows = TEMPLATES[page["template"]]
    usable_w = width - 2 * margin - gap * (columns - 1)
    usable_h = height - 2 * margin - title_height - footer_height - gap * (rows - 1)
    if usable_w <= columns * 12 or usable_h <= rows * 12:
        raise ValueError("Paper size too small for this template")
    cell_w, cell_h = usable_w / columns, usable_h / rows
    return [(round(margin + col * (cell_w + gap)),
             round(margin + title_height + row * (cell_h + gap)),
             round(cell_w), round(cell_h))
            for row in range(rows) for col in range(columns)]


def _font(size, bold=False):
    path = FONT_BOLD if bold else FONT_REGULAR
    return ImageFont.truetype(str(path), max(9, round(size)))


def _text_line(draw, xy, text, font, color, max_width=None, anchor=None):
    """Bound a line of user-provided text to a specified drawing width."""
    line = text.replace("\n", " ").strip()
    if max_width is not None:
        while line and draw.textbbox((0, 0), line, font=font)[2] > max_width:
            line = line[:-1]
        if line != text.replace("\n", " ").strip() and len(line) >= 2:
            line = line[:-2].rstrip() + "…"
    if line:
        draw.text(xy, line, font=font, fill=color, anchor=anchor)


def _decoration(draw, width, height, dpi, mode, color="#c5a989"):
    unit = dpi / 25.4
    if mode == "none":
        return
    if mode == "classic":
        border = round(3.5 * unit)
        stroke = max(1, round(0.35 * unit))
        draw.rectangle((border, border, width - border, height - border), outline=color, width=stroke)
        draw.line((border + 2 * unit, 18 * unit, width - border - 2 * unit, 18 * unit),
                  fill=color, width=max(1, stroke // 2))
    elif mode == "confetti":
        colors = ("#db6d87", "#68a6b6", "#e2bc5e", "#9189b8")
        for i in range(22):
            x = width * (i + 1) / 24
            y = (5 + (i * 11) % 9) * unit
            r = (0.55 + (i % 3) * 0.3) * unit
            draw.ellipse((x - r, y - r, x + r, y + r), fill=colors[i % len(colors)])
    elif mode == "botanical":
        for side in (0, 1):
            x = 10 * unit if not side else width - 10 * unit
            y = 10 * unit
            dx = 1 if not side else -1
            draw.arc((x - 7 * unit, y - 6 * unit, x + 7 * unit, y + 12 * unit),
                     55 if not side else 125, 260 if not side else 330,
                     fill="#769b7f", width=max(2, round(unit * 0.5)))
            for j in range(3):
                px = x + dx * j * 2 * unit
                py = y + j * 3 * unit
                draw.ellipse((px, py, px + 3 * unit, py + 1.5 * unit), fill="#a2baa2")


def render_page(project, index=0, dpi=150):
    """Rasterize the page; preview and print share this same geometry."""
    validate(project)
    if not 0 <= index < len(project["pages"]):
        raise IndexError("Album page not found")
    if not 50 <= dpi <= 300:
        raise ValueError("Unsupported render DPI")
    width, height = page_size(project, dpi)
    page = project["pages"][index]
    im = Image.new("RGB", (width, height), BACKGROUNDS[page["background"]])
    draw = ImageDraw.Draw(im)
    unit = dpi / 25.4
    _decoration(draw, width, height, dpi, page["decoration"])
    if page["title"]:
        _text_line(draw, (width / 2, round(11 * unit)), page["title"],
                   _font(19 * dpi / 72, True), "#24364d", width - 26 * unit, "mm")
    if page["footer"]:
        _text_line(draw, (width / 2, round(height - 9 * unit)), page["footer"],
                   _font(10 * dpi / 72), "#48586d", width - 20 * unit, "mm")
    for slot, (x, y, w, h) in zip(page["slots"], layout_regions(project, index, dpi)):
        cap_h = round(7 * unit) if slot["caption"] else 0
        frame_h = h - cap_h
        draw.rectangle((x, y, x + w - 1, y + frame_h - 1),
                       fill="#f7f7f6", outline="#a9afad", width=max(1, round(0.28 * unit)))
        photo_path = Path(slot["path"]).expanduser() if slot["path"] else None
        if photo_path is not None and photo_path.is_file():
            try:
                with Image.open(photo_path) as original:
                    upright = ImageOps.exif_transpose(original)
                    upright.thumbnail((6000, 6000), Image.Resampling.LANCZOS)
                    photo = upright.convert("RGB")
                target = (max(1, w - round(1 * unit)), max(1, frame_h - round(1 * unit)))
                if page.get("fit", "fill") == "fit":
                    rendered = ImageOps.contain(photo, target, Image.Resampling.LANCZOS)
                else:
                    rendered = ImageOps.fit(photo, target, Image.Resampling.LANCZOS)
                px = x + (w - rendered.width) // 2
                py = y + (frame_h - rendered.height) // 2
                im.paste(rendered, (px, py))
                photo.close()
                rendered.close()
            except (OSError, ValueError) as err:
                _text_line(draw, (x + 5, y + 5), str(err)[:35],
                           _font(10 * dpi / 72), "#b12c31", w - 10)
        else:
            placeholder = "ADD PHOTO" if not slot["path"] else "IMAGE NOT FOUND"
            _text_line(draw, (x + w / 2, y + frame_h / 2), placeholder,
                       _font(11 * dpi / 72), "#a0a9b3", w - 12, "mm")
        if slot["caption"]:
            _text_line(draw, (x + w / 2, y + h - cap_h / 2), slot["caption"],
                       _font(9 * dpi / 72), "#273242", w - 4, "mm")
    return im


def render_preview(project, index, max_size=(960, 760)):
    image = render_page(project, index, dpi=150)
    image.thumbnail(max_size, Image.Resampling.LANCZOS)
    result = BytesIO()
    image.save(result, "PNG")
    image.close()
    return result.getvalue()


def export_png(project, index, destination):
    validate(project)
    image = render_page(project, index, 300)
    try:
        image.save(str(destination), "PNG", dpi=(300, 300))
    finally:
        image.close()
    return Path(destination)


def export_pdf(project, destination):
    """Export all pages at 300 DPI; no printing is triggered."""
    validate(project)
    pages = []
    try:
        for i in range(len(project["pages"])):
            pages.append(render_page(project, i, 300))
        pages[0].save(str(destination), "PDF", save_all=True,
                      append_images=pages[1:], resolution=300.0,
                      title="GiuxLab Photo Album")
        return Path(destination)
    finally:
        for image in pages:
            image.close()


def save_project(project, destination):
    """Write the project atomically; store relative photo links when possible."""
    validate(project)
    destination = Path(destination).expanduser().resolve()
    parent = destination.parent
    copy = deepcopy(project)
    for page in copy["pages"]:
        for slot in page["slots"]:
            if slot["path"]:
                slot["path"] = os.path.relpath(Path(slot["path"]).expanduser().resolve(), parent)
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=parent,
                                     prefix=".giux-album-", suffix=".tmp", delete=False) as stream:
        temp = Path(stream.name)
        json.dump(copy, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    try:
        os.replace(temp, destination)
    finally:
        temp.unlink(missing_ok=True)
    return destination


def load_project(source):
    source = Path(source).expanduser().resolve()
    data = json.loads(source.read_text(encoding="utf-8"))
    validate(data)
    for page in data["pages"]:
        for slot in page["slots"]:
            if slot["path"]:
                photo = Path(slot["path"]).expanduser()
                slot["path"] = str((source.parent / photo).resolve() if not photo.is_absolute() else photo.resolve())
    return data
