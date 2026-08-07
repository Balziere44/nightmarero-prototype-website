#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Builds guide.html, the page for people who have never played here.

    python tools/build_guide.py

The page is a shell meant to grow. There is no guide in it yet, so it shows a
placeholder and points at the pages that already exist.

To add one, append to GUIDES and rebuild. A guide is prose someone wrote, not
data anyone exports, so it lives in this file rather than in a sheet. Each one
gets its own card and its own credit line.
"""

import io
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from build_classes import esc, head, header, footer, slugify, SITE, REGISTER

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(ROOT, "guide.html")

# A guide is a title, who wrote it, one line of what it covers, and a list of
# blocks. A block is ("steps", [line, ...]) for a numbered route,
# ("split", [(heading, [line, ...]), ...]) for a fork in the road, or
# ("notes", [line, ...]) for loose advice.
GUIDES = []


def steps_block(title, lines):
    items = "".join(
        '<li class="q-step"><span class="q-n">%d</span><div><p>%s</p></div></li>'
        % (n, esc(line)) for n, line in enumerate(lines, start=1))
    return ('<h3 class="guide-head">%s</h3><ol class="q-steps">%s</ol>'
            % (esc(title), items))


def split_block(title, pairs):
    cards = "".join(
        '<div class="guide-branch"><h4>%s</h4>%s</div>'
        % (esc(heading), "".join("<p>%s</p>" % esc(line) for line in lines))
        for heading, lines in pairs)
    return ('<h3 class="guide-head">%s</h3><div class="guide-branches">%s</div>'
            % (esc(title), cards))


def notes_block(title, lines):
    items = "".join("<li>%s</li>" % esc(line) for line in lines)
    return ('<h3 class="guide-head">%s</h3><ul class="guide-notes">%s</ul>'
            % (esc(title), items))


def guide_html(guide):
    blocks = []
    for kind, title, body in guide["blocks"]:
        if kind == "steps":
            blocks.append(steps_block(title, body))
        elif kind == "split":
            blocks.append(split_block(title, body))
        else:
            blocks.append(notes_block(title, body))

    return """      <article class="guide-card" id="g-{slug}">
        <div class="guide-card-head">
          <h2>{title}</h2>
          <p class="guide-credit"><span data-i18n="g.by">Written by</span> <b>{credit}</b></p>
          <p class="lede">{blurb}</p>
        </div>
        <p>{intro}</p>
{blocks}
      </article>""".format(
        slug=slugify(guide["title"]), title=esc(guide["title"]),
        credit=esc(guide["credit"]), blurb=esc(guide["blurb"]),
        intro=esc(guide["intro"]),
        blocks="\n".join("        " + b for b in blocks))


PLACEHOLDER = """      <article class="guide-card -empty">
        <h2 data-i18n="g.soonTitle">Nothing here yet</h2>
        <p data-i18n="g.soonText">The first routes are being written. Until they land, the pages below already answer most of what a new character needs to decide.</p>
      </article>"""


def build():
    cards = "\n".join(guide_html(g) for g in GUIDES) or PLACEHOLDER

    ld = """<script type="application/ld+json">
{{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {{ "@type": "ListItem", "position": 1, "name": "Home", "item": "{site}/" }},
    {{ "@type": "ListItem", "position": 2, "name": "New players", "item": "{site}/guide.html" }}
  ]
}}
</script>""".format(site=SITE)

    parts = [
        head("", "New player guide | Nightmare RO",
             "Where to start on Nightmare RO: a levelling route from the "
             "first job to level fifty, which cards are worth stopping for, "
             "and where to go next.",
             "guide.html", ld),
        header("", "guide.html"),
        """<main id="main">
  <section class="page-head">
    <div class="shell">
      <nav class="breadcrumb" aria-label="Breadcrumb"><ol>
        <li><a href="index.html" data-i18n="nav.home">Home</a></li>
        <li data-i18n="nav.guide">New players</li>
      </ol></nav>
      <div class="section-head">
        <p class="eyebrow" data-i18n="g.eyebrow">First time here</p>
        <h1 data-i18n="g.title">Where to start when everything is new</h1>
        <p class="lede" data-i18n="g.lede">Every class, skill, item and monster on this server was remade, so what you remember from anywhere else is a rough guide at best. This page collects routes and advice from people who have already walked it.</p>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <p class="note" data-i18n="g.wip">This page is a start rather than a finished guide. More routes, starting builds and a proper map of where to go at each level are on the way. If you want to write one, the Discord is the place.</p>

""",
        cards,
        """

      <div class="guide-next">
        <h3 data-i18n="g.nextTitle">Where to go from here</h3>
        <div class="hero-actions">
          <a class="btn -ghost" href="quiz.html" data-i18n="nav.quiz">Class test</a>
          <a class="btn -ghost" href="classes.html" data-i18n="nav.classes">Classes</a>
          <a class="btn -ghost" href="database.html" data-i18n="nav.items">Items and cards</a>
          <a class="btn -ghost" href="mvps.html" data-i18n="nav.mvps">MVPs and altars</a>
        </div>
      </div>
    </div>
  </section>

  <section class="section-pad-sm">
    <div class="shell">
      <div class="cta-band">
        <div class="inner">
          <h2 data-i18n="band.title">Come find out what changed</h2>
          <p class="lede text-center" data-i18n="band.lede">Make an account now, grab the client, and be there when the servers go up.</p>
          <div class="hero-actions">
            <a class="btn -primary -lg" href="{reg}" target="_blank" rel="noopener" data-i18n="cta.registerFree">Create a free account</a>
            <a class="btn -ghost -lg" href="download.html" data-i18n="nav.download">Download</a>
          </div>
        </div>
      </div>
    </div>
  </section>
</main>
""".format(reg=REGISTER),
        footer(""),
    ]

    io.open(OUT, "w", encoding="utf-8", newline="\n").write("".join(parts))
    print("guide.html: %d guide(s) (%.0f KB)"
          % (len(GUIDES), os.path.getsize(OUT) / 1024.0))


if __name__ == "__main__":
    build()
