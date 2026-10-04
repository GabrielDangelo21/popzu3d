"""Converte as fotos dos modelos do Whale (pasta Originais) para images/<slug>/ em WebP, até 1200 px.
Ignora GIFs, guias de montagem, 3MF e PDF. Gera images/manifest.csv com a origem de cada foto."""
import csv, re, sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from PIL import Image, ImageOps

SRC = Path(r"G:\3D\Arquivos de impressão\Patreon\Whale 3D\Originais")
DST = Path(r"G:\Popzu\Site\images")
MAX = 1200
EXTS = {".jpg", ".jpeg", ".png", ".webp"}

def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")

def convert(job):
    src, dst = job
    try:
        with Image.open(src) as im:
            im = ImageOps.exif_transpose(im)
            im.thumbnail((MAX, MAX), Image.LANCZOS)
            if im.mode not in ("RGB", "RGBA"):
                im = im.convert("RGBA" if "A" in im.getbands() or im.mode == "P" else "RGB")
            w, h = im.size
            im.save(dst, "WEBP", quality=80, method=6)
        return (str(src), str(dst), w, h, "")
    except Exception as e:
        return (str(src), str(dst), 0, 0, repr(e))

def main():
    jobs = []
    for model in sorted(p for p in SRC.iterdir() if p.is_dir()):
        photo = model / "Photo"
        files = sorted(
            f for f in photo.rglob("*")
            if f.is_file() and f.suffix.lower() in EXTS
            and "assembly guide" not in str(f.relative_to(photo)).lower()
        )
        out = DST / slug(model.name)
        out.mkdir(parents=True, exist_ok=True)
        for i, f in enumerate(files, 1):
            jobs.append((f, out / f"{slug(model.name)}-{i:02d}.webp"))
    with ProcessPoolExecutor() as ex:
        rows = list(ex.map(convert, jobs, chunksize=4))
    with open(DST / "manifest.csv", "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(["origem", "destino", "largura", "altura", "erro"])
        for r in rows:
            w.writerow([r[0], str(Path(r[1]).relative_to(DST.parent)).replace("\\", "/"), *r[2:]])
    errs = [r for r in rows if r[4]]
    print(f"{len(rows)} imagens, {len(errs)} erros")
    for r in errs:
        print(r)

if __name__ == "__main__":
    main()
