# 0002 — Notas y bases de conocimiento

- **Fecha**: 2026-10-12
- **Estado**: aceptada
- **Origen**: sesión de definición de producto con el autor (2026-10-12), sobre `persistent-working-memory-plan.md` y el change `add-working-memory-layer`.

## Contexto

El plan define WCM alrededor de una sola unidad: la iniciativa, el trabajo en vuelo que se suelta y se retoma. Su norte es "qué tan barato es cambiar de contexto" (§1, §2) y su núcleo es `pause`, `now` y `resume`.

El autor describe la herramienta como algo para "gestionar ideas y notas de manera rápida y fácil", y quiere que ese contenido sirva como base de conocimiento mantenida por agentes. En el modelo actual eso no tiene lugar:

- Una idea es una captura de una línea en el inbox, y su única salida es `promote`. No se puede descartar ni guardar.
- Una nota sobre una iniciativa tiene tres lugares parciales: el bloque NOW (se reescribe en cada pause), la cola Markdown de `initiative.md` (solo se escribe con `wcm edit` y ningún comando la muestra) y los checkpoints (no se cargan por defecto).
- Una nota que no es de ninguna iniciativa no tiene lugar.
- La búsqueda está en "DESPUÉS" (§8, §14).

La base de conocimiento sigue el patrón "LLM Wiki" que Andrej Karpathy publicó en abril de 2026 ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)):

- tres capas: fuentes crudas que el LLM lee pero nunca modifica, una wiki en Markdown que el LLM escribe y mantiene, y un archivo de esquema (`AGENTS.md` o `CLAUDE.md`) que define estructura y convenciones;
- tres operaciones: *ingest*, *query* y *lint*;
- un `index.md` (catálogo) y un `log.md` (cronológico, solo se agrega);
- Obsidian como lector;
- sin embeddings: según el autor del patrón, el `index.md` alcanza para navegar a escala moderada (~100 fuentes, algunos cientos de páginas), sin infraestructura de RAG.

Nada está implementado todavía: el único change está propuesto, sin aprobar y sin código. Cambiar el formato de los archivos ahora es barato; después del primer release es un breaking change.

## Decisión

### Producto

1. **WCM tiene dos ejes.** El primero es la memoria de trabajo: soltar, ver y retomar iniciativas. El segundo es el conocimiento: guardar y encontrar notas, que con el tiempo forman bases de conocimiento. El norte de §2 sigue siendo el del primer eje y el núcleo se construye primero. El segundo eje extiende el principio "la memoria humana no es el sistema de almacenamiento" de lo que estaba haciendo a lo que aprendí.

2. **Una captura no es una nota.** Una captura es algo que pide acción: entra al inbox y se procesa. Puede promoverse a iniciativa, convertirse en nota (`wcm promote <CAP> --note`, siempre en `work`, así su ID sigue a la vista de la derivación) o descartarse (`wcm drop <CAP>`). Al descartarla, la línea pasa a `inbox-dropped.md`, que también se escanea para derivar IDs, así un ID nunca se reutiliza. Una nota es algo para recordar y no pide nada: el inbox tiende a cero, las notas se acumulan.

### Notas

3. **Una nota es un archivo.** `notes/NOTE-0012.md`: frontmatter con `id`, `title`, `tags`, `initiative`, `capture`, `created` y `updated`, un H1 con el título y un cuerpo Markdown libre. Solo `id` y `title` son obligatorios.

4. **Crear una nota no abre nada.** `wcm note "<texto>"` guarda la nota con el texto como título, en menos de 5 segundos.
   - `-e` abre el editor para escribir el cuerpo en el momento; `wcm note edit <ID>` lo completa después.
   - `-t` suma tags; se repite o acepta comas.
   - Sin texto y en una terminal, `wcm note` y `wcm capture` piden una línea y la leen ellos mismos; sin terminal y sin texto, fallan. En Windows PowerShell 5.1 el texto como argumento es frágil: sin comillas, un `#` al comienzo de una palabra corta el resto y `;` lo parte en otro comando; entre comillas dobles, `$algo` se expande y las comillas internas no llegan a la CLI. Por pipe, los acentos llegan como `?`.

