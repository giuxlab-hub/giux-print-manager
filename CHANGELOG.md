# Changelog

## 0.4.0 — Album Composer

- Added a separate Album tab, album model and Pillow-based page renderer.
- Added accurate page preview, 1/2/4/6/9-photo templates, portrait/landscape and paper format choices, title/captions/footer and decorative backgrounds.
- Added multiple album pages, automatic continuation for photo batches, zoom/pan preview and open/save `.gpa` UTF-8 project files.
- Added PNG (current page), PDF (all pages) export and opt-in CUPS print of the album.
- Kept Photo Print, Scanner/OCR, ImageMagick and printer profiles independent and unchanged.
- Published release using the author-evaluated local 0.4.0 package without changing its original archives.

## 0.3.2 — Launch fix

- Fix the startup import-order regression in the v0.3.1 Debian package: installed `photo_editor.py` and OCR helpers are resolved before imports.
- Resolve the relative Debian installation prefix while retaining source-checkout execution.
- Add a regression test that executes the actual launcher from an isolated extracted Debian package, without altering the installed application or submitting print/scan jobs.
- No changes to the photo editor's filters, the OCR workspace, CUPS/SANE behavior or printer profiles.

## 0.3.1 — Consolidated OCR workspace and photo-print editor

- Based on the author's frozen original 0.3.0 source and release assets, preserving its scan Preview, OCR, searchable-PDF and acquired-image ImageMagick controls.
- Integrated the independent photo-print canvas, rotation/reflection controls and non-destructive ImageMagick slider pipeline developed on the public 0.2.0 branch.
- Preserved both independent workflows and the existing CUPS/SANE/profile authorities.
- Updated Debian dependencies, installation packaging, bilingual documentation and merged automated test coverage.

## 0.2.0 — Interactive photo canvas and ImageMagick processing

- Introduced a new `photo_editor.py` module for non-destructive photo transformations shared by preview and final printing.
- Replaced the static GTK image preview with a GTK DrawingArea canvas supporting left/middle-button pan, cursor-centered wheel zoom, and fit-to-view.
- Added rotation left/right by 90°, fine-angle rotation by slider, and horizontal/vertical mirror toggles.
- Added slider-only controls for brightness, contrast, saturation, sharpening and blur; no editable numeric fields.
- Added filter presets: original, grayscale, sepia and auto-level, with a Reset control.
- Added asynchronous bounded preview rendering, debounced slider updates, stale-preview cancellation and error/status messages.
- Print output applies the same transforms at full resolution before the existing 300 DPI CUPS page layout, with independent Fit/Fill selection and 3 mm margins.
- Preserved photo and adjustment state during Italian/English UI language changes.
- Declared ImageMagick 7 as a runtime dependency and packaged the independent module under `/usr/lib/giux-print-manager/`.
- Added source-only and live ImageMagick tests. The original photo is never overwritten.
- Preserved original CUPS/SANE and printer-profile behavior. No physical-printer validation claimed.

## 0.1.1 — Isolated SANE/eSCL profiles

- Introduced an isolated per-user SANE configuration scoped to the declared eSCL scanner profiles.
- Updated Canon G600 and Brother DCP-L2665DW JSON profiles to include scanner endpoints.
- Preserved original author `.deb` and source tarball.

## 0.1.0 — Initial experimental release

- GTK3 application integrating CUPS printer queues, simple photo-print layouts and SANE scanning.
- Bilingual Italian/English UI with JSON printer profile configuration.
