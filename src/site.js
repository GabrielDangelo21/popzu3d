(function () {
  var root = document.documentElement;

  // Seizoen: bepaalt de topbalk en welke favorieten zichtbaar zijn.
  // De build zet al een standaard; dit corrigeert het als de datum intussen veranderd is.
  try {
    var seasons = JSON.parse(root.getAttribute('data-seasons') || '{}');
    var now = new Date();
    var md = String(now.getMonth() + 1).padStart(2, '0') + '-' + String(now.getDate()).padStart(2, '0');
    var current = 'none';
    Object.keys(seasons).forEach(function (k) {
      if (md >= seasons[k][0] && md <= seasons[k][1]) current = k;
    });
    document.querySelectorAll('[data-season]').forEach(function (el) {
      el.hidden = el.getAttribute('data-season') !== current;
    });
    var favKey = current === 'halloween' ? 'halloween' : 'default';
    document.querySelectorAll('[data-fav]').forEach(function (el) {
      el.hidden = el.getAttribute('data-fav') !== favKey;
    });
  } catch (e) {}

  // Filters in de collectie.
  var chips = document.querySelectorAll('.chip[data-filter]');
  if (chips.length) {
    var cards = document.querySelectorAll('#catalog .card');
    var intro = document.querySelector('.col-intro');
    var apply = function (key, push) {
      var found = false;
      chips.forEach(function (c) {
        var on = c.getAttribute('data-filter') === key;
        if (on) found = true;
        c.setAttribute('aria-pressed', on ? 'true' : 'false');
        if (on && intro) intro.textContent = c.getAttribute('data-intro') || '';
      });
      if (!found) return apply('all', push);
      cards.forEach(function (card) {
        card.hidden = key !== 'all' && card.getAttribute('data-col') !== key;
      });
      if (push && history.replaceState) {
        var url = new URL(location.href);
        if (key === 'all') url.searchParams.delete('c'); else url.searchParams.set('c', key);
        history.replaceState(null, '', url.pathname + url.search + url.hash);
      }
    };
    chips.forEach(function (c) {
      c.addEventListener('click', function () { apply(c.getAttribute('data-filter'), true); });
    });
    var start = new URLSearchParams(location.search).get('c');
    if (start) apply(start, false);
  }

  // Een vraag openen als de link ernaar verwijst (bv. #levering).
  var openHash = function () {
    var el = location.hash && document.getElementById(location.hash.slice(1));
    if (el && el.tagName === 'DETAILS') el.open = true;
  };
  openHash();
  window.addEventListener('hashchange', openHash);

  // Kleurkeuze: de gekozen kleur komt mee in het WhatsApp-bericht van elk formaat.
  var picker = document.querySelector('.colors[data-tpl]');
  if (picker) {
    picker.addEventListener('change', function (ev) {
      var extra = ' ' + picker.getAttribute('data-tpl').replace('{c}', ev.target.value);
      document.querySelectorAll('.sizes a[data-msg]').forEach(function (a) {
        a.href = picker.getAttribute('data-wa') + encodeURIComponent(a.getAttribute('data-msg') + extra);
      });
    });
  }

  // Fotogalerij op de productpagina.
  var main = document.querySelector('.gallery .main img');
  document.querySelectorAll('.thumbs button').forEach(function (b, i, all) {
    b.addEventListener('click', function () {
      main.src = b.getAttribute('data-src');
      main.alt = b.getAttribute('data-alt');
      all.forEach(function (x) { x.setAttribute('aria-current', x === b ? 'true' : 'false'); });
    });
  });
})();
