# Cómo actualizar el inventario con nuevos álbumes

Pasos para cuando aparezcan más URLs de álbumes de Google Photos y haya que
sumarlas al inventario que ve la app (front-invetario-ng).

## 1. Añadir las URLs nuevas

Agrega una línea por álbum en [`album.md`](album.md), con el mismo formato
que las existentes:

```
- https://photos.google.com/share/AF1Qip....?key=....
```

No borres las URLs que ya están: el pipeline usa `data/<carpeta>/manifest.json`
para recordar qué álbumes ya procesó, así que solo hace trabajo nuevo con las
que agregues.

## 2. Correr el pipeline

Desde la raíz del proyecto, con el entorno virtual activado:

```powershell
.\.venv\Scripts\python.exe -m src.main
```

Esto ejecuta las 5 etapas (`scrape` → `descargar` → `rotar` → `ocr` → `csv`)
para **todos** los álbumes de `album.md`, pero gracias al manifest los álbumes
ya procesados se saltan casi de inmediato — no hace falta filtrar nada a mano.

Motor de OCR:
- Por defecto usa Tesseract.
- Para usar Google Vision (mejor calidad, requiere `GOOGLE_VISION_API_KEY` en
  `.env`): añade `--motor vision`.

```powershell
.\.venv\Scripts\python.exe -m src.main --motor vision
```

Si algo falla a mitad de camino, puedes re-lanzar el mismo comando: retoma
donde quedó. Si necesitas rehacer un álbum concreto desde cero:

```powershell
.\.venv\Scripts\python.exe -m src.main --album caja-15 --forzar
```

Al terminar tendrás:
- Fotos descargadas en `descargas/<carpeta>/`
- Portadas enderezadas en `rotadas/<carpeta>/`
- `inventario.csv` regenerado completo (todas las filas, viejas y nuevas)

## 3. Optimizar y copiar las imágenes al front

El Angular sirve las imágenes desde `front-invetario-ng/public/rotadas/`, no
desde `rotadas/` directamente. Hay que sincronizarlas y comprimirlas:

```powershell
.\.venv\Scripts\python.exe scripts\optimizar_imagenes.py
```

Esto recorre **todo** `rotadas/` de nuevo, pero como reescribe archivo por
archivo no importa: es idempotente, solo tarda un poco más cuantas más fotos
haya. Usa `--dry-run` primero si quieres ver qué haría sin escribir nada.

## 4. Subir las filas nuevas a Supabase

El front no lee `inventario.csv`: lee la tabla `inventario` en Supabase. Importar
el CSV entero cada vez duplicaría las filas ya cargadas (no hay restricción de
unicidad sobre `carpeta`+`archivo`), así que hay que importar solo las filas del
álbum nuevo:

1. Abre `inventario.csv` en Excel/Sheets y filtra por la columna `carpeta` para
   quedarte solo con las filas del álbum recién agregado (p. ej. `caja-15`).
2. Copia esas filas (con el encabezado) a un CSV nuevo, por ejemplo
   `nuevo-caja-15.csv`.
3. En el [panel de Supabase](https://supabase.com/dashboard/project/vonmqsvepqyaeefzayeo) →
   **Table Editor** → tabla `inventario` → botón **Insert** → **Import data
   from CSV** → sube ese archivo.
   - Los nombres de columna del CSV ya coinciden con los de la tabla
     (`portada, titulo, album, carpeta, archivo, rotacion, titulo_confianza,
     texto_ocr, url_origen`), así que el mapeo es automático.
   - No incluyas `id`, `created_at` ni `eliminado`: se rellenan solos.

   Alternativa: si estás en una sesión de Claude Code con acceso al MCP de
   Supabase de este proyecto, puedes pedirle directamente "inserta en la tabla
   inventario las filas del álbum caja-15 del CSV" y lo hace por SQL sin pasar
   por el dashboard.

## 5. Publicar

Los cambios de datos (Supabase) ya quedan visibles al instante porque el front
los lee en vivo. Solo hace falta un deploy nuevo si cambiaste código del front
(no por agregar libros). Si sí tocaste código:

```powershell
git add -A
git commit -m "actualiza inventario"
git push
```

El workflow de GitHub Actions (`.github/workflows/deploy-gh-pages.yml`)
recompila y publica solo automáticamente.

## Notas

- `comparar_vision.py`, `probar_vision.py` y `codigo.js` están archivados en
  `backup/` — no son parte de este flujo.
- Pendiente de seguridad: la tabla `inventario` en Supabase tiene Row Level
  Security **desactivado**, así que cualquiera con la anon key (pública en el
  bundle del front) puede leer, insertar o borrar cualquier fila, no solo las
  suyas. No lo cambié porque activar RLS sin políticas bloquearía también al
  propio front. Si quieres, puedo proponerte políticas (p. ej. lectura pública
  pero escritura solo autenticada) para cerrar eso.
