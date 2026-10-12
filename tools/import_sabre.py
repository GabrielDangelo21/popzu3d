"""Importa a coleção de Natal (Sabre Design, MakerWorld) para data/catalog.json -> kerst.items.

Lê preços (com IVA) e alturas da aba "Sabre Design" de Catalogo_Precos_Tamanho.xlsx,
copia as fotos escolhidas para images/<slug>/ e gera uma foto por cor (<slug>-cor-NN.webp)
quando existe uma foto daquela cor. Uso: python tools/import_sabre.py
"""
import json
from pathlib import Path

import openpyxl
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
SRC = Path(r"G:\3D\Arquivos de impressão\Patreon\Sabre Design")
XLSX = ROOT / "Catalogo_Precos_Tamanho.xlsx"


def L(nl, fr, en):
    return {"nl": nl, "fr": fr, "en": en}


RED, GREEN, BEIGE = L("Rood", "Rouge", "Red"), L("Groen", "Vert", "Green"), L("Beige", "Beige", "Beige")

# Todos os preços são por unidade, mesmo quando a foto mostra várias peças (confirmado pelo dono em 12/10/2026).
ONE_SIZE = L("Per stuk", "À l'unité", "Per piece")
NO_LED = L("Wordt geleverd zonder ledlichtje.", "Livré sans bougie LED.", "Supplied without LED light.")

# Linha da planilha (nº) -> dados do site. photos: posição (1 = primeira) das fotos da pasta, já ordenadas por nome;
# a primeira é a capa. Fotos com LED aceso ficaram de fora (a luz não vem junto).
# color_photos: foto de cada cor, na ordem de colors (None = não há foto só daquela cor).
ITEMS = [
    dict(row=1, folder="Enfeite arvore de natal", slug="kerstboomhanger", collection="kerst-hangers",
         name=L("Kerstboomhanger", "Suspension sapin", "Christmas tree ornament"),
         photos=[4, 1, 2, 3], colors=[RED, GREEN, BEIGE], color_photos=[1, 3, 2]),
    dict(row=6, folder="Sino de Natal Funcional", slug="kerstklokje", collection="kerst-hangers",
         name=L("Kerstklokje", "Clochette de Noël", "Christmas bell"),
         tagline=L("Een klokje dat echt rinkelt.", "Une clochette qui tinte vraiment.", "A little bell that really rings."),
         photos=[4, 1, 3, 2], colors=[RED, GREEN, BEIGE], color_photos=[1, None, 3]),
    dict(row=5, folder="Bola de Natal Japandi", slug="japandi-kerstbal", collection="kerst-hangers",
         name=L("Japandi-kerstbal", "Boule de Noël japandi", "Japandi bauble"),
         photos=[1, 2, 3], colors=[RED, GREEN, BEIGE], color_photos=[2, None, 3]),
    dict(row=9, folder="Bolas pontudas", slug="druppelhanger", collection="kerst-hangers",
         name=L("Druppelhanger", "Suspension goutte", "Drop ornament"),
         photos=[2, 1, 3], colors=[RED, GREEN, BEIGE], color_photos=[None, None, None]),
    dict(row=2, folder="Quebra Nozes", slug="notenkraker", collection="kerst-tafel",
         name=L("Notenkraker", "Casse-noisette", "Nutcracker"),
         photos=[3, 1, 2, 5, 4], colors=[RED, GREEN, BEIGE], color_photos=[1, 2, None]),
    dict(row=3, folder="Renas Natalinas", slug="rendier", collection="kerst-tafel",
         name=L("Rendier", "Renne", "Reindeer"),
         photos=[1, 3, 4, 2], colors=[RED, GREEN, BEIGE], color_photos=[2, None, None]),
    dict(row=4, folder="Árvores Nórdicas", slug="noords-kerstboompje", collection="kerst-tafel",
         name=L("Noords kerstboompje", "Sapin nordique", "Nordic Christmas tree"),
         photos=[4, 2, 3, 1], colors=[RED, GREEN], color_photos=[3, 2]),
    dict(row=7, folder="Papai Noel", slug="kerstman", collection="kerst-tafel",
         name=L("Kerstman", "Père Noël", "Santa"), photos=[2, 1], note=NO_LED),
    dict(row=8, folder="Boneco de neve", slug="sneeuwman", collection="kerst-tafel",
         name=L("Sneeuwman", "Bonhomme de neige", "Snowman"), photos=[4, 3, 2], note=NO_LED),
    dict(row=10, folder="Gnomos", slug="kerstkabouter", collection="kerst-tafel",
         name=L("Kerstkabouter", "Gnome de Noël", "Christmas gnome"), photos=[2, 3, 1]),
]



def save(src, dst, square=False):
    with Image.open(src) as im:
        im = im.convert("RGB")
        if square:
            w, h = im.size
            s = min(w, h)
            im = im.crop(((w - s) // 2, (h - s) // 2, (w + s) // 2, (h + s) // 2))
        im.thumbnail((1200, 1200), Image.LANCZOS)
        im.save(dst, "WEBP", quality=84, method=6)


def main():
    ws = openpyxl.load_workbook(XLSX, data_only=True)["Sabre Design"]
    rows = {r[0]: r for r in ws.iter_rows(values_only=True) if isinstance(r[0], int)}
    items = []
    for it in ITEMS:
        _, sheet_name, _, price, cm = rows[it["row"]]
        files = sorted((SRC / it["folder"]).glob("*.webp"))
        out = ROOT / "images" / it["slug"]
        out.mkdir(parents=True, exist_ok=True)
        photos = []
        for k, n in enumerate(it["photos"], 1):
            name = f'{it["slug"]}-{k:02d}.webp'
            save(files[n - 1], out / name)
            photos.append(name)
        for k, n in enumerate(it.get("color_photos", []), 1):
            dst = out / f'{it["slug"]}-cor-{k:02d}.webp'
            if n:
                save(files[n - 1], dst, square=True)
            elif dst.exists():
                dst.unlink()
        item = {"slug": it["slug"], "name": it["name"], "collection": it["collection"], "photos": photos,
                "sizes": [{"key": "u", "label": ONE_SIZE, "cm": cm, "price": price}], "source": sheet_name}
        if it.get("tagline"):
            item["tagline"] = it["tagline"]
        if it.get("note"):
            item["note"] = it["note"]
        if it.get("colors"):
            item["colors"] = {"options": it["colors"]}
        items.append(item)
        print(f'{it["slug"]:22s} {cm:>5} cm  € {price}')
    p = ROOT / "data" / "catalog.json"
    cat = json.loads(p.read_text(encoding="utf-8"))
    cat["kerst"]["items"] = items
    p.write_text(json.dumps(cat, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
