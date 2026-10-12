"""Recorta cada variação de cor do quadro modelos.png do Whale.

Gera images/<slug>/<slug>-cor-NN.webp (quadrado, fundo completado com a cor da borda).
Uso: python tools/color_crops.py             -> gera os recortes (ou: python tools/color_crops.py "Baby Werewolf")
     python tools/color_crops.py --debug DIR -> desenha a grade sobre cada quadro em DIR
Cada grade: lista de linhas (y0, y1, x0, x1, colunas), em frações da imagem.
"""
import sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageStat

SRC = Path(r"G:\3D\Arquivos de impressão\Patreon\Whale 3D\Originais")
ROOT = Path(__file__).resolve().parent.parent
SIZE = 800

GRIDS = {
    "Alien":              [(0.26, 0.89, 0.02, 0.98, 6)],
    "Alien Baby":         [(0.07, 0.48, 0.01, 0.99, 4), (0.52, 0.93, 0.01, 0.99, 4)],
    "Alien Women":        [(0.00, 0.48, 0.10, 0.90, 4), (0.50, 0.98, 0.10, 0.90, 4)],
    "Baby Brachiosaurus": [(0.02, 0.46, 0.02, 0.98, 4), (0.52, 0.94, 0.02, 0.98, 4)],
    "Baby Reaper":        [(0.31, 0.525, 0.00, 1.00, 5), (0.58, 0.795, 0.00, 1.00, 5)],
    "Baby Spinosaurus":   [(0.16, 0.42, 0.00, 1.00, 5), (0.55, 0.84, 0.00, 1.00, 5)],
    "Baby T-Rex":         [(0.12, 0.51, 0.08, 0.95, 4), (0.565, 0.94, 0.08, 0.95, 4)],
    "Baby Vampire":       [(0.15, 0.82, 0.00, 1.00, 5)],
    "Pumpboo":            [(0.165, 0.385, 0.08, 0.92, 3), (0.46, 0.70, 0.08, 0.92, 3), (0.735, 0.965, 0.08, 0.92, 3)],
}

# Modelos com caixas explícitas (quadros com legenda ou bolinhas ao lado da figura) e/ou mais de um quadro.
# Cada caixa: (arquivo, x0, y0, x1, y1) em frações. A ordem é a ordem das cores em catalog.json.
def _werewolf():
    out = []
    for f in ("modelos.png", "modelos 1.png"):
        for y0, y1 in ((0.12, 0.50), (0.55, 0.935)):
            for x0 in (0.04, 0.36, 0.68):
                out.append((f, x0, y0, x0 + 0.24, y1))
    return out


def _mermaid():  # quadro novo (12/10/2026), com textura de tricô
    return [("modelos.png", x0, y0, x1, y1) for y0, y1 in ((0.04, 0.432), (0.548, 0.89))
            for x0, x1 in ((0.12, 0.40), (0.40, 0.69), (0.69, 0.98))]


BOXES = {"Baby Werewolf": _werewolf(), "Baby Mermaid": _mermaid()}

# Áreas do quadro pintadas com a cor do fundo antes de recortar (títulos que encostam nas figuras).
MASK = {"Baby Mermaid": [(0.30, 0.0, 0.70, 0.11)]}

# Cor extra que não está no quadro (a versão das fotos): número da cor -> foto do modelo.
# Os recortes do quadro começam depois dela.
FIRST_PHOTO = {"Baby Werewolf": "baby-werewolf-16.webp"}

# Ajuste da borda de cima de uma célula (número da cor, 1 = primeira), para fugir de títulos.
TOP = {}

# Cores em que o quadro não dá um recorte limpo (texto por cima): usa uma foto do modelo em images/<slug>/.
PHOTO = {("Baby T-Rex", 1): "baby-t-rex-14.webp"}


def cells(name, im):
    w, h = im.size
    k = 0
    for y0, y1, x0, x1, n in GRIDS[name]:
        step = (x1 - x0) / n
        for i in range(n):
            k += 1
            top = TOP.get((name, k), y0)
            yield (int((x0 + i * step) * w), int(top * h), int((x0 + (i + 1) * step) * w), int(y1 * h))


