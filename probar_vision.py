"""Prueba suelta: confirma que GOOGLE_VISION_API_KEY funciona.

Uso:
    python3 probar_vision.py [ruta_imagen]

No toca el pipeline (src/main.py) ni requiere dependencias nuevas: lee el
.env a mano y usa urllib de la libreria estandar.
"""
import base64
import json
import re
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).parent
IMAGEN_DEFECTO = RAIZ / "rotadas" / "caja-3" / "001_AP1GczNS2q.jpg"


def leer_env(clave: str) -> str:
    texto = (RAIZ / ".env").read_text(encoding="utf-8")
    m = re.search(rf'^{clave}\s*=\s*"?([^"\n]*)"?\s*$', texto, re.MULTILINE)
    if not m:
        raise RuntimeError(f"{clave} no encontrada en .env")
    return m.group(1)


def main() -> int:
    api_key = leer_env("GOOGLE_VISION_API_KEY")
    if not api_key:
        print("GOOGLE_VISION_API_KEY esta vacia en .env", file=sys.stderr)
        return 1

    ruta = Path(sys.argv[1]) if len(sys.argv) > 1 else IMAGEN_DEFECTO
    if not ruta.is_file():
        print(f"No existe la imagen: {ruta}", file=sys.stderr)
        return 1

    imagen_b64 = base64.b64encode(ruta.read_bytes()).decode("ascii")
    payload = {
        "requests": [{
            "image": {"content": imagen_b64},
            "features": [{"type": "TEXT_DETECTION"}],
        }]
    }

    url = f"https://vision.googleapis.com/v1/images:annotate?key={api_key}"
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    print(f"imagen: {ruta}")
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            cuerpo = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print(f"HTTP {e.code}: {e.read().decode('utf-8')}", file=sys.stderr)
        return 1

    respuesta = cuerpo["responses"][0]
    if "error" in respuesta:
        print(f"Error de Vision API: {respuesta['error']['message']}", file=sys.stderr)
        return 1

    anotaciones = respuesta.get("textAnnotations")
    if not anotaciones:
        print("La API respondio OK pero no detecto texto en la imagen.")
        return 0

    print("conexion OK, texto detectado:\n")
    print(anotaciones[0]["description"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
