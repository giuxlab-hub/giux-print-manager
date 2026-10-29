# SPDX-License-Identifier: GPL-3.0-or-later
"""Test the installed launcher from an isolated Debian-shaped directory tree.

No GUI is shown, no printer/scanner is contacted, and no user configuration is changed.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


class InstalledLauncherContracts(unittest.TestCase):
    def test_imports_resolve_from_install_prefix(self):
        with tempfile.TemporaryDirectory(prefix="giux-launch-contract-") as directory:
            root = Path(directory)
            bin_dir = root / "usr/bin"
            module_dir = root / "usr/share/giux-print-manager"
            bin_dir.mkdir(parents=True)
            module_dir.mkdir(parents=True)
            launcher = bin_dir / "giux-print-manager"
            shutil.copyfile(ROOT / "giux-print-manager", launcher)
            for name in (
                "photo_editor.py",
                "giux_ocr_workspace.py",
                "giux_image_canvas.py",
                "giux_image_filters.py",
            ):
                shutil.copyfile(ROOT / name, module_dir / name)

            code = (
                "import pathlib,runpy,sys; "
                f"root=pathlib.Path({str(root)!r}); "
                "launcher=root/'usr/bin/giux-print-manager'; "
                "modules=root/'usr/share/giux-print-manager'; "
                "assert str(modules) not in sys.path; "
                "namespace=runpy.run_path(str(launcher),run_name='__test_import_only__'); "
                "assert namespace['PhotoEditor'].__module__=='photo_editor'; "
                "assert pathlib.Path(sys.modules['photo_editor'].__file__).resolve().parent==modules; "
                "assert pathlib.Path(sys.modules['giux_ocr_workspace'].__file__).resolve().parent==modules"
            )
            env = os.environ.copy()
            env.pop("PYTHONPATH", None)
            result = subprocess.run(
                [sys.executable, "-c", code],
                cwd="/",
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )
            self.assertEqual(result.returncode, 0, result.stderr)

    def test_builder_version(self):
        text = (ROOT / "build-deb.sh").read_text(encoding="utf-8")
        self.assertIn("V=0.3.2", text)
        self.assertIn("Version: 0.3.2", text)


if __name__ == "__main__":
    unittest.main()