5. **La nota se vincula sola a la iniciativa activa.** Si hay una activa y la nota va a la KB `work`, su frontmatter guarda `initiative: "[[INIT-0007]]"`, y la salida lo dice. `--free` la deja suelta. `wcm resume` y `wcm show` muestran cuántas notas tiene la iniciativa y la última.

6. **Las notas se buscan por texto, sin índice.** `wcm notes [texto] [-t tag] [-i ID]` busca subcadenas sin distinguir mayúsculas en el título, los tags y el cuerpo, y ordena de la más nueva a la más vieja. Recorre los archivos sin un índice, como el resto del store.

7. **Los IDs se aceptan cortos.** `12`, `NOTE-0012` y `note-12` son la misma nota, igual que con las iniciativas y las capturas.

### Bases de conocimiento

8. **Hay varias KBs, separadas por tema y opcionalmente por lugar.** Por defecto una KB es una carpeta dentro del hub (`wcm kb new ideas`). Una KB también puede vivir en otra ruta y quedar registrada (`wcm kb new reading --path D:/vaults/reading`). Así el conocimiento de trabajo puede quedarse en la máquina de trabajo, y uno personal, como las lecturas, puede vivir en un repo propio.

9. **El hub no es una KB; cada KB es un vault.** `~/.wcm` (o `WCM_HOME`) guarda `config.yaml` y `kbs/`. Si el hub fuera el vault de trabajo, las otras KBs quedarían como vaults anidados, que Obsidian desaconseja, y el graph las mezclaría.

   ```text
   ~/.wcm/                         hub: no se abre en Obsidian
     config.yaml                   KBs registradas y la default
     kbs/
       work/                       vault "work", se crea en el primer uso
         inbox.md  inbox-dropped.md
         initiatives/INIT-0007/INIT-0007.md
         initiatives/INIT-0007/checkpoints/<ts>.md
         done/INIT-0003/INIT-0003.md
         notes/NOTE-0012.md
         AGENTS.md  raw/  wiki/    F3: la capa de los agentes
       ideas/                      vault "ideas": notes/ (y su capa de agentes)
   D:/vaults/reading/              vault "reading", registrado afuera
   ```

   Sin `config.yaml` existe solo `work`, en `kbs/work`: el núcleo de F1 no necesita configuración.

10. **Las iniciativas, el inbox y los checkpoints viven en la KB `work`.** Son su materia prima: la wiki de trabajo los lee. Las otras KBs tienen solo notas y su capa de agentes. `wcm note` escribe en la KB por defecto (`work`, salvo que `config.yaml` diga otra) o en la que indique `-k <kb>`. Solo las notas de `work` se vinculan a la iniciativa activa, porque los links no cruzan vaults.

11. **El nombre del archivo es el ID.** `notes/NOTE-0012.md` e `initiatives/INIT-0007/INIT-0007.md`, con `checkpoints/` al lado. El título vive en el frontmatter y en un H1, en notas e iniciativas: la iniciativa empieza con `# <título>` y su bloque pasa a `## NOW`. No hay slug. El motivo es que Obsidian no resuelve un link a un alias del frontmatter (`[[NOTE-0012]]` apuntando a `NOTE-0012-timeouts-del-gateway.md`); solo resuelve `[[archivo|alias]]`. Con el ID como nombre, el link corto `[[NOTE-0012]]` resuelve sin ayuda, cambiar un título no rompe nada, y "el ID es la identidad" pasa a ser literal.

12. **Los IDs de notas son por KB.** `NOTE-0012` puede existir en `work` y en `reading`; la CLI resuelve contra la KB por defecto o la de `-k`. `INIT` y `CAP` existen solo en `work`. Derivar `max + 1` asume que una sola máquina escribe cada KB. La sincronización sigue en "DESPUÉS" y, cuando llegue, va a obligar a revisar este punto.

13. **Las KBs se leen en Obsidian.** Cada KB es un vault independiente. Los links se escriben `[[ID]]`, también en el frontmatter (`initiative: "[[INIT-0007]]"`). WCM ignora `.obsidian/` y cualquier archivo que no reconoce.

### Agentes

