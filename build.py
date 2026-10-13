"""Gera o site estático do Popzu em public/.

Uso:
    python build.py            -> public/  (para publicar no Netlify)
    python build.py --preview  -> preview/ (mostra os destaques mesmo sem preço)
    python build.py --preview --season kerst -> preview/ como se fosse novembro

Dados em data/: catalog.json (modelos, tamanhos e preços, fotos), texts.json (textos NL/FR/EN), site.json (contato, prazo, estações).
Precisa de Pillow para gerar as miniaturas (pip install pillow).
"""
import datetime
import html
import json
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

ROOT = Path(__file__).parent
PREVIEW = "--preview" in sys.argv
OUT = ROOT / ("preview" if PREVIEW else "public")
LANGS = ["nl", "fr", "en"]
THUMB = 600

load = lambda name: json.loads((ROOT / "data" / name).read_text(encoding="utf-8"))
SITE, CAT, TXT = load("site.json"), load("catalog.json"), load("texts.json")
MODELS = CAT["models"]
# Kerstcollectie: aparte lijn, alleen zichtbaar op de homepage in het seizoen "kerst" (productpagina's bestaan altijd).
KERST = CAT.get("kerst", {"categories": [], "items": []})
KITEMS = KERST["items"]
ALL = MODELS + KITEMS
BY_SLUG = {m["slug"]: m for m in ALL}
COLS = {c["key"]: c for c in CAT["collections"] + KERST["categories"]}
WARN = []

e = lambda s: html.escape(str(s), quote=True)


# ---------- helpers ----------

# Nomes que já começam com "The" (The Mummy, The Elemental Dragon): sem artigo duplicado.
ARTICLE_FIX = {"en": (("The The ", "The "), ("the The ", "the ")),
               "nl": (("De The ", "The "), ("de The ", "The "))}


def F(lang, s, **kw):
    out = _F(lang, s, **kw)
    for a, b in ARTICLE_FIX.get(lang, ()):
        out = out.replace(a, b)
    return out


def _F(lang, s, **kw):
    base = {"lead": lead(lang), "ship_from": ship_from(lang), "small": size_range(lang, "s"), "large": size_range(lang, "l"),
            "shipping_table": "{shipping_table}"}
    return s.format(**{**base, **kw})


def T(lang, key, **kw):
    return F(lang, TXT[lang][key], **kw)


def ship_from(lang):
    paid = [r["price"] for r in SITE.get("shipping", {}).get("rows", []) if r["price"]]
    return price_text(lang, min(paid)) if paid else ""


def ship_transit(lang, v):
    if v in ("sameday", "24h"):
        return T(lang, "ship_" + v)
    d = v.replace("-", " à " if lang == "fr" else "–")
    return T(lang, "ship_days", d=d)


def shipping_table(lang):
    rows = "".join(
        f'<tr><td>{e(r["dest"][lang])}</td><td>{e(T(lang, "ship_" + r["type"]))}</td>'
        f'<td>{e(price_text(lang, r["price"]) if r["price"] else T(lang, "ship_free"))}</td><td>{e(ship_transit(lang, r["transit"]))}</td></tr>'
        for r in SITE["shipping"]["rows"])
    head = "".join(f"<th scope=\"col\">{e(T(lang, k))}</th>" for k in ("ship_dest", "ship_type", "ship_price", "ship_transit"))
    return f'<div class="table-wrap"><table class="ship"><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table></div>'


def lead(lang):
    d = SITE["lead_days"]
    if d["min"] == d["max"]:
        return TXT[lang]["lead_one" if d["min"] == 1 else "lead_same"].format(n=d["min"])
    return TXT[lang]["lead"].format(min=d["min"], max=d["max"])


def sizes(m):
    return [s for s in m.get("sizes", []) if s.get("price") is not None]


def from_price(m):
    return min((s["price"] for s in sizes(m)), default=None)


def num(lang, x):
    """Altura: 13.5 -> '13,5' em NL/FR, '13.5' em EN; inteiros sem casa decimal."""
    s = f"{int(x)}" if float(x).is_integer() else f"{x:g}"
    return s if lang == "en" else s.replace(".", ",")


def size_range(lang, key):
    cms = [s["cm"] for m in MODELS for s in sizes(m) if s["key"] == key]
    return TXT[lang]["range"].format(a=num(lang, min(cms)), b=num(lang, max(cms))) if cms else ""


def heights(lang, m):
    cms = [s["cm"] for s in sizes(m) if s.get("cm")]
    if len(cms) == 2:
        return T(lang, "heights", a=num(lang, cms[0]), b=num(lang, cms[1]))
    return T(lang, "size", cm=num(lang, cms[0])) if cms else ""