def square(crop):
    w, h = crop.size
    edge = [crop.crop((0, 0, w, 3)), crop.crop((0, h - 3, w, h)), crop.crop((0, 0, 3, h)), crop.crop((w - 3, 0, w, h))]
    bg = tuple(int(sum(ImageStat.Stat(e).median[i] for e in edge) / 4) for i in range(3))
    side = max(w, h)
    out = Image.new("RGB", (side, side), bg)
    out.paste(crop, ((side - w) // 2, (side - h) // 2))
    return out.resize((SIZE, SIZE), Image.LANCZOS) if side > SIZE else out


def slug(name):
    return name.lower().replace(" ", "-")


def save_square(src_img, out, zoom=False):
    if zoom:
        w, h = src_img.size
        src_img = src_img.crop((int(w * 0.2), int(h * 0.15), int(w * 0.8), int(h * 0.85)))
    square(src_img.convert("RGB")).save(out, "WEBP", quality=84, method=6)


def boxes_model(name, debug_dir):
    folder = ROOT / "images" / slug(name)
    k = 0
    if name in FIRST_PHOTO:
        k += 1
        with Image.open(folder / FIRST_PHOTO[name]) as ph:
            save_square(ph, folder / f"{slug(name)}-cor-{k:02d}.webp", zoom=True)
    charts, originals = {}, {}
    for f, x0, y0, x1, y1 in BOXES[name]:
        if f not in charts:
            originals[f] = Image.open(SRC / name / "Photo" / f).convert("RGB")
            charts[f] = originals[f].copy()
            for mx0, my0, mx1, my1 in MASK.get(name, []):
                cw, ch = charts[f].size
                box = (int(mx0 * cw), int(my0 * ch), int(mx1 * cw), int(my1 * ch))
                below = charts[f].crop((box[0], box[3], box[2], box[3] + 6))
                bg = tuple(int(v) for v in ImageStat.Stat(below).median)
                ImageDraw.Draw(charts[f]).rectangle(box, fill=bg)
        im = charts[f]
        w, h = im.size
        box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
        k += 1
        if debug_dir:
            ImageDraw.Draw(im).rectangle(box, outline=(255, 0, 0), width=6)
        else:
            square(im.crop(box)).save(folder / f"{slug(name)}-cor-{k:02d}.webp", "WEBP", quality=84, method=6)
    # Quadro de cores do site: os quadros originais (sem máscara), empilhados.
    ims = list(charts.values()) if debug_dir else list(originals.values())
    stacked = Image.new("RGB", (max(i.width for i in ims), sum(i.height for i in ims)), "white")
    y = 0
    for i in ims:
        stacked.paste(i, (0, y))
        y += i.height
    if debug_dir:
        stacked.thumbnail((900, 1800))
        stacked.save(debug_dir / f"grid-{slug(name)}.jpg", quality=80)
    else:
        stacked.thumbnail((1600, 3200))
        stacked.save(folder / f"{slug(name)}-cores.webp", "WEBP", quality=84, method=6)
    print(name, k, "cores")


def main():
    debug_dir = Path(sys.argv[sys.argv.index("--debug") + 1]) if "--debug" in sys.argv else None
    only = [a for a in sys.argv[1:] if a in GRIDS or a in BOXES]
    for name in BOXES:
        if not only or name in only:
            boxes_model(name, debug_dir)
    for name in GRIDS:
        if only and name not in only:
            continue
        chart = next((SRC / name / "Photo" / f for f in ("modelos.png", "modelo.png") if (SRC / name / "Photo" / f).exists()),
                     SRC / name / "Photo" / "modelos.png")
        if not chart.exists():
            print(f"{name}: quadro não encontrado ({chart}), recortes existentes mantidos")
            continue
        im = Image.open(chart).convert("RGB")
        boxes = list(cells(name, im))
        if debug_dir:
            d = ImageDraw.Draw(im)
            for k, b in enumerate(boxes, 1):
                d.rectangle(b, outline=(255, 0, 0), width=6)
                d.text((b[0] + 10, b[1] + 10), str(k), fill=(255, 0, 0))
            im.thumbnail((900, 900))
            im.save(debug_dir / f"grid-{slug(name)}.jpg", quality=80)
            continue
        folder = ROOT / "images" / slug(name)
        for k, b in enumerate(boxes, 1):
            out = folder / f"{slug(name)}-cor-{k:02d}.webp"
            if (name, k) in PHOTO:
                with Image.open(folder / PHOTO[(name, k)]) as ph:
                    w, h = ph.size  # aproxima no centro, como nos recortes do quadro
                    ph = ph.convert("RGB").crop((int(w * 0.2), int(h * 0.15), int(w * 0.8), int(h * 0.85)))
                    square(ph).save(out, "WEBP", quality=84, method=6)
            else:
                square(im.crop(b)).save(out, "WEBP", quality=84, method=6)
        print(name, len(boxes), "recortes")


if __name__ == "__main__":
    main()
