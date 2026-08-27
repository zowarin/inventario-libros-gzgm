"""Descarga de los originales a descargas/<carpeta>/."""
from concurrent.futures import ThreadPoolExecutor

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

import config


def crear_sesion() -> requests.Session:
    s = requests.Session()
    reintentos = Retry(
        total=config.REINTENTOS,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
    )
    adaptador = HTTPAdapter(max_retries=reintentos, pool_maxsize=16)
    s.mount("https://", adaptador)
    s.headers["User-Agent"] = config.USER_AGENT
    return s


def nombre_archivo(indice: int, url: str) -> str:
    """Nombre determinista: si ya existe, la descarga se salta (reanudable)."""
    ident = url.rsplit("/", 1)[-1]
    return f"{indice:03d}_{ident[:10]}.jpg"


def _descargar_una(sesion, url, destino, forzar):
    if not forzar and destino.is_file() and destino.stat().st_size > 0:
        return False  # ya estaba
    # El sufijo =d devuelve el original a resolucion completa.
    resp = sesion.get(url + "=d", timeout=120, stream=True)
    resp.raise_for_status()
    parcial = destino.with_suffix(".part")
    with open(parcial, "wb") as f:
        for trozo in resp.iter_content(chunk_size=65536):
            f.write(trozo)
    parcial.replace(destino)
    return True


def descargar_album(datos: dict, forzar: bool = False) -> dict:
    carpeta = config.DIR_DESCARGAS / datos["carpeta"]
    carpeta.mkdir(parents=True, exist_ok=True)
    sesion = crear_sesion()

    # Primera pasada: crea la lista de fotos con nombres deterministas.
    if not datos.get("items"):
        datos["items"] = [
            {"indice": i, "url": url, "archivo": nombre_archivo(i, url)}
            for i, url in enumerate(datos["fotos"], start=1)
        ]

    def tarea(item):
        destino = carpeta / item["archivo"]
        nuevo = _descargar_una(sesion, item["url"], destino, forzar)
        item["descargado"] = True
        return nuevo

    with ThreadPoolExecutor(max_workers=config.DESCARGAS_PARALELAS) as pool:
        nuevos = sum(pool.map(tarea, datos["items"]))

    print(f"  descargadas {nuevos} nuevas, {len(datos['items']) - nuevos} ya estaban")
    return datos