def size_name(lang, s):
    return s["label"][lang] if s.get("label") else T(lang, "size_" + s["key"])


def variant(lang, s):
    return f'{size_name(lang, s)}, {T(lang, "size", cm=num(lang, s["cm"]))}' if s.get("cm") else size_name(lang, s)


def price_text(lang, p):
    if p is None:
        return None
    whole = float(p).is_integer()
    n = f"{int(p)}" if whole else f"{p:.2f}"
    if lang == "en":
        return f"€{n}"
    n = n.replace(".", ",")
    return f"{n} €" if lang == "fr" else f"€ {n}"


def url(lang, path=""):
    return ("/" if lang == "nl" else f"/{lang}/") + path


def wa(text):
    return f"https://wa.me/{SITE['whatsapp']}?text={quote(text)}"


def order_msg(lang, m, s):
    return T(lang, "wa_order", name=nm(m, lang), size=variant(lang, s), price=price_text(lang, s["price"]))


def page_link(lang, m):
    """Link da página do produto, posto no fim da mensagem do WhatsApp para o dono saber qual é o modelo."""
    base = (SITE.get("base_url") or "").rstrip("/")
    return f"{base}{url(lang, m['slug'] + '/')}" if base else ""


def with_link(msg, lang, m):
    link = page_link(lang, m)
    return f"{msg}\n{link}" if link else msg


def wa_order(lang, m, s=None):
    if s:
        return wa(with_link(order_msg(lang, m, s), lang, m))
    return wa(with_link(T(lang, "wa_order_noprice", name=nm(m, lang), size=heights(lang, m)), lang, m))


def todo(lang):
    return f'<span class="todo">{e(T(lang, "todo"))}</span>'


def nm(m, lang):
    """Nome do produto: texto único (figuras do Whale) ou {nl, fr, en} (coleção de Natal)."""
    return m["name"][lang] if isinstance(m["name"], dict) else m["name"]


def cname(c, lang):
    return c[lang] if isinstance(c, dict) else c


def has_color_img(m, i):
    return (ROOT / "images" / m["slug"] / f'{m["slug"]}-cor-{i + 1:02d}.webp').exists()


def colors_img(m):
    return f"/img/{m['slug']}/cores.webp"


def color_img(m, i):
    return f"/img/{m['slug']}/cor-{i + 1:02d}.webp"


def img(m, i, small=False):
    return f"/img/{m['slug']}/{i + 1}{'-' + str(THUMB) if small else ''}.webp"


def season_today():
    md = datetime.date.today().strftime("%m-%d")
    for k, v in SITE["seasons"].items():
        if not k.startswith("_") and v["from"] <= md <= v["to"]:
            return k
    return "none"


# --season kerst|halloween|none simula outra época (útil com --preview para ver a seção de Natal antes de novembro).
SEASON = sys.argv[sys.argv.index("--season") + 1] if "--season" in sys.argv else season_today()
CUR = ' aria-current="page"'
FORCE = f' data-force-season="{SEASON}"' if "--season" in sys.argv else ""
WA_ICON = ('<svg class="wa-ico" viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M12 2a10 10 0 0 0-8.6 15.1L2 22l5-1.3A10 10 0 1 0 12 2Zm0 18.2a8.2 8.2 0 0 1-4.2-1.2l-.3-.2-3 .8.8-2.9-.2-.3A8.2 8.2 0 1 1 12 20.2Zm4.5-6.1c-.2-.1-1.5-.7-1.7-.8-.2-.1-.4-.1-.6.1l-.8 1c-.1.2-.3.2-.5.1a6.7 6.7 0 0 1-3.3-2.9c-.3-.4.2-.4.7-1.3.1-.2 0-.3 0-.4l-.8-1.8c-.2-.5-.4-.4-.6-.4h-.5a1 1 0 0 0-.7.3 3 3 0 0 0-.9 2.2 5.2 5.2 0 0 0 1.1 2.7 11.9 11.9 0 0 0 4.6 4c1.7.7 2.3.8 3.2.6a2.7 2.7 0 0 0 1.8-1.2 2.2 2.2 0 0 0 .2-1.3c-.1-.1-.3-.2-.5-.3Z"/></svg>')


def wa_button(href, label, cls="", msg=None, link=None):
    data = f' data-msg="{e(msg)}"' if msg else ""
    if msg and link:
        data += f' data-link="{e(link)}"'
    return f'<a class="btn btn-wa {cls}" href="{e(href)}"{data} target="_blank" rel="noopener">{WA_ICON}{e(label)}</a>'


# ---------- featured ----------

