# Vida Interesante: sistema de videos automáticos

Canal: **Vida Interesante** (YouTube `interesantevida454@gmail.com`, TikTok "Vida Interesante").
Este repo guarda el motor (`engine.py`), los guiones (`guiones/`), los videos (`videos/`) y la lista de temas ya hechos (`temas_hechos.txt`).

## Cómo se hace un video (lo sigue la tarea programada)

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

6. **Renderizar:** `python3 engine.py guiones/X.json videos/X.mp4` (unos 3-4 minutos). Debe pesar menos de 100 MB.

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
