"""Enderezado de fotos usando Google Vision en vez del OSD de Tesseract.

Vision ordena los vertices de cada palabra segun SU direccion de lectura
(arriba-izq, arriba-der, abajo-der, abajo-izq), sin importar como este
rotada la foto. Eso permite leer, con una sola llamada por imagen, el angulo
del vector arriba-izq -> arriba-der en las coordenadas de la imagen: ese
angulo es directamente la correccion en grados antihorarios que hay que
aplicar (0/90/180/270) para dejar la palabra horizontal. Se vota por palabra
y gana la mayoria, reusando decidir()/aplicar() de src/rotate.py (que no
dependen de Tesseract, solo _palabras_horizontales lo usa).
"""
import base64
import io
import json
import math
import urllib.error
import urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import config
from src import imagen
from src.rotate import CANDIDATOS, aplicar, decidir


def _img_a_base64(img) -> str:
    buf = io.BytesIO()
    img.convert("RGB").save(buf, format="JPEG", quality=90)
    return base64.b64encode(buf.getvalue()).decode("ascii")


def _llamar_vision(img) -> dict:
    payload = {
        "requests": [{
            "image": {"content": _img_a_base64(img)},
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


def _votos_por_palabra(fulltext: dict) -> Counter:
    votos = Counter()
    for pagina in fulltext.get("pages", []):
        for bloque in pagina.get("blocks", []):
            for parrafo in bloque.get("paragraphs", []):
                for palabra in parrafo.get("words", []):
                    vertices = palabra.get("boundingBox", {}).get("vertices", [])
                    if len(vertices) < 2:
                        continue
                    v0, v1 = vertices[0], vertices[1]
                    dx = v1.get("x", 0) - v0.get("x", 0)
                    dy = v1.get("y", 0) - v0.get("y", 0)
                    if dx == 0 and dy == 0:
                        continue
                    angulo = math.degrees(math.atan2(dy, dx)) % 360
                    correccion = round(angulo / 90) % 4 * 90
                    votos[correccion] += 1
    return votos


def sondear(ruta) -> dict[int, int]:
    base = imagen.cargar(ruta, config.ANCHO_SONDA)
    votos = _votos_por_palabra(_llamar_vision(base))
    return {angulo: votos.get(angulo, 0) for angulo, _ in CANDIDATOS}


def rotar_album(datos: dict, forzar: bool = False) -> dict:
    origen_dir = config.DIR_DESCARGAS / datos["carpeta"]
    destino_dir = config.DIR_ROTADAS / datos["carpeta"]
    destino_dir.mkdir(parents=True, exist_ok=True)

    pendientes = [
        it for it in datos["items"]
        if forzar or "rotacion" not in it or not (destino_dir / it["archivo"]).is_file()
    ]
    ids_pendientes = {id(it) for it in pendientes}

    if pendientes:
        with ThreadPoolExecutor(max_workers=config.OCR_PARALELO) as pool:
            sondas = list(pool.map(lambda it: sondear(origen_dir / it["archivo"]), pendientes))
        for item, puntos in zip(pendientes, sondas):
            item["_puntos"] = puntos

    votos = Counter()
    for item in datos["items"]:
        if "_puntos" in item:
            angulo, fiabilidad = decidir(item["_puntos"])
            if fiabilidad == "alta":
                votos[angulo] += 1
    if votos:
        mayoritario = votos.most_common(1)[0][0]
        datos["rotacion_album"] = mayoritario
        datos["rotacion_votos"] = dict(votos)
    else:
        mayoritario = datos.get("rotacion_album", 0)

    def tarea(item):
        if id(item) not in ids_pendientes:
            return 0
        angulo, fiabilidad = decidir(item.pop("_puntos"))
        if fiabilidad != "alta":
            angulo = mayoritario
            fiabilidad = "por-album"
        aplicar(origen_dir / item["archivo"], destino_dir / item["archivo"], angulo)
        item["rotacion"] = angulo
        item["rotacion_confianza"] = fiabilidad
        return 1 if angulo else 0

    with ThreadPoolExecutor(max_workers=config.OCR_PARALELO) as pool:
        girados = sum(pool.map(tarea, datos["items"]))

    for item in datos["items"]:
        item.pop("_puntos", None)

    heredadas = sum(1 for i in datos["items"] if i.get("rotacion_confianza") == "por-album")
    print(f"  album gira {mayoritario}° (votos {dict(votos)}); "
          f"{girados} giradas, {heredadas} heredaron el angulo del album")
    return datos
