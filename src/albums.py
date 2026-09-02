"""Lectura de album.md -> lista de URLs de albumes compartidos."""
from __future__ import annotations

import re
from pathlib import Path

import config

RE_URL_ALBUM = re.compile(r"https://photos\.google\.com/share/\S+")


def leer_urls(ruta: Path | None = None) -> list[str]:
    """Extrae las URLs de album.md.

    El archivo viene con finales de linea CRLF: sin quitar el \\r las URLs
    arrastran el retorno de carro y las peticiones fallan.
    """
    ruta = ruta or config.ALBUM_MD
    texto = ruta.read_text(encoding="utf-8").replace("\r", "")
    urls = RE_URL_ALBUM.findall(texto)
    return list(dict.fromkeys(urls))