def featured(season):
    f = CAT["featured"]
    base = list(f["list"])
    if season != "halloween":
        base = [f["swap"].get(s, s) for s in base]
    ok = lambda s: s in BY_SLUG and (PREVIEW or sizes(BY_SLUG[s]))
    out = []
    for s in base + f["reserve"]:
        if len(out) >= len(f["list"]):
            break
        if ok(s) and s not in out:
            out.append(s)
    return out


# ---------- layout ----------

def head(lang, title, desc, paths, og=None):
    base = (SITE.get("base_url") or "").rstrip("/")
    alt = ""
    if base:
        alt = "".join(f'<link rel="alternate" hreflang="{l}" href="{base}{url(l, paths)}">' for l in LANGS)
        alt += f'<link rel="alternate" hreflang="x-default" href="{base}{url("nl", paths)}">'
        alt += f'<link rel="canonical" href="{base}{url(lang, paths)}">'
    og_tags = f'<meta property="og:title" content="{e(title)}"><meta property="og:description" content="{e(desc)}"><meta property="og:type" content="website">'
    if og:
        og_tags += f'<meta property="og:image" content="{e(base + og)}">'
    seasons = {k: [v["from"], v["to"]] for k, v in SITE["seasons"].items() if not k.startswith("_")}
    return f"""<!doctype html>
<html lang="{lang}" data-seasons='{e(json.dumps(seasons))}'{FORCE}>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="theme-color" content="#1E1B22">
{og_tags}{alt}
<link rel="icon" href="/favicon-32.png" type="image/png" sizes="32x32">
<link rel="apple-touch-icon" href="/apple-touch-icon.png" sizes="180x180">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Fredoka:wght@500;600&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
</head>
<body>
<a class="skip" href="#inhoud">{e(T(lang, "skip"))}</a>
"""


def topbar(lang, home):
    coll = "#collectie" if home else url(lang) + "#collectie"
    spooky = (url(lang) if not home else "") + "?c=spooky#collectie"
    out = ""
    for s, txt, href in (("halloween", T(lang, "topbar_halloween"), spooky), ("kerst", T(lang, "topbar_kerst"), coll)):
        hid = "" if SEASON == s else " hidden"
        out += f'<div class="topbar {s}" data-season="{s}"{hid}><a href="{e(href)}">{e(txt)}</a></div>\n'
    return out


def nav(lang, paths, home, has_fav):
    pre = "" if home else url(lang)
    links = []
    if has_fav:
        links.append((pre + "#favorieten", T(lang, "nav_favourites")))
    links += [(pre + "#collectie", T(lang, "nav_collection")), (pre + "#hoe", T(lang, "nav_how")),
              (pre + "#opmaat", T(lang, "nav_custom")), (pre + "#faq", T(lang, "nav_faq"))]
    ls = "".join(f'<a href="{e(h)}">{e(t)}</a>' for h, t in links)
    if KITEMS:
        hid = "" if SEASON == "kerst" else " hidden"
        ls = f'<a href="{e(pre)}#kerst" data-season="kerst"{hid}>{e(T(lang, "nav_kerst"))}</a>' + ls
    langs = "".join(
        f'<a href="{url(l, paths)}" hreflang="{l}" lang="{l}" title="{e(TXT[l]["lang_name"])}"'
        f'{CUR if l == lang else ""}>{l.upper()}</a>' for l in LANGS)
    return f"""<nav class="main"><div class="wrap">
  <a class="logo" href="{url(lang)}"><img src="/assets/logo.svg" alt="popzu" width="130" height="44"></a>
  <div class="links">{ls}</div>
  <div class="lang">{langs}</div>
</div></nav>
"""


def footer(lang):
    L = SITE["legal"]
    contact = [f'<a href="{e(wa(T(lang, "wa_general")))}" target="_blank" rel="noopener">WhatsApp {e(SITE["whatsapp_display"])}</a>']
    if SITE.get("instagram"):
        handle = SITE["instagram"].lstrip("@")
        contact.append(f'<a href="https://instagram.com/{e(handle)}" target="_blank" rel="noopener">Instagram @{e(handle)}</a>')
    elif PREVIEW:
        contact.append(f"Instagram: {todo(lang)}")
    if SITE.get("email"):
        contact.append(f'<a href="mailto:{e(SITE["email"])}">{e(SITE["email"])}</a>')
    elif PREVIEW:
        contact.append(f"E-mail: {todo(lang)}")
    # No site publicado, dados legais vazios ficam ocultos; no preview aparecem como 'nog in te vullen'.
    company = []
    for key, prefix in (("name", ""), ("address", ""), ("vat", T(lang, "footer_vat") + " ")):
        if L.get(key):
            company.append(e(prefix) + e(L[key]))
        elif PREVIEW:
            company.append(e(prefix) + todo(lang))
    year = datetime.date.today().year
    return f"""<footer><div class="wrap">
  <div><a class="logo logo-foot" href="{url(lang)}"><img src="/assets/logo.svg" alt="popzu" width="154" height="52" loading="lazy"></a><p style="margin-top:8px">{e(T(lang, "footer_tagline"))}</p><p style="margin-top:14px">© {year} popzu</p></div>
  <div><h4>{e(T(lang, "footer_contact"))}</h4><p>{"<br>".join(contact)}</p></div>
  {f'<div><h4>{e(T(lang, "footer_company"))}</h4><p>{"<br>".join(company)}</p></div>' if company else ""}
</div></footer>
<script src="/assets/site.js" defer></script>
</body>
</html>
"""


