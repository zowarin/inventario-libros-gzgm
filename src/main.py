"""CLI del inventario de libros.

    python -m src.main setup                  prepara tesseract y el idioma espanol
    python -m src.main                        pipeline completo
    python -m src.main --solo descargar       una sola etapa
    python -m src.main --album caja-6         un solo album
    python -m src.main --forzar               ignora el manifest y rehace
    python -m src.main --motor vision         usa Google Vision en vez de Tesseract
"""
from __future__ import annotations

import argparse
import shutil
import sys
import time
from pathlib import Path

import requests

import config
from src import albums, csv_out, download, manifest, ocr, ocr_vision, rotate, rotate_vision, scrape

ETAPAS = ["scrape", "descargar", "rotar", "ocr", "csv"]


# --- setup ----------------------------------------------------------------

def cmd_setup() -> int:
    ruta = config.localizar_tesseract()
    print(f"tesseract: {ruta}")

    config.DIR_TESSDATA.mkdir(parents=True, exist_ok=True)
    origen = Path(ruta).parent / "tessdata"

    # Se copian a un tessdata local para poder anadir el espanol sin escribir
    # en Program Files, que exigiria permisos de administrador.
    for lang in ("eng", "osd"):
        src_f = origen / f"{lang}.traineddata"
        dst_f = config.DIR_TESSDATA / f"{lang}.traineddata"
        if dst_f.is_file():
            continue
        if not src_f.is_file():
            print(f"  aviso: no se encontro {src_f}")
            continue
        shutil.copy2(src_f, dst_f)
        print(f"  copiado {lang}.traineddata")

    dst_spa = config.DIR_TESSDATA / "spa.traineddata"
    if dst_spa.is_file():
        print("  spa.traineddata ya estaba")
    else:
        url = config.URL_TRAINEDDATA.format(lang="spa")
        print(f"  descargando spa.traineddata ...")
        resp = requests.get(url, timeout=300)
        resp.raise_for_status()
        dst_spa.write_bytes(resp.content)
        print(f"  spa.traineddata ({len(resp.content) / 1e6:.1f} MB)")

    config.configurar_tesseract()
    import pytesseract

    idiomas = pytesseract.get_languages()
    print(f"idiomas disponibles: {', '.join(sorted(idiomas))}")
    if "spa" not in idiomas:
        print("ERROR: el espanol no quedo disponible.", file=sys.stderr)
        return 1
    print("setup correcto.")
    return 0


# --- etapas ---------------------------------------------------------------

def etapa_scrape(forzar: bool) -> list[dict]:
    urls = albums.leer_urls()
    print(f"albumes en album.md: {len(urls)}")
    sesion = download.crear_sesion()
    salida = []

    for url in urls:
        datos = scrape.leer_album(url, sesion)
        previo = manifest.cargar(datos["carpeta"])
        if previo and not forzar:
            # Conserva el trabajo ya hecho y solo refresca lo que viene del HTML.
            previo["album"] = datos["album"]
            previo["fotos"] = datos["fotos"]
            datos = previo
        manifest.guardar(datos)
        print(f"  {datos['album']}: {len(datos['fotos'])} fotos -> {datos['carpeta']}")
        salida.append(datos)

    print(f"  total: {sum(len(d['fotos']) for d in salida)} fotos")
    return salida


def seleccionar(filtro: str | None) -> list[dict]:
    todos = manifest.listar()
    if not todos:
        print("No hay manifests. Ejecuta primero la etapa 'scrape'.", file=sys.stderr)
        return []
    if not filtro:
        return todos
    elegidos = [m for m in todos if filtro.lower() in m["carpeta"]]
    if not elegidos:
        print(f"Ningun album coincide con '{filtro}'. "
              f"Disponibles: {', '.join(m['carpeta'] for m in todos)}", file=sys.stderr)
    return elegidos


def main() -> int:
    p = argparse.ArgumentParser(description="Inventario de libros desde Google Photos")
    p.add_argument("accion", nargs="?", default="pipeline", choices=["pipeline", "setup"])
    p.add_argument("--solo", choices=ETAPAS, help="ejecuta una sola etapa")
    p.add_argument("--album", help="filtra por carpeta, p.ej. caja-6")
    p.add_argument("--forzar", action="store_true", help="rehace aunque ya este en el manifest")
    p.add_argument("--motor", choices=["tesseract", "vision"], default="tesseract",
                    help="motor de OCR/rotacion para las etapas rotar y ocr (por defecto tesseract)")
    args = p.parse_args()

    if args.accion == "setup":
        return cmd_setup()

    etapas = [args.solo] if args.solo else ETAPAS
    inicio = time.time()

    if "scrape" in etapas:
        print("[scrape]")
        etapa_scrape(args.forzar)

    necesita_tesseract = args.motor == "tesseract" and ({"rotar", "ocr"} & set(etapas))
    if necesita_tesseract:
        config.configurar_tesseract()

    rotar_album = rotate_vision.rotar_album if args.motor == "vision" else rotate.rotar_album
    ocr_album = ocr_vision.ocr_album if args.motor == "vision" else ocr.ocr_album

    for etapa in ("descargar", "rotar", "ocr"):
        if etapa not in etapas:
            continue
        seleccion = seleccionar(args.album)
        if not seleccion:
            return 1
        print(f"[{etapa}]" + (" (vision)" if args.motor == "vision" and etapa != "descargar" else ""))
        for datos in seleccion:
            print(f"  {datos['album']}")
            if etapa == "descargar":
                datos = download.descargar_album(datos, args.forzar)
            elif etapa == "rotar":
                datos = rotar_album(datos, args.forzar)
            else:
                datos = ocr_album(datos, args.forzar)
            manifest.guardar(datos)

    if "csv" in etapas:
        print("[csv]")
        filas = csv_out.escribir(manifest.listar())
        print(f"  {filas} filas -> {config.CSV_SALIDA}")

    print(f"listo en {time.time() - inicio:.1f}s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
