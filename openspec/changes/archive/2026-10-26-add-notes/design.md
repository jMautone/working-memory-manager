## Context

Ver `proposal.md` para el porqué y el alcance; los requirements están en `specs/notes`, `specs/memory-store` y `specs/initiative-context`, y este documento no los repite.

Estado actual del código (`v0.1.0-alpha.1`):

- `src/wcm/cli.py`: árbol de `argparse` con `new`, `now`, `pause`, `resume`, `done`; un handler por comando que lee por `Store`, decide y recién después escribe. Los errores son `DomainError` (código 1) y `UsageError` (código 2).
- `src/wcm/model.py`: el archivo de iniciativa. Tiene el `_Loader` de PyYAML que lee todo escalar como texto salvo null y booleanos, y el `_Dumper` que escribe timestamps sin comillas. Los dos son privados del módulo.
- `src/wcm/store.py`: todo el efecto sobre `kbs/work/` (escaneo, IDs derivados, escritura atómica con `.tmp` y `os.replace`, checkpoints, `done/`).
- `src/wcm/ids.py`: solo IDs de iniciativa (`INIT-0007`, `init-7`, `7`).
- `src/wcm/render.py`: texto puro (`now`, brief, edades, truncado por columnas de terminal).
- `src/wcm/prompt.py`: `stdin_is_tty()` y `ask()`; los tests reemplazan los dos.
- `tests/conftest.py`: `WCM_HOME` en `tmp_path`, reloj inyectable y un `run(...)` que llama a `cli.main`.

Probado en Python 3.14 (macOS): `argparse` con un posicional `nargs="*"` acepta las opciones antes o después del texto (`note a b -t x`, `note -t x a b`), y rechaza con código 2 las opciones intercaladas (`note a -t x b`).

## Goals / Non-Goals

**Goals:**

- `wcm note "<texto>"` termina en bien menos de un segundo: no parsea ninguna nota, solo lista nombres de archivo para derivar el ID y escanea las iniciativas para encontrar la activa.
- Una nota editada a mano o en Obsidian nunca se re-renderiza: lo único que WCM toca después de crearla es el valor de `updated`.
- `wcm notes` y la línea `Notes:` del brief evitan parsear YAML de notas que no pueden coincidir.
- El editor se prueba de punta a punta en CI, con un editor falso, en los tres OS.

**Non-Goals:**

- Cambiar el formato de las iniciativas o de los checkpoints.
- Concurrencia: una persona, una máquina, comandos secuenciales (como en el change 1).
- Un pager para `wcm notes`.

## Decisions

### D1. El frontmatter se extrae a `frontmatter.py`, compartido por iniciativas y notas

`model.py` tiene hoy el loader, el dumper y el corte del frontmatter. Se mueven a `src/wcm/frontmatter.py`: `split(text) -> (lines del frontmatter, body, newline)`, `load(text) -> dict` y `dump(mapping) -> str`. `model.py` los importa y su comportamiento no cambia (lo cubren los tests existentes). El dumper suma una regla: un string que empieza con `[[` se escribe entre comillas dobles (`initiative: "[[INIT-0007]]"`), como lo escribe Obsidian en sus propiedades y como lo muestra la ADR 0002. YAML lo exige entre comillas de algún tipo, porque `[` abre una lista.

*Descartada:* importar `model._Loader` desde el módulo de notas; acopla las notas a un detalle privado de la iniciativa.
*Descartada:* `python-frontmatter`; una dependencia nueva para algo que ya está resuelto.

### D2. `note.py`: el archivo de nota, puro

`src/wcm/note.py` no toca el filesystem ni el reloj:

