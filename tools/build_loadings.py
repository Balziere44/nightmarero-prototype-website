#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds the loading screen gallery.

    python tools/build_loadings.py
    python tools/build_loadings.py "C:/path/to/Loading Screens"

Given the source folder it imports every screen listed in SCREENS below,
copying the original to assets/img/loadings/<slug>.jpg and writing a 720px
wide thumbnail next to it in thumbs/. Without the folder it only rebuilds
the thumbnails and the markup from the files already in the repo.

Either way it rewrites the grid inside loading-screens.html, between the
two markers, and updates the count next to the filter chips. The grid is
generated, so the page itself is never edited by hand from that div down.

Adding a screen is one line in SCREENS: the slug (which is also the file
name and the class page it links to), the name printed on the card, the
tier, and the file it comes from in the source folder. Order here is the
order on the page, and the pairs read best kept next to each other.

Requires Pillow:  pip install Pillow
"""

import io
import os
import re
import sys
import shutil

try:
    from PIL import Image
except ImportError:
    sys.exit("Pillow is not installed. Run: pip install Pillow")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "assets", "img", "loadings")
THUMBS = os.path.join(OUT, "thumbs")
PAGE = os.path.join(ROOT, "loading-screens.html")

THUMB_W = 720
THUMB_Q = 82

# slug, name on the card, tier, file in the source folder
SCREENS = [
    ("lord-knight", "Lord Knight", "trans", "loading01.jpg"),
    ("rune-knight", "Rune Knight", "third", "loading02.jpg"),
    ("paladin", "Paladin", "trans", "loading03.jpg"),
    ("royal-guard", "Royal Guard", "third", "loading04.jpg"),
    ("mastersmith", "Mastersmith", "trans", "loading05.jpg"),
    ("mechanic", "Mechanic", "third", "loading06.jpg"),
    ("assassin-cross", "Assassin Cross", "trans", "loading07.jpg"),
    ("guillotine-cross", "Guillotine Cross", "third", "loading08.jpg"),
    ("high-wizard", "High Wizard", "trans", "loading09.jpg"),
    ("warlock", "Warlock", "third", "loading10.jpg"),
    ("sniper", "Sniper", "trans", "loading11.jpg"),
    ("ranger", "Ranger", "third", "loading12.jpg"),
    ("high-priest", "High Priest", "trans", "loading13.jpg"),
    ("arch-bishop", "Arch Bishop", "third", "loading14.jpg"),
]

TIERS = {"trans": ("Transcendent", "ls.fTrans"),
         "third": ("Third class", "ls.fThird")}

GRID = re.compile(r'(<div class="ls-grid" id="lsGrid">\n).*?(\n      </div>)', re.S)
COUNT = re.compile(r'(<b id="lsCountN">)\d+(</b>)')

CARD = """
        <figure class="ls-card reveal{third}" data-tier="{tier}" data-slug="{slug}" \
data-name="{name}" data-role="{role}">
          <a class="ls-shot" href="assets/img/loadings/{slug}.jpg" data-ls-open>
            <img src="assets/img/loadings/thumbs/{slug}.jpg" alt="{name} loading screen" \
width="{tw}" height="{th}" loading="lazy" decoding="async">
            <span class="ls-tier" data-i18n="{key}">{role}</span>
            <span class="ls-zoom"><i><svg aria-hidden="true"><use href="#i-expand"></use></svg></i></span>
          </a>
          <figcaption>
            <div>
              <strong>{name}</strong>
              <em><a href="classes/{slug}.html" data-i18n="ls.classPage">Class page</a></em>
            </div>
            <a class="ls-get" href="assets/img/loadings/{slug}.jpg" \
download="nightmarero-loading-{slug}.jpg">
              <svg aria-hidden="true"><use href="#i-download"></use></svg>\
<span data-i18n="ls.get">JPG</span>
            </a>
          </figcaption>
        </figure>
"""


def thumb(src, dest):
    """Write the grid sized copy. Returns its dimensions."""
    img = Image.open(src)
    img = img.convert("RGB")
    h = int(round(img.height * THUMB_W / float(img.width)))
    img = img.resize((THUMB_W, h), Image.LANCZOS)
    img.save(dest, "JPEG", quality=THUMB_Q, optimize=True, progressive=True)
    return THUMB_W, h


def main():
    source = sys.argv[1] if len(sys.argv) > 1 else None
    if source and not os.path.isdir(source):
        sys.exit("not a folder: %s" % source)

    for folder in (OUT, THUMBS):
        if not os.path.isdir(folder):
            os.makedirs(folder)

    cards = []
    missing = []

    for slug, name, tier, origin in SCREENS:
        full = os.path.join(OUT, slug + ".jpg")

        if source:
            src = os.path.join(source, origin)
            if not os.path.isfile(src):
                missing.append("%s (looking for %s)" % (slug, origin))
                continue
            shutil.copyfile(src, full)

        if not os.path.isfile(full):
            missing.append("%s (no %s.jpg, and no source folder given)" % (slug, slug))
            continue

        tw, th = thumb(full, os.path.join(THUMBS, slug + ".jpg"))
        role, key = TIERS[tier]
        cards.append(CARD.format(slug=slug, name=name, tier=tier, role=role, key=key,
                                 third=" -third" if tier == "third" else "",
                                 tw=tw, th=th))

    if not cards:
        sys.exit("nothing to build")

    text = io.open(PAGE, encoding="utf-8").read()
    before = text

    grid = "".join(cards)
    text, hit = GRID.subn(lambda m: m.group(1) + grid + m.group(2), text, count=1)
    if not hit:
        sys.exit("could not find the grid in loading-screens.html")

    text, _ = COUNT.subn(lambda m: m.group(1) + str(len(cards)) + m.group(2), text, count=1)

    io.open(PAGE, "w", encoding="utf-8", newline="\n").write(text)

    print("%d screens, %s" % (len(cards),
                              "page updated" if text != before else "page already current"))
    for line in missing:
        print("  skipped: %s" % line)
    print("  reminder: the FAQ answer ls.a1 counts the classes out loud, "
          "in the page and in all five locale files")


if __name__ == "__main__":
    main()