14. **Las notas son de la persona; la wiki es de los agentes.**
    - Un agente lee `notes/`, `raw/`, las iniciativas, los checkpoints y el `AGENTS.md`, y nunca los reescribe.
    - Escribe solo en `wiki/`, y además agrega checkpoints por el contrato de §11.
    - El `AGENTS.md` lo genera WCM y lo ajusta la persona. En el patrón original lo co-escriben la persona y el LLM; acá no, para que la división de autoría sea simple.
    - WCM nunca lee `wiki/` para funcionar, así que sigue siendo utilizable sin LLM.
    - `wiki/index.md` es un índice generado, pero pertenece a los agentes, no al store. El principio "sin índices generados" se aplica a lo que WCM necesita para funcionar.

15. **El formato entra en F1; los agentes, en F3.** F1 define el layout, los nombres de archivo y los links. F3 (DELEGATE) suma el `AGENTS.md` de cada KB e *ingest*, *query* y *lint* como contrato de archivo, igual que el checkpoint de agente (§4.6, §11): WCM escribe el esquema y genera la instrucción, y el agente la ejecuta. Ningún comando de WCM llama a un LLM.

### F1

16. **F1 se corta en cinco changes y empieza por el núcleo.** Cada change publica su alpha. El uso real y el simulacro de F1 arrancan con la primera alpha. El test de salida se cierra después de la última, antes de `release/v0.1.0` (ADR 0001), y sigue midiendo time-to-pause y time-to-resume. El uso puede reordenar los changes 2 a 5, pero el cambio de orden se hace primero en la tabla de §14, en un PR `docs/`.

    | Orden | Change | Entrega |
    |---|---|---|
    | 1 | `add-working-memory-layer` | El store en el hub con la KB `work`, `new`, `now`, `pause`, `resume`, `done`, el wrapper de PowerShell con el cd y la alerta de activa sin checkpoint |
    | 2 | `add-notes` | `note`, `note edit`, `notes` |
    | 3 | `add-inbox` | `capture`, `inbox`, `promote` (a iniciativa o a nota), `drop` |
    | 4 | `add-knowledge-bases` | `config.yaml`, `kb new`, `kb list`, `-k`, KBs fuera del hub |
    | 5 | `add-initiative-tools` | `wait`, `list`, `show`, `checkpoint`, `edit` |

17. **`workspaces` mínimo desde F1.** La iniciativa guarda `workspaces: [{path, primary: true}]` en lugar de un `path` único. `resume` aterriza en el `path` del primary. F2 suma `repo`, `root` y `branch` a cada entrada sin romper el formato.

18. **Una alerta de atención se adelanta a F1.** `wcm now` avisa cuando la iniciativa activa lleva más de N horas sin checkpoint, contadas desde lo más reciente entre su `last_resumed` y su último checkpoint. Hasta que exista `wcm checkpoint` (change 5), el aviso sugiere `wcm pause`. El riesgo de abandono más probable es cambiar de tarea sin avisarle a WCM: la activa queda vieja y un pause con "Enter, Enter, Enter" confirma un estado que ya no es real. N se fija en el design del change.

19. **`wcm resume` sin ID retoma la activa.** Si hay una iniciativa activa, `wcm resume` sin ID vuelve a mostrar su brief y lleva a su carpeta, sin escribir un checkpoint.

## Consecuencias

- El plan cambia en este mismo PR: §1 a §9, §11 a §21 y §23. Los números de sección no cambian, porque `openspec/config.yaml`, `CONTRIBUTING.md` y la ADR 0001 los citan. §15 alinea además el boceto del wrapper con el protocolo `WCM_CD_FILE` que ya fijaba el design del change.
- El change `add-working-memory-layer` se achica al núcleo (change 1). Después de mergear este PR, en `v0.1/add-working-memory-layer` creada desde `main`, `/opsx:update` lo alinea con esta ADR:
  - el layout: hub, `kbs/work`, nombre de archivo igual al ID sin slug (se reescriben los requirements de identidad y de derivación de IDs de `memory-store`), y título en frontmatter y H1 con `## NOW`;
  - `workspaces: [{path, primary: true}]` en lugar de `path`;
  - `resume` sin ID con una activa (decisión 19), la alerta de `now` (decisión 18) y los IDs cortos (decisión 7);
  - se quitan la capacidad de inbox, los requirements de `wait`, `list`, `show`, `checkpoint` y `edit`, y en `now` la sección WAITING y la línea INBOX. No se crean todavía los otros changes: lo quitado queda en la historia de git como punto de partida;
  - el proposal suma las secciones Fase (con la rama) y Non-goals que pide `openspec/config.yaml`;
  - los arreglos de `tasks.md` que pide el paso 4 de la transición de la ADR 0001.

  Después el autor aprueba los artifacts, recién ahí corre `/opsx:apply`, y el archive va en el mismo PR.
