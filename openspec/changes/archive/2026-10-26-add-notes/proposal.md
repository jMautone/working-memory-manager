## Why

Mientras se trabaja aparece algo que vale la pena guardar: un dato del gateway, una decisión, un link. Hoy no tiene lugar en `wcm`. Si es de la iniciativa activa, los únicos lugares son el bloque NOW, que se reescribe en cada pause, y la cola de `INIT-0007.md`, que solo se escribe a mano y ningún comando muestra. Si no es de ninguna iniciativa, no hay lugar. Así que queda en la cabeza o en un chat, justo lo que el producto quiere evitar.

En el flujo de la persona son dos momentos, y hoy los dos son caros:

- **Guardar**: anotar algo en menos de 5 segundos sin soltar lo que se está haciendo. Abrir un editor, elegir un archivo o pensar un nombre ya es demasiado.
- **Encontrar**: semanas después, recuperar ese dato sin recordar dónde se guardó ni de qué iniciativa era.

Este change suma el segundo eje del producto (ADR 0002): notas como archivos, vinculadas solas a la iniciativa activa, y una búsqueda de texto. Es el change 2 de 5 de la Fase 1. El núcleo ya está mergeado (`v0.1.0-alpha.1`) y en uso, así que las notas se pueden medir en el mismo simulacro de F1.

## What Changes

Tres comandos nuevos sobre la KB `work`, una línea nueva en el brief de `resume` y un directorio nuevo en el store. No hay cambios **BREAKING**: el formato de las iniciativas y de los checkpoints no cambia, y ningún comando ni flag existente cambia de significado.

### Agrega

Comandos:

- `wcm note [texto...]`: guarda una nota con el texto como título, sin abrir nada. Imprime `NOTE-0012 saved.` o `NOTE-0012 saved, linked to INIT-0007 <título>.`
  - `-t/--tag <tag>`: suma tags; se repite o acepta comas (`-t infra -t db`, `-t infra,db`).
  - `-e/--edit`: después de guardarla, abre la nota en el editor para escribir el cuerpo.
  - `--free`: no la vincula a la iniciativa activa.
  - Sin texto y con una terminal, pide una línea (`Note`) y la lee la CLI. Sin texto y sin terminal, falla con código 2.
- `wcm note edit <ID>`: abre una nota existente en el editor, incluso si está malformada (es la manera de arreglarla).
- `wcm notes [término...]`: lista las notas de la más nueva a la más vieja, una por línea (ID, título, edad, iniciativa vinculada). Cada término es una subcadena que tiene que aparecer, sin distinguir mayúsculas, en el título, en los tags o en el cuerpo.
  - `-t/--tag <tag>`: solo las notas que tienen ese tag; se repite o acepta comas.
  - `-i/--initiative <ID>`: solo las notas vinculadas a esa iniciativa.
- IDs de nota aceptados como `NOTE-0012`, `note-12` o `12`, sin distinguir mayúsculas, igual que las iniciativas.

Variables de entorno (las lee la CLI, no las define):

- `VISUAL`, y si no está, `EDITOR`: el editor que abren `note -e` y `note edit`. Sin ninguna, `notepad` en Windows y `vi` en macOS y Linux.

Archivos, bajo `<hub>/kbs/work/`:

- `notes/<ID>.md`, con `<ID>` = `NOTE-` y cuatro dígitos. Frontmatter YAML con `id`, `title`, `tags`, `initiative` (`"[[INIT-0007]]"` o `null`), `capture` (siempre `null` en este change; lo llena `add-inbox`), `created` y `updated`. Cuerpo: `# <título>` y Markdown libre. Solo `id` y `title` son obligatorios para leer una nota escrita a mano.

### Modifica

- El brief de `wcm resume` (también el de `resume` sin ID) suma, cuando la iniciativa tiene notas, la línea `Notes: 3 (latest: <título>)`, entre los campos de NOW y `Path:`.
- El layout del store suma `notes/`. Los archivos de `notes/` que no se llaman `NOTE-<dígitos>.md` se siguen ignorando.

### Quita

Nada.

### Supuestos registrados acá

Detalles que la ADR 0002 no fija; se pueden cambiar al aprobar:

