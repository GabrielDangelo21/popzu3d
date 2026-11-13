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
    // Alleen in een preview gebouwd met --season.
    if (root.getAttribute('data-force-season')) current = root.getAttribute('data-force-season');
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
      var mainImg = document.querySelector('.gallery .main img');
      if (mainImg && ev.target.getAttribute('data-img')) {
        mainImg.src = ev.target.getAttribute('data-img');
        mainImg.alt = ev.target.getAttribute('data-alt');
        document.querySelectorAll('.thumbs button').forEach(function (x) { x.setAttribute('aria-current', 'false'); });
      }
      var extra = ' ' + picker.getAttribute('data-tpl').replace('{c}', ev.target.value);
      document.querySelectorAll('.sizes a[data-msg]').forEach(function (a) {
        var link = a.getAttribute('data-link');
        a.href = picker.getAttribute('data-wa') + encodeURIComponent(a.getAttribute('data-msg') + extra + (link ? '\n' + link : ''));
      });
    });
  }

  // Statistieken: elke klik op een WhatsApp-knop telt als gebeurtenis, per pagina.
  document.addEventListener('click', function (ev) {
    var a = ev.target.closest && ev.target.closest('a[href*="wa.me/"]');
    if (a && window.goatcounter && window.goatcounter.count) {
      window.goatcounter.count({ path: 'whatsapp' + location.pathname, title: document.title, event: true });
    }
  });

  // Knop naar boven: alleen zichtbaar nadat er naar beneden gescrold is.
  var toTop = document.querySelector('.totop');
  if (toTop) {
    var showToTop = function () { toTop.hidden = window.scrollY < 600; };
    window.addEventListener('scroll', showToTop, { passive: true });
    showToTop();
  }

  // Video bij 'Zo werkt het': speelt alleen als hij in beeld is. Met 'minder beweging' blijft hij stil, met knoppen.
  // De knop pauzeert of speelt; wie zelf pauzeert, krijgt de video niet automatisch terug.
  var vid = document.querySelector('.how-video video'), vbtn = document.querySelector('.vid-toggle');
  if (vid) {
    var still = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    var userPaused = still, inView = false;
    var mark = function () {
      var paused = vid.paused;
      if (!vbtn) return;
      vbtn.setAttribute('aria-pressed', paused ? 'true' : 'false');
      vbtn.setAttribute('aria-label', vbtn.getAttribute(paused ? 'data-play' : 'data-pause'));
      vbtn.classList.toggle('is-paused', paused);
    };
    var go = function () { var p = vid.play(); if (p && p.catch) p.catch(function () { userPaused = true; mark(); }); };
    vid.addEventListener('play', mark);
    vid.addEventListener('pause', mark);
    if (vbtn) vbtn.addEventListener('click', function () {
      if (vid.paused) { userPaused = false; go(); } else { userPaused = true; vid.pause(); }
    });
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (entries) {
        entries.forEach(function (en) {
          inView = en.isIntersecting;
          if (inView && !userPaused) go(); else if (!inView) vid.pause();
        });
      }, { threshold: 0.4 }).observe(vid);
    }
    mark();
  }

  // Productpagina op de telefoon: vaste balk met prijs, weg zodra de keuze (kleur/formaat) in beeld is.
  var bar = document.querySelector('.buybar'), choice = document.getElementById('bestel');
  if (bar && choice && 'IntersectionObserver' in window) {
    var seen = false;
    new IntersectionObserver(function (entries) {
      entries.forEach(function (en) { seen = en.isIntersecting || en.boundingClientRect.top < 0; bar.hidden = seen; });
    }).observe(choice);
    bar.hidden = false;
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

  // Animaties: alleen als het systeem geen 'minder beweging' vraagt.
  var calm = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (calm) return;

  // 1. FAQ: het antwoord schuift open en dicht in plaats van te springen.
  document.querySelectorAll('.faq details').forEach(function (d) {
    var sum = d.querySelector('summary'), anim = null;
    sum.addEventListener('click', function (ev) {
      if (!d.animate) return;
      ev.preventDefault();
      if (anim) anim.cancel();
      var start = d.offsetHeight;
      if (d.open) {
        var end = sum.offsetHeight + parseFloat(getComputedStyle(d).paddingTop) + parseFloat(getComputedStyle(d).paddingBottom);
        anim = d.animate({ height: [start + 'px', end + 'px'] }, { duration: 260, easing: 'cubic-bezier(.2,.7,.2,1)' });
        anim.onfinish = function () { d.open = false; anim = null; };
      } else {
        d.open = true;
        var full = d.offsetHeight;
        anim = d.animate({ height: [start + 'px', full + 'px'] }, { duration: 300, easing: 'cubic-bezier(.2,.7,.2,1)' });
        anim.onfinish = function () { anim = null; };
      }
    });
  });

  // 2. Karakterkaart kantelt mee met de muis, als een verzamelkaart tegen het licht.
  if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
    document.querySelectorAll('.kaart').forEach(function (k) {
      k.addEventListener('pointermove', function (ev) {
        var r = k.getBoundingClientRect();
        var x = (ev.clientX - r.left) / r.width, y = (ev.clientY - r.top) / r.height;
        k.classList.add('tilting');
        k.style.setProperty('--ry', ((x - 0.5) * 14).toFixed(2) + 'deg');
        k.style.setProperty('--rx', ((0.5 - y) * 12).toFixed(2) + 'deg');
        k.style.setProperty('--gx', (x * 100).toFixed(1) + '%');
        k.style.setProperty('--gy', (y * 100).toFixed(1) + '%');
      });
      k.addEventListener('pointerleave', function () {
        k.classList.remove('tilting');
        k.style.setProperty('--rx', '0deg');
        k.style.setProperty('--ry', '0deg');
      });
    });
  }

  // 3. De meters worden 'gebreid': de eerste keer dat een kaart in beeld komt, vullen de steken zich een voor een.
  if ('IntersectionObserver' in window) {
    var knit = function (k) {
      k.querySelectorAll('.steken').forEach(function (m, row) {
        var n = parseInt(getComputedStyle(m).getPropertyValue('--n'), 10) || 0, i = 0;
        m.style.setProperty('--k', '0');
        setTimeout(function step() {
          i++;
          m.style.setProperty('--k', String(i));
          if (i < n) setTimeout(step, 55);
        }, 150 + row * 180);
      });
    };
    var ioAlive = false;
    // garantia: se o navegador não informar a visibilidade (aba em segundo plano, por exemplo), os medidores aparecem cheios
    setTimeout(function () {
      if (!ioAlive) document.querySelectorAll('.steken').forEach(function (m) { m.style.removeProperty('--k'); });
    }, 2000);
    var io = new IntersectionObserver(function (entries) {
      ioAlive = true;
      entries.forEach(function (en) {
        if (en.isIntersecting) { io.unobserve(en.target); knit(en.target); }
      });
    }, { threshold: 0.6 });
    document.querySelectorAll('.kaart').forEach(function (k) {
      // começa vazia só se ainda não está na tela (evita piscar o que já foi visto)
      k.querySelectorAll('.steken').forEach(function (m) { m.style.setProperty('--k', '0'); });
      io.observe(k);
    });
  }
})();
