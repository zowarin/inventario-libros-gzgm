"""Rutas, umbrales y localizacion del binario de Tesseract."""
import os
import shutil
from pathlib import Path

RAIZ = Path(__file__).parent

# --- Entradas / salidas ---------------------------------------------------
ALBUM_MD = RAIZ / "album.md"
DIR_DESCARGAS = RAIZ / "descargas"
DIR_ROTADAS = RAIZ / "rotadas"
DIR_DATOS = RAIZ / "data"
DIR_TESSDATA = RAIZ / "tessdata"
CSV_SALIDA = RAIZ / "inventario.csv"

# --- Red ------------------------------------------------------------------
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
DESCARGAS_PARALELAS = 5
REINTENTOS = 3

# --- OCR ------------------------------------------------------------------
IDIOMAS = "spa+eng"
OCR_PARALELO = 4

# 1600 px da mejores resultados que 2400: a mas resolucion Tesseract empieza a
# partir palabras. Y NO se pasa a gris: varias portadas son texto oscuro sobre
# fondo del mismo tono (rojo sobre rojo) y la luminancia borra esa diferencia.
ANCHO_OCR = 1600
ANCHO_SONDA = 1600        # ancho de la miniatura para detectar orientacion

# Una palabra cuenta como senal si supera esta confianza y parece una palabra.
CONF_PALABRA_SONDA = 80
MIN_PALABRAS_SONDA = 3    # menos que esto se considera "sin senal"

CONFIANZA_MINIMA_LINEA = 55   # descarta lineas de OCR por debajo de esto
TOLERANCIA_ALTURA = 0.25      # dos lineas son del mismo bloque si difieren <25%

URL_TRAINEDDATA = "https://github.com/tesseract-ocr/tessdata_best/raw/main/{lang}.traineddata"


def localizar_tesseract() -> str:
    """Devuelve la ruta al ejecutable de Tesseract.

    El instalador de Windows no siempre lo deja en el PATH, asi que se buscan
    tambien las ubicaciones habituales de instalacion por usuario y por maquina.
    """
    encontrado = shutil.which("tesseract")
    if encontrado:
        return encontrado

    candidatos = [
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Tesseract-OCR" / "tesseract.exe",
        Path(r"C:\Program Files\Tesseract-OCR\tesseract.exe"),
        Path(r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"),
    ]
    for c in candidatos:
        if c.is_file():
            return str(c)

    raise RuntimeError(
        "No se encontro tesseract.exe.\n"
        "Instalalo con:  winget install --id UB-Mannheim.TesseractOCR --scope user\n"
        "y despues ejecuta:  python -m src.main setup"
    )


def configurar_tesseract() -> str:
    """Apunta pytesseract al binario y al tessdata local. Devuelve la ruta."""
    import pytesseract

    ruta = localizar_tesseract()
    pytesseract.pytesseract.tesseract_cmd = ruta
    if DIR_TESSDATA.is_dir():
        # TESSDATA_PREFIX local evita tener que escribir en Program Files
        # (que exigiria permisos de administrador) para anadir el espanol.
        os.environ["TESSDATA_PREFIX"] = str(DIR_TESSDATA)
    return ruta