- **Varios términos se combinan con AND.** `wcm notes gateway timeout` encuentra las notas que contienen las dos palabras, en cualquier campo. Entre comillas, `"gateway timeout"` es un solo término. Funciona igual con y sin comillas en PowerShell 5.1, donde las comillas son frágiles.
- **Las mayúsculas no importan; los acentos sí.** `versión` no encuentra `version`. Ignorar acentos se reconsidera con el uso.
- **Sin resultados no es un error.** `wcm notes` sin coincidencias imprime una línea y sale con 0.
- **Sin límite de resultados.** `wcm notes` sin términos lista todas. Si la lista deja de caber en una pantalla durante el simulacro, se suma un límite.
- **`-t` repetido es AND, y se compara sin distinguir mayúsculas.** Un `#` inicial en un tag se descarta, porque Obsidian guarda los tags del frontmatter sin `#`.
- **La edad y el orden salen de `created`.** `updated` es informativo.
- **`updated` sigue a las ediciones.** Si el archivo cambió mientras el editor estaba abierto, `wcm` actualiza solo la línea `updated:` del frontmatter y deja el resto del archivo byte a byte como lo escribió la persona.
- **Con más de una iniciativa activa en disco, la nota se guarda suelta** y la salida lo advierte. Nunca se pierde una nota por un estado ambiguo, y nunca se elige entre candidatas.
- **`edit` es una palabra reservada solo como primer argumento.** `wcm note edit 12` edita la nota 12. Para guardar una nota que empieza con la palabra "edit", el texto va entero entre comillas (`wcm note "edit the config"`) o por el prompt.
- **`-i` de `notes` falla con código 1 si la iniciativa no existe** (ni activa, ni pausada, ni en `done/`), para atrapar un ID mal tipeado.

## Fase

- **Fase**: F1 SWITCH (plan §14), change 2 de 5. Anterior: `add-working-memory-layer`. Siguientes: `add-inbox`, `add-knowledge-bases`, `add-initiative-tools`.
- **Rama**: `v0.1/add-notes`.
- **Versión**: publica `v0.1.0-alpha.2`.
- El test de salida de F1 no es una tarea de este change. Después de la última alpha se le suman las dos preguntas de las notas (qué se guardó en el momento y qué quedó para después, y si `wcm notes` encontró lo que se buscaba) y la métrica Time To Note < 5 s.

## Non-goals

- `-k <kb>`, otras KBs y `config.yaml` (`add-knowledge-bases`). Toda nota de este change va a `work`.
- `wcm promote <CAP> --note` y la derivación de IDs de captura desde el campo `capture` (`add-inbox`).
- Las notas en `wcm show` (`add-initiative-tools`).
- Vincular una nota a una iniciativa que no es la activa desde la CLI, o a varias. Se hace a mano en el frontmatter.
- Mostrar las notas en `wcm now`.
- Búsqueda difusa, con ranking, por acentos o con índice; fragmentos del cuerpo en los resultados.
- Borrar, renombrar o mover notas desde la CLI: se hace con el sistema de archivos o con Obsidian.
- La capa de agentes de la KB (`AGENTS.md`, `raw/`, `wiki/`), que llega en F3.

## OS impact

- **Editor por defecto**: `notepad` en Windows, `vi` en macOS y Linux, cuando no hay `VISUAL` ni `EDITOR`. Un editor gráfico que vuelve enseguida (`code` sin `--wait`) hace que `wcm` no vea los cambios hasta la próxima edición; el README lo explica.
- **Texto como argumento en Windows PowerShell 5.1**: sin comillas, un `#` al comienzo de una palabra corta el resto y `;` lo parte en otro comando; entre comillas dobles, `$algo` se expande. Por eso `wcm note` sin texto pide la línea y la lee la CLI. Por pipe los acentos llegan como `?`, así que la CLI no lee el título desde un pipe en ningún OS.
- Fuera de eso, el comportamiento es el mismo en los tres OS. Las notas se escriben en UTF-8 sin BOM y con `\n`, como el resto del store.

## Capabilities

### New Capabilities

- `notes`: el archivo de nota, guardar una nota (`note`), el vínculo automático a la iniciativa activa, editarla (`note edit`, `-e`) con el editor del OS, encontrarla (`notes`), sus IDs derivados y cortos, y las notas malformadas.

### Modified Capabilities

- `memory-store`: el layout suma `notes/<ID>.md`, los archivos no reconocidos de `notes/` se ignoran, y la escritura atómica cubre también las notas.
- `initiative-context`: el brief de `resume` suma la línea `Notes:` con la cantidad de notas vinculadas y la última.

## Impact

- Código: `src/wcm/cli.py` (comandos `note` y `notes`), `ids.py` (IDs de nota), `store.py` (notas en `kbs/work/notes/`), `render.py` (lista de notas y línea `Notes:` del brief), y módulos nuevos para el formato de la nota y para lanzar el editor. Tests nuevos bajo `tests/`.
- Sin dependencias nuevas: PyYAML sigue siendo la única.
- `README.md` suma la sección de notas y el editor. `shell/wcm.psm1` no cambia: ya conecta stdin, stdout y stderr a la consola, así que el prompt y el editor funcionan a través del wrapper.
- Sin red, sin LLM, sin índice: `notes` recorre los archivos en cada llamada.