- `Note` (dataclass): `id`, `title`, `tags`, `initiative` (el ID vinculado o `None`), `created` (o `None`) y `body`.
- `parse(text, file_id) -> Note`: lanza `model.MalformedError` con el motivo (sin frontmatter, YAML inválido, no es un mapping, sin `id`, `id` distinto del nombre, sin título). El título sale de `title` o, si falta, del primer `# ` del body. `tags` acepta una lista o un string suelto.
- `link_of(value) -> str | None`: reconoce `[[INIT-0007]]`, `[[INIT-0007|alias]]` e `INIT-0007`, sin distinguir mayúsculas, y devuelve el ID canónico; cualquier otro valor es `None`.
- `render_new(note_id, title, tags, initiative, created) -> str`: frontmatter en el orden de la spec, una línea en blanco, `# <título>` y un `\n` final.
- `normalize_tags(values) -> list[str]`: separa por comas, recorta, quita un `#` inicial, descarta vacíos y repetidos (sin distinguir mayúsculas), y conserva el orden.
- `matches(note, terms, tags, initiative) -> bool`: cada término con `casefold()` contra el título, cada tag y el body; los tags con igualdad sin distinguir mayúsculas; la iniciativa por ID canónico.
- `touch_updated(text, when) -> str`: ver D6.

### D3. Las notas en `store.py`

`Store` suma, bajo `self.kb / "notes"`:

- `next_note_id()`: el máximo de `NOTE-(\d+)\.md` entre los nombres de `notes/` más uno, sin abrir archivos. Un archivo malformado cuenta.
- `note_path(note_id)` y `find_note_path(note_id)` (este último lanza `NotFound`). `note edit` abre por la ruta, sin parsear, así una nota malformada se puede arreglar.
- `scan_notes(prefilter=None) -> (list[NoteEntry], list[Problem])`: solo archivos que están directamente en `notes/` y cuyo nombre coincide con `NOTE-<dígitos>.md`. Lee el texto y, si se pasó `prefilter`, solo parsea los archivos para los que `prefilter(texto.casefold())` es verdadero (D7).
- `create_note(note_id, text)`: escribe en `<ID>.md.tmp`, verifica que `<ID>.md` no exista y hace `os.replace`; si existe, falla sin tocar nada. No hay carrera posible con una persona y comandos secuenciales (non-goal de concurrencia), y así el archivo nunca queda a medias.
- `replace_note(path, text)`: la misma escritura atómica de las iniciativas, para el `updated` después de editar.

`relative()` ya devuelve rutas relativas a la KB (`notes/NOTE-0005.md`) para los mensajes.

### D4. El editor en `editor.py`, el único efecto nuevo

`src/wcm/editor.py`:

1. `command()`: `VISUAL` si no está vacía; si no, `EDITOR`; si no, el default del OS.
2. `split(command)`: la cadena en programa y argumentos.
3. `open(path) -> int`: resuelve el programa con `shutil.which`, corre `subprocess.run([programa, *args, str(path)])` sin shell y con los streams heredados, y devuelve el código de salida. Si el programa no se encuentra o no arranca (`FileNotFoundError`, `PermissionError`, `OSError`), lanza `EditorError` con el comando que intentó.

Las dos formas, porque difieren:

```text
Windows                                     macOS y Linux
default    notepad                          vi
split      shlex.split(cmd, posix=False)    shlex.split(cmd)
           y quitar las comillas dobles
           que rodean cada token (las
           barras invertidas de C:\... son
           literales)
which      honra PATHEXT: "code" resuelve   busca en PATH
           a code.cmd, que CreateProcess
           no encontraría solo
ejemplo    "C:\Program Files\Notepad++\     nvim -u NONE
           notepad++.exe" -multiInst
```

`shutil.which` es lo que hace funcionar `EDITOR="code --wait"` en Windows: `code` es un `.cmd`, y `subprocess` sin shell solo encuentra `.exe`. Con la ruta completa, CreateProcess sí lo lanza.

*Descartada:* `shell=True`; cada OS cita distinto y la ruta de la nota pasaría por el parser de `cmd.exe` o de `sh`.
*Descartada:* abrir el editor sobre un temporal y crear la nota al cerrarlo; si el editor no arranca o se cuelga, la nota no existe, y guardar tiene que costar menos de 5 segundos pase lo que pase.

### D5. La línea de comandos de `note` y `notes`

- `note`: posicional `text` con `nargs="*"`, `-t/--tag` con `action="append"`, `-e/--edit` y `--free`. Si `text[0] == "edit"`, el handler toma la forma de edición: exige exactamente un argumento más, lo parsea con `ids.parse_note` y, si falla, levanta `UsageError` (código 2). `-t`, `-e` o `--free` junto con `edit` también son `UsageError`.
- `notes`: posicional `terms` con `nargs="*"`, `-t/--tag` con `action="append"` e `-i/--initiative` con el tipo `_id_arg` que ya usan `pause` y `resume` (un ID inválido sale con 2 desde `argparse`).
- `ids.py` suma `parse_note`, `format_note` y `NOTE_FILE` (`NOTE-(\d+)\.md`) con la misma regla que las iniciativas (`NOTE-0012`, `note-12`, `12`). `parse` y `format_id` no cambian de nombre, para no tocar al núcleo.

