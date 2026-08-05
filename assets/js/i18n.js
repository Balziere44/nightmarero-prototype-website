/* ==========================================================================
   Nightmare RO - language switcher
   --------------------------------------------------------------------------
   English lives in the HTML itself, so search engines and no-JS visitors
   always get real content. Other languages are separate script files that
   register themselves and swap the text in place.

   Markup contract:
     data-i18n="some.key"                -> replaces the element's content
     data-i18n-attr="placeholder:key"    -> replaces an attribute
                                            (several pairs, comma separated)

   Strings may contain simple inline markup (<strong>, <b class="kw ...">).
   Those come from our own locale files, never from user input.
   ========================================================================== */

(function () {
  'use strict';

  var LOCALES = [
    { code: 'en', label: 'English',    tag: 'en' },
    { code: 'pt', label: 'Português',  tag: 'pt-BR' },
    { code: 'fr', label: 'Français',   tag: 'fr' },
    { code: 'it', label: 'Italiano',   tag: 'it' },
    { code: 'de', label: 'Deutsch',    tag: 'de' },
    { code: 'ja', label: '日本語',      tag: 'ja' }
  ];

  var STORE_KEY = 'nm-lang';
  var dict = {};      // code -> { key: string }
  var loading = {};   // code -> Promise
  var current = 'en';
  var originals = null;

  /* Work out where the site root is, relative to this script, so the same
     file works from /index.html and from /classes/whatever.html. */
  var base = (function () {
    var s = document.currentScript;
    if (!s) {
      var all = document.getElementsByTagName('script');
      s = all[all.length - 1];
    }
    return s.src.replace(/assets\/js\/i18n\.js.*$/, '');
  })();

  /* ---------------------------------------------------------------- store */

  window.NM_I18N_REGISTER = function (code, table) {
    dict[code] = table;
  };

  function load(code) {
    if (code === 'en' || dict[code]) return Promise.resolve();
    if (loading[code]) return loading[code];

    loading[code] = new Promise(function (resolve) {
      var el = document.createElement('script');
      el.src = base + 'assets/i18n/' + code + '.js';
      el.onload = resolve;
      el.onerror = function () { resolve(); };   // fall back to English
      document.head.appendChild(el);
    });
    return loading[code];
  }

  /* Japanese needs a font that actually has the glyphs. */
  var jpFontLoaded = false;
  function ensureJapaneseFont() {
    if (jpFontLoaded) return;
    jpFontLoaded = true;
    var l = document.createElement('link');
    l.rel = 'stylesheet';
    l.href = 'https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;700&display=swap';
    document.head.appendChild(l);
  }

  /* ---------------------------------------------------------------- apply */

  function snapshot() {
    if (originals) return;
    originals = { text: new Map(), attrs: new Map() };

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      originals.text.set(el, el.innerHTML);
    });
    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      var store = {};
      parsePairs(el).forEach(function (p) { store[p.attr] = el.getAttribute(p.attr); });
      originals.attrs.set(el, store);
    });
  }

  function parsePairs(el) {
    return el.getAttribute('data-i18n-attr').split(',').map(function (chunk) {
      var bits = chunk.split(':');
      return { attr: bits[0].trim(), key: (bits[1] || '').trim() };
    });
  }

  function apply(code) {
    snapshot();
    var table = dict[code] || {};

    /* Scripts that build strings at runtime (the database filters) read the
       active table straight off the window instead of the DOM. */
    window.NM_I18N_TABLE = table;

    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      var key = el.getAttribute('data-i18n');
      var value = code === 'en' ? originals.text.get(el) : table[key];
      if (value == null) value = originals.text.get(el);
      if (value == null) return;
      if (value.indexOf('<') !== -1) el.innerHTML = value;
      else el.textContent = value;
    });

    document.querySelectorAll('[data-i18n-attr]').forEach(function (el) {
      var saved = originals.attrs.get(el) || {};
      parsePairs(el).forEach(function (p) {
        var value = code === 'en' ? saved[p.attr] : table[p.key];
        if (value == null) value = saved[p.attr];
        if (value != null) el.setAttribute(p.attr, value);
      });
    });

    var meta = LOCALES.filter(function (l) { return l.code === code; })[0] || LOCALES[0];
    document.documentElement.lang = meta.tag;
    if (code === 'ja') ensureJapaneseFont();

    var codeLabel = document.getElementById('langCode');
    if (codeLabel) codeLabel.textContent = code.toUpperCase();

    document.querySelectorAll('#langMenu button').forEach(function (b) {
      b.setAttribute('aria-checked', String(b.dataset.lang === code));
    });

    current = code;
    document.dispatchEvent(new CustomEvent('nm:lang', { detail: { lang: code } }));
  }

  function set(code, remember) {
    if (!LOCALES.some(function (l) { return l.code === code; })) code = 'en';
    load(code).then(function () { apply(code); });
    if (remember !== false) {
      try { localStorage.setItem(STORE_KEY, code); } catch (e) {}
    }
  }

  /* ------------------------------------------------------------------- ui */

  function buildMenu() {
    var menu = document.getElementById('langMenu');
    var btn = document.getElementById('langBtn');
    if (!menu || !btn) return;

    menu.innerHTML = LOCALES.map(function (l) {
      return '<button type="button" role="menuitemradio" aria-checked="false" data-lang="' + l.code +
             '"><span>' + l.label + '</span><span>' + l.code.toUpperCase() + '</span></button>';
    }).join('');

    function close() {
      menu.dataset.open = 'false';
      btn.setAttribute('aria-expanded', 'false');
    }

    btn.addEventListener('click', function (e) {
      e.stopPropagation();
      var open = menu.dataset.open === 'true';
      menu.dataset.open = String(!open);
      btn.setAttribute('aria-expanded', String(!open));
    });

    menu.addEventListener('click', function (e) {
      var b = e.target.closest('button[data-lang]');
      if (!b) return;
      set(b.dataset.lang);
      close();
    });

    document.addEventListener('click', close);
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape') close(); });
  }

  /* ----------------------------------------------------------------- boot */

  function initial() {
    var saved;
    try { saved = localStorage.getItem(STORE_KEY); } catch (e) {}
    if (saved) return saved;

    var nav = (navigator.languages || [navigator.language || 'en'])[0].slice(0, 2).toLowerCase();
    return LOCALES.some(function (l) { return l.code === nav; }) ? nav : 'en';
  }

  function boot() {
    buildMenu();
    var start = initial();
    if (start !== 'en') set(start, false);
    else apply('en');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }

  window.NM_I18N = {
    set: set,
    locales: LOCALES,
    get current() { return current; }
  };
})();
