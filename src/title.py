"""De los datos crudos de Tesseract al titulo del libro.

Tesseract devuelve texto suelto, no estructura, asi que el titulo hay que
elegirlo. La senal mas fiable en una portada es el tamano: el titulo casi
siempre es el bloque de texto mas grande, y con frecuencia esta arriba.
"""
import re
from statistics import median

import config
from src import stopwords

RE_LETRA = re.compile(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]")
RE_ALFANUM = re.compile(r"[A-Za-z0-9ÁÉÍÓÚÜÑáéíóúüñ]")

MAX_LINEAS_TITULO = 4


def agrupar_lineas(datos: dict) -> list[dict]:
    """Agrupa las palabras en lineas.

    image_to_data ya numera bloque, parrafo y linea, asi que no hace falta
    reagrupar por solapamiento vertical.
    """
    alto_pagina = 1
    for i, nivel in enumerate(datos.get("level", [])):
        if nivel == 1:
            alto_pagina = max(datos["height"][i], 1)
            break

    grupos: dict[tuple, list] = {}
    for i, bruto in enumerate(datos["text"]):
        palabra = (bruto or "").strip()
        # Los tokens de pura puntuacion ensucian el titulo ("- La muerte . del")
        # sin aportar nada.
        if not palabra or not RE_ALFANUM.search(palabra):
            continue
        try:
            conf = float(datos["conf"][i])
        except (TypeError, ValueError):
            continue
        if conf < 0:
            continue
        clave = (datos["block_num"][i], datos["par_num"][i], datos["line_num"][i])
        grupos.setdefault(clave, []).append(
            {
                "texto": palabra,
                "conf": conf,
                "top": datos["top"][i],
                "height": datos["height"][i],
            }
        )

    lineas = []
    for palabras in grupos.values():
        texto = re.sub(r"\s+", " ", " ".join(p["texto"] for p in palabras)).strip()
        if not texto:
            continue
        lineas.append(
            {
                "texto": texto,
                "conf": median(p["conf"] for p in palabras),
                "altura": median(p["height"] for p in palabras),
                "top": min(p["top"] for p in palabras),
                "bottom": max(p["top"] + p["height"] for p in palabras),
                "alto_pagina": alto_pagina,
            }
        )

    lineas.sort(key=lambda l: l["top"])
    return lineas


def _es_candidata(linea: dict) -> bool:
    if linea["conf"] < config.CONFIANZA_MINIMA_LINEA:
        return False
    if len(linea["texto"]) < 3:
        return False
    if not RE_LETRA.search(linea["texto"]):
        return False
    return not stopwords.es_ruido(linea["texto"])


def _compatibles(arriba: dict, abajo: dict) -> bool:
    """Dos lineas contiguas pertenecen al mismo titulo multilinea."""
    mayor = max(arriba["altura"], abajo["altura"])
    if mayor <= 0:
        return False
    if abs(arriba["altura"] - abajo["altura"]) / mayor > config.TOLERANCIA_ALTURA:
        return False
    return (abajo["top"] - arriba["bottom"]) <= mayor * 1.5


def _extender(candidatas: list[dict], mejor: dict) -> list[dict]:
    """Anade las lineas contiguas del mismo tamano, p.ej.
    'DE LOS' + 'AMMONITAS A LOS CABALLOS'."""
    orden = sorted(candidatas, key=lambda l: l["top"])
    i = orden.index(mejor)
    bloque = [mejor]

    j = i - 1
    while j >= 0 and len(bloque) < MAX_LINEAS_TITULO and _compatibles(orden[j], bloque[0]):
        bloque.insert(0, orden[j])
        j -= 1

    k = i + 1
    while k < len(orden) and len(bloque) < MAX_LINEAS_TITULO and _compatibles(bloque[-1], orden[k]):
        bloque.append(orden[k])
        k += 1

    return bloque


def elegir_titulo(lineas: list[dict]) -> tuple[str, float]:
    candidatas = [l for l in lineas if _es_candidata(l)]
    if not candidatas:
        return "", 0.0

    altura_max = max(l["altura"] for l in candidatas) or 1
    alto_pagina = candidatas[0]["alto_pagina"] or 1

    def puntuar(l: dict) -> float:
        # La altura pesa el doble que la posicion: en las portadas revisadas
        # el titulo unas veces esta arriba y otras a media altura, pero
        # siempre es el texto mas grande.
        relativa = l["altura"] / altura_max
        arriba = 1.0 if (l["top"] / alto_pagina) < 0.33 else 0.0
        return relativa * 2 + arriba

    mejor = max(candidatas, key=puntuar)
    bloque = _extender(candidatas, mejor)

    texto = re.sub(r"\s+", " ", " ".join(l["texto"] for l in bloque)).strip()
    texto = texto.strip("-–—.,;:|/\\ ")
    confianza = round(median(l["conf"] for l in bloque), 1)
    return texto, confianza
