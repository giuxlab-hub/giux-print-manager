#!/bin/sh
set -eu
cd "$(dirname "$0")"
V=0.3.2
S=$(mktemp -d)
trap 'rm -rf "$S"' EXIT
mkdir -p "$S/DEBIAN" "$S/usr/bin" "$S/usr/share/giux-print-manager/profiles" "$S/usr/share/applications" "$S/usr/share/doc/giux-print-manager" "$S/usr/share/icons/hicolor/scalable/apps"
install -m 755 giux-print-manager "$S/usr/bin/giux-print-manager"
install -m 644 photo_editor.py "$S/usr/share/giux-print-manager/photo_editor.py"
install -m 644 giux_ocr_workspace.py "$S/usr/share/giux-print-manager/giux_ocr_workspace.py"
install -m 644 giux_image_canvas.py giux_image_filters.py "$S/usr/share/giux-print-manager/"
install -m 644 profiles/*.json "$S/usr/share/giux-print-manager/profiles/"
install -m 644 README.package.md "$S/usr/share/doc/giux-print-manager/README.md"
install -m 644 COPYING "$S/usr/share/doc/giux-print-manager/COPYING"
cat > "$S/DEBIAN/control" <<'CONTROL'
Package: giux-print-manager
Version: 0.3.2
Section: utils
Priority: optional
Architecture: all
Maintainer: GiuxLab <noreply@giux-lab.it>
Depends: python3, python3-gi, gir1.2-gtk-3.0, python3-pil, cups-client, sane-utils, sane-airscan, xdg-utils, tesseract-ocr, imagemagick-7.q16
Recommends: xsane
Suggests: tesseract-ocr-all, tesseract-ocr-ita, tesseract-ocr-deu, tesseract-ocr-fra, tesseract-ocr-spa, tesseract-ocr-por, tesseract-ocr-chi-sim, tesseract-ocr-chi-tra, tesseract-ocr-jpn, tesseract-ocr-kor
Description: Modular bilingual print, photo and scan GUI
 GTK3 front end for CUPS printing, photo layouts and SANE scanners.
 Includes extensible model profiles, Canon G600 and Brother DCP-L2665DW.
CONTROL
cat > "$S/usr/share/applications/giux-print-manager.desktop" <<'DESKTOP'
[Desktop Entry]
Type=Application
Name=GiuxLab Print & Scan Manager
Name[it]=GiuxLab Gestione Stampanti e Scanner
Comment=Printers, photos and scanners
Comment[it]=Stampanti, fotografie e scanner
Exec=giux-print-manager
Icon=giux-print-manager
Terminal=false
Categories=System;GTK;
Keywords=CUPS;SANE;Print;Scan;Photo;Stampa;Scanner;
StartupNotify=true
DESKTOP
cat > "$S/usr/share/icons/hicolor/scalable/apps/giux-print-manager.svg" <<'SVG'
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64"><rect width="64" height="64" rx="12" fill="#22374b"/><rect x="12" y="24" width="40" height="26" rx="4" fill="#dbe5ef"/><rect x="18" y="10" width="28" height="22" rx="2" fill="white"/><path d="M22 16h20m-20 6h15" stroke="#4274a0" stroke-width="2"/><rect x="18" y="40" width="28" height="13" rx="2" fill="white"/><path d="M23 45h18" stroke="#28b6af" stroke-width="3"/><circle cx="46" cy="32" r="2" fill="#32bf69"/></svg>
SVG
find "$S" -type d -exec chmod 755 {} +
dpkg-deb --build --root-owner-group "$S" "./giux-print-manager_${V}_all.deb"
