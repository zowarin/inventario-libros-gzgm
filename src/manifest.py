"""Estado por album en data/<carpeta>/manifest.json.

Cada etapa lee y escribe aqui, de modo que una interrupcion no obliga a
repetir las descargas ni el OCR.
"""
from __future__ import annotations

import json

import config


def ruta(carpeta: str):
    return config.DIR_DATOS / carpeta / "manifest.json"


def cargar(carpeta: str) -> dict | None:
    p = ruta(carpeta)
    if not p.is_file():
        return None
    return json.loads(p.read_text(encoding="utf-8"))


def guardar(datos: dict) -> None:
    p = ruta(datos["carpeta"])
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def listar() -> list[dict]:
    """Todos los manifests existentes, en orden alfabetico de carpeta."""
    if not config.DIR_DATOS.is_dir():
        return []
    salida = []
    for d in sorted(config.DIR_DATOS.iterdir()):
        if (d / "manifest.json").is_file():
            salida.append(json.loads((d / "manifest.json").read_text(encoding="utf-8")))
    return salida
