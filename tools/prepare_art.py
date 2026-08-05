#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Turns raw class artwork into the two web sizes the site expects.

    python tools/prepare_art.py "C:/path/to/art folder"

It looks for files named "<Class Name> Male.png" or "<Class Name> Female.png",
trims the transparent border, scales them down and writes:

    assets/img/classes/<slug>-<sex>.webp      full size, up to 760px tall
    assets/img/classes/<slug>-<sex>-sm.webp   card size, up to 420px tall

Files that are not named that way are skipped and listed at the end, so a typo
in a filename is easy to spot. Existing files are overwritten.

Requires Pillow:  pip install Pillow
"""

import os
import re
import sys
import glob

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is not installed. Run: pip install Pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img", "classes")

FULL_H, FULL_W = 760, 700
CARD_H, CARD_W = 420, 400

# Filenames in the source set that do not match the class name. Some are
# typos, some are the gendered job names, which the site keeps as one page.
ALIASES = {
    "mastermsith": "mastersmith",   # typo
    "scholas": "scholar",           # typo
    "shura": "sura",
    "nightwatcher": "night watch",
    "bard": "bard and dancer",
    "dancer": "bard and dancer",
    "clown": "clown/gypsy",
    "gypsy": "clown/gypsy",
    "minstrel": "minstrel/wanderer",
    "wanderer": "minstrel/wanderer",
}

# Artwork in the same folder that is not a class portrait.
SKIP = {"aprendiz"}             # the two figures in the landing page hero

NAME_RE = re.compile(r"^(.*?)[\s_-]+(male|female)$", re.I)


def slugify(name):
    s = name.lower().replace("/", "-").replace(" and ", "-")
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def fit(img, max_h, max_w):
    w, h = img.size
    scale = min(float(max_h) / h, float(max_w) / w, 1.0)
    return img.resize((max(1, int(w * scale)), max(1, int(h * scale))), Image.LANCZOS)


def main():
    if len(sys.argv) < 2:
        sys.exit("Usage: python tools/prepare_art.py <folder with the artwork>")

    src = sys.argv[1]
    if not os.path.isdir(src):
        sys.exit("Not a folder: %s" % src)

    if not os.path.isdir(OUT):
        os.makedirs(OUT)

    written, skipped = [], []

    for path in sorted(glob.glob(os.path.join(src, "*.png")) +
                       glob.glob(os.path.join(src, "*.webp"))):
        base = os.path.splitext(os.path.basename(path))[0]
        match = NAME_RE.match(base.strip())
        if not match:
            skipped.append(os.path.basename(path))
            continue

        cls, sex = match.group(1).strip(), match.group(2).lower()
        if cls.lower() in SKIP:
            continue
        slug = slugify(ALIASES.get(cls.lower(), cls))

        img = Image.open(path).convert("RGBA")
        box = img.getbbox()
        if box:
            img = img.crop(box)

        full = fit(img, FULL_H, FULL_W)
        full.save(os.path.join(OUT, "%s-%s.webp" % (slug, sex)),
                  "WEBP", quality=84, method=4)
        fit(full, CARD_H, CARD_W).save(
            os.path.join(OUT, "%s-%s-sm.webp" % (slug, sex)),
            "WEBP", quality=82, method=4)

        written.append("%s-%s" % (slug, sex))

    print("Wrote %d image pairs:" % len(written))
    for name in written:
        print("  %s.webp + %s-sm.webp" % (name, name))

    if skipped:
        print("\nSkipped (name did not end in Male or Female):")
        for name in skipped:
            print("  %s" % name)

    print("\nNow run: python tools/build_classes.py")


if __name__ == "__main__":
    main()
