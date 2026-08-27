"""Lee una pagina compartida de Google Photos y saca titulo + fotos.

Las paginas publicas traen todo el listado en el HTML inicial, asi que basta
una peticion normal con User-Agent de navegador: no hace falta OAuth ni un
navegador headless.
"""
import html as htmllib
import re
import unicodedata

import requests

import config

# El prefijo /pw/ distingue las fotos del album de los avatares de perfil,
# que usan /a/ y /ogw/.
RE_FOTO = re.compile(r"https://lh3\.googleusercontent\.com/pw/[A-Za-z0-9_-]+")
RE_OG_TITLE = re.compile(r'<meta\s+property="og:title"\s+content="([^"]*)"')


def slug(texto: str) -> str:
    """'Inventario caja #1' -> 'inventario-caja-1'."""
    base = unicodedata.normalize("NFKD", texto)
    base = "".join(c for c in base if not unicodedata.combining(c))
    base = re.sub(r"[^a-zA-Z0-9]+", "-", base.lower())
    return base.strip("-")


def limpiar_titulo(crudo: str) -> str:
    """Quita el sufijo de fecha que Google anade al nombre del album.

    'Inventario caja #1 - Thursday, Aug 13' -> 'Inventario caja #1'
    """
    titulo = htmllib.unescape(crudo)
    titulo = re.sub(r"\s*·\s*.*$", "", titulo)
    return titulo.strip()


def leer_album(url: str, sesion: requests.Session | None = None) -> dict:
    s = sesion or requests.Session()
    resp = s.get(url, headers={"User-Agent": config.USER_AGENT}, timeout=60)
    resp.raise_for_status()
    html = resp.text

    m = RE_OG_TITLE.search(html)
    if not m:
        raise RuntimeError(
            f"No se encontro og:title en {url}. Es probable que Google haya "
            "cambiado el HTML de las paginas compartidas."
        )
    titulo = limpiar_titulo(m.group(1))

    # dict.fromkeys deduplica conservando el orden: la portada del album
    # aparece repetida al principio del documento.
    fotos = list(dict.fromkeys(RE_FOTO.findall(html)))
    if not fotos:
        raise RuntimeError(f"No se encontro ninguna foto en {url}.")

    return {"album": titulo, "carpeta": slug(titulo), "url": url, "fotos": fotos}
