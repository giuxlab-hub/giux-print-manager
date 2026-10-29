# Source provenance — GiuxLab Print & Scan Manager

Source archives and Debian packages are copied from the original author's Linux home, and the files are read-only inputs to this publication workflow. No private scan/print jobs, cache files or system configuration are part of the repository.

## Original release assets

| Release | Original Debian package SHA-256 | Original source tarball SHA-256 |
|---|---|---|
| 0.1.0 | `61abf51ec002356c62f6f0f33cd3b6facd0ef1af5b9b501b8d34b8c720d32d53` | `eb2e44b97486ce9b186fbce1049a667dc8ff4a8c17225809c2c66beb6de8326d` |
| 0.1.1 | `64895719d1b839cdf0c2a4c4ec723ddd85079d7cb66dc68a9eb7fe86128c0bea` | `1db38ad67bd3a47c99d8cd3a944863fe81faedb494273bf23b0a4544a6e56638` |

The Python program and the two JSON printer profiles inside each release `.deb` match the same files in its corresponding source tarball **byte-for-byte**.

## Source history

- **0.1.0:** Initial GTK3 CUPS/photographic printing/SANE application, including Canon G600 and Brother DCP-L2665DW JSON device profiles.
- **0.1.1:** Adds a controlled, per-user SANE environment for declared eSCL profiles, isolated in `~/.cache/giux-print-manager/sane/`. The user data and system SANE configuration are not bundled. New profiles include `scanner_url` fields. The author-provided README still carries the initial 0.1.0 title; release identity comes from the actual Debian `Version` field and build script.

The repository includes a new bilingual `README.md` and this provenance note; `README.original.md` preserves the original supplied README.

Original Debian assets, including the desktop launcher and SVG icon, are available under `packaging/` for inspection. The `COPYING` text is the author's original GPLv3 license file.

**Build script portability:** The repository builder changes the final output path from the author's fixed absolute path under `/home/giu` to a relative file, and selects `README.original.md` for the Debian-installed documentation so the published GitHub landing README does not replace the original package guide. The original script is preserved in the unchanged source tarball attached to GitHub Releases.

## Validation scope

- Inspected Debian metadata and package contents.
- Compared source and installed program bytes and profile JSON bytes for both published versions.
- Parsed the Python source with `ast.parse` without running printing or scanning operations.
- Checked profile JSON schemas and ran a local Debian packaging rebuild from the public checkout.

No printer, scanner, official web interface or printer consumable was exercised as part of publication. The experimental architecture and unimplemented capabilities remain described in the original documentation.
