# GiuxLab Print & Scan Manager 0.3.2

GTK3 desktop manager for Linux printing, photo editing/printing and SANE scanning.

## Photo workspace

The photo workspace now has an interactive **pan and zoom canvas** and a side panel of adjustment controls.

- Drag with the left or middle mouse button to pan the image.
- Zoom at the cursor position using the mouse wheel; **Fit view** centers the full preview.
- Rotate left or right by 90°, or use the **Fine rotation** slider for intermediate angles.
- Flip horizontally or vertically with dedicated checkboxes.
- Adjust **brightness, contrast, saturation, sharpening and blur** using sliders only. No numeric entry is required.
- Choose a filter from **Original, Grayscale, Sepia and Auto levels**.
- **Reset edits** restores the default transforms without modifying the source file.
- Change the language between **Italiano** and **English** without discarding the current photo or adjustment state.

The image-processing backend is **ImageMagick 7**. ImageMagick renders the bounded preview and the full-resolution adjusted print input using the same transformations. Paper layout at 300 DPI continues to use Pillow, with 3 mm margins and A4, A5, 4×6 or 5×7 sizes.

**Preview zoom/pan never changes the printed crop.** Paper layout is controlled independently by Fit/Fill. The original photo is never overwritten. Printing remains subject to user confirmation and uses the existing CUPS authority.

## Other capabilities

CUPS printer queue discovery, official device web management, JSON device profiles for Canon G600 and Brother DCP-L2665DW, and SANE scanner discovery/acquisition are retained from 0.1.1.

The device profile system remains experimental: current modules are declarative JSON profiles rather than general-purpose executable plugins.

## Install

Install the packaged `giux-print-manager_0.3.2_all.deb` with:

```bash
sudo apt install ./giux-print-manager_0.3.2_all.deb
```

The package requires Python 3, GTK3 PyGObject, Pillow, CUPS tools, SANE tools, `sane-airscan`, `xdg-utils` and **ImageMagick 7**. XSane is optional.

## Build

```bash
./build-deb.sh
```

The new processing module `photo_editor.py` is installed under `/usr/share/giux-print-manager/`. The main application imports it from the local checkout or the installed Debian module directory.

## Italiano

La versione 0.2.0 introduce un **canvas navigabile** per la fotografia, con trascinamento per il pan e zoom con la rotella. Il pannello laterale consente rotazioni a passi di 90°, inclinazione fine con cursore, riflessione orizzontale/verticale, luminosità, contrasto, saturazione, nitidezza, sfocatura e filtri (Originale, Bianco e nero, Seppia, Livelli automatici).

**Nessun campo per l'inserimento di numeri:** le regolazioni utilizzano esclusivamente cursori e controlli grafici. La fotografia originale rimane invariata e la stampa usa le stesse elaborazioni dell'anteprima, calcolate a piena risoluzione. Il pan e lo zoom riguardano solo la visualizzazione sul canvas.

La selezione della lingua italiano/inglese conserva la fotografia e le regolazioni. Stampa, scansione SANE e profili JSON per le stampanti restano disponibili.

**Licenza:** GNU GPL-3.0-or-later. Applicazione sperimentale, non affiliata ai produttori delle stampanti.

## OCR and acquired-image workspace

Version 0.3.2 also integrates the author's separate scanner-image editor from 0.3.0: rectangular capture/resize handles, zoom/pan, Tesseract text OCR, configurable language/PSM, original-image/region export and searchable PDF. This independent workspace has its own ImageMagick sliders and is opened from scanning or the Scan tab. See `README.author-v0.3.0.md`.

## 0.3.2 startup correction

The launcher now resolves the installed helper-module directory before importing the photo editor and OCR workspace. This corrects the failure to open the v0.3.1 Debian package from the Linux desktop menu.
