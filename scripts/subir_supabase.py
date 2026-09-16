"""Sube el inventario (desde los manifests) a la tabla `inventario` de Supabase.

Lee data/<carpeta>/manifest.json -- la misma fuente que usa src/csv_out.py --
en vez de inventario.csv, y evita duplicados consultando por url_origen antes
de insertar.

Uso:
    python scripts/subir_supabase.py --album caja-15
    python scripts/subir_supabase.py --album caja-15 --album caja-16
    python scripts/subir_supabase.py --album caja-15 --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import requests

import config
from src import manifest

LOTE = 100


def construir_filas(m: dict) -> list[dict]:
    filas = []
    for item in m.get("items", []):
        filas.append(
            {
                "portada": f"rotadas/{m['carpeta']}/{item['archivo']}",
                "titulo": item.get("titulo") or None,
                "album": m["album"],
                "carpeta": m["carpeta"],
                "archivo": item["archivo"],
                "rotacion": item.get("rotacion"),
                "titulo_confianza": item.get("titulo_confianza"),
                "texto_ocr": item.get("texto_ocr") or None,
                "url_origen": item["url"],
            }
        )
    return filas


def url_origen_existentes(sesion: requests.Session, base_url: str, carpeta: str) -> set[str]:
    resp = sesion.get(
        f"{base_url}/rest/v1/inventario",
        params={"select": "url_origen", "carpeta": f"eq.{carpeta}"},
        timeout=30,
    )
    resp.raise_for_status()
    return {fila["url_origen"] for fila in resp.json() if fila.get("url_origen")}


def insertar_lote(sesion: requests.Session, base_url: str, filas: list[dict]) -> None:
    resp = sesion.post(
        f"{base_url}/rest/v1/inventario",
        json=filas,
        headers={"Prefer": "return=minimal"},
        timeout=60,
    )
    resp.raise_for_status()


def main() -> int:
    p = argparse.ArgumentParser(description="Sube manifests a la tabla inventario de Supabase")
    p.add_argument("--album", action="append", help="carpeta a subir (repetible); sin esto, sube todas")
    p.add_argument("--dry-run", action="store_true", help="solo muestra que se haria, sin escribir")
    args = p.parse_args()

    base_url, clave = config.cargar_supabase_config()

    manifests = manifest.listar()
    if not manifests:
        print("No hay manifests. Corre primero el pipeline (python -m src.main).", file=sys.stderr)
        return 1

    if args.album:
        objetivo = set(args.album)
        manifests = [m for m in manifests if m["carpeta"] in objetivo]
        faltantes = objetivo - {m["carpeta"] for m in manifests}
        if faltantes:
            print(f"aviso: no hay manifest para: {', '.join(sorted(faltantes))}", file=sys.stderr)

    if not manifests:
        print("Ningun album coincide con el filtro.", file=sys.stderr)
        return 1

    sesion = requests.Session()
    sesion.headers.update({"apikey": clave, "Authorization": f"Bearer {clave}", "Content-Type": "application/json"})

    total_insertadas = 0
    total_omitidas = 0

    for m in manifests:
        existentes = url_origen_existentes(sesion, base_url, m["carpeta"])
        filas = [f for f in construir_filas(m) if f["url_origen"] not in existentes]
        omitidas = len(m.get("items", [])) - len(filas)
        total_omitidas += omitidas

        print(f"{m['album']} ({m['carpeta']}): {len(filas)} nuevas, {omitidas} ya existian")

        if args.dry_run or not filas:
            continue

        for i in range(0, len(filas), LOTE):
            insertar_lote(sesion, base_url, filas[i : i + LOTE])
            total_insertadas += len(filas[i : i + LOTE])

    print(f"\ntotal: {total_insertadas} insertadas, {total_omitidas} omitidas (ya existian)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