Las opciones intercaladas con el texto (`note a -t x b`) salen con código 2 desde `argparse`; la spec solo promete antes o después.

*Descartada:* un subparser `edit` dentro de `note`; `argparse` no permite un posicional libre y subcomandos en el mismo parser.
*Descartada:* `parse_intermixed_args`; no soporta subparsers.

### D6. `updated` después de editar, sin re-renderizar

`cmd_note` (forma de edición y `-e`) lee los bytes del archivo antes de abrir el editor y los compara después:

- Editor con código distinto de 0: código 1, sin escribir nada.
- Bytes iguales: `<ID> unchanged.`, sin escribir.
- Bytes distintos: decodifica, `note.parse(texto, id)`. Si falla, código 1 con la ruta y el motivo, sin escribir. Si anda, `note.touch_updated(texto, ahora)` y `store.replace_note`.

`touch_updated` trabaja por líneas sobre el frontmatter: reemplaza el valor de la primera línea `updated:` sin sangría y conserva su fin de línea (`\n` o `\r\n`). Si no hay `updated:`, agrega `updated: <ts>` antes del `---` de cierre con el fin de línea del archivo. El BOM, los comentarios YAML, las listas en flujo y el body quedan byte a byte. Es puro y se prueba con textos escritos a mano (Bloc de notas con `\r\n` y BOM, comentarios, `tags: [a, b]`).

*Descartada:* re-renderizar la nota con el dumper; pierde comentarios y estilo de flujo, y la nota es de la persona.
*Descartada:* no tocar `updated` después de editar; el campo mentiría desde la primera edición.

### D7. Búsqueda en dos pasos: prefiltro por texto, coincidencia exacta después

Para `notes` con términos, `-t` o `-i`, y para la línea `Notes:` del brief, el `cli` arma un prefiltro puro: cada término, cada tag (sin `#`) y el ID de la iniciativa en `casefold()` tienen que aparecer en el texto crudo del archivo, también en `casefold()`. Todo lo que puede coincidir de verdad aparece en el texto crudo (el título y los tags están en el frontmatter, el body está entero), así que el prefiltro solo descarta archivos que no pueden coincidir. Los que pasan se parsean y se comparan con `note.matches`.

Consecuencia: con filtros, `wcm notes` solo advierte las notas malformadas que pasan el prefiltro (las que podrían coincidir); sin filtros las advierte todas. La spec "Malformed notes are reported, never fixed" lo dice así (decidido al aplicar).

Para el brief, el prefiltro es el ID (`init-0007`) y la coincidencia exacta es `link_of(initiative) == ID`. La cantidad cuenta las notas válidas vinculadas; la última es la de `created` más reciente, con el ID más alto como desempate.

Orden de la lista (puro, en `render`): `created` más reciente primero; a igual `created`, ID más alto primero; sin `created`, al final por ID descendente.

*Descartada:* un índice; contradice "sin índices generados" y la ADR 0002 lo descarta.
*Descartada:* ordenar por `updated`; editar una nota vieja la subiría arriba y cambiaría el orden que la persona recuerda.

### D8. Salida: `render.note_list` y el brief

- `render.note_list(notes, now, width, ellipsis)`: una línea por nota, `  <ID>  <título>  <edad>  <INIT>`. El título se trunca con `truncate()` para que la línea quepa en `width`, con el ancho de terminal de `shutil.get_terminal_size(fallback=(100, 24))`, como `now`. La edad usa `render.age`. Después de la lista, una línea `!  Could not read notes/NOTE-0005.md: <motivo>` por nota malformada.
- `render.brief` suma un argumento `notes: tuple[int, str] | None` e imprime `  Notes:          3 (latest: <título>)` entre los campos de NOW y `Path:`, con la misma columna de etiquetas.
- `cmd_note` imprime `NOTE-0012 saved.` o `NOTE-0012 saved, linked to INIT-0007 Payment retries.`; con más de una activa, `!  More than one initiative is active (INIT-0003, INIT-0004); the note was not linked`.

