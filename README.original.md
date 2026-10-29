# GiuxLab Print & Scan Manager (0.1.0)

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