# ---------- components ----------

def card_heights(lang, m):
    cms = [s["cm"] for s in sizes(m) if s.get("cm")]
    return TXT[lang]["range"].format(a=num(lang, cms[0]), b=num(lang, cms[-1])) if len(cms) > 1 else (T(lang, "size", cm=num(lang, cms[0])) if cms else "")


def card(lang, m, fav=False, halloween=False):
    col = COLS[m["collection"]]
    p = from_price(m)
    if p is not None:
        label = price_text(lang, p) if len(sizes(m)) == 1 else T(lang, "from_price", p=price_text(lang, p))
        price = f'<span class="price">{e(label)}</span>'
    else:
        price = f'<span class="price ask">{e(T(lang, "price_on_request"))}</span>'
    tag = ""
    if fav and halloween:
        tag = f'<span class="tag">{e(T(lang, "badge_halloween"))}</span>'
    elif m.get("badge") == "flexi":
        tag = f'<span class="tag flexi">{e(T(lang, "badge_flexi"))}</span>'
    alt = T(lang, "p_photo", name=nm(m, lang), i=1)
    href = url(lang, m["slug"] + "/")
    body = f'<h3><a href="{href}">{e(nm(m, lang))}</a></h3><div class="sub">{e(col["name"][lang])}{(" · " + e(card_heights(lang, m))) if card_heights(lang, m) else ""}{(" · " + e(T(lang, "card_colors", n=len(m["colors"]["options"])))) if m.get("colors") else ""}</div>'
    if fav:
        line = m.get("tagline", {}).get(lang, "")
        body += f'<p class="line">{e(line)}</p>' if line else ""
        body += f'<div class="row">{price}</div>'
        # Com dois tamanhos, o pedido é feito na página do produto (um botão de WhatsApp por tamanho).
        body += f'<a class="btn btn-coral btn-sm btn-block" href="{href}" tabindex="-1">{e(T(lang, "fav_btn"))}</a>'
    else:
        body += f'<div class="row">{price}</div>'
    return (f'<article class="card" data-col="{m["collection"]}">'
            f'<div class="pic">{tag}<img src="{img(m, 0, True)}" alt="{e(alt)}" width="{THUMB}" height="{THUMB}" loading="lazy" decoding="async"></div>'
            f'<div class="info">{body}</div></article>')


# ---------- pages ----------

