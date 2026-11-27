# Vida Interesante: sistema de videos automáticos

Canal: **Vida Interesante** (YouTube `interesantevida454@gmail.com`, TikTok "Vida Interesante").
Este repo guarda el motor (`engine.py`), los guiones (`guiones/`), los videos (`videos/`) y la lista de temas ya hechos (`temas_hechos.txt`).


## ⭐ FORMATO ACTUAL: videos 3D con voz neural (desde 26-11-2026)

Desde ahora **todos los videos se hacen en 3D** con `3d/engine3d.py` y la voz neural Kokoro (`em_alex`, neutral y natural). El motor 2D (`engine.py`) queda solo como respaldo si el 3D falla.

**Preparar el entorno:**
```bash
pip install moderngl kokoro-onnx soundfile piper-tts --break-system-packages -q
```
El modelo de voz (~350 MB) se descarga solo desde GitHub a `~/.cache/kokoro` la primera vez.

**Duración objetivo: 2:00 a 2:10** (unas 17-19 escenas y ~300-330 palabras). Revisar la duración al final; si sale de 1:50 a 2:20 está bien.

**Comandos:**
- Vista previa (un cuadro por escena, segundos): `python3 3d/engine3d.py --preview guiones/X.json /tmp/prev` → mirar `/tmp/prev/preview3d.jpg`. Corregir personajes cortados, textos encima de cosas importantes, utilería fuera de cuadro.
- Render (~8 min): `python3 3d/engine3d.py guiones/X.json videos/X.mp4`

**Guion 3D** (ejemplo completo: `guiones/2026-11-26-paso-dyatlov-parte-2.json`). Mismos campos que el 2D (`line`, `chip`, `big`, `emoji`, `title` en la primera y la última escena, `youtube`, `mood`) más:
- `set` (escenario): `forest_day`, `forest_night`, `snow_day`, `snow_night`, `desert`, `ocean`, `city_night`, `lab`, `red` (peligro/terror), `space`.
- `camera`: `medium` (normal), `close`, `wide`, `low` (mirando al cielo), `high` (desde arriba), `tall` (para cosas altas). En `space`: `space` o `space_far`.
- `props` (utilería 3D, lista): `{"type": ..., "x": ..., "z": ..., "s": escala}`. Tipos: `pine`, `snowpine`, `cedar` (`broken`: true), `deadtree`, `house`, `building`, `factory`, `tent` (`buried`, `torn`), `fire`, `rock`, `cactus`, `boots` (`n`), `footprints` (`n`), `orbs` (luces en el cielo, `y`, `n`), `moon` (`y`), `sun` (`y`, `r`), `ravine`, `avalanche`, `wave`, `table`, `flask`, `glow_items`, y para `space`: `earth`, `moon_planet`, `mars` (`r`, `y`, `spin`, `tilt`), `sun`, `ring`. Cada escenario ya trae decoración de fondo; `"keep_decor": false` la quita. x de -2 a 2 queda dentro de cuadro; z negativo = más al fondo.
- `stickman` (lista): `action`, `face`, `x` (0 a 1), `z`, `y` (altura, ej. trepado a un árbol), `facing`, `color` (`white`, `yellow`, `red`, `blue`, `green`, `orange`), `prop` (emoji en la mano), `say` (globo, máx. 3 palabras), `size`, `phase`, `fly`: true + `fly_at` (sale volando). En `space` el stickman se para sobre el planeta con `wx`, `wy`.
- `weather`: `snow`, `rain`, `dust`, `embers`, `none` (por defecto según el escenario).
- `shake_at`: segundo de la escena en que hay un golpe (sacude la cámara y suena un "boom"). `sfx: "boom"` solo el sonido.
- Si un tema necesita algo que no existe (un animal, un objeto), se puede agregar un tipo nuevo en `prop()` de `3d/engine3d.py` con las piezas básicas (`g.draw` con `sphere`, `cyl`, `cone`, `box`, `pyr`, `torus`), probar con la vista previa y hacer commit del cambio.
- En el texto narrado escribir los números con palabras ("mil seiscientos") para que la voz los lea bien. Nada de símbolos raros en `big` (la fuente no tiene ☢ ni similares).

## Cómo se hace un video (lo sigue la tarea programada)

0. **Leer `aprendizajes.md`** (si existe): ahí la revisión semanal anota qué funcionó en el canal y en canales parecidos. Aplicar esas conclusiones al elegir el tema, el gancho y el guion.

1. **Preparar el entorno**
   ```bash
   pip install piper-tts --break-system-packages -q
   ```
   La voz (piper `es-carlfm-x-low`) se descarga sola desde GitHub la primera vez. Se procesa con `VOICE_FX` de `engine.py` (tono parecido al audio de referencia del usuario, volumen alto, eco ligero). No cambiar este efecto salvo que el usuario lo pida.

2. **Elegir el tema.** Rotar entre las cuatro categorías, en este orden según la última línea de `temas_hechos.txt`:
   `¿Qué pasaría si...?` → `Datos curiosos` → `Misterios y terror` → `Historia oscura` → (vuelve a empezar).
   No repetir ningún tema de `temas_hechos.txt`. Temas populares y visuales, para público general (no dirigidos a niños).

