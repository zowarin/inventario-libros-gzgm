"""Respaldo de src/ocr.py (motor Tesseract) previo a integrar Google Vision.

No se importa desde el pipeline; es solo referencia/rollback. Ver src/ocr.py
(Tesseract, sigue activo) y src/ocr_vision.py (Google Vision, nuevo).
"""
from concurrent.futures import ThreadPoolExecutor

import pytesseract
from pytesseract import Output

import config
from src import imagen, title


def leer(ruta) -> dict:
    """Lee la imagen probando cada preparacion y se queda con la mejor."""
    base = imagen.cargar(ruta, config.ANCHO_OCR)
    mejor = None
    mejor_puntos = -1
    for _, img in imagen.variantes(base):
        datos = pytesseract.image_to_data(
            img, lang=config.IDIOMAS, output_type=Output.DICT, config="--dpi 300"
        )
        puntos = imagen.contar_palabras(datos)
        if puntos > mejor_puntos:
            mejor, mejor_puntos = datos, puntos
    return mejor


def ocr_album(datos: dict, forzar: bool = False) -> dict:
    origen_dir = config.DIR_ROTADAS / datos["carpeta"]

    def tarea(item):
        if not forzar and "titulo" in item:
            return 0
        crudos = leer(origen_dir / item["archivo"])
        lineas = title.agrupar_lineas(crudos)
        item["texto_ocr"] = " / ".join(l["texto"] for l in lineas)
        titulo, confianza = title.elegir_titulo(lineas)
        item["titulo"] = titulo
        item["titulo_confianza"] = confianza
        return 1 if titulo else 0

    with ThreadPoolExecutor(max_workers=config.OCR_PARALELO) as pool:
        nuevos = sum(pool.map(tarea, datos["items"]))

    # Se informa del total, no de los recien procesados: al reanudar, los ya
    # hechos se saltan y contarlos como 0 hacia parecer que se habia perdido.
    total = sum(1 for i in datos["items"] if i.get("titulo"))
    print(f"  titulo en {total}/{len(datos['items'])} ({nuevos} nuevos)")
    return datos
