"""Compara el motor Tesseract (ya en el manifest) contra Google Vision.

Uso:
    python3 comparar_vision.py [carpeta]      # por defecto: inventario-caja-1

No modifica data/<carpeta>/manifest.json ni inventario.csv: parte de una
copia del manifest existente (que ya trae los resultados de Tesseract de la
corrida anterior), corre Vision aparte con src/ocr_vision.py y deja un CSV de
comparacion en la raiz del proyecto.
"""
import csv
import sys
import time
from copy import deepcopy

import config
from src import manifest, ocr_vision

CARPETA_DEFECTO = "inventario-caja-1"


def main() -> int:
    carpeta = sys.argv[1] if len(sys.argv) > 1 else CARPETA_DEFECTO
    original = manifest.cargar(carpeta)
    if not original:
        print(f"No hay manifest para '{carpeta}'. Corre primero el pipeline.", file=sys.stderr)
        return 1

    con_vision = deepcopy(original)
    for item in con_vision["items"]:
        item.pop("titulo", None)
        item.pop("titulo_confianza", None)
        item.pop("texto_ocr", None)

    print(f"{original['album']} ({carpeta}): {len(con_vision['items'])} fotos -> Google Vision")
    inicio = time.time()
    ocr_vision.ocr_album(con_vision, forzar=False)
    print(f"  {time.time() - inicio:.1f}s")

    filas = []
    coincidencias = 0
    for previo, nuevo in zip(original["items"], con_vision["items"]):
        t_tess = (previo.get("titulo") or "").strip()
        t_vis = (nuevo.get("titulo") or "").strip()
        igual = t_tess.lower() == t_vis.lower() and t_tess != ""
        coincidencias += igual
        filas.append({
            "archivo": previo["archivo"],
            "titulo_tesseract": previo.get("titulo", ""),
            "conf_tesseract": previo.get("titulo_confianza", ""),
            "titulo_vision": nuevo.get("titulo", ""),
            "conf_vision": nuevo.get("titulo_confianza", ""),
            "coincide": "si" if igual else "no",
            "texto_ocr_tesseract": previo.get("texto_ocr", ""),
            "texto_ocr_vision": nuevo.get("texto_ocr", ""),
        })

    salida = config.RAIZ / f"comparacion_vision_{carpeta}.csv"
    campos = ["archivo", "titulo_tesseract", "conf_tesseract", "titulo_vision",
              "conf_vision", "coincide", "texto_ocr_tesseract", "texto_ocr_vision"]
    with salida.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=campos)
        w.writeheader()
        w.writerows(filas)

    con_titulo_tess = sum(1 for f in filas if f["titulo_tesseract"])
    con_titulo_vis = sum(1 for f in filas if f["titulo_vision"])
    print(f"\ntitulos iguales: {coincidencias}/{len(filas)}")
    print(f"con titulo -> tesseract: {con_titulo_tess}/{len(filas)}  vision: {con_titulo_vis}/{len(filas)}")
    print(f"csv -> {salida}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