def home(lang):
    n = len(MODELS)
    lists = {"halloween": featured("halloween"), "default": featured("default")}
    has_fav = any(lists.values())
    cur = "halloween" if SEASON == "halloween" else "default"

    out = head(lang, T(lang, "meta_title_home"), T(lang, "meta_desc_home"), "", "/img/hero.webp")
    out += topbar(lang, True) + nav(lang, "", True, has_fav)
    out += f"""<main id="inhoud">
<header class="hero"><div class="wrap">
  <div>
    <div class="eyebrow">{e(T(lang, "hero_eyebrow"))}</div>
    <h1>{e(T(lang, "hero_h1a"))}<br><em>{e(T(lang, "hero_h1b"))}</em></h1>
    <p>{e(T(lang, "hero_p"))}</p>
    <div class="ctas">
      <a class="btn btn-coral" href="#collectie">{e(T(lang, "hero_cta1"))}</a>
      {wa_button(wa(T(lang, "wa_general")), T(lang, "hero_cta2"))}
    </div>
  </div>
  <div class="hero-visual">
    <img src="/img/hero.webp" alt="" width="800" height="1000" fetchpriority="high">
    <span class="badge b1">{e(T(lang, "hero_badge1"))}</span>
    <span class="badge b2">{T(lang, "hero_badge2", lead=e(lead(lang)))}</span>
  </div>
</div></header>
<div class="trust"><div class="wrap">
  {"".join(f"<div><b>{e(F(lang, a))}</b>{e(F(lang, b))}</div>" for a, b in TXT[lang]["trust"])}
</div></div>
"""
    if has_fav:
        out += '<div id="favorieten">\n'
        for key, slugs in lists.items():
            if not slugs:
                continue
            hid = "" if key == cur else " hidden"
            cards = "".join(card(lang, BY_SLUG[s], fav=True, halloween=(key == "halloween" and s in CAT["featured"]["halloween_badge"])) for s in slugs)
            out += f"""<section data-fav="{key}"{hid}><div class="wrap">
  <div class="head"><div><div class="eyebrow">{e(T(lang, "fav_label"))}</div><h2>{e(T(lang, "fav_title"))}</h2></div><p>{e(T(lang, "fav_sub"))}</p></div>
  <div class="grid">{cards}</div>
  <div class="center"><a class="btn btn-ghost" href="#collectie">{e(T(lang, "fav_all", n=n))}</a></div>
</div></section>
"""
        out += "</div>\n"

    if KITEMS:
        groups = ""
        for c in KERST["categories"]:
            items = [m for m in KITEMS if m["collection"] == c["key"]]
            if items:
                groups += (f'<h3 class="kerst-cat">{e(c["name"][lang])}</h3><p class="kerst-tag">{e(c["tagline"][lang])}</p>'
                           f'<div class="grid">{"".join(card(lang, m) for m in items)}</div>')
        hid = "" if SEASON == "kerst" else " hidden"
        out += f"""<section id="kerst" class="kerst" data-season="kerst"{hid}><div class="wrap">
  <div class="head"><div><div class="eyebrow">{e(T(lang, "kerst_label"))}</div><h2>{e(T(lang, "kerst_title"))}</h2></div><p>{e(T(lang, "kerst_sub"))}</p></div>
  {groups}
</div></section>
"""

    chips = f'<button class="chip" type="button" data-filter="all" data-intro="" aria-pressed="true">{e(T(lang, "filter_all"))}<small>{n}</small></button>'
    for c in CAT["collections"]:
        cnt = sum(1 for m in MODELS if m["collection"] == c["key"])
        chips += (f'<button class="chip" type="button" data-filter="{c["key"]}" data-intro="{e(c["tagline"][lang])}" aria-pressed="false">'
                  f'{e(c["name"][lang])}<small>{cnt}</small></button>')
    cards = "".join(card(lang, m) for m in MODELS)
    steps = "".join(f'<div class="step"><div class="num">{i}</div><h3>{e(a)}</h3><p>{e(F(lang, b))}</p></div>'
                    for i, (a, b) in enumerate(TXT[lang]["steps"], 1))
    faq = ""
    for q, a in TXT[lang]["faq"]:
        a = F(lang, a)
        if "{shipping_table}" in a:
            faq += f'<details id="levering"><summary>{e(q)}</summary><p>{e(a.replace("{shipping_table}", ""))}</p>{shipping_table(lang)}<p>{e(T(lang, "ship_note"))}</p></details>'
        else:
            faq += f"<details><summary>{e(q)}</summary><p>{e(a)}</p></details>"
    out += f"""<section id="collectie"{' class="alt"' if has_fav else ''}><div class="wrap">
  <div class="head"><div><div class="eyebrow">{e(T(lang, "cat_label"))}</div><h2>{e(T(lang, "cat_title"))}</h2></div><p>{e(T(lang, "cat_sub", n=n))}</p></div>
  <div class="chips" role="group" aria-label="{e(T(lang, "filter_label"))}">{chips}</div>
  <p class="col-intro" aria-live="polite"></p>
  <div class="grid" id="catalog">{cards}</div>
</div></section>
<section id="hoe"{'' if has_fav else ' class="alt"'}><div class="wrap">
  <div class="head"><div><div class="eyebrow">{e(T(lang, "how_label"))}</div><h2>{e(T(lang, "how_title"))}</h2></div></div>
  <div class="steps">{steps}</div>
</div></section>
<section id="opmaat" style="padding-top:0"><div class="wrap split">
  <div class="panel">
    <div class="eyebrow">{e(T(lang, "custom_label"))}</div>
    <h2>{e(T(lang, "custom_title"))}</h2>
    <p>{e(T(lang, "custom_p"))}</p>
    {wa_button(wa(T(lang, "wa_custom")), T(lang, "custom_btn"))}
  </div>
  <div class="panel">
    <div class="eyebrow">{e(T(lang, "about_label"))}</div>
    <h2>{e(T(lang, "about_title"))}</h2>
    <p>{e(T(lang, "about_p"))}</p>
  </div>
</div></section>
<section id="faq" style="padding-top:0"><div class="wrap faq">
  <div class="head"><div><div class="eyebrow">{e(T(lang, "faq_label"))}</div><h2>{e(T(lang, "faq_title"))}</h2></div></div>
  {faq}
</div></section>
</main>
"""
    return out + footer(lang)