### D9. El prompt de la nota

`prompt.py` suma `line(label, out) -> str`: imprime `Note` y lee con `input("> ")`. El handler lo llama solo si no hay texto y `stdin_is_tty()`. Sin terminal y sin texto, `UsageError`; no se lee stdin, porque por pipe Windows PowerShell 5.1 convierte los acentos en `?`. Ctrl+C y EOF siguen en el manejo que ya tiene `main` ("interrupted; nothing was changed", código 1).

### D10. Borde entre decisión pura y efecto

```text
puro (sin filesystem ni reloj)            efecto
-------------------------------------     ----------------------------------
ids       parse_note, format_note         store    listar notes/, leer texto,
note      parse, link_of, render_new,              create_note, replace_note
          normalize_tags, matches,        editor   VISUAL/EDITOR, which,
          touch_updated                            subprocess
frontmatter split, load, dump             prompt   tty, input
render    note_list, brief                clock    la hora
cli       prefiltro, orden, a quién
          vincular, qué imprimir
```

Cada handler lee por `store`, decide con funciones puras y escribe una vez al final. La única excepción es `note -e`: la nota se guarda antes de abrir el editor, a propósito (D4).

### D11. Tests

- Unidad: `note.parse` (mínima a mano, título desde el H1, `tags` string, cada motivo de malformada), `link_of`, `normalize_tags`, `matches`, `touch_updated` (con y sin `updated`, `\r\n`, BOM, comentarios) y `render.note_list` (truncado a 80 columnas, sin iniciativa, edad `?`).
- Punta a punta con `run(...)`: cada escenario de las specs.
- Editor: `tests/fake_editor.py` agrega al archivo el texto de `WCM_TEST_EDIT`, o sale con el código de `WCM_TEST_EXIT`, o no toca nada. El test pone `EDITOR` en `"<sys.executable>" "<ruta a fake_editor.py>"`, así ejercita las comillas de D4 en los tres OS de CI. El editor que no existe se prueba con un nombre inventado. El default por OS se prueba sobre `editor.command()` con `sys.platform` reemplazado, sin lanzar `notepad` ni `vi`.

## Risks / Trade-offs

- [`wcm notes` sin términos parsea todas las notas, y PyYAML puro tarda ~0,5 ms por frontmatter] → se mide en Windows con 1000 notas (tarea [manual]). Si pasa de 500 ms, `frontmatter.py` usa `yaml.CSafeLoader` cuando `yaml.__with_libyaml__` es verdadero (las wheels de PyPI lo traen), con los mismos resolvers.
- [El prefiltro descarta una nota cuyo título, escrito a mano, usa escapes YAML (`"\u00e9"`)] → el H1 del body casi siempre repite el título, así que el término aparece igual. Se acepta.
- [Un editor gráfico que vuelve enseguida (`code` sin `--wait`)] → WCM ve el archivo sin cambios e imprime `unchanged`. La nota igual queda guardada al cerrar el editor; el `updated` se corrige en la próxima edición. El README pide `--wait`.
- [Un `.cmd` como editor en Windows recibe sus argumentos por el parser de `cmd.exe`] → la ruta de la nota está bajo el hub y no lleva `%`, `^` ni `&` salvo que `WCM_HOME` los tenga; se documenta.
- [`wcm note edit` deja de ser una nota titulada "edit ..." sin comillas] → registrado en el proposal; la salida de `edit` con un ID inválido explica que el texto va entre comillas.
- [Una nota vinculada a una iniciativa cerrada sigue apuntando a `INIT-0007`] → es lo correcto: el link sigue resolviendo en Obsidian porque `done/INIT-0007/INIT-0007.md` conserva el nombre.

## Migration Plan

No hay nada que migrar: el primer `wcm note` crea `kbs/work/notes/`.

Rollback: volver a `v0.1.0-alpha.1`. Esa versión ignora `notes/` (requirement "Unrecognized files are ignored"), así que las notas quedan en disco, legibles en Obsidian, y vuelven a aparecer al reinstalar `alpha.2`.
