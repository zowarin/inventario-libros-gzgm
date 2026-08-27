# Inventario de Libros

Convierte álbumes compartidos de Google Photos en un inventario CSV: descarga
las fotos, las endereza, lee la portada con OCR y extrae el título.

## Puesta en marcha

Requiere Tesseract nativo (`pytesseract` solo es el envoltorio: el binario no
puede vivir dentro del entorno virtual).

```powershell
winget install --id UB-Mannheim.TesseractOCR
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m src.main setup
```

El instalador solo trae `eng` y `osd`. `setup` descarga `spa.traineddata` a
`tessdata/` dentro del proyecto y apunta ahí `TESSDATA_PREFIX`, para no tener
que escribir en `C:\Program Files` con permisos de administrador.

## Uso

```powershell
.\.venv\Scripts\python.exe -m src.main                      # pipeline completo
.\.venv\Scripts\python.exe -m src.main --solo descargar     # una etapa
.\.venv\Scripts\python.exe -m src.main --album caja-6       # un solo álbum
.\.venv\Scripts\python.exe -m src.main --forzar             # rehace todo
```

Etapas: `scrape` → `descargar` → `rotar` → `ocr` → `csv`.

Cada álbum guarda su estado en `data/<carpeta>/manifest.json`, así que una
interrupción no obliga a repetir las descargas ni el OCR.

## Salida

`inventario.csv`, en UTF-8 con BOM para que Excel respete los acentos:

| columna | contenido |
|---|---|
| `portada` | ruta a la imagen enderezada |
| `titulo` | título detectado |
| `album` | nombre del álbum, ya limpio de la fecha |
| `carpeta` | slug del álbum |
| `rotacion` | grados aplicados |
| `titulo_confianza` | confianza media del OCR |
| `texto_ocr` | texto crudo, para corregir a mano las filas dudosas |

## Notas de implementación

Tres cosas salieron distintas de lo previsto, y conviene saberlas antes de
tocar el código:

**El OSD de Tesseract no sirve aquí.** `image_to_osd` está pensado para páginas
escaneadas con texto denso. Sobre fotos de portadas devuelve confianzas por
debajo de 1 y detecta alfabetos árabe o katakana en libros en español. En su
lugar (`src/rotate.py`) se prueban las cuatro orientaciones y se mide cuál lee
mejor.

**Leer más texto no basta para decidir la orientación.** Tesseract rota
internamente las líneas, así que lee igual de bien la orientación correcta y
una de las giradas 90°. Lo que las separa es la geometría: solo en la correcta
las palabras salen más anchas que altas. Ese criterio acertó en las 6 fotos de
prueba, incluidas las dos donde fallaban los demás.

**Ninguna conversión de color vale para todas las portadas**, y las que fallan
lo hacen por motivos opuestos: el texto oscuro sobre fondo del mismo tono solo
se lee en color, y el texto blanco sobre fondo saturado solo en gris. Por eso
`src/imagen.py` prueba las dos y se queda con la que más texto creíble
devuelve.

Además, cada caja se fotografió de una sentada, así que todas sus fotos
comparten orientación. `rotar` aprovecha eso: decide por mayoría del álbum y
las portadas sin texto legible heredan ese ángulo.

## Límite conocido

La extracción del título es heurística (el texto más grande, con la posición
como desempate) y no acierta siempre: se queda con el autor en vez del título,
o corta títulos largos. Por eso el CSV conserva `texto_ocr`, para corregir esas
filas sin reprocesar nada. Si ves un sello o colección que se cuela de forma
repetida, añade su patrón a `src/stopwords.py` y vuelve a correr `--solo ocr`.
