"""Enderezado de las fotos.

Por que no se usa el OSD de Tesseract (image_to_osd): esta pensado para
paginas escaneadas con texto denso. Sobre fotos de portadas devuelve
confianzas por debajo de 1 y detecta alfabetos arabe o katakana en libros en
espanol, con resultados que cambian segun el tamano de la miniatura.

En su lugar se prueban las cuatro orientaciones y se mide cual lee mejor. El
detalle importante es que Tesseract rota internamente las lineas de texto: lee
igual de bien la orientacion correcta y una de las giradas 90 grados. Lo que
las separa es la geometria, porque solo en la correcta las palabras salen mas
anchas que altas.
"""
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

import pytesseract
from PIL import Image, ImageOps
from pytesseract import Output

import config
from src import imagen

# La etiqueta son grados ANTIHORARIOS, que es como transpone PIL. La
# transposicion ganadora es directamente la correccion a aplicar, asi que no
# hay que traducir entre sentidos horario y antihorario en ningun momento.
CANDIDATOS = [
    (0, None),
    (90, Image.Transpose.ROTATE_90),
    (180, Image.Transpose.ROTATE_180),
    (270, Image.Transpose.ROTATE_270),
]


def _palabras_horizontales(img: Image.Image) -> int:
    """Cuenta palabras creibles que ademas son mas anchas que altas."""
    datos = pytesseract.image_to_data(
        img, lang=config.IDIOMAS, output_type=Output.DICT, config="--dpi 300"
    )
    return imagen.contar_palabras(datos, solo_horizontales=True)


def sondear(ruta) -> dict[int, int]:
    """Puntua las cuatro orientaciones de una foto.

    Se empieza en color, que basta para la mayoria, y solo si no hay senal se
    reintenta en gris: asi las portadas de texto blanco sobre fondo saturado
    no se quedan sin voto, sin pagar el doble de OCR en todas las demas.
    """
    base = imagen.cargar(ruta, config.ANCHO_SONDA)
    for _, preparada in imagen.variantes(base):
        puntos = {
            etq: _palabras_horizontales(preparada.transpose(t) if t else preparada)
            for etq, t in CANDIDATOS
        }
        if max(puntos.values()) >= config.MIN_PALABRAS_SONDA:
            return puntos
    return puntos


def decidir(puntos: dict[int, int]) -> tuple[int, str]:
    """Angulo a aplicar y si la deteccion es fiable."""
    mejor = max(puntos, key=lambda o: puntos[o])
    if puntos[mejor] < config.MIN_PALABRAS_SONDA:
        return 0, "sin-senal"
    segundo = max((v for o, v in puntos.items() if o != mejor), default=0)
    if segundo >= puntos[mejor]:
        return mejor, "baja"
    return mejor, "alta"


def aplicar(origen, destino, angulo: int) -> None:
    transpuesta = dict(CANDIDATOS)[angulo]
    with Image.open(origen) as abierta:
        img = ImageOps.exif_transpose(abierta)
        if transpuesta is not None:
            img = img.transpose(transpuesta)
        if img.mode != "RGB":
            img = img.convert("RGB")
        img.save(destino, "JPEG", quality=95, subsampling=0)


def rotar_album(datos: dict, forzar: bool = False) -> dict:
    origen_dir = config.DIR_DESCARGAS / datos["carpeta"]
    destino_dir = config.DIR_ROTADAS / datos["carpeta"]
    destino_dir.mkdir(parents=True, exist_ok=True)

    pendientes = [
        it for it in datos["items"]
        if forzar or "rotacion" not in it or not (destino_dir / it["archivo"]).is_file()
    ]
    ids_pendientes = {id(it) for it in pendientes}

    # 1) Sondear. Muchas portadas tienen poco texto legible y no dan senal,
    #    asi que primero se recoge la evidencia de todo el album.
    if pendientes:
        with ThreadPoolExecutor(max_workers=config.OCR_PARALELO) as pool:
            sondas = list(pool.map(lambda it: sondear(origen_dir / it["archivo"]), pendientes))
        for item, puntos in zip(pendientes, sondas):
            item["_puntos"] = puntos

    # 2) Angulo mayoritario del album: cada caja se fotografio de una sentada,
    #    asi que sirve de respaldo para las fotos sin senal propia.
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
        # Sin fotos pendientes no hay evidencia nueva: se conserva lo decidido
        # en la pasada anterior en vez de degradarlo a 0.
        mayoritario = datos.get("rotacion_album", 0)

    # 3) Aplicar.
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
