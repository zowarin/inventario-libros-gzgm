"""
Reduce el tamano/peso de las imagenes en rotadas/ y las copia a
front-invetario-ng/public/ manteniendo la estructura de carpetas (caja-1, caja-2, ...).

Uso:
    python scripts/optimizar_imagenes.py
    python scripts/optimizar_imagenes.py --max-dimension 1600 --quality 80
    python scripts/optimizar_imagenes.py --origen rotadas --destino front-invetario-ng/public/rotadas
"""

import argparse
from pathlib import Path

from PIL import Image, ImageOps

EXTENSIONES_VALIDAS = {".jpg", ".jpeg", ".png", ".webp"}


def procesar_imagen(origen: Path, destino: Path, max_dimension: int, quality: int) -> tuple[int, int]:
    with Image.open(origen) as img:
        img = ImageOps.exif_transpose(img)  # respeta la orientacion EXIF antes de reescalar

        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        ancho, alto = img.size
        if max(ancho, alto) > max_dimension:
            ratio = max_dimension / max(ancho, alto)
            nuevo_tamano = (round(ancho * ratio), round(alto * ratio))
            img = img.resize(nuevo_tamano, Image.LANCZOS)

        destino.parent.mkdir(parents=True, exist_ok=True)
        img.save(destino, format="JPEG", quality=quality, optimize=True, progressive=True)

    return origen.stat().st_size, destino.stat().st_size


def main():
    parser = argparse.ArgumentParser(description="Optimiza imagenes de rotadas/ hacia public/")
    parser.add_argument("--origen", default="rotadas", help="Carpeta origen (default: rotadas)")
    parser.add_argument(
        "--destino",
        default="front-invetario-ng/public/rotadas",
        help="Carpeta destino (default: front-invetario-ng/public/rotadas)",
    )
    parser.add_argument("--max-dimension", type=int, default=1600, help="Lado maximo en px (default: 1600)")
    parser.add_argument("--quality", type=int, default=80, help="Calidad JPEG 1-95 (default: 80)")
    parser.add_argument("--dry-run", action="store_true", help="Solo mostrar que se haria, sin escribir archivos")
    args = parser.parse_args()

    raiz = Path(__file__).resolve().parent.parent
    origen = (raiz / args.origen).resolve()
    destino = (raiz / args.destino).resolve()

    if not origen.exists():
        raise SystemExit(f"No existe la carpeta origen: {origen}")

    archivos = sorted(
        p for p in origen.rglob("*") if p.is_file() and p.suffix.lower() in EXTENSIONES_VALIDAS
    )
    if not archivos:
        raise SystemExit(f"No se encontraron imagenes en: {origen}")

    print(f"Origen:  {origen}")
    print(f"Destino: {destino}")
    print(f"Imagenes encontradas: {len(archivos)}")
    print(f"Max dimension: {args.max_dimension}px | Calidad JPEG: {args.quality}")
    if args.dry_run:
        print("(dry-run: no se escribiran archivos)\n")

    total_origen = 0
    total_destino = 0
    errores = []

    for i, archivo in enumerate(archivos, 1):
        relativo = archivo.relative_to(origen).with_suffix(".jpg")
        salida = destino / relativo

        if args.dry_run:
            print(f"[{i}/{len(archivos)}] {relativo}")
            continue

        try:
            peso_origen, peso_destino = procesar_imagen(archivo, salida, args.max_dimension, args.quality)
            total_origen += peso_origen
            total_destino += peso_destino
            reduccion = 100 * (1 - peso_destino / peso_origen)
            print(
                f"[{i}/{len(archivos)}] {relativo}  "
                f"{peso_origen/1024:.0f}KB -> {peso_destino/1024:.0f}KB ({reduccion:.0f}% menos)"
            )
        except Exception as e:
            errores.append((archivo, str(e)))
            print(f"[{i}/{len(archivos)}] ERROR en {relativo}: {e}")

    if not args.dry_run:
        print("\n--- Resumen ---")
        print(f"Total original:  {total_origen/1024/1024:.1f} MB")
        print(f"Total optimizado: {total_destino/1024/1024:.1f} MB")
        if total_origen:
            print(f"Reduccion total: {100 * (1 - total_destino / total_origen):.1f}%")
        if errores:
            print(f"\n{len(errores)} archivo(s) con error:")
            for archivo, msg in errores:
                print(f"  - {archivo}: {msg}")


if __name__ == "__main__":
    main()
