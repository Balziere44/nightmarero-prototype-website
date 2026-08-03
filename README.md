# Nightmare RO website

Static site for the Nightmare RO server. No build step, no framework, no
dependencies. Plain HTML, one stylesheet, two small scripts. Drop it on any
static host and it works.

---

## Contents

```
.
├── index.html               landing page
├── classes.html             class hub, filter + search over all 55
├── download.html            client download and install help
├── classes/                 55 generated class pages
├── assets/
│   ├── css/style.css        the whole design system
│   ├── js/main.js           theme, menus, countdown, filters
│   ├── js/i18n.js           language switcher
│   ├── i18n/                pt, fr, it, de, ja  (English lives in the HTML)
│   └── img/
│       ├── classes/         character art, .webp, two sizes each
│       ├── bg/              hero and secondary backgrounds
│       ├── hero-a/-b.webp   the two figures in the landing page hero
│       ├── logo.webp/.png   logo
│       ├── icon-*.png       favicons and app icons
│       └── og-cover.jpg     social share card
├── tools/                   regeneration scripts (harmless if uploaded,
│                            nothing links to them)
├── robots.txt
├── sitemap.xml
├── site.webmanifest
└── _headers                 Cloudflare Pages cache and security headers
```

---

## Before it goes live

Three things need a real value. Everything else is ready.

### 1. The domain

Every canonical URL, Open Graph tag and sitemap entry currently points at
`https://www.nightmarero.com`. Replace it with the real domain everywhere:

```bash
grep -rl "www.nightmarero.com" . | xargs sed -i 's|https://www.nightmarero.com|https://YOUR-DOMAIN|g'
```

Then update the same constant in `tools/build_classes.py` (`SITE`) and
`tools/build_sitemap.py` (`SITE`) so regenerated pages keep the right URL.

### 2. The client download link

`download.html` has one primary download button. It currently points at the
control panel as a placeholder. Search the file for the comment that starts
`Twilight: replace the href below` and swap in the real link.

To add mirrors, duplicate that button:

```html
<a class="btn -ghost -lg" href="MIRROR-URL" target="_blank" rel="noopener">
  <svg aria-hidden="true"><use href="#i-download"></use></svg>
  <span>Mirror: Mega</span>
</a>
```

### 3. Missing class artwork

28 of the 55 classes have no character art yet and fall back to a letter
placeholder. The current list is in `tools/missing-art.txt`. See below for how
to add them.

---

## Deploying to Cloudflare Pages

1. Push this folder to a GitHub repository.
2. In the Cloudflare dashboard: **Workers & Pages → Create → Pages → Connect to Git**.
3. Pick the repo. Leave the build settings empty:
   - Framework preset: **None**
   - Build command: *(blank)*
   - Build output directory: `/`
4. Deploy, then add the custom domain under **Custom domains**.

`_headers` is picked up automatically and sets the cache and security headers.

---

## Regenerating the class pages

The 55 class pages and `classes.html` are generated from
`tools/classes.json`, which holds the text of the Class Overviews document.

```bash
python tools/build_classes.py
python tools/build_sitemap.py
```

`build_classes.py` also prints which classes are still missing artwork and
writes that list to `tools/missing-art.txt`.

### When the class document changes

`tools/extract.py` turns a saved copy of the published Google Doc into
`classes.json`:

```bash
python tools/extract.py "Class Overviews.html" tools/classes.json
```

Then re-run `build_classes.py`.

### Adding class artwork

Every class page looks for these two files and uses whichever exist:

```
assets/img/classes/<slug>-male.webp      up to 760px tall,  full size
assets/img/classes/<slug>-male-sm.webp   up to 420px tall,  card size
assets/img/classes/<slug>-female.webp
assets/img/classes/<slug>-female-sm.webp
```

The slug is the class name lowercased with non-letters turned into hyphens:
`Shadow Chaser` becomes `shadow-chaser`, `Clown/Gypsy` becomes `clown-gypsy`,
`Bard and Dancer` becomes `bard-dancer`.

Drop new PNGs named `<Class Name> Male.png` / `<Class Name> Female.png` into a
folder and run `tools/prepare_art.py` to crop, resize and convert them:

```bash
python tools/prepare_art.py "path/to/new/art"
```

Then re-run `build_classes.py` so the pages pick them up. Nothing else changes.

---

## Languages

Six languages: English, Portuguese, French, Italian, German, Japanese.

English is written directly into the HTML, so crawlers and anyone with
JavaScript disabled always get real content. The other five live in
`assets/i18n/*.js` and swap the text in at runtime. The choice is remembered in
`localStorage` and the browser language is used on a first visit.

To change a string, find its key:

```html
<h3 data-i18n="feat.t4">Bosses you summon</h3>
```

Edit the English in the HTML, then edit `'feat.t4'` in each locale file. A key
that is missing from a locale falls back to English rather than breaking.

Strings may contain inline `<strong>` and `<b class="kw kw-burn">` markup, and
it survives a language change. Keep the tags balanced: the value is written
straight into the element.

Skill names and skill descriptions on the class pages stay in English on
purpose, because that is how they appear in game.

---

## The status codex

Combat runs on status effects, so each family has a colour that is used
everywhere: inline in skill text, on the chips above each skill list, and on
the reference cards at the bottom of `classes.html` (anchor `#codex`).

The colours live in one place, `:root` in `style.css`, as `--kw-bleed`,
`--kw-burn` and so on, with darker values under `html[data-theme="light"]`.

The terms themselves are defined in the `STATUS` list in
`tools/build_classes.py`. Matching is case sensitive, so an ordinary lowercase
"cold" or "slow" in a sentence is left alone. To add a status, add a row there
with a new key, add `--kw-<key>` to both theme blocks in `style.css`, and
re-run the build.

Each class page shows chips only for the statuses that class actually
mentions, so a Crusader page shows Bleeding, Blind and Vulnerable and nothing
else.

## Naming

The site deliberately never uses the name of the game this server is based on,
or its publisher. Search visibility is carried by "private RO server", "custom
RO server", "PvE MMORPG server" and similar phrasing instead. Worth keeping in
mind when writing new copy.

The only exception is the control panel domain in the account and download
links, which is what it is.

---

## Design notes

- Theme: red and black, eclipse and broken glass. Light mode is a bone-white
  variant of the same palette.
- Type: Outfit for headings, Inter for body, JetBrains Mono for labels, all
  from Google Fonts. Noto Sans JP loads only when Japanese is selected.
- All colours, spacing and type sizes are CSS custom properties at the top of
  `style.css`. Change them there and the whole site follows.
- Motion respects `prefers-reduced-motion`.

## Licence

Site code is free to reuse for the server. Character art, backgrounds and the
logo belong to their creators.
