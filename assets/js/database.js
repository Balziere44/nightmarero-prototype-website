/* ==========================================================================
   Nightmare RO - item database
   --------------------------------------------------------------------------
   Loads assets/data/items.json once, filters it in memory, and paints the
   results in chunks so a 1200 item list never blocks the main thread.
   Clicking a result opens a panel with the full entry and a share block
   ready to paste into Discord.
   ========================================================================== */

(function () {
  'use strict';

  /* Ask for our own files under the build stamp the page carries, so a copy
     cached before the last deploy is at an address we never request again.
     i18n.js defines it and is the first script on every page. */
  function fresh(url) {
    return window.NM_FRESH ? window.NM_FRESH(url) : url;
  }

  var grid = document.getElementById('dbGrid');
  if (!grid) return;

  var $ = function (id) { return document.getElementById(id); };

  var els = {
    name: $('qName'), effect: $('qEffect'), drops: $('qDrops'),
    slot: $('fSlot'), cat: $('fCat'), source: $('fSource'), sort: $('fSort'),
    lvMin: $('lvMin'), lvMax: $('lvMax'),
    count: $('dbCount'), empty: $('dbEmpty'), reset: $('dbReset'),
    more: $('dbMore'), sentinel: $('dbSentinel'),
    modal: $('dbModal'), modalBody: $('dbModalBody'), modalClose: $('dbModalClose'),
    share: $('dbShare'), shareLink: $('dbShareLink'),
    prompt: $('dbPrompt'), all: $('dbAll')
  };

  var CHUNK = 60;
  var all = [];
  var view = [];
  var painted = 0;
  var kind = 'all';
  var statusTerms = {};
  var statusRe = null;
  var open = null;          // the item currently in the panel
  var showAll = false;      // the reader asked to see the lot anyway

  /* ------------------------------------------------------------ dictionary */

  function t(key, fallback) {
    var table = window.NM_I18N_TABLE;
    return (table && table[key]) || fallback;
  }

  var SLOT_KEYS = ['weapon', 'armor', 'shield', 'garment', 'shoes', 'headgear',
    'accessory', 'costume', 'shadow-armor', 'shadow-gloves', 'shadow-shoes',
    'shadow-pendant', 'any'];
  /* Shadow gear equips in a second window, so it has slots of its own that
     sit alongside the ordinary ones rather than competing with them. */
  var SLOT_FALLBACK = {
    weapon: 'Weapon', armor: 'Armour', shield: 'Shield', garment: 'Garment',
    shoes: 'Shoes', headgear: 'Headgear', accessory: 'Accessory', any: 'Fits any slot',
    'shadow-armor': 'Shadow armour', 'shadow-gloves': 'Shadow gloves',
    'shadow-shoes': 'Shadow shoes', 'shadow-pendant': 'Shadow pendant',
    costume: 'Costume'
  };
  /* "unknown" is for the pieces typed out of in game tooltips, which nobody
     has written down a drop for yet. */
  var SOURCE_FALLBACK = {
    core: 'World drop', mvp: 'Boss drop', card: 'Card', shadow: 'Shadow gear',
    relic: 'Relic gear', 'mvp-card': 'Boss card',
    unknown: 'Location unknown', discord: 'Answered on Discord',
    wiki: 'Player wiki', client: "The item's own description"
  };

  function slotLabel(s) { return t('db.s.' + s, SLOT_FALLBACK[s] || s); }
  function sourceLabel(s) { return t('db.src.' + s, SOURCE_FALLBACK[s] || s); }

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  /* Same colours the class pages use. The term list rides along in the JSON
     so there is only ever one copy of it. */
  function colorize(text) {
    if (!statusRe) return esc(text);
    return esc(text).replace(statusRe, function (m) {
      return '<b class="kw kw-' + statusTerms[m] + '">' + m + '</b>';
    });
  }

  function buildStatusRe() {
    var terms = Object.keys(statusTerms);
    if (!terms.length) return;
    terms.sort(function (a, b) { return b.length - a.length; });
    var safe = terms.map(function (s) { return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'); });
    statusRe = new RegExp('\\b(' + safe.join('|') + ')\\b', 'g');
  }

  /* ---------------------------------------------------------------- selects */

  function option(value, label) {
    var o = document.createElement('option');
    o.value = value;
    o.textContent = label;
    return o;
  }

  function fillSelects() {
    els.slot.innerHTML = '';
    els.slot.appendChild(option('', t('db.anySlot', 'Any slot')));
    SLOT_KEYS.forEach(function (s) {
      if (all.some(function (i) { return i.slot === s; })) {
        els.slot.appendChild(option(s, slotLabel(s)));
      }
    });

    els.source.innerHTML = '';
    els.source.appendChild(option('', t('db.anySource', 'Any source')));
    ['core', 'mvp', 'card', 'mvp-card', 'shadow', 'relic', 'wiki', 'discord',
     'client', 'unknown']
      .forEach(function (s) {
        if (all.some(function (i) { return i.source === s; })) {
          els.source.appendChild(option(s, sourceLabel(s)));
        }
      });

    els.sort.innerHTML = '';
    [['name', t('db.sortName', 'Name')],
     ['levelUp', t('db.sortLevelUp', 'Level, lowest first')],
     ['levelDown', t('db.sortLevelDown', 'Level, highest first')]]
      .forEach(function (p) { els.sort.appendChild(option(p[0], p[1])); });

    fillCategories();
  }

  /* Categories follow the slot and kind already chosen, so the list never
     offers a combination that returns nothing. */
  function fillCategories() {
    var chosen = els.cat.value;
    var pool = all.filter(function (i) {
      return (kind === 'all' || i.kind === kind) &&
             (!els.slot.value || i.slot === els.slot.value);
    });
    var cats = [];
    pool.forEach(function (i) { if (cats.indexOf(i.cat) === -1) cats.push(i.cat); });
    cats.sort();

    els.cat.innerHTML = '';
    els.cat.appendChild(option('', t('db.anyCategory', 'Any category')));
    cats.forEach(function (c) { els.cat.appendChild(option(c, c)); });
    if (cats.indexOf(chosen) !== -1) els.cat.value = chosen;
  }

  /* ---------------------------------------------------------------- filter */

  function norm(s) { return (s || '').toLowerCase(); }

  /* Is the reader asking for anything yet? Painting all 3638 entries the
     moment the page opens gives the results column a scrollbar of its own,
     and the filters below the fold become unreachable: the wheel scrolls the
     results instead of the page. So nothing is listed until something is
     asked for, and "show everything" is a button rather than the default. */
  function filtering() {
    return !!(els.name.value.trim() || els.effect.value.trim() ||
              els.drops.value.trim() || els.slot.value || els.cat.value ||
              els.source.value || els.lvMin.value || els.lvMax.value ||
              kind !== 'all');
  }

  function apply() {
    if (!filtering() && !showAll) {
      view = [];
      grid.innerHTML = '';
      painted = 0;
      els.empty.hidden = true;
      if (els.prompt) els.prompt.hidden = false;
      els.count.textContent = all.length + ' ' +
        t('db.inDatabase', 'items in the database');
      return;
    }
    if (els.prompt) els.prompt.hidden = true;
    run();
  }

  function run() {
    var qn = norm(els.name.value).trim();
    var qe = norm(els.effect.value).trim();
    var qd = norm(els.drops.value).trim();
    var slot = els.slot.value;
    var cat = els.cat.value;
    var src = els.source.value;
    var lo = parseInt(els.lvMin.value, 10);
    var hi = parseInt(els.lvMax.value, 10);

    view = all.filter(function (i) {
      if (kind !== 'all' && i.kind !== kind) return false;
      if (slot && i.slot !== slot) return false;
      if (cat && i.cat !== cat) return false;
      if (src && i.source !== src) return false;
      if (qn && norm(i.name).indexOf(qn) === -1) return false;
      if (qe && i._search.indexOf(qe) === -1) return false;
      /* A card is named after the monster that drops it, so searching a
         monster by name has to turn up its card as well as its gear. */
      if (qd && norm(i.drops).indexOf(qd) === -1 &&
          !(i.kind === 'card' && norm(i.name).indexOf(qd) !== -1)) return false;
      if (!isNaN(lo) && (i.level == null || i.level < lo)) return false;
      if (!isNaN(hi) && (i.level == null || i.level > hi)) return false;
      return true;
    });

    var mode = els.sort.value;
    view.sort(function (a, b) {
      if (mode === 'levelUp' || mode === 'levelDown') {
        var av = a.level == null ? (mode === 'levelUp' ? 1e6 : -1) : a.level;
        var bv = b.level == null ? (mode === 'levelUp' ? 1e6 : -1) : b.level;
        if (av !== bv) return mode === 'levelUp' ? av - bv : bv - av;
      }
      return a.name.localeCompare(b.name);
    });

    grid.innerHTML = '';
    painted = 0;
    paint();

    els.empty.hidden = view.length > 0;
    els.count.textContent = view.length + ' ' +
      (view.length === 1 ? t('db.result', 'result') : t('db.results', 'results'));
  }

  /* ----------------------------------------------------------------- paint */

  function metaBits(i) {
    var bits = [];
    if (i.slots != null) bits.push(i.slots + ' ' + t('db.slotsWord', 'slots'));
    if (i.stat) bits.push(esc(i.statLabel) + ' ' + esc(i.stat));
    if (i.level != null) bits.push(t('db.lv', 'Lv') + ' ' + i.level);
    return bits;
  }

  /* A card's category is always the word "Card", which says nothing. The slot
     it goes in is the useful part, so that is what the tag shows. */
  function tagFor(i) {
    return i.kind === 'card' && i.slot ? slotLabel(i.slot) : i.cat;
  }

  function effectList(i, limit) {
    var lines = i.effect || [];
    var shown = limit ? lines.slice(0, limit) : lines;
    var html = '<ul class="db-effects">' + shown.map(function (line) {
      return '<li>' + colorize(line) + '</li>';
    }).join('') + '</ul>';
    if (limit && lines.length > limit) {
      html += '<p class="db-rest">+' + (lines.length - limit) + ' ' +
              t('db.moreLines', 'more') + '</p>';
    }
    return html;
  }

  function card(i, idx) {
    var meta = metaBits(i);
    return '<li><button class="db-card' + (i.kind === 'card' ? ' -card' : '') +
             '" type="button" data-idx="' + idx + '">' +
        '<span class="db-card-top">' +
          '<span class="db-name">' + esc(i.name) + '</span>' +
          '<span class="db-tag' + (i.kind === 'card' ? ' -slot' : '') + '">' +
            esc(tagFor(i)) + '</span>' +
        '</span>' +
        (meta.length ? '<span class="db-meta">' + meta.join('<span aria-hidden="true"> · </span>') + '</span>' : '') +
        effectList(i, 3) +
        '<span class="db-source -' + i.source + '">' + esc(sourceLabel(i.source)) + '</span>' +
      '</button></li>';
  }

  function paint() {
    if (painted >= view.length) { syncMore(); return; }
    var slice = view.slice(painted, painted + CHUNK);
    var html = '';
    for (var n = 0; n < slice.length; n++) html += card(slice[n], painted + n);
    grid.insertAdjacentHTML('beforeend', html);
    painted += slice.length;
    syncMore();
    keepFilling();
  }

  function syncMore() {
    if (!els.more) return;
    var left = view.length - painted;
    els.more.hidden = left <= 0;
    if (left > 0) els.more.textContent = t('db.more', 'Show more') + ' (' + left + ')';
  }

  /* IntersectionObserver only fires when the sentinel crosses the boundary.
     After a chunk lands it is often still on screen and no second event
     comes, so top up until it is pushed out of range. */
  function keepFilling() {
    if (!els.sentinel || painted >= view.length) return;
    requestAnimationFrame(function () {
      if (els.sentinel.getBoundingClientRect().top < window.innerHeight + 600) paint();
    });
  }

  /* ----------------------------------------------------------------- panel */

  /* Always English. This gets pasted into a Discord channel where people run
     every UI language, and the item names are English in game anyway. */
  function shareText(i) {
    var head = ['**' + i.name + '**', i.kind === 'card' ? 'Card' : i.cat];
    if (i.kind === 'material' && !i.drops) head.push('source not confirmed');
    if (i.kind === 'card') head.push(SLOT_FALLBACK[i.slot] + ' slot');
    if (i.slots != null) head.push(i.slots + ' slots');
    if (i.stat) head.push(i.statLabel + ' ' + i.stat);
    if (i.level != null) head.push('Lv ' + i.level);

    var lines = [head.shift() + '  ' + head.join(' · ')];
    (i.effect || []).forEach(function (line) { lines.push('- ' + line); });
    if (i.affix) lines.push('Affix: ' + i.affix);
    if (i.drops) lines.push('Drops from: ' + i.drops);
    lines.push('<' + itemUrl(i) + '>');
    return lines.join('\n');
  }

  function itemUrl(i) {
    return location.origin + location.pathname + '?item=' + encodeURIComponent(i.name);
  }

  function openItem(i) {
    if (!els.modal) return;
    open = i;
    var meta = metaBits(i);

    var html =
      '<p class="db-modal-tag">' + esc(i.cat) +
        (i.slot ? '<span aria-hidden="true"> · </span><b>' +
                  esc(slotLabel(i.slot)) + '</b>' : '') +
        '<span aria-hidden="true"> · </span>' +
        esc(sourceLabel(i.source)) + '</p>' +
      '<h2 id="dbModalTitle">' + esc(i.name) + '</h2>' +
      (meta.length ? '<p class="db-meta">' + meta.join('<span aria-hidden="true"> · </span>') + '</p>' : '') +
      '<h3 class="db-modal-h">' +
        (i.kind === 'material' ? t('db.aboutHead', 'What it is')
                               : t('db.effectHead', 'Effects')) + '</h3>' +
      effectList(i);

    if (i.affix) {
      html += '<h3 class="db-modal-h">' + t('db.affix', 'Affix') + '</h3>' +
              '<p class="db-modal-p">' + esc(i.affix) + '</p>';
    }
    if (i.drops) {
      html += '<h3 class="db-modal-h">' + t('db.drops', 'Drops from') + '</h3>' +
              '<p class="db-modal-p">' + esc(i.drops) + '</p>';
    }

    els.modalBody.innerHTML = html;
    els.modal.hidden = false;
    document.body.classList.add('no-scroll');
    if (els.modalClose) els.modalClose.focus();

    history.replaceState(null, '', itemUrl(i));
  }

  function closeItem() {
    if (!els.modal || els.modal.hidden) return;
    els.modal.hidden = true;
    open = null;
    document.body.classList.remove('no-scroll');
    history.replaceState(null, '', location.pathname);
  }

  function flash(btn, key, fallback) {
    var old = btn.dataset.label || btn.textContent;
    btn.dataset.label = old;
    btn.textContent = t(key, fallback);
    setTimeout(function () { btn.textContent = btn.dataset.label; }, 1600);
  }

  function copy(text, btn) {
    var done = function () { flash(btn, 'db.copied', 'Copied'); };
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text, done); });
    } else {
      fallbackCopy(text, done);
    }
  }

  function fallbackCopy(text, done) {
    var ta = document.createElement('textarea');
    ta.value = text;
    ta.setAttribute('readonly', '');
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    document.body.appendChild(ta);
    ta.select();
    try { document.execCommand('copy'); done(); } catch (e) {}
    document.body.removeChild(ta);
  }

  /* ------------------------------------------------------------------ wire */

  grid.addEventListener('click', function (e) {
    var btn = e.target.closest('.db-card');
    if (!btn) return;
    var i = view[parseInt(btn.dataset.idx, 10)];
    if (i) openItem(i);
  });

  if (els.modal) {
    els.modalClose.addEventListener('click', closeItem);
    els.modal.addEventListener('click', function (e) {
      if (e.target === els.modal) closeItem();
    });
    document.addEventListener('keydown', function (e) {
      if (e.key === 'Escape') closeItem();
    });
    els.share.addEventListener('click', function () {
      if (open) copy(shareText(open), els.share);
    });
    els.shareLink.addEventListener('click', function () {
      if (open) copy(itemUrl(open), els.shareLink);
    });
  }

  var debounce;
  function onInput() {
    clearTimeout(debounce);
    debounce = setTimeout(apply, 140);
  }

  [els.name, els.effect, els.drops, els.lvMin, els.lvMax].forEach(function (el) {
    el.addEventListener('input', onInput);
  });

  els.slot.addEventListener('change', function () { fillCategories(); apply(); });
  [els.cat, els.source, els.sort].forEach(function (el) {
    el.addEventListener('change', apply);
  });

  Array.prototype.forEach.call(document.querySelectorAll('.chip[data-kind]'), function (chip) {
    chip.addEventListener('click', function () {
      kind = chip.dataset.kind;
      Array.prototype.forEach.call(document.querySelectorAll('.chip[data-kind]'), function (c) {
        c.setAttribute('aria-pressed', String(c === chip));
      });
      fillCategories();
      apply();
    });
  });

  if (els.all) {
    els.all.addEventListener('click', function () {
      showAll = true;
      apply();
    });
  }

  els.reset.addEventListener('click', function () {
    showAll = false;
    els.name.value = els.effect.value = els.drops.value = '';
    els.lvMin.value = els.lvMax.value = '';
    els.slot.value = els.cat.value = els.source.value = '';
    els.sort.value = 'name';
    kind = 'all';
    Array.prototype.forEach.call(document.querySelectorAll('.chip[data-kind]'), function (c) {
      c.setAttribute('aria-pressed', String(c.dataset.kind === 'all'));
    });
    fillCategories();
    apply();
  });

  if (els.more) els.more.addEventListener('click', paint);

  if ('IntersectionObserver' in window && els.sentinel) {
    new IntersectionObserver(function (entries) {
      if (entries[0].isIntersecting) paint();
    }, { rootMargin: '600px' }).observe(els.sentinel);
  }

  document.addEventListener('nm:lang', function () {
    var keep = { slot: els.slot.value, cat: els.cat.value, src: els.source.value, sort: els.sort.value };
    fillSelects();
    els.slot.value = keep.slot;
    els.source.value = keep.src;
    els.sort.value = keep.sort;
    fillCategories();
    els.cat.value = keep.cat;
    apply();
    if (open) openItem(open);
  });

  /* ------------------------------------------------------------------ boot */

  fetch(fresh('assets/data/items.json'))
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      all = data.items || [];
      statusTerms = data.statusTerms || {};
      buildStatusRe();

      all.forEach(function (i) {
        i._search = norm((i.effect || []).join(' ') + ' ' + (i.affix || ''));
      });

      fillSelects();
      els.sort.value = 'name';
      apply();

      var params = new URLSearchParams(location.search);

      /* ?drops=Poporing is how the site search sends a monster here: the
         answer to "what does this thing drop" is this page, filtered. */
      var from = params.get('drops');
      if (from) {
        els.drops.value = from;
        apply();
      }

      var wanted = params.get('item');
      if (wanted) {
        var hit = all.filter(function (i) { return i.name === wanted; })[0];
        if (hit) {
          // so closing the panel leaves that item on screen rather than the
          // empty grid the page now opens with
          els.name.value = wanted;
          apply();
          openItem(hit);
        }
      }
    })
    .catch(function () {
      els.count.textContent = t('db.failed', 'The database could not be loaded. Try a refresh.');
    });
})();