def product(lang, m):
    col = COLS[m["collection"]]
    path = m["slug"] + "/"
    plain = "" if m.get("knitted", True) else "_plain"
    out = head(lang, T(lang, "meta_title_product" + plain, name=nm(m, lang)), T(lang, "meta_desc_product" + plain, name=nm(m, lang), heights=heights(lang, m)), path, img(m, 0))
    out += topbar(lang, False) + nav(lang, path, False, any(featured(k) for k in ("halloween", "default")))

    photos = m["photos"]
    thumbs = ""
    if len(photos) > 1:
        thumbs = '<div class="thumbs">' + "".join(
            f'<button type="button" data-src="{img(m, i)}" data-alt="{e(T(lang, "p_photo", name=nm(m, lang), i=i + 1))}" aria-current="{"true" if i == 0 else "false"}" aria-label="{e(T(lang, "p_photo", name=nm(m, lang), i=i + 1))}">'
            f'<img src="{img(m, i, True)}" alt="" width="{THUMB}" height="{THUMB}" loading="lazy"></button>'
            for i in range(len(photos))) + "</div>"
    tagline = m.get("tagline", {}).get(lang)
    colors_fig = ""
    if m.get("colors", {}).get("image"):
        colors_fig = (f'<figure class="color-chart"><a href="{colors_img(m)}" target="_blank" rel="noopener">'
                      f'<img src="{colors_img(m)}" alt="{e(T(lang, "p_color") + ": " + ", ".join(cname(c, lang) for c in m["colors"]["options"]))}" loading="lazy"></a>'
                      f'<figcaption>{e(T(lang, "p_colors_caption"))}</figcaption></figure>')
    if sizes(m):
        opts = "".join(
            f'<div class="size-opt"><div class="sz"><b>{e(size_name(lang, s))}</b><span>{e(T(lang, "size", cm=num(lang, s["cm"]))) if s.get("cm") else ""}</span></div>'
            f'<div class="sp">{e(price_text(lang, s["price"]))}</div>{wa_button(wa_order(lang, m, s), T(lang, "order_short"), "btn-sm", order_msg(lang, m, s), page_link(lang, m))}</div>'
            for s in sizes(m))
        order = f'<h2 class="choose">{e(T(lang, "p_choose" if len(sizes(m)) > 1 else "p_order_one"))}</h2><div class="sizes">{opts}</div>'
        if m.get("colors"):
            chips = "".join(
                f'<label class="color-chip"><input type="radio" name="kleur" value="{e(cname(c, lang))}"'
                + (f' data-img="{color_img(m, i)}" data-alt="{e(nm(m, lang) + " · " + cname(c, lang))}"' if has_color_img(m, i) else "")
                + f'><span>{e(cname(c, lang))}</span></label>'
                for i, c in enumerate(m["colors"]["options"]))
            order = (f'<h2 class="choose">{e(T(lang, "p_color"))}</h2>'
                     f'<div class="colors" data-tpl="{e(T(lang, "wa_color", c="{c}"))}" data-wa="https://wa.me/{SITE["whatsapp"]}?text=">{chips}</div>'
                     f'<p class="color-hint">{e(T(lang, "p_color_hint" if m["colors"].get("image") else "p_color_hint_plain"))}</p>' + order)
    else:
        order = (f'<p class="big-price ask">{e(T(lang, "price_on_request"))}</p>'
                 + wa_button(wa_order(lang, m), T(lang, "ask_btn"), "btn-block"))
    tag = f' <span class="tag flexi" style="position:static;vertical-align:middle">{e(T(lang, "badge_flexi"))}</span>' if m.get("badge") == "flexi" else ""

    kerst = m in KITEMS
    same = [x for x in ALL if x["collection"] == m["collection"]]
    k = same.index(m)
    related = [same[(k + j) % len(same)] for j in range(1, min(5, len(same)))]

    related_html = ""
    if related:
        related_html = f"""<section class="alt"><div class="wrap">
  <div class="head"><div><h2>{e(T(lang, "p_related", collection=col["name"][lang]))}</h2></div><p><a class="btn btn-ghost btn-sm" href="{url(lang)}{"#kerst" if kerst else "#collectie"}">{e(T(lang, "p_back"))}</a></p></div>
  <div class="grid">{"".join(card(lang, x) for x in related)}</div>
</div></section>"""
    out += f"""<main id="inhoud">
<div class="wrap crumbs"><a href="{url(lang)}">{e(T(lang, "p_home"))}</a> › <a href="{url(lang) + ("#kerst" if kerst else "?c=" + col["key"] + "#collectie")}">{e(col["name"][lang])}</a> › {e(nm(m, lang))}</div>
<section class="product"><div class="wrap">
  <div class="gallery">
    <div class="main"><img src="{img(m, 0)}" alt="{e(T(lang, "p_photo", name=nm(m, lang), i=1))}" width="1200" height="1200" fetchpriority="high"></div>
    {thumbs}
    <p class="notice">{e(T(lang, "p_notice"))}</p>
    {colors_fig}
  </div>
  <div class="pinfo">
    <div class="eyebrow">{e(col["name"][lang])}{tag}</div>
    <h1>{e(nm(m, lang))}</h1>
    {f'<p class="tagline">{e(tagline)}</p>' if tagline else ''}
    <p class="desc">{e(T(lang, "p_desc_kerst" if kerst else ("p_desc" if m.get("knitted", True) else "p_desc_plain"), name=nm(m, lang), collection=col["name"][lang]))}</p>
    {f'<p class="pnote">{e(m["note"][lang])}</p>' if m.get("note") else ""}
    {order}
    <ul class="facts">
      {f'<li><span>{e(T(lang, "p_contents"))}</span>{e(m["contents"][lang])}</li>' if m.get("contents") else ""}
      <li><span>{e(T(lang, "p_finish"))}</span>{e(T(lang, "p_finish_kerst" if kerst else ("p_finish_val" if m.get("knitted", True) else "p_finish_plain")))}</li>
      <li><span>{e(T(lang, "p_lead"))}</span>{e(lead(lang))}</li>
      <li><span>{e(T(lang, "p_delivery"))}</span><div>{e(T(lang, "p_delivery_val"))}<br><a class="more" href="{url(lang)}#levering">{e(T(lang, "p_shipping_link"))} →</a></div></li>
    </ul>
    <p class="bigger">{e(T(lang, "p_bigger"))} <a href="{e(wa(with_link(T(lang, "wa_bigger", name=nm(m, lang)), lang, m)))}" target="_blank" rel="noopener">{e(T(lang, "p_bigger_link"))}</a></p>
  </div>
</div></section>
{related_html}
</main>
"""
    return out + footer(lang)


