/* Nightmare RO, MVP page.
   One search box drives both the boss grid and the champion drop table, so
   typing "Orc" narrows the cards and the table at the same time. */
(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };

  var search = $('#mvpSearch');
  var grid = $('#mvpGrid');
  if (!search || !grid) return;

  var cards = $$('[data-mvp]');
  var rows = $$('[data-champ-row]');
  var empty = $('#mvpEmpty');
  var chips = $$('[data-mvp-filter]');
  var mode = 'all';

  var apply = function () {
    var q = search.value.trim().toLowerCase();
    var shown = 0;

    cards.forEach(function (card) {
      var okMode = mode === 'all' ||
        (mode === 'champ' && card.dataset.champ === 'yes') ||
        (mode === 'farm' && card.dataset.champ === 'no');
      var okText = !q || card.dataset.search.indexOf(q) !== -1;
      var show = okMode && okText;
      card.hidden = !show;
      if (show) shown++;
    });

    rows.forEach(function (row) {
      row.hidden = !!q && row.dataset.search.indexOf(q) === -1;
    });

    if (empty) empty.hidden = shown !== 0;
  };

  search.addEventListener('input', apply);

  chips.forEach(function (chip) {
    chip.addEventListener('click', function () {
      mode = chip.dataset.mvpFilter;
      chips.forEach(function (c) {
        c.setAttribute('aria-pressed', String(c === chip));
      });
      apply();
    });
  });

  /* A link straight to one boss should open its details, not just scroll to
     a collapsed card. */
  var openTarget = function () {
    if (!location.hash) return;
    var card = document.getElementById(location.hash.slice(1));
    if (!card || !card.hasAttribute('data-mvp')) return;
    var more = card.querySelector('.mvp-more');
    if (more) more.open = true;
  };

  window.addEventListener('hashchange', openTarget);
  openTarget();
  apply();
}());
