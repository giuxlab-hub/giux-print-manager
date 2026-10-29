# GiuxLab Print & Scan Manager (0.1.2)

GTK3 printer, photo-printing and SANE scanner desktop application. Italian/English selectable at runtime. Printer-specific integrations use JSON profiles in /usr/share/giux-print-manager/profiles and ~/.config/giux-print-manager/profiles.

## Capabilities

- List CUPS queues without altering or duplicating them.
- Open official printer web administration, inspect queue state.
- Photos: JPEG/PNG/TIFF, EXIF orientation, page layout at 300 dpi, 3 mm margins, A4/A5/4x6/5x7, CUPS quality, media type; print job confirmation.
- SANE scanner discovery and scanning to PNG/JPEG/TIFF at 150/300/600 dpi, optional Flatbed or ADF source; output file selection; XSane launcher.
- Add a printer JSON profile with keys id, match, web_url, photo_media list containing key and label.

## Limitations

- Bundled printer profiles use local network addresses and must be edited for a different site. Print queues are discovered automatically.
- SANE scanner detection depends on configured backends; detection can be slow or unsuccessful on a network. A SANE device ID can be manually entered.
- Canon maintenance and Brother toner status are accessed via official embedded web interface; this does not implement undocumented proprietary commands.
- No borderless printing, ICC color management, PDF output, multi-page feeder job orchestration, or scanner preview/crop UI yet.
- When printing on laser devices, use ONLY laser-compatible media; do not insert inkjet photo paper.
- This is an experimental release. Printer operations need user confirmation and physical testing.

## Dependencies

Runtime: python3, python3-gi, gir1.2-gtk-3.0, python3-pil, cups-client, sane-utils, sane-airscan, xdg-utils. Optional: xsane.

License: GPL-3.0-or-later. Canon and Brother trademarks belong to their respective owners. No affiliation.

## Security and dependencies
The application invokes only /usr/bin/lp, lpstat, scanimage and xdg-open/XSane through subprocess argument lists, without shell interpolation. Image conversions use python3-pil. Dependencies are declared in Debian control; XSane remains optional (Recommends).

## Preview and region selection (0.1.2)

Open Scanner, discover a device, then click Preview (100 dpi). Drag with the left mouse button over the resulting image to select a rectangular region. Click Scan to acquire only that region at the chosen final resolution. Clear selection to scan the whole flatbed. This invokes the SANE scanner geometry options (top-left and width/height in mm), rather than merely cropping an already acquired full-resolution image. Selection is for flatbed scanning only; the ADF is not supported for region selection. Preview is discarded if switching the application language.

Preview uses a temporary PNG, removed after image loading. Scan output supports PNG/JPEG/TIFF. Tested crop capture on Canon G600 and Brother DCP-L2665DW.

## Version 0.2.0: acquired-image canvas and OCR

After a successful scan, the original image is saved and a **separate OCR workspace window** opens automatically. Existing image files (PNG/JPEG/TIFF) can also be opened in this workspace using the Scan tab's **Open image in OCR workspace** action.

The dedicated canvas includes zoom, image-coordinate rectangle selection (drag to create; drag inside the rectangle to move), a clear-selection button, and high-resolution region export. OCR runs on the selected original-pixel region (or the full image if no selection), using Tesseract subprocesses off the GTK main thread.

OCR languages are populated dynamically from `tesseract --list-langs`, not hard-coded. Individual languages and combinations like `eng+ita` are supported; only models actually installed are accepted. Page segmentation options: PSM 3, 6, 7, 11. The OCR text appears in an editable text panel with copy-to-clipboard and UTF-8 save actions. A searchable PDF export uses Tesseract's PDF renderer on the selected region.

**Dependencies**: `tesseract-ocr` is required by the Debian package and brings the default English and OSD data on Debian. Additional language packages are optional, listed in the Debian `Suggests` field, including the `tesseract-ocr-all` meta-package for users who explicitly wish to install all models. `Suggests` does not automatically install those extra packages. The PDF/OCR extension does not require OCRmyPDF, Poppler or qpdf because it operates on acquired raster images rather than existing PDF documents.

**Design inspiration**: [GiuxLab PDFLab Crop & OCR](https://github.com/giuxlab-hub/pdflab-crop-ocr), which is written in Tcl/Tk. This GTK3 implementation is independent, not a copied port.

Known limitations: the acquired-image workspace currently has a single selectable rectangle and move operation, without resize handles; zoom uses a horizontal slider. Editable OCR text can be saved separately, but the PDF action re-runs Tesseract from the selected image region rather than embedding edits made in the text panel. Printer and scanner operations were previously tested on Canon G600 and Brother DCP-L2665DW; this release's OCR workspace was tested with generated text images and existing scanner output.

## Version 0.3.0 — Interactive image editing

The acquired-image OCR workspace includes **non-destructive** ImageMagick 7 processing. The original acquisition file remains unchanged. Toolbar operations: rotate left/right 90°, horizontal mirror, vertical mirror, export edited full image. Adjustments use simple, non-numeric GTK sliders for brightness, contrast, sharpness, and saturation, processed by ImageMagick in a worker thread after a short pause. Reset returns to the most recent geometric image, without applying cumulative filter passes. OCR, cropped PNG and searchable PDF export operate on the processed image, not on the untouched original. The edited full image can also be saved to PNG.

The canvas supports wheel zoom centered on the pointer, middle-button drag to pan within the scrolled viewport, left drag to create a crop selection, left drag inside to move it, and eight white/blue resize handles. Selections use original-image pixel coordinates, independent of zoom. Transformations reset the selection to avoid mismatched geometry. Reset Filter does not undo an earlier rotation/flip. The package depends on `imagemagick-7.q16` so that `/usr/bin/magick` is available; all prior dependencies remain declared in the Debian control file.
