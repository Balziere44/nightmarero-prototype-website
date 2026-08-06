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

Two things need a real value. Everything else is ready.

### 1. The domain

Every canonical URL, Open Graph tag and sitemap entry points at the current
home, `https://nightmarero.pages.dev`. These have to be absolute and they have
to resolve: Discord, Slack and Google fetch the share image from that exact
address, so if it points at a domain that is not live yet the preview comes up
blank.

When the real domain is ready, swap it in and rebuild:

```bash
grep -rl "nightmarero.pages.dev" . --exclude-dir=.git | xargs sed -i 's|https://nightmarero.pages.dev|https://YOUR-DOMAIN|g'
python tools/build_classes.py && python tools/build_sitemap.py
```

The `grep` covers `tools/build_classes.py` and `tools/build_sitemap.py` too, so
the `SITE` constant in both scripts moves with everything else.

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

That is all that is strictly outstanding. All 55 classes have artwork, so
nothing on the site falls back to a placeholder.

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

The 55 class pages and `classes.html` are generated from two sources:

- `tools/classes.json`, the text of the Class Overviews document
- `tools/data/wiki-classes.json`, the skill tables off the player wiki

```bash
python tools/build_classes.py
python tools/build_sitemap.py
```

`build_classes.py` also prints which classes are still missing artwork and
writes that list to `tools/missing-art.txt`.

### How a skill list gets built

The document is prose. It names every skill and describes it well, but it runs
four different kinds of line together and never says which is which:

```
Void Infusion: Converts all magic damage dealt...      a skill
Ghost: The user's Magic Pierce is reduced to 0         an option of it
Phantasmal Crush: Invokes forbidden magic...           a skill
If Void Infusion: Ghost is active, cooldown halved     a rider on it
```

The wiki carries the part the document does not: which branch a skill sits in,
whether it is physical or magical or supportive, and its level cap. So the
wiki skill tables are treated as the authority on what counts as a skill.
Anything in the document that is not on that list gets folded into the entry
above it, as an option or as a conditional rider. That work lives in
`tools/skills.py`.

On top of that the build works out two more things per class:

- **Mechanics.** Resources, stances and states that are referred to over and
  over but are not skills: Void Spheres, Axe Stance, Extort, Rhythm Stacks.
  Found by head noun, then required to turn up in two different skills or in
  the class introduction. They get listed above the skill grid and marked
  inline in the accent colour with a dotted underline, so they never look like
  a status effect.
- **Dependencies.** A skill whose text names another skill of the same class
  gets a "Works with" link to it. Option labels are excluded on purpose: an
  Axe Stance table listing "Counter Kick: Inflicts Vulnerable" is saying what
  the stance does to that kick, not depending on it.

Skill types are coloured by family. The wiki uses about seventy type labels;
`TYPE_FAMILIES` in `tools/skills.py` folds them onto eight `--sk-*` colours,
which are separate from the status codex so the two never compete on a card.

To refresh the wiki side:

```bash
python tools/fetch_wiki.py
```

That is the only script besides `fetch_sheets.py` that touches the network.
The JSON it writes is committed, so `build_classes.py` runs offline.

If the wiki adds a skill the document has not caught up with, it simply does
not appear. If the document has one the wiki has not listed, it still appears,
under a "Mechanics" heading, without a type or level. Renames between the two
are matched by similarity, which is how "Seismic Tremor" in the document finds
"Seismic Tremors" on the wiki.

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

`prepare_art.py` also writes `tools/art-sizes.json`, the real pixel size of
every file. `build_classes.py` reads it to put `width` and `height` on each
image so the layout does not jump while the art loads. It is generated, so
there is nothing to edit by hand.

### Classes that show two characters

Bard and Dancer, Clown/Gypsy and Minstrel/Wanderer are two jobs sharing one
page, not two genders of one job. They skip the male/female toggle and show
both characters side by side, each with its own name underneath.

