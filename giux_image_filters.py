# SPDX-License-Identifier: GPL-3.0-or-later
"""ImageMagick-based non-destructive adjustments and geometric transformations."""
import subprocess
from pathlib import Path

def render_filters(source,destination,brightness=0,contrast=0,sharpness=0,saturation=100):
    """Apply bounded controls using ImageMagick 7, never a shell."""
    brightness=max(-80,min(80,int(brightness)))
    contrast=max(-80,min(80,int(contrast)))
    sharpness=max(0,min(5,float(sharpness)))
    saturation=max(0,min(200,int(saturation)))
    args=["magick",str(source),"-auto-orient"]
    if brightness or contrast:
        args+=["-brightness-contrast",f"{brightness}x{contrast}"]
    if saturation!=100:
        args+=["-modulate",f"100,{saturation},100"]
    if sharpness:
        args+=["-unsharp",f"0x{sharpness:.2f}+1+0"]
    args+=["-strip",str(destination)]
    p=subprocess.run(args,capture_output=True,text=True,timeout=120)
    if p.returncode or not Path(destination).is_file():
        raise RuntimeError(p.stderr[:1300] or "ImageMagick filtering failed")
    return str(destination)

def transform(source,destination,operation):
    operations={
        "left":["-rotate","-90"],
        "right":["-rotate","90"],
        "horizontal":["-flop"],
        "vertical":["-flip"]
    }
    if operation not in operations:raise ValueError("Unknown image transformation")
    args=["magick",str(source),"-auto-orient",*operations[operation],
          "-strip",str(destination)]
    p=subprocess.run(args,capture_output=True,text=True,timeout=120)
    if p.returncode or not Path(destination).is_file():
        raise RuntimeError(p.stderr[:1300] or "ImageMagick transform failed")
    return str(destination)