3. **Investigar y verificar** con WebSearch los datos que se van a decir. Nada inventado. Las leyendas, teorías y casos sin resolver se presentan como tales ("se dice que", "según la leyenda", "una teoría dice"), y si existe una explicación oficial o científica, se dice al final. Nada de salud ni política presentado de forma engañosa.

4. **Escribir el guion** en `guiones/AAAA-MM-DD-slug.json` (copiar la estructura de `guiones/2026-11-24-paso-dyatlov.json`):
   - **Duración objetivo: 1:30** (80 a 95 segundos). Unas 11 a 13 escenas y 220 a 250 palabras de narración. Después de renderizar, si dura más de 100 s o menos de 75 s, ajustar el guion y volver a renderizar.
   - **Personajes stickman en TODAS las escenas** (`"stickman": [{...}]`, uno o dos por escena). Campos: `action` (`idle`, `talk`, `walk`, `run`, `run_away`, `scared`, `shiver`, `point`, `think`, `cheer`, `shrug`, `look`, `dizzy`, `sad`, `sneak`, `wave`), `face` opcional (`neutral`, `happy`, `fear`, `surprised`, `sad`, `cold`, `thinking`, `angry`, `dizzy`), `x` (0 a 1, posición horizontal; con dos personajes usar 0.35 y 0.65), `facing` (`right`/`left`), `color` (`white`, `yellow`, `red`, `blue`, `green`), `prop` (emoji que sostiene en la mano, ej. "🔦"), `say` (globo de diálogo corto, máx. 3 palabras, sin "¡" y "?" juntos), `phase` (desfase de animación si hay dos), `size` (por defecto 1.2). La acción debe ilustrar lo que dice la narración.
   - En la escena de cierre poner el stickman con `"x": 0.22, "size": 0.8` (por ejemplo `wave`) para no tapar el globo de comentarios.
   - Para que no se vea vacío: el motor agrega solo decoración en el suelo según el fondo, partículas (nieve, polvo, lluvia), barra de progreso y la marca "VIDA INTERESANTE". Se puede cambiar con `decor` (lista de 2 a 4 emojis) y `weather` (`snow`, `rain`, `dust`, `none`).
   - Escena 1 = gancho: `title` con 2 líneas cortas en mayúsculas (la segunda sale en amarillo), y una frase que enganche en 2 segundos.
   - Escenas intermedias: `chip` ("1 · ALGO"), `emoji` (1 a 3 emojis simples, sin combinaciones ZWJ), `anim` opcional (`float`, `shake`, `pulse`, `spin`, `fade_out`), `big` opcional (un número o palabra clave corta) y `line` (una o dos frases cortas).
   - Última escena = cierre: `title` con 2-3 líneas y una pregunta para comentar.
   - `bg` disponibles: `space` (con `planet`: `earth`, `moon`, `mars`, `sun` o `none`), `night` (`planet: moon` opcional), `ocean`, `underwater`, `fog` (bosque con niebla, terror), `sepia` (papel antiguo, historia), `lab` (ciencia, cuerpo humano), `fire` (peligro, guerra, terror), `desert`, `city`.
   - `mood`: `dark` para misterio/terror/historia oscura (música grave con latidos, viñeta y grano), `bright` para ciencia y datos curiosos.
   - `youtube`: `title` (máx. 100 caracteres, con emoji y `#shorts`), `description` (resumen, fuentes y hashtags), `tags`.

5. **Revisar antes de renderizar:** `python3 engine.py --preview guiones/X.json /tmp/prev` y mirar `/tmp/prev/preview.jpg` (textos que no se salgan, emojis visibles).

6. **Renderizar** con el motor 3D (ver arriba). Solo si falla, usar `python3 engine.py guiones/X.json videos/X.mp4` (2D). Debe pesar menos de 100 MB.

7. **Guardar en GitHub:** agregar el tema al final de `temas_hechos.txt` (`AAAA-MM-DD | categoría | tema`), luego `git add`, `git commit` y `git -c push.negotiate=true push origin main`.

8. **Subir a YouTube como PRIVADO** con el conector Windsor.ai (`connector: youtube`, cuenta `118909`, acción `upload_video`):
   - `video_url`: `https://raw.githubusercontent.com/adrianyourmon-source/vida-interesante-videos/main/videos/X.mp4`
   - `title`, `description`, `tags` del guion
   - `made_for_kids: false` (contenido para público general)
   - `privacy_status: "private"`. **Nunca** `public` ni `publish_at` sin que el usuario lo apruebe en el chat.

9. **Avisar al usuario** (SendUserFile con el mp4, para que también lo suba a TikTok a mano, y un mensaje con el título, el enlace de YouTube y un resumen de los datos). Pedirle que responda **"publica"** para hacerlo público (con `update_video_details`, `privacy_status: "public"`), o que lo haga él en YouTube Studio.

## Notas
- TikTok: el conector no permite subir videos, solo gestionar comentarios. El usuario los sube a mano.
- Si una descarga, el push o la subida fallan, no reintentar en bucle: avisar al usuario qué falló.
