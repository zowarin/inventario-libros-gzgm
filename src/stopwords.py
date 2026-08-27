"""Texto de portada que casi nunca es el titulo del libro.

Lista pensada para editarse: si al revisar el CSV ves que se cuela un sello o
una coleccion concreta, anade su patron aqui y vuelve a correr la etapa de OCR.
"""
import re

PATRONES = [
    # Colecciones y series
    r"^colecc?i[oó]n\b",
    r"^serie\b",
    r"^biblioteca\b",
    r"^tomo\b",
    r"^volumen\b",
    r"^n[uú]mero\b",
    # Sellos e instituciones
    r"^editorial\b",
    r"\beditores?\b",
    r"^ediciones\b",
    r"^instituto\b",
    r"^universidad\b",
    r"^fondo de cultura",
    r"^siglo\s+(xxi|veintiuno)\b",
    r"\bs\.?\s?a\.?\s*(de\s*c\.?\s?v\.?)?$",
    r"\bunam\b|\binah\b|\bfce\b|\bconaculta\b",
    # Metadatos
    r"^isbn\b",
    r"^\d{4}$",                 # un ano suelto
    r"^[\W\d_]+$",              # solo simbolos o numeros
]

_COMPILADOS = [re.compile(p, re.IGNORECASE) for p in PATRONES]


def es_ruido(texto: str) -> bool:
    limpio = texto.strip()
    return any(p.search(limpio) for p in _COMPILADOS)
