/* ==========================================================================
   Nightmare RO - item database
   --------------------------------------------------------------------------
   Loads assets/data/items.json once, filters it in memory, and paints the
   results in chunks so a 1200 item list never blocks the main thread.
   ========================================================================== */

(function () {
  'use strict';

  var grid = document.getElementById('dbGrid');
  if (!grid) return;

  var $ = function (id) { return document.getElementById(id); };

  var els = {
    name: $('qName'), effect: $('qEffect'),
    slot: $('fSlot'), cat: $('fCat'), source: $('fSource'), sort: $('fSort'),
    lvMin: $('lvMin'), lvMax: $('lvMax'),
    count: $('dbCount'), empty: $('dbEmpty'), reset: $('dbReset'),
    more: $('dbMore'), sentinel: $('dbSentinel')
  };

  var CHUNK = 60;
  var all = [];
  var view = [];
  var painted = 0;
  var kind = 'all';

  /* ------------------------------------------------------------ dictionary */

  /* Slot names are UI words, so they translate. Category names are the game's
     own weapon types and stay as they are, like the skill names elsewhere. */
  function t(key, fallback) {
    var table = window.NM_I18N_TABLE;
    return (table && table[key]) || fallback;
  }

  var SLOT_KEYS = ['weapon', 'armor', 'shield', 'garment', 'shoes', 'headgear', 'accessory', 'any'];
  var SLOT_FALLBACK = {
    weapon: 'Weapon', armor: 'Armour', shield: 'Shield', garment: 'Garment',
    shoes: 'Shoes', headgear: 'Headgear', accessory: 'Accessory', any: 'Fits any slot'
  };
  var SOURCE_FALLBACK = { core: 'World drop', mvp: 'Boss drop', card: 'Card' };

  function slotLabel(s) { return t('db.s.' + s, SLOT_FALLBACK[s] || s); }
  function sourceLabel(s) { return t('db.src.' + s, SOURCE_FALLBACK[s] || s); }

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
    ['core', 'mvp', 'card'].forEach(function (s) {
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

  /* Categories depend on the slot and kind currently chosen, so the list
     never offers a combination that returns nothing. */
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

  function apply() {
    var qn = norm(els.name.value).trim();
    var qe = norm(els.effect.value).trim();
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
      if (qe && norm(i.effect).indexOf(qe) === -1 && norm(i.affix).indexOf(qe) === -1) return false;
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

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  }

  function card(i) {
    var meta = [];
    if (i.slots != null) meta.push(i.slots + ' ' + t('db.slotsWord', 'slots'));
    if (i.stat) meta.push(esc(i.statLabel) + ' ' + esc(i.stat));
    if (i.level != null) meta.push(t('db.lv', 'Lv') + ' ' + i.level);

    var html =
      '<li class="db-card' + (i.kind === 'card' ? ' -card' : '') + '">' +
        '<div class="db-card-top">' +
          '<h3>' + esc(i.name) + '</h3>' +
          '<span class="db-tag">' + esc(i.cat) + '</span>' +
        '</div>' +
        (meta.length ? '<p class="db-meta">' + meta.join('<span aria-hidden="true"> · </span>') + '</p>' : '') +
        '<p class="db-effect">' + esc(i.effect) + '</p>';

    if (i.affix) {
      html += '<p class="db-line"><b>' + t('db.affix', 'Affix') + '</b> ' + esc(i.affix) + '</p>';
    }
    if (i.drops) {
      html += '<p class="db-line"><b>' + t('db.drops', 'Drops from') + '</b> ' + esc(i.drops) + '</p>';
    }
    html += '<span class="db-source -' + i.source + '">' + esc(sourceLabel(i.source)) + '</span>';
    return html + '</li>';
  }

  function paint() {
    if (painted >= view.length) { syncMore(); return; }
    var slice = view.slice(painted, painted + CHUNK);
    grid.insertAdjacentHTML('beforeend', slice.map(card).join(''));
    painted += slice.length;
    syncMore();
    keepFilling();
  }

  /* Scrolling tops the list up on its own, but the button is what guarantees
     the rest is reachable: by keyboard, and anywhere the observer misbehaves. */
  function syncMore() {
    if (!els.more) return;
    var left = view.length - painted;
    els.more.hidden = left <= 0;
    if (left > 0) {
      els.more.textContent = t('db.more', 'Show more') + ' (' + left + ')';
    }
  }

  /* IntersectionObserver only fires when the sentinel crosses the boundary.
     After a chunk lands the sentinel is often still on screen, and no second
     event ever comes, so top up until it is pushed out of range. */
  function keepFilling() {
    if (!els.sentinel || painted >= view.length) return;
    requestAnimationFrame(function () {
      var box = els.sentinel.getBoundingClientRect();
      if (box.top < window.innerHeight + 600) paint();
    });
  }

  /* ------------------------------------------------------------------ wire */

  var debounce;
  function onInput() {
    clearTimeout(debounce);
    debounce = setTimeout(apply, 140);
  }

  [els.name, els.effect, els.lvMin, els.lvMax].forEach(function (el) {
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

  els.reset.addEventListener('click', function () {
    els.name.value = els.effect.value = els.lvMin.value = els.lvMax.value = '';
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

  /* Rebuild the option labels when the language changes. */
  document.addEventListener('nm:lang', function () {
    var keep = { slot: els.slot.value, cat: els.cat.value, src: els.source.value, sort: els.sort.value };
    fillSelects();
    els.slot.value = keep.slot;
    els.source.value = keep.src;
    els.sort.value = keep.sort;
    fillCategories();
    els.cat.value = keep.cat;
    apply();
  });

  /* ------------------------------------------------------------------ boot */

  fetch('assets/data/items.json')
    .then(function (r) {
      if (!r.ok) throw new Error('HTTP ' + r.status);
      return r.json();
    })
    .then(function (data) {
      all = data.items || [];
      fillSelects();
      els.sort.value = 'name';
      apply();
    })
    .catch(function () {
      els.count.textContent = t('db.failed', 'The database could not be loaded. Try a refresh.');
    });
})();
