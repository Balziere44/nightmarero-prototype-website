/* Nightmare RO, quests page.
   The walkthroughs stay behind a gate until the reader asks for them, and the
   choice is remembered so the gate does not nag on every visit. */
(function () {
  'use strict';

  var gate = document.getElementById('questGate');
  var body = document.getElementById('questBody');
  var reveal = document.getElementById('questReveal');
  var hide = document.getElementById('questHide');
  if (!gate || !body || !reveal) return;

  var KEY = 'nm-quest-spoilers';

  var set = function (open, remember) {
    body.hidden = !open;
    gate.dataset.open = String(open);
    reveal.hidden = open;
    if (hide) hide.hidden = !open;
    if (remember) {
      try { localStorage.setItem(KEY, open ? 'yes' : 'no'); } catch (e) {}
    }
  };

  reveal.addEventListener('click', function () {
    set(true, true);
    var first = body.querySelector('details');
    if (first) first.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });

  if (hide) {
    hide.addEventListener('click', function () { set(false, true); });
  }

  var saved = null;
  try { saved = localStorage.getItem(KEY); } catch (e) {}
  set(saved === 'yes', false);

  /* A link to one quest should open it, even through the gate. */
  var openTarget = function () {
    if (!location.hash) return;
    var el = document.getElementById(location.hash.slice(1));
    if (!el || el.tagName !== 'DETAILS') return;
    set(true, false);
    el.open = true;
    el.scrollIntoView({ block: 'start' });
  };
  window.addEventListener('hashchange', openTarget);
  openTarget();
}());