def not_found():
    lang = "nl"
    out = head(lang, "popzu · 404", T(lang, "nf_title"), "")
    out += nav(lang, "", False, False)
    out += f"""<main id="inhoud" class="nf"><div class="wrap">
  <div class="eyebrow">404</div>
  <h1>{e(T(lang, "nf_title"))}</h1>
  <p>{e(T(lang, "nf_p"))}</p>
  <a class="btn btn-coral" href="/#collectie">{e(T(lang, "nf_btn"))}</a>
</div></main>
"""
    return out + footer(lang)


# ---------- images ----------

def build_images():
    try:
        from PIL import Image
    except ImportError:
        Image = None
        WARN.append("Pillow não instalado: miniaturas copiadas no tamanho original (pip install pillow).")
    src_root = ROOT / "images"

    def put(src, dst, size=None):
        if dst.exists() and dst.stat().st_mtime >= src.stat().st_mtime:
            return
        dst.parent.mkdir(parents=True, exist_ok=True)
        if size and Image:
            with Image.open(src) as im:
                im.thumbnail((size, size), Image.LANCZOS)
                im.save(dst, "WEBP", quality=78, method=6)
        else:
            shutil.copy2(src, dst)

    for m in ALL:
        for i, name in enumerate(m["photos"]):
            src = src_root / m["slug"] / name
            if not src.exists():
                WARN.append(f"Foto não encontrada: {src}")
                continue
            put(src, OUT / img(m, i).lstrip("/"))
            put(src, OUT / img(m, i, True).lstrip("/"), THUMB)
        if m.get("colors"):
            chart = m["colors"].get("image")
            if chart:
                src = src_root / m["slug"] / chart
                if src.exists():
                    put(src, OUT / colors_img(m).lstrip("/"))
                else:
                    WARN.append(f"Imagem de cores não encontrada: {src}")
            # Uma foto por cor (tools/color_crops.py ou tools/import_sabre.py). Sem foto, a cor só entra na mensagem.
            for i in range(len(m["colors"]["options"])):
                src = src_root / m["slug"] / f'{m["slug"]}-cor-{i + 1:02d}.webp'
                if src.exists():
                    put(src, OUT / color_img(m, i).lstrip("/"))
                elif chart:
                    WARN.append(f"Foto da cor não encontrada: {src} (rode tools/color_crops.py)")
    hero = src_root / SITE["hero_photo"]
    if Image:
        dst = OUT / "img" / "hero.webp"
        if not dst.exists() or dst.stat().st_mtime < hero.stat().st_mtime:
            with Image.open(hero) as im:
                w, h = im.size
                tw = int(h * 4 / 5)
                im = im.crop(((w - tw) // 2, 0, (w - tw) // 2 + tw, h)) if tw < w else im
                im.thumbnail((800, 1000), Image.LANCZOS)
                dst.parent.mkdir(parents=True, exist_ok=True)
                im.save(dst, "WEBP", quality=80, method=6)
    else:
        put(hero, OUT / "img" / "hero.webp")


# ---------- main ----------

def clean_stale():
    """Remove páginas e fotos de modelos que saíram do catálogo."""
    keep = set(BY_SLUG)
    for base in [OUT] + [OUT / l for l in LANGS if l != "nl"]:
        if not base.exists():
            continue
        for d in base.iterdir():
            if d.is_dir() and (d / "index.html").exists() and d.name not in keep and d.name not in LANGS:
                shutil.rmtree(d)
                WARN.append(f"Removido (fora do catálogo): {d.relative_to(OUT)}/")
    imgs = OUT / "img"
    if imgs.exists():
        for d in imgs.iterdir():
            if d.is_dir() and d.name not in keep:
                shutil.rmtree(d)


_HASH = {}


def versioned(content):
    """Acrescenta ?v=<hash do arquivo> a /img/... e /assets/..., para o navegador baixar a versão nova
    quando um arquivo muda sem mudar de nome (as fotos ficam 7 dias em cache, veja netlify.toml)."""
    import hashlib
    import re

    def add(mt):
        path = mt.group(1)
        if path not in _HASH:
            f = OUT / path.lstrip("/")
            _HASH[path] = hashlib.md5(f.read_bytes()).hexdigest()[:8] if f.exists() else ""
        return f'"{path}?v={_HASH[path]}"' if _HASH[path] else mt.group(0)

    return re.sub(r'"(/(?:img|assets)/[^"?#]+)"', add, content)


def write(path, content):
    if path.endswith(".html"):
        content = versioned(content)
    p = OUT / path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    for m in ALL:
        if m["collection"] not in COLS:
            sys.exit(f"Coleção desconhecida em {m['slug']}: {m['collection']}")
    for k in ("halloween", "default"):
        if not featured(k):
            WARN.append(f"Destaques ({k}): nenhum modelo com preço, seção escondida.")
        elif len(featured(k)) < len(CAT["featured"]["list"]):
            WARN.append(f"Destaques ({k}): só {len(featured(k))} modelos com preço.")
    missing = sum(1 for m in MODELS if not sizes(m))
    if missing:
        WARN.append(f"{missing} de {len(MODELS)} modelos sem preço ('Prijs op aanvraag').")
    for key in ("instagram", "email", "base_url"):
        if not SITE.get(key):
            WARN.append(f"site.json: '{key}' vazio.")
    for key, v in SITE["legal"].items():
        if not v:
            WARN.append(f"site.json: legal.{key} vazio (oculto no site; 'nog in te vullen' no preview).")

    OUT.mkdir(exist_ok=True)
    clean_stale()
    build_images()
    (OUT / "assets").mkdir(exist_ok=True)
    for f in ("site.css", "site.js"):
        shutil.copy2(ROOT / "src" / f, OUT / "assets" / f)
    shutil.copy2(ROOT / "logo" / "selo-fundo-escuro.svg", OUT / "assets" / "logo.svg")
    for lang in LANGS:
        pre = "" if lang == "nl" else lang + "/"
        write(pre + "index.html", home(lang))
        for m in ALL:
            write(pre + m["slug"] + "/index.html", product(lang, m))
    write("404.html", not_found())
    (OUT / "assets").mkdir(exist_ok=True)
    for f in ("site.css", "site.js"):
        shutil.copy2(ROOT / "src" / f, OUT / "assets" / f)
    # Logo e ícones da pasta logo/ (fornecidos pelo dono).
    for src, dst in (("selo-fundo-escuro.svg", "assets/logo.svg"), ("favicon-32.png", "favicon-32.png"),
                     ("icone-180.png", "apple-touch-icon.png")):
        shutil.copy2(ROOT / "logo" / src, OUT / dst)
    for old in ("favicon.svg",):
        (OUT / old).unlink(missing_ok=True)
    base = (SITE.get("base_url") or "").rstrip("/")
    if base:
        urls = [url(l, p) for l in LANGS for p in [""] + [m["slug"] + "/" for m in ALL]]
        write("sitemap.xml", '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
              + "".join(f"<url><loc>{base}{u}</loc></url>\n" for u in urls) + "</urlset>\n")
        write("robots.txt", f"User-agent: *\nAllow: /\nSitemap: {base}/sitemap.xml\n")
    else:
        write("robots.txt", "User-agent: *\nAllow: /\n")

    pages = len(LANGS) * (len(ALL) + 1) + 1
    print(f"OK: {pages} páginas em {OUT.name}/ (estação de hoje: {SEASON}{', modo preview' if PREVIEW else ''})")
    for w in WARN:
        print("  aviso:", w)


if __name__ == "__main__":
    main()