The mapping lives in `PAIRED` near the top of `tools/build_classes.py`:

```python
PAIRED = {
    "Bard and Dancer": ("Bard", "Dancer"),      # male art, female art
    "Clown/Gypsy": ("Clown", "Gypsy"),
    "Minstrel/Wanderer": ("Minstrel", "Wanderer"),
}
```

The artwork still uses the `-male` and `-female` filenames, since that is
which slot each job occupies. On the card these get the `-pair` class, which
lays them out as a band rather than one full height figure.

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

## The item database

`database.html` searches every weapon, armour piece and card on the server.
It loads `assets/data/items.json` once and filters in memory, painting results
in chunks of 60 so a 1200 entry list never stalls the page.

The data comes from Twilight's two published reference sheets. Refresh it in
two steps:

```bash
python tools/fetch_sheets.py     # re-download tools/data/*.csv from Google
python tools/build_database.py   # rebuild assets/data/items.json
```

`fetch_sheets.py` is the only script that needs the network. The CSVs are
committed, so anyone can rebuild the JSON offline.

Two things to know about the source data:

- **Shadow Gear and Shadow Enchants are empty tabs** in the gear sheet, so
  none of it is in the database yet. It will appear on its own once Twilight
  fills those tabs in and the two commands above are re-run.
- **The sheets mark champion drops with a green cell fill.** Colour does not
  survive the CSV export, so that distinction is not in the database. If it
  matters later, the champion names would need their own column.

Category names differ slightly between the two gear docs (`GATLINGS` versus
`GATLING GUNS`). `CATEGORY_ALIASES` in `build_database.py` folds those
together so the filter does not list near-duplicates.

## The class personality test

`quiz.html` asks nine scenarios set in Midgard, scores six traits, and uses
the top two to pick one of fifteen archetypes. Every unordered pair of traits
has exactly one archetype, so there is no combination that falls through.

Everything lives in `assets/js/quiz.js`:

- `TRAITS` the six axes
- `QUESTIONS` the scenarios and what each answer scores
- `ARCHETYPES` fifteen entries keyed by `pair`, each naming a class and a
  runner up
- `OLD_CLASSES` the class the player used to main, which only changes the
  wording of the result, never the maths

The result card reads `assets/data/classes-brief.json`, generated by
`build_classes.py` alongside the class pages. "Save as image" composes a
1200x630 PNG on a canvas with the logo, the archetype and the class art.

Questions and archetypes are English only, the same call made for skill names
elsewhere. The page chrome around them is translated.

## The launch countdown

The hero counts down to launch and then swaps itself for a "servers are live"
badge. The moment is defined once, at the top of the countdown section in
`assets/js/main.js`:

```js
var LAUNCH = Date.UTC(2026, 7, 7, 23, 0, 0);  // 7 Aug 2026, 20:00 Brasilia
var LAUNCH_OFFSET_MIN = -180;                 // Brasilia, minutes from UTC
```

Months are zero based, so `7` is August, and the hour is **UTC**, not local.
If the date moves, change those two lines and then update the text in three
places: `cd.when` and `hero.badge` in each locale file plus the English in
`index.html`, `faq.a8`, and the `datePublished` field in the JSON-LD block.

Visitors outside Brazil also get the launch time in their own zone,
formatted by `Intl.DateTimeFormat` and re-rendered whenever the language
changes. That line stays hidden for anyone already on UTC-3.

## The status codex

Combat runs on status effects, so each family has a colour that is used
everywhere: inline in skill text, on the chips above each skill list, and on
the reference cards at the bottom of `classes.html` (anchor `#codex`).

The colours live in one place, `:root` in `style.css`, as `--kw-bleed`,
`--kw-burn` and so on, with darker values under `html[data-theme="light"]`.

The terms themselves are defined in the `STATUS` list in
`tools/status_codex.py`. Matching is case sensitive, so an ordinary lowercase
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
