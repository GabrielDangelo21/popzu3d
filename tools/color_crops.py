"""Recorta cada variação de cor do quadro modelos.png do Whale.

Gera images/<slug>/<slug>-cor-NN.webp (quadrado, fundo completado com a cor da borda).
Uso: python tools/color_crops.py             -> gera os recortes
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
    "Baby Mermaid":       [(0.04, 0.41, 0.07, 0.93, 3), (0.50, 0.905, 0.07, 0.93, 3)],
    "Baby Reaper":        [(0.31, 0.525, 0.00, 1.00, 5), (0.58, 0.795, 0.00, 1.00, 5)],
    "Baby Spinosaurus":   [(0.16, 0.42, 0.00, 1.00, 5), (0.55, 0.84, 0.00, 1.00, 5)],
    "Baby T-Rex":         [(0.12, 0.51, 0.08, 0.95, 4), (0.565, 0.94, 0.08, 0.95, 4)],
    "Baby Vampire":       [(0.15, 0.82, 0.00, 1.00, 5)],
    "Pumpboo":            [(0.165, 0.385, 0.08, 0.92, 3), (0.46, 0.70, 0.08, 0.92, 3), (0.735, 0.965, 0.08, 0.92, 3)],
}

# Ajuste da borda de cima de uma célula (número da cor, 1 = primeira), para fugir de títulos.
TOP = {("Baby Mermaid", 2): 0.15, ("Baby Mermaid", 5): 0.535}

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


def main():
    debug_dir = Path(sys.argv[sys.argv.index("--debug") + 1]) if "--debug" in sys.argv else None
    for name in GRIDS:
        im = Image.open(SRC / name / "Photo" / "modelos.png").convert("RGB")
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