- Los changes 2 a 5 se proponen de a uno, cuando se mergea el anterior. Cada uno retoma lo que se quitó del change 1 y toca lo que el núcleo ya tiene (la tabla de §14 dice qué).
- `openspec/config.yaml` se alimenta en cada artifact y hoy contradice este modelo. Antes del `/opsx:update` del change 1, en un PR `docs/`, hay que:
  - sumar el segundo eje al `context`;
  - reformular "el almacenamiento vive fuera de cualquier repo" (una KB registrada puede ser un repo propio) y "sin índices generados" (`wiki/index.md` es de los agentes);
  - sumar los principios y los invariantes nuevos de §3 y §17;
  - ampliar "el formato de los archivos de `~/.wcm`" a "del hub y de las KBs", también en `CONTRIBUTING.md` y en la regla del `!` de la ADR 0001, para que un cambio de formato en una KB externa también cuente como breaking.
- `config.yaml` llega en F1, con el change 4, no en F2 como suponía el change.
- Si una KB se escribe desde dos máquinas, los IDs pueden chocar. Queda como riesgo en §20 hasta que llegue el sync.

## Alternativas descartadas

- **Notas como bitácora con hora** (una línea en un archivo del día o de la iniciativa): más rápida, pero sin título, tags ni links por nota, y difícil de enlazar desde una wiki.
- **Notas solo dentro de iniciativas**: no cubre aprendizajes, links ni lecturas sueltas.
- **Un solo comando para capturas y notas, con `--todo`**: mezcla la cola de pendientes con lo que se guarda.
- **Todo entra por `capture` y se procesa a nota**: guardar un dato suelto cuesta un paso más.
- **Abrir siempre el editor al crear una nota**: cada nota cuesta abrir y cerrar el editor.
- **Vincular a la activa solo con `-i`**: las notas de trabajo quedan sueltas cada vez que falta el flag.
- **Una nota vinculada a varias iniciativas**: más superficie sin un caso que la pida.
- **Solo listar y filtrar por tag, búsqueda después**: encontrar es el uso principal de una nota.
- **Búsqueda difusa con ranking**: necesita un índice o una dependencia; se reconsidera si la de texto no alcanza.
- **Agentes que editan las notas**: mezcla quién escribió qué y rompe "la evidencia no se sobrescribe con conclusiones de agentes" (§17).
- **Agentes que solo leen, sin wiki**: pierde lo central del patrón, que el mantenimiento lo haga el LLM.
- **KB con agentes antes que `pause` y `resume`**: cambia el centro del producto antes de validar el núcleo.
- **El hub como vault de trabajo con las otras KBs adentro**: vaults anidados.
- **Iniciativas fuera de toda KB**: no se navegan en Obsidian y la wiki de trabajo no ve los checkpoints.
- **Que cada iniciativa elija su KB**: más reglas sin un caso que las pida.
- **ID más slug en el nombre, con links `[[archivo|ID]]`**: los links son largos de escribir a mano, y renombrar fuera de Obsidian los rompe.
- **El título como nombre de archivo**: el ID deja de ser la identidad, renombrar rompe links y dos títulos iguales chocan.
- **IDs de notas globales entre KBs**: obliga a escanear KBs externas que pueden no estar disponibles.
- **Un solo change para F1**: nada instalable hasta el final y un PR gigante.
- **Notas antes que el núcleo**: retrasa el test de salida de F1.
- **Un `path` único por iniciativa**: obliga a romper el formato en F2.
- **La iniciativa activa en el prompt de PowerShell**: ruido visual en cada línea; se reconsidera si la alerta de `now` no alcanza.
