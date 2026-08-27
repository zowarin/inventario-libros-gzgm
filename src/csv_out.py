"""Generacion de inventario.csv."""
import csv

import config

COLUMNAS = [
    "portada",
    "titulo",
    "album",
    "carpeta",
    "archivo",
    "rotacion",
    "titulo_confianza",
    "texto_ocr",
    "url_origen",
]


def escribir(manifests: list[dict], destino=None) -> int:
    destino = destino or config.CSV_SALIDA
    filas = 0

    # utf-8-sig: sin el BOM, Excel en Windows rompe los acentos.
    # newline="": si no, csv intercala filas en blanco.
    with open(destino, "w", newline="", encoding="utf-8-sig") as f:
        escritor = csv.writer(f)
        escritor.writerow(COLUMNAS)

        for m in manifests:
            for item in m.get("items", []):
                portada = f"rotadas/{m['carpeta']}/{item['archivo']}"
                escritor.writerow(
                    [
                        portada,
                        item.get("titulo", ""),
                        m["album"],
                        m["carpeta"],
                        item["archivo"],
                        item.get("rotacion", ""),
                        item.get("titulo_confianza", ""),
                        (item.get("texto_ocr") or "").replace("\n", " / "),
                        item["url"],
                    ]
                )
                filas += 1

    return filas
