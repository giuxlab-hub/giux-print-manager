# GiuxLab Print & Scan Manager

**Experimental, modular GTK3 desktop application for Linux printing, photo layouts and SANE scanning.**

**Latest version:** 0.3.2 · **Languages:** Italian and English · **License:** GPL-3.0-or-later · **Platform:** Debian/Linux

[Download Debian package and original source](https://github.com/giuxlab-hub/giux-print-manager/releases/latest) · [Giux-Lab](https://giux-lab.it/) · [Original README](README.original.md)

GiuxLab Print & Scan Manager integrates three distinct workflows into one desktop interface: CUPS printer queues, photo printing, and SANE scanner acquisition. Printer-model extensions are currently **declarative JSON profiles**, not independent executable plugins. The architecture is an early-stage project and is published as such.

## 0.3.2 — Linux launcher fix

Fixes an import-order regression in the previous 0.3.1 Debian package: the launcher imported `photo_editor` before adding the installed modules directory to the Python import path. The executable now resolves its actual installation location and loads the companion modules before importing them. This correction preserves the photo-print editor, the acquired-image OCR workspace, CUPS/SANE routines and all existing profiles. Existing 0.3.1 packages remain archived.

## 0.3.1 — Combined photo printing and acquired-image OCR

**Version 0.3.1 combines two independently developed features:** the author's original 0.3.0 acquired-image OCR/retouching workspace, and the interactive photo-print editor released separately through GitHub.

- **Photo printing:** rotation, flips, contrast/brightness/saturation/sharpening/blur, grayscale/sepia/auto-level filters and slider-only controls in a pan/zoom canvas, with the full-resolution print using the same processing sequence.
- **Acquired-image workspace:** retains the original 0.3.0 scanner Preview/crop selection, Tesseract OCR (with installed language discovery), editable text, selection/full-image export, searchable PDF, zoom/pan, handles and ImageMagick filters.
- **Printing and scanning:** retains the CUPS/SANE/eSCL services, printer JSON profiles and device authorities. Neither workspace overwrites the original source image.

**Dependencies:** Python 3, GTK3, Pillow, CUPS, SANE, `sane-airscan`, `tesseract-ocr` and `imagemagick-7.q16` on Debian 13. Additional OCR language models are optional. See [the author's original 0.3.0 guide](README.author-v0.3.0.md) for the acquired-image OCR interface and [the photo guide](README.package.md) for the print editor.

**Scope:** Experimental software. The two editors are separate workflows and do not automatically share editing sessions. No physical printer or scanner operation is claimed by this merge.

## Photo-print editor — adjustments with sliders

The photo workspace now includes an interactive **pan/zoom canvas**, 90° rotation buttons, a fine-angle slider, horizontal and vertical reflections and an **ImageMagick 7** adjustments panel. Brightness, contrast, saturation, sharpening and blur are controlled with **sliders only**, without numerical input fields. Filters include **Grayscale, Sepia and Auto levels**. A reset control restores the original appearance.

The original image is never modified. Preview and printing use the same ImageMagick transformations; printed output is processed at full resolution. Zoom and pan affect only canvas navigation, while Fit/Fill remains an independent print-layout choice. The image, controls and print selections are retained when switching the interface language.

Full instructions: [Photo workspace guide](README.package.md) and [Changelog](CHANGELOG.md).

## Features

- **Printers:** discover existing CUPS queues, inspect status, open CUPS configuration, and open the device's official web-based management page when a corresponding JSON profile is configured.
- **Photo printing:** open JPEG, PNG or TIFF images; respect EXIF rotation; create a 300-DPI page layout with 3 mm margins; choose A4, A5, 4×6 or 5×7 paper; fit or fill with cropping; select media and print quality; confirm before submitting the job.
- **Scanning:** discover SANE devices or enter a SANE device identifier, select 150/300/600 DPI, choose color/gray/lineart and Flatbed/ADF, then save PNG, JPEG or TIFF; optionally launch XSane.
- **Italian/English interface:** switch language at runtime.
- **Device profiles:** included JSON profiles for Canon G600 and Brother DCP-L2665DW, defining queue matching, official web UI address, photo media options and eSCL scanner URL.

### Modules and extensibility

The **Modules** tab currently lists recognized JSON device profiles. To add another printer, provide a compatible JSON file in `~/.config/giux-print-manager/profiles/`. The installed default profiles live under `/usr/share/giux-print-manager/profiles/`.

A device profile defines `id`, `match`, `web_url`, `photo_media`, and optionally `scanner_url`. Photo media entries contain a CUPS option `key` and a human-readable `label`.

The included profiles contain **example local-network addresses** from the development setup. Edit them or provide your own local profile before using Web Management or eSCL scanning on another network. The application does not create or change CUPS printer queues.

In v0.1.1, scanner discovery and scanning use an isolated SANE configuration in the user's cache to limit backend discovery to declared eSCL profiles. It does not modify system-wide `/etc/sane.d`.

## Debian installation

Download `giux-print-manager_0.3.2_all.deb` from [v0.3.2 releases](https://github.com/giuxlab-hub/giux-print-manager/releases/tag/v0.3.2), then:

```bash
sudo apt install ./giux-print-manager_0.3.2_all.deb
```

Required Debian packages are `python3`, `python3-gi`, `gir1.2-gtk-3.0`, `python3-pil`, `imagemagick-7.q16` (ImageMagick 7), `cups-client`, `sane-utils`, `sane-airscan`, `tesseract-ocr` and `xdg-utils`. The optional `xsane` package is recommended.

Start the application through the desktop applications menu or:

```bash
giux-print-manager
```

Printing requires a configured CUPS queue; scanning requires an available SANE backend and a supported scanner.

## Build from source

```bash
git clone https://github.com/giuxlab-hub/giux-print-manager.git
cd giux-print-manager
./build-deb.sh
```

The repository builder writes `giux-print-manager_0.3.2_all.deb` in the checkout directory, installing `photo_editor.py` together with the OCR/image helpers under `/usr/share/giux-print-manager/`. Historical original source archives remain separately preserved.

## Current limitations

This is an **experimental** desktop application, not a finished general-purpose print/scan platform.

- No borderless printing, ICC color-management workflow or multi-page ADF orchestration. The OCR workspace now supports scanner preview/crop and searchable PDF, with limitations documented separately.
- The effective behavior of CUPS media, page and quality options depends on the installed printer driver.
- Network scanner discovery can be slow, unavailable, or dependent on correct local eSCL/SANE configuration.
- Canon maintenance and Brother toner/device management are delegated to their official web interfaces; the software does not execute undocumented maintenance commands.
- For laser printers, use **laser-compatible media only**, never inkjet photo paper.
- No physical hardware or cross-platform GUI qualification is claimed by the GitHub publication.

## Source, history and license

Versions **0.1.0** and **0.1.1** remain available with their original Debian/source archives and SHA-256 checksums. GitHub version **0.2.0** added ImageMagick-based photo-print editing. The author independently advanced scanning/OCR through version **0.3.0**; version **0.3.1** combines both features.

Source code is provided under **GNU GPL v3 or later (GPL-3.0-or-later)**; see [COPYING](COPYING). Canon and Brother names are used to identify compatible printers; this project is **not affiliated** with their manufacturers.

---

## Italiano

**GiuxLab Print & Scan Manager** è un'applicazione sperimentale indipendente per **stampa, fotografie e scansioni** in ambiente Linux, realizzata in Python 3/GTK3.

La versione disponibile è la **0.3.2**. L'interfaccia è in italiano e inglese, con selezione della lingua durante l'utilizzo.

### Regolazione fotografie in stampa — versione consolidata 0.3.1

La pagina fotografica comprende **canvas navigabile con pan trascinando e zoom con la rotella**, rotazione a passi di 90°, inclinazione fine, riflessione orizzontale/verticale e regolazioni ImageMagick di **luminosità, contrasto, saturazione, nitidezza e sfocatura**. I parametri si impostano soltanto con **cursori**, senza caselle numeriche. Sono disponibili filtri bianco e nero, seppia e livelli automatici.

Le modifiche sono non distruttive: l'immagine originale rimane intatta e l'output di stampa applica i medesimi filtri dell'anteprima, a piena risoluzione. Il pan e lo zoom non modificano l'impaginazione finale.

### Funzioni presenti

- Gestione delle code CUPS esistenti, stato e accesso alle pagine web ufficiali delle stampanti.
- Stampa fotografica JPEG/PNG/TIFF con orientamento EXIF, formati A4/A5/4×6/5×7, margini 3 mm, qualità e tipo di carta.
- Acquisizione tramite SANE con risoluzioni 150/300/600 DPI, Flatbed/ADF e salvataggio PNG/JPEG/TIFF.
- Profili JSON per Canon G600 e Brother DCP-L2665DW, estendibili attraverso `~/.config/giux-print-manager/profiles/`.
- Nella 0.1.1, configurazione SANE privata per i dispositivi eSCL, senza alterare i file di configurazione globali.

### Installazione

Scaricare [il pacchetto Debian 0.3.2](https://github.com/giuxlab-hub/giux-print-manager/releases/tag/v0.3.2):

```bash
sudo apt install ./giux-print-manager_0.3.2_all.deb
```

I profili attuali rappresentano **moduli dichiarativi di configurazione**, non un sistema completo di plugin eseguibili. Gli indirizzi IP contenuti nei profili sono esempi del sistema di sviluppo e devono essere adattati alla propria rete.

### Funzioni ancora da sviluppare

Non sono ancora presenti stampa senza bordi, gestione ICC e orchestrazione multipagina dell'ADF. L'interfaccia OCR acquisita dalla versione 0.3.0 include invece anteprima/ritaglio e PDF ricercabile. Per stampanti laser utilizzare esclusivamente supporti compatibili con la stampa laser.

**Licenza:** GNU GPL-3.0-or-later. Progetto Giux-Lab indipendente, non affiliato a Canon o Brother.

[Archivio delle release](https://github.com/giuxlab-hub/giux-print-manager/releases) · [Provenienza delle sorgenti](SOURCE_PROVENANCE.md)
