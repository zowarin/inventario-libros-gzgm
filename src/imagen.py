"""Preparacion de imagenes para OCR.

No hay una sola conversion que sirva para todas las portadas, y las dos que
fallan lo hacen por motivos opuestos:

  - texto oscuro sobre fondo del mismo tono (rojo sobre rojo): la luminancia
    borra la diferencia, y solo se lee en color.
  - texto blanco sobre fondo de color saturado: en color no se separa, y solo
    se lee en gris.

Por eso se prueban las dos y se elige la que mas texto creible devuelve.
"""
import re

from PIL import Image

import config

VOCAL = re.compile(r"[aeiouáéíóúü]", re.IGNORECASE)
SOLO_LETRAS = re.compile(r"^[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+$")


def cargar(ruta, ancho: int) -> Image.Image:
    with Image.open(ruta) as abierta:
        img = abierta.convert("RGB")
        img.thumbnail((ancho, ancho * 4), Image.LANCZOS)
        return img


def variantes(img: Image.Image):
    yield "color", img
    yield "gris", img.convert("L")


def es_palabra(texto: str, conf: float, minimo: float) -> bool:
    """Filtra el ruido que Tesseract devuelve sobre texturas y fotografias."""
    return (
        conf >= minimo
        and len(texto) >= 4
        and bool(SOLO_LETRAS.match(texto))
        and bool(VOCAL.search(texto))
    )


def contar_palabras(datos: dict, solo_horizontales: bool = False) -> int:
    total = 0
    for i, bruto in enumerate(datos["text"]):
        palabra = (bruto or "").strip()
        try:
            conf = float(datos["conf"][i])
        except (TypeError, ValueError):
            continue
        if not es_palabra(palabra, conf, config.CONF_PALABRA_SONDA):
            continue
        if solo_horizontales and datos["width"][i] <= datos["height"][i]:
            continue
        total += 1
    return total
