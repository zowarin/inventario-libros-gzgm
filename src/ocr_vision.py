"""OCR con Google Vision sobre las imagenes ya enderezadas.

Reusa src/title.py (agrupar_lineas / elegir_titulo) para que la eleccion de
titulo sea identica a la de Tesseract y la comparacion entre motores mida
solo la calidad del OCR, no dos heuristicas distintas. Para eso, la respuesta
de Vision se reempaqueta en el mismo formato de diccionario que devuelve
pytesseract.image_to_data (arrays paralelos: text/conf/top/height/...).

Vision no numera "linea" como Tesseract (su jerarquia es pagina > bloque >
parrafo > palabra > simbolo, y un parrafo puede abarcar varias lineas
visuales), asi que las lineas se reconstruyen agrupando palabras por
solapamiento vertical tras ordenarlas por su coordenada Y.
"""
import base64
import json
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import config
from src import title


def _llamar_vision(ruta: Path) -> dict:
    contenido = base64.b64encode(Path(ruta).read_bytes()).decode("ascii")
    payload = {
        "requests": [{
            "image": {"content": contenido},
            "features": [{"type": "DOCUMENT_TEXT_DETECTION"}],
        }]
    }
    url = f"{config.VISION_API_URL}?key={config.cargar_vision_api_key()}"
    peticion = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(peticion, timeout=30) as resp:
            cuerpo = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise RuntimeError(f"HTTP {e.code} llamando a Vision: {e.read().decode('utf-8')}") from e

    respuesta = cuerpo["responses"][0]
    if "error" in respuesta:
        raise RuntimeError(f"Error de Vision API: {respuesta['error']['message']}")
    return respuesta.get("fullTextAnnotation", {})


def _aplanar_palabras(fulltext: dict) -> tuple[list[dict], int]:
    """Devuelve las palabras con caja delimitadora y la altura de pagina."""
    palabras = []
    alto_pagina = 1
    for pagina in fulltext.get("pages", []):
        alto_pagina = pagina.get("height") or alto_pagina
        for bloque in pagina.get("blocks", []):
            for parrafo in bloque.get("paragraphs", []):
                for palabra in parrafo.get("words", []):
                    texto = "".join(s.get("text", "") for s in palabra.get("symbols", []))
                    if not texto.strip():
                        continue
                    vertices = palabra.get("boundingBox", {}).get("vertices", [])
                    xs = [v.get("x", 0) for v in vertices]
                    ys = [v.get("y", 0) for v in vertices]
                    if not ys or not xs:
                        continue
                    palabras.append({
                        "texto": texto,
                        # Vision da confianza 0-1; Tesseract la da 0-100.
                        "conf": palabra.get("confidence", 0.0) * 100,
                        "left": min(xs),
                        "top": min(ys),
                        "bottom": max(ys),
                        "height": max(ys) - min(ys),
                    })
    return palabras, alto_pagina


def _asignar_lineas(palabras: list[dict]) -> list[dict]:
    """Agrupa por solapamiento vertical (cada grupo es una linea sintetica) y
    dentro de cada linea reordena de izquierda a derecha: agrupar por "top"
    no garantiza el orden de lectura, solo la pertenencia a la linea."""
    palabras = sorted(palabras, key=lambda p: p["top"])
    linea = -1
    rango = None
    for p in palabras:
        centro = (p["top"] + p["bottom"]) / 2
        if rango is None or not (rango[0] <= centro <= rango[1]):
            linea += 1
            rango = (p["top"], p["bottom"])
        else:
            rango = (min(rango[0], p["top"]), max(rango[1], p["bottom"]))
        p["line_num"] = linea
    return sorted(palabras, key=lambda p: (p["line_num"], p["left"]))


def _a_formato_tesseract(palabras: list[dict], alto_pagina: int) -> dict:
    """Reempaqueta como el dict de pytesseract.image_to_data (nivel 1 = pagina,
    para que agrupar_lineas calcule alto_pagina; nivel 5 = palabra)."""
    datos = {"level": [1], "text": [""], "conf": [-1], "top": [0], "height": [alto_pagina],
             "block_num": [0], "par_num": [0], "line_num": [0]}
    for p in palabras:
        datos["level"].append(5)
        datos["text"].append(p["texto"])
        datos["conf"].append(p["conf"])
        datos["top"].append(p["top"])
        datos["height"].append(p["height"])
        datos["block_num"].append(0)
        datos["par_num"].append(0)
        datos["line_num"].append(p["line_num"])
    return datos


def leer(ruta) -> dict:
    """Lee la imagen con Vision y devuelve datos en formato Tesseract."""
    fulltext = _llamar_vision(Path(ruta))
    palabras, alto_pagina = _aplanar_palabras(fulltext)
    palabras = _asignar_lineas(palabras)
    return _a_formato_tesseract(palabras, alto_pagina)


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

    total = sum(1 for i in datos["items"] if i.get("titulo"))
    print(f"  titulo en {total}/{len(datos['items'])} ({nuevos} nuevos)")
    return datos
