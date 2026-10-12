# Plan: Working Memory Layer (WCM)

> El sistema recuerda dónde quedó el trabajo para que la persona pueda dejar de hacerlo.

---

## 1. El problema, reducido a su núcleo

El desarrollo asistido por agentes multiplica la cantidad de trabajo que una persona puede tener en vuelo. No multiplica su capacidad de recordar dónde quedó cada cosa.

Hoy el estado mental de una iniciativa vive en tres lugares frágiles:

```text
la cabeza de la persona
terminales abiertas
historiales de chat
```

Evidencia local: esta máquina tiene 327 sesiones de Copilot CLI en `~/.copilot/session-state`. Cada una fue, en algún momento, "la sesión donde estaba haciendo X". Ninguna responde hoy qué era X ni qué faltaba.

Todo el plan cabe en una frase:

> **El cambio de contexto es caro porque el estado mental vive en la cabeza y en chats, no en un lugar que responda "¿dónde quedé y qué sigue?" en segundos.**

De ahí salen exactamente tres necesidades, que son el núcleo:

```text
  +--------------------------------------------------------------+
  |  1. SOLTAR      pause:  externalizar el estado en < 30 s     |
  |  2. VER         now:    que requiere mi atencion, global     |
  |  3. RETOMAR     resume: recuperar contexto en < 30 s         |
  +--------------------------------------------------------------+
        Todo lo demas (Git, sesiones, agentes, findings,
        decisiones) existe para hacer estas tres cosas mas
        baratas o mas confiables. No al reves.
```

### 1.1 Segundo eje: conocimiento

Mientras se trabaja también se aprende: un dato del gateway, una decisión, un artículo leído. Eso vive hoy en los mismos lugares frágiles, o en ninguno. WCM lo externaliza igual que el estado de trabajo:

```text
  +--------------------------------------------------------------+
  |  A. GUARDAR     note:   anotar algo en < 5 s, sin soltar     |
  |                         lo que estoy haciendo                |
  |  B. ENCONTRAR   notes:  volver a encontrarlo semanas despues |
  +--------------------------------------------------------------+
        Las notas viven en bases de conocimiento (KB) que se
        abren en Obsidian y que, desde la Fase 3, los agentes
        mantienen como una wiki (ver 12.2).
```

El norte de §2 no cambia: las tres operaciones de arriba siguen siendo el núcleo y se construyen primero (§14). La búsqueda de notas (§7.4) sirve a este segundo eje, no al núcleo. El segundo eje extiende el primer principio de §3, de lo que estaba haciendo a lo que aprendí. La decisión y sus alternativas están en [`docs/decisions/0002-notas-y-bases-de-conocimiento.md`](docs/decisions/0002-notas-y-bases-de-conocimiento.md).

---

## 2. Objetivo y North Star

> **Interrumpir cualquier iniciativa, sacarla de la memoria de corto plazo, y retomarla horas, días o semanas después en menos de 30 segundos sin releer conversaciones.**

North Star:

> **How cheaply can a human safely switch context?**

No se mide en sesiones administradas, documentos generados ni tokens ahorrados.

### Criterios de éxito

- [ ] Puedo cerrar todas las terminales sin miedo a olvidar en qué estaba.
- [ ] Puedo interrumpir una feature por un incidente en menos de 30 segundos.
- [ ] Después de varios días entiendo una iniciativa pausada en menos de 30 segundos.
- [ ] No necesito buscar qué sesión de Copilot contenía determinada información.
- [ ] Desde cualquier carpeta veo todo mi working set.
- [ ] Una iniciativa puede abarcar varios repositorios y worktrees.
- [ ] Toda iniciativa pausada tiene una siguiente acción.
- [ ] Un agente nuevo puede continuar sin recuperar la sesión anterior.
- [ ] El estado declarado puede contrastarse con Git.
- [ ] Puedo capturar una preocupación nueva sin romper la concentración actual.
- [ ] Puedo guardar una nota en menos de 5 segundos sin cambiar de iniciativa.
- [ ] Encuentro una nota de hace semanas sin recordar dónde la guardé.
- [ ] Cada base de conocimiento se abre en Obsidian y sus links funcionan.
- [ ] La herramienta reduce, en vez de aumentar, el trabajo administrativo.

---

## 3. Principios

**La memoria humana no es el sistema de almacenamiento.** Si el usuario siente que igual debe recordar algo después de pausar, el pause fue insuficiente.

**La iniciativa está por encima del repositorio.** Una iniciativa tiene 0..N repos, worktrees, branches, sesiones y agentes. El almacenamiento principal vive fuera de cualquier repo.

**Las sesiones son descartables.** Una sesión es un entorno de ejecución conversacional. Borrarla no debe impedir continuar.

**Git es evidencia, no memoria de trabajo.** Git responde qué cambió. WCM responde qué intentaba, por qué, dónde quedé y qué sigue.

**Estado actual antes que historial.** `resume` carga el estado actual. El historial se consulta solo cuando hay que investigar cómo se llegó ahí.

**Contexto humano y contexto de agente son productos distintos.** Una persona retoma con 5 a 15 líneas. Un agente puede necesitar plan, diff, decisiones y archivos.

**Markdown y YAML como almacenamiento.** Legible, versionable, editable a mano, reconstruible sin la herramienta.

**Utilizable sin LLM.** Todo lo que un agente puede escribir, una persona también puede escribirlo. El agente es un acelerador, no una dependencia.

**Advertir, no corregir en silencio.** Estados ambiguos se muestran, no se arreglan solos.

**Las notas son de la persona; la wiki es de los agentes.** Un agente lee notas, fuentes, iniciativas y checkpoints, pero solo escribe en la wiki de una KB y en checkpoints por contrato (§11). WCM nunca necesita la wiki para funcionar.

**El ID es el nombre del archivo.** `NOTE-0012.md`, `INIT-0007/INIT-0007.md`. Un link `[[NOTE-0012]]` se resuelve en Obsidian y en WCM, y cambiar un título no rompe nada.

---

## 4. Nueve decisiones estructurales

Estas decisiones son las que diferencian este plan de una lista de features. Cada una simplifica algo aguas abajo.

### 4.1 Una sola iniciativa activa

Hay una persona. La atención humana es singular. Agentes pueden correr en segundo plano sobre iniciativas pausadas; eso no cambia qué está atendiendo la persona.

Definición operativa: **active es lo que retomo si se cierra la terminal.**

Consecuencia: `wcm resume B` pausa automáticamente la iniciativa activa anterior. El **switch** es la operación primitiva. `pause` es un switch a nada.

```text
        wcm resume B
   +-----------------------------------------------+
   |  A active --> checkpoint(A) --> A paused      |
   |                                B active       |
   +-----------------------------------------------+
   Un solo comando. Una sola pregunta obligatoria:
   "Next action para A?"
```

### 4.2 Cuatro estados, no ocho

```text
active    lo que atiendo ahora (a lo sumo una)
paused    interrumpida deliberadamente; tiene next action
waiting   no puede progresar; tiene `on:` (que espera, de quien depende)
done      objetivo cumplido
```

Lo que no es estado:

- `inbox` es otra entidad: capturas, no iniciativas.
- `ready` se infiere: `paused` con `last_resumed: null`.
- `blocked` es `waiting` con `on.owner: me`.
- `archived` es `done` con más de N días; se oculta de `list` por defecto.

Menos estados, menos invariantes, menos trabajo administrativo.

### 4.3 Un archivo por iniciativa, y uno por nota

Frontmatter YAML para lo mecánico. Cuerpo Markdown para el contexto humano. Sin índice derivado hasta que duela: escanear 20 frontmatters es instantáneo, y unos miles de notas también.

### 4.4 Tres fuentes de estado en el pause, con costos distintos

```text
  Fuente     Costo             Fase   Que aporta
  ---------  ----------------  -----  --------------------------------
  Humano     1-3 preguntas,    1      next action (obligatorio),
             Enter = mantener         donde pare, algo importante
  Git        gratis            2      branch, dirty files, commits
  Agente     una convencion    3      lo semantico que Git no sabe
             de archivo
```

En Fase 1 escribe el humano. El prompt viene pre-llenado con el valor anterior: "Enter, Enter, Enter" es un pause válido si nada cambió.

### 4.5 Descubrimiento de sesiones en modo lectura

Cada sesión de Copilot CLI ya tiene un `workspace.yaml` con:

```text
id, cwd, git_root, repository, branch, created_at, updated_at
```

WCM escanea ese directorio y asocia sesiones a iniciativas por `git_root` y `branch`. Cero adapter, cero API. El link manual queda para la excepción. Esto va en Fase 2, no en una fase de "integración con agentes".

### 4.6 Checkpoints de agente por contrato de archivo, no por adapter de runtime

WCM no integra Copilot CLI. Define un contrato: "escribí un checkpoint en esta ruta con esta plantilla". Cualquier agente que pueda escribir archivos lo cumple. Copilot, Claude Code, o el que venga.

### 4.7 Wrapper de shell como entregable

Un proceso hijo no puede hacer `cd` en el shell padre. `wcm resume` promete llevarte al `path` del workspace primario. Se distribuye una función de PowerShell `wcm` que envuelve al binario y ejecuta el `cd` que este le indique. Es parte del producto desde el día uno.

### 4.8 El conocimiento vive en KBs, y cada KB es un vault

Una KB es una carpeta de notas que se abre en Obsidian como vault. Puede haber varias, separadas por tema (trabajo, ideas, lecturas). Cada una vive dentro de `~/.wcm` o en otra ruta registrada, por ejemplo un repo personal, porque no todo el conocimiento puede estar en la misma máquina. La KB `work` es especial: además de notas, tiene las iniciativas, el inbox y los checkpoints, que son su materia prima.

### 4.9 Notas de la persona, wiki de los agentes

WCM adopta el patrón "LLM Wiki" de Karpathy (§12.2) con una división de autoría estricta. La persona escribe notas rápido, desde la CLI. Los agentes compilan y mantienen una wiki encima. WCM define el formato desde la Fase 1 y el contrato de los agentes en la Fase 3; ningún comando de WCM llama a un LLM.

---

## 5. Modelo

### 5.1 Entidades de Fase 1

```text
Initiative     unidad de trabajo con estado, contexto humano y next action
Capture        una linea en el inbox; se promueve a Initiative o a Note,
               o se descarta
Checkpoint     fotografia semantica append-only de una Initiative
Note           un archivo con titulo, tags y cuerpo; puede vincularse a
               una Initiative
Knowledge Base carpeta de notas que se abre como vault de Obsidian; `work`
               tiene ademas las iniciativas, el inbox y los checkpoints
Workspace      en F1 solo `path` y `primary`: donde aterriza `resume`
```

### 5.2 Entidades de Fase 2 en adelante

```text
Workspace      F2 le suma repo, root y branch (ver 9)
Session        referencia descubierta o vinculada a una sesion de agente
Wiki page      F3: pagina de la wiki de una KB, escrita por agentes (ver 12.2)
Decision       solo si el simulacro de F1 muestra que hace falta
Finding        idem
```

### 5.3 Tres niveles de memoria

```text
  NIVEL 1  Working Set        wcm now         que requiere mi atencion
  NIVEL 2  Initiative Memory  INIT-0007.md    que pasa con esta iniciativa
  NIVEL 3  Evidencia          Git, checkpoints, sesiones, docs en repo,
                              notas, wiki
```

Ni humanos ni agentes cargan el nivel 3 completo por defecto. De las notas, el nivel 2 solo muestra cuántas tiene la iniciativa y la última; el resto se busca.

---

## 6. Almacenamiento

```text
~/.wcm/                             # WCM_HOME: el hub; no se abre en Obsidian
  config.yaml                       # KBs registradas y la default (ver 6.5)
  kbs/
    work/                           # vault "work"; se crea en el primer uso
      inbox.md                      # una captura por linea
      inbox-dropped.md              # capturas descartadas; solo crece
      initiatives/
        INIT-0007/
          INIT-0007.md              # frontmatter + NOW; se reescribe
          checkpoints/
            2026-09-16T1640.md      # append-only; HOW WE GOT HERE
        INIT-0008/
          INIT-0008.md
      done/                         # iniciativas movidas al cerrar
      notes/
        NOTE-0012.md                # una nota por archivo
      AGENTS.md  raw/  wiki/        # Fase 3: la capa de los agentes (ver 12.2)
    ideas/                          # otra KB: solo notas, y su capa de agentes
      notes/
D:/vaults/reading/                  # KB registrada fuera del hub
  notes/
```

Reglas:

- Los IDs se derivan del máximo existente dentro de la KB: `INIT` en `initiatives/` y `done/`, `NOTE` en `notes/`, `CAP` en `inbox.md`, `inbox-dropped.md` y el campo `capture` de iniciativas y notas. No hay contador que se pueda corromper.
- El nombre del archivo, y el del directorio de una iniciativa, es el ID. El título vive en el frontmatter y en el H1, en notas e iniciativas, así Obsidian lo muestra. No hay slug.
- Los IDs de notas son por KB: `NOTE-0012` puede existir en `work` y en `reading`. La CLI resuelve contra la KB por defecto, o contra la de `-k <kb>`. `INIT` y `CAP` existen solo en `work`.
- Los IDs se aceptan cortos: `7`, `init-7` e `INIT-0007` son la misma iniciativa; lo mismo para notas y capturas.
- WCM ignora `.obsidian/` y cualquier archivo que no reconoce.
- Se asume que una sola máquina escribe cada KB. Sincronizar una KB entre máquinas queda para DESPUÉS y va a obligar a revisar la derivación de IDs (§20).
- Nada de esto vive en el repositorio de código de una iniciativa. Una KB registrada puede ser un repo propio (por ejemplo, uno personal de lecturas). Lo que el equipo deba compartir (planes, decisiones) puede vivir en `repo/.ai/` y ser referenciado desde WCM.

### 6.1 La iniciativa: `INIT-0007.md`

```markdown
---
id: INIT-0007
title: Payment retries
type: feature            # feature | bug | incident | research | refactor | other
status: paused           # active | paused | waiting | done
priority: normal         # critical | high | normal | low
created: 2026-09-10T09:12:00-03:00
updated: 2026-09-16T16:40:00-03:00
last_resumed: 2026-09-16T14:12:00-03:00
last_paused: 2026-09-16T16:40:00-03:00
waiting_on: null         # { what: "...", owner: me | <nombre>, since: <ts> }
tags: [payments]
workspaces:              # F1: path y primary; F2 suma repo, root y branch (§9)
  - path: C:/wt/payment-retries
    primary: true
sessions: []             # Fase 2
links: []                # work items externos, PRs, docs
capture: null            # CAP-<NNNN> si vino de `wcm promote`
---

# Payment retries

## NOW

**Focus:** Implementar la política de retry para autorizaciones de pago.

**Stopped at:** Clasificación de reintentos hecha; el backoff está incompleto.

**Why it matters:** El proveedor puede devolver el mismo transaction ID después de un timeout.

**Important:** Validar idempotencia antes de habilitar retries.

**Next:** Terminar `PaymentRetryPolicy` y verificar el comportamiento con transacciones duplicadas.
```

El H1 repite el título del frontmatter, para que Obsidian muestre algo legible en un archivo que se llama como el ID.

Restricciones del bloque NOW:

- Cinco campos fijos. Solo `Next` es obligatorio.
- Se reescribe en cada pause. Nunca crece como timeline.
- Si supera ~15 líneas, `wcm now` lo advierte.

### 6.2 `inbox.md`

```markdown
- 2026-09-16T15:02 CAP-0027 Revisar posible leak de refresh tokens
- 2026-09-16T15:40 CAP-0028 Preguntar a infra por el timeout del gateway
```

Una captura pide acción; el inbox tiende a cero. Cada captura tiene tres salidas:

- `wcm promote CAP-0027` corta la línea y crea una iniciativa con ese título.
- `wcm promote CAP-0027 --note` la convierte en nota (§6.4), siempre en `work`, sin importar la KB por defecto: así su ID sigue a la vista de la derivación.
- `wcm drop CAP-0027` la descarta: la línea pasa a `inbox-dropped.md`, así su ID no se reutiliza.

`wcm capture` sin texto, en una terminal, pide una línea y la lee él mismo, por el mismo motivo que `wcm note` (§7.4).

### 6.3 Checkpoint

```markdown
# Checkpoint 2026-09-16T16:40

Author: human | agent:<session-id>
Trigger: pause | switch | milestone | manual

## Focus
## Completed since previous checkpoint
## Incomplete work
## Discoveries
## Open questions
## Next action
## Workspace snapshot        (Fase 2: branch, dirty files, ultimos commits)
```

Un checkpoint no es una copia del chat. Es lo que Git no puede saber.

### 6.4 Nota: `NOTE-0012.md`

```markdown
---
id: NOTE-0012
title: el gateway corta a los 30s, no a los 60
tags: [infra]
initiative: "[[INIT-0007]]"    # null si es suelta
capture: null                  # CAP-<NNNN> si vino de `promote --note`
created: 2026-10-12T14:32:00-03:00
updated: 2026-10-12T14:32:00-03:00
---

# el gateway corta a los 30s, no a los 60

Lo confirmó infra. Ver [[NOTE-0004]].
```

Restricciones:

- Solo `id` y `title` son obligatorios. El cuerpo puede estar vacío.
- Los links se escriben `[[ID]]`, también en el frontmatter. Obsidian los resuelve porque el archivo se llama así; un link a un alias del frontmatter no se resolvería.
- Una nota pertenece a una sola KB. Los links no cruzan KBs.
- Como en la iniciativa, lo que la persona escribe a mano se preserva.

### 6.5 KBs y `config.yaml`

```yaml
default_kb: work
kbs:
  work:    { path: kbs/work }              # relativa al hub
  ideas:   { path: kbs/ideas }
  reading: { path: D:/vaults/reading }     # registrada fuera del hub
```

- `wcm kb new <nombre>` crea la KB bajo `kbs/`. Con `--path <dir>` la crea o registra en otra ruta. `wcm kb list` las muestra.
- Sin `config.yaml` existe solo `work`, en `kbs/work`: el núcleo de F1 no necesita configuración.
- Cada KB es un vault de Obsidian independiente. El hub no es un vault: si lo fuera, las KBs quedarían como vaults anidados.

---

## 7. Las tres operaciones, y las notas

### 7.1 `wcm pause [ID]`

Sin ID, pausa la activa. Si no hay activa, lo dice y termina.

```text
PS> wcm pause

INIT-0007 Payment retries

Next action  [Terminar PaymentRetryPolicy y verificar duplicados]
> _
Stopped at   [Clasificacion hecha; backoff incompleto]
> _
Important    [Validar idempotencia antes de habilitar retries]
> _

  Checkpoint saved.
  Safe to switch context.
```

- Enter mantiene el valor anterior. Tres Enter es un pause válido.
- `Next` vacío y sin valor anterior: no se pausa. Es el único invariante duro.
- Flags para el caso urgente: `wcm pause -n "next action"` pausa sin prompts.
- Fase 2: adjunta el snapshot de Git al checkpoint sin preguntar.
- Fase 3: si hay una sesión de agente asociada, ofrece el prompt de checkpoint.

### 7.2 `wcm resume [ID]`

```text
PS> wcm resume INIT-0007

INIT-0007 Payment retries
paused 2 days ago

  Focus:       Implementar la politica de retry para autorizaciones.
  Stopped at:  Clasificacion hecha; backoff incompleto.
  Important:   Validar idempotencia antes de habilitar retries.
  Next:        Terminar PaymentRetryPolicy y verificar duplicados.

  Notes:       3 (latest: el gateway corta a los 30s, no a los 60)
  Workspace:   payments  feature/payment-retries  C:\wt\payment-retries
  Sessions:    2 (last active 2d ago)                       <- Fase 2
```

- Si había otra activa, corre el flujo de pause sobre ella primero.
- Sin ID y con una activa, vuelve a mostrar su brief y lleva a su carpeta, sin escribir un checkpoint.
- El wrapper de shell hace `cd` al `path` del workspace primario si existe.
- Fase 2: si la branch real difiere de la declarada, lo advierte.
- Fase 3: `--agent` lanza una sesión nueva con el contexto armado.

### 7.3 `wcm now`

```text
PS> wcm now

ACTIVE
  INIT-0008  Login incident                 critical   1h 23m
             Next: reproducir la race condition del lockout

PAUSED
  INIT-0007  Payment retries                           2d
             Next: terminar PaymentRetryPolicy y verificar duplicados
  INIT-0005  Security analysis                         5h
             Next: validar el flujo de refresh de tokens

WAITING
  INIT-0003  API migration                             6d
             on: aprobacion de arquitectura (owner: Ana)

INBOX  3 capturas sin procesar

!  INIT-0005 pausada hace 5h con working tree sucio    <- Fase 2
```

Esta pantalla es la memoria externa del usuario. Debe caber en una pantalla de terminal.

Desde F1, `now` avisa cuando la activa lleva más de N horas sin checkpoint (`!  INIT-0008 active for 6h without a checkpoint`). Las horas se cuentan desde lo más reciente entre su `last_resumed` y su último checkpoint. Hasta que exista `wcm checkpoint` (change `add-initiative-tools`, §14), el aviso sugiere `wcm pause`. El riesgo de abandono más probable es cambiar de tarea sin avisarle a WCM: la activa queda vieja, y un pause con "Enter, Enter, Enter" confirma un estado que ya no es real. Es la única alerta de §13 que se adelanta.

### 7.4 `wcm note` y `wcm notes`

```text
PS> wcm note "el gateway corta a los 30s, no a los 60" -t infra
  NOTE-0012 saved, linked to INIT-0007 Payment retries.

PS> wcm note -k reading "Thinking in Systems: stocks y flows"
  NOTE-0003 saved in reading.

PS> wcm notes gateway
  NOTE-0012  el gateway corta a los 30s, no a los 60   2h   INIT-0007
  NOTE-0004  gateway: retries en el borde              3w
```

- `wcm note "<texto>"` guarda la nota sin abrir nada: el texto es el título. `-e` abre el editor para escribir el cuerpo; `wcm note edit <ID>` lo completa después. `-t` suma tags.
- Sin texto y en una terminal, la CLI pide una línea y la lee ella misma. En Windows PowerShell 5.1 el texto como argumento es frágil: sin comillas, un `#` al comienzo de una palabra corta el resto y `;` lo parte en otro comando; entre comillas dobles, `$algo` se expande y las comillas internas no llegan a la CLI. Por pipe, los acentos llegan como `?`.
- En `work`, `-i` filtra por iniciativa. Las notas de otras KBs nunca se vinculan, porque los links no cruzan vaults.
- En `work`, la nota se vincula sola a la iniciativa activa; `--free` la deja suelta. `resume` y `show` muestran cuántas notas tiene la iniciativa y la última.
- `wcm notes [texto] [-t tag] [-i ID]` busca subcadenas sin distinguir mayúsculas en el título, los tags y el cuerpo, de la más nueva a la más vieja. Recorre los archivos sin índice.

---

## 8. Comandos por fase

```text
FASE 1   nucleo   new, now, pause, resume, done
         notas    note, note edit, notes
         inbox    capture, inbox, promote, drop
         KBs      kb new, kb list
         resto    wait, list, show, checkpoint, edit
FASE 2   workspace add|list, status, session list|link
FASE 3   context --role, resume --agent, checkpoint --from-agent,
         esquema y operaciones de KB para agentes (ver 12.2)
FASE 4   attention, wrap
DESPUES  busqueda semantica, ask, sync
```

El orden de la Fase 1 es el de los changes de §14. `edit` abre el archivo de la iniciativa (`INIT-0007.md`) en `$EDITOR`. Es la válvula de escape: todo lo que la CLI no cubre se hace a mano.

---

## 9. Workspaces y resolución por CWD (Fase 2)

```yaml
workspaces:
  - path: C:/wt/payment-retries        # F1: donde aterriza resume
    primary: true                      # F1
    repo: payments                     # F2
    root: C:/src/payments              # F2: raiz del repo, si difiere de path
    branch: feature/payment-retries    # F2
```

En F1 cada iniciativa guarda `workspaces` con `path` y `primary` solamente. F2 suma `repo`, `root` y `branch` a cada entrada sin romper el formato.

Resolución cuando falta el ID:

```text
  1. flag explicito             --initiative INIT-0007
  2. CWD dentro de un path      match por path del workspace
  3. CWD dentro de un repo      match por root + branch actual
  4. iniciativa activa          si el comando lo admite
  5. si hay varias candidatas   lista corta, nunca eligir sola
  6. si no hay ninguna          pedir ID
```

Iniciativas sin repositorio existen y son válidas. La resolución por CWD nunca las encuentra: siempre requieren ID o ser la activa.

Snapshot de Git al pausar:

```text
repo, branch, worktree
archivos modificados y sin trackear
ultimos 5 commits
```

Deriva detectable: branch declarada distinta a la real, `path` que ya no existe, working tree sucio en una iniciativa pausada hace días.

---

## 10. Sesiones (Fase 2)

Descubrimiento automático:

```text
~/.copilot/session-state/<id>/workspace.yaml
        |
        | git_root + branch  ==  workspace de alguna iniciativa
        v
sessions:
  - id: 2f4d7eed-...
    provider: copilot-cli
    discovered: true
    last_active: 2026-09-14T18:51:00Z
```

`wcm session link <id>` cubre el caso manual. `wcm session list` muestra las de la iniciativa con su fecha de última actividad.

Regla: reanudar una sesión anterior es una optimización, no una dependencia. WCM muestra el comando para reanudarla; no lo ejecuta hasta la Fase 3.

Nota de nomenclatura: Copilot CLI llama "checkpoints" a sus resúmenes de conversación por sesión. WCM mantiene la palabra para los suyos y muestra los de Copilot como "session summaries".

---

## 11. Contrato de checkpoint para agentes (Fase 3)

WCM genera una instrucción que se puede pegar en cualquier agente:

```text
Write a checkpoint for initiative INIT-0007 to
  C:\Users\...\.wcm\kbs\work\initiatives\INIT-0007\checkpoints\<ts>.md
using this template: <plantilla de 6.3>.
Only include what Git cannot know: intent, discoveries, open questions,
incomplete reasoning, and the single most useful next action.
Do not include secrets, tokens, or file contents.
```

Después del checkpoint, `wcm pause` ofrece extraer `Next` y `Stopped at` desde ese archivo hacia NOW. El humano confirma o edita. El resultado siempre queda editable a mano.

Spike pendiente: verificar si Copilot CLI admite modo no interactivo sobre una sesión existente. Si sí, `wcm pause` puede lanzarlo solo. Si no, el flujo "pegar el prompt" es el definitivo y alcanza.

---

## 12. Context Builder y bases de conocimiento (Fase 3)

### 12.1 Context Builder

Entrada: iniciativa, rol, tarea opcional, presupuesto.

Salida: un paquete de texto para pegar o inyectar en una sesión nueva.

```text
  Rol            Incluye
  -------------  -------------------------------------------------------
  implementer    NOW, ultimo checkpoint, decisiones, snapshot Git, next
  reviewer       objetivo, NOW sin opiniones, diff, criterios, sin
                 razonamientos del implementer (aislamiento)
  investigator   objetivo, preguntas abiertas, discoveries, snapshot Git
```

`wcm context INIT-0007 --role reviewer` imprime el paquete y su tamaño estimado. Más contexto no es mejor contexto. El paquete puede sumar las notas vinculadas a la iniciativa.

### 12.2 Bases de conocimiento mantenidas por agentes

WCM adopta el patrón "LLM Wiki" que Karpathy publicó en abril de 2026 ([gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)). El conocimiento se compila una vez y se mantiene al día, en vez de rederivarse en cada pregunta. Cada KB tiene tres capas:

```text
  Capa      Quien escribe   En la KB
  --------  --------------  --------------------------------------------
  fuentes   la persona      notes/, y en `work` tambien las iniciativas
            (y WCM)         y los checkpoints; raw/ (clips, PDFs).
                            Los agentes nunca las reescriben; solo
                            agregan checkpoints por el contrato de 11.
  wiki      agentes         wiki/: paginas de conceptos, sistemas y
                            decisiones, mas wiki/index.md (catalogo) y
                            wiki/log.md (cronologico, solo se agrega)
  esquema   WCM y la        AGENTS.md: estructura, convenciones y
            persona         operaciones de esa KB. WCM lo genera, la
                            persona lo ajusta, los agentes lo leen.
```

Las operaciones son un contrato de archivo, igual que el checkpoint de §11: WCM escribe el `AGENTS.md` y genera la instrucción, y el agente la ejecuta. En el patrón original el esquema lo co-escriben la persona y el LLM; acá un agente no lo reescribe, para que la división de autoría sea simple.

```text
  ingest   leer notas y fuentes nuevas; actualizar paginas, index y log
  query    responder citando [[NOTE-...]] e [[INIT-...]]; una buena
           respuesta puede quedar como pagina nueva
  lint     contradicciones, paginas huerfanas, links rotos, datos viejos
```

Reglas:

- Un agente nunca reescribe `notes/`, `raw/`, `AGENTS.md` ni una iniciativa. Escribe en `wiki/` y, en `work`, además agrega checkpoints por el contrato de §11.
- WCM nunca lee `wiki/` para funcionar. `wiki/index.md` es un índice generado, pero es de los agentes, no del store: el principio "sin índices generados" se aplica a lo que WCM necesita.
- Un agente trabaja sobre una KB por vez. Las KBs no se mezclan.
- Según Karpathy, el `index.md` alcanza para navegar a escala moderada (~100 fuentes, algunos cientos de páginas), sin búsqueda vectorial. Si una KB crece y el índice no alcanza, la búsqueda entra como herramienta del agente, no del núcleo.
- Obsidian es el lector. La wiki es Markdown con links `[[...]]`, como las notas.

---

## 13. Atención (Fase 4)

Solo después de que las fases anteriores estén en uso real. Candidatos:

```text
paused sin actividad hace > N dias
waiting cuyo `since` supera un umbral
active hace > 1 dia sin checkpoint
working tree sucio en iniciativa pausada
inbox con mas de N capturas
```

La alerta de activa sin checkpoint se adelanta a F1, con un umbral en horas (§7.3).

`wcm wrap` al final del día: checkpoint de la activa, listado de lo sucio, inbox pendiente, y confirmación de que todo es seguro de retomar mañana.

Decisiones y findings como objetos de primera clase entran acá **solo si** el simulacro de F1 y el uso de F2 y F3 muestran que se pierden. Hasta entonces viven en notas, en el cuerpo del archivo de la iniciativa o en `repo/.ai/`.

---

## 14. Fases con test de salida

```text
  F1  SWITCH    esquema de archivos (hub y KBs), wrapper de shell,
                comandos de Fase 1: nucleo, notas, inbox, KBs y resto
                TEST: simulacro con 3 iniciativas reales de distinta
                      naturaleza (feature, research, incidente) durante
                      una semana. Secuencia: A active, pause A, B active,
                      pause B, C critical, done C, resume A, pause A,
                      resume B. Medir a mano time-to-pause y
                      time-to-resume. Cada relectura de un chat se
                      registra como falla de working memory.

  F2  GROUND    workspaces, snapshot Git, resolucion por CWD, deteccion
                de deriva, descubrimiento de sesiones Copilot
                TEST: desde cualquier worktree, `wcm status` sin ID.
                      Sesiones listadas por iniciativa sin link manual.

  F3  DELEGATE  contrato de checkpoint, `wcm context --role`,
                `resume --agent`, KBs mantenidas por agentes (ver 12.2)
                TEST: "borrar todas las sesiones". Un agente nuevo
                      continua cada iniciativa importante con WCM +
                      repos solamente. Un agente hace ingest de una
                      semana de notas de `work` y responde una pregunta
                      citando las notas.

  F4  ATTEND    attention, wrap, y decisiones/findings si hicieron falta
                TEST: `wcm now` un lunes a la manana responde que estaba
                      haciendo, que requiere atencion, que esta
                      bloqueado y que puedo retomar, sin abrir nada mas.

  DESPUES       busqueda semantica, sync entre maquinas via repo
                privado, `wcm ask`.
```

Después del test de F1, responder por escrito:

```text
Que informacion falto para retomar?
Que informacion sobro?
Que podria haber obtenido Git automaticamente?
Que deberia haber escrito el agente?
Que dato fue dificil de localizar?
Cuanto tomo recuperar mentalmente cada tarea?
Que notas guarde en el momento y cuales deje para despues?
Encontre con `wcm notes` lo que buscaba?
```

Esas respuestas definen el alcance de F2 y F3, no este documento.

### Versiones

Cada fase sale como un minor, y cada change mergeado como una pre-release de ese minor (`v0.1.0-alpha.N`). El detalle está en [`docs/decisions/0001-versionado-y-releases.md`](docs/decisions/0001-versionado-y-releases.md).

| Fase | Versión |
|---|---|
| F1 SWITCH | `0.1.0` |
| F2 GROUND | `0.2.0` |
| F3 DELEGATE | `0.3.0` |
| F4 ATTEND | `1.0.0` |

Una fase no está cerrada hasta que: pasa su test de salida, los tests pasan en la matrix de 3 OSes y las specs están sincronizadas a `openspec/specs/`. Recién ahí se abre `release/vX.Y.0`.

### F1, desglosado en changes

F2 en adelante se desglosa cuando le toca: lo define el test de salida de la fase anterior.

| Change | Rama | Entrega |
|---|---|---|
| `add-working-memory-layer` | `v0.1/add-working-memory-layer` | El núcleo: el store en el hub con la KB `work`, `new`, `now`, `pause`, `resume`, `done`, el wrapper de PowerShell con el cd y la alerta de activa sin checkpoint. |
| `add-notes` | `v0.1/add-notes` | `note`, `note edit`, `notes`: notas como archivos, vínculo a la activa, links `[[ID]]`, búsqueda de texto. |
| `add-inbox` | `v0.1/add-inbox` | `capture`, `inbox`, `promote` (a iniciativa o a nota), `drop`. |
| `add-knowledge-bases` | `v0.1/add-knowledge-bases` | `config.yaml`, `kb new`, `kb list`, `-k`, KBs fuera del hub. |
| `add-initiative-tools` | `v0.1/add-initiative-tools` | `wait`, `list`, `show`, `checkpoint`, `edit`. |

El orden es el de la tabla; la decisión está en [`docs/decisions/0002-notas-y-bases-de-conocimiento.md`](docs/decisions/0002-notas-y-bases-de-conocimiento.md). El núcleo va primero porque es la hipótesis más riesgosa (§20) y porque se puede usar a diario desde la primera alpha. Cada change se propone cuando se mergea el anterior. El uso real puede reordenar los que faltan, pero el cambio de orden se hace primero en esta tabla, en un PR `docs/`.

El uso real y el simulacro de F1 arrancan con la primera alpha. El test de salida se cierra después de la última alpha de F1, antes de `release/v0.1.0`, y ahí se escriben sus respuestas.

Lo que hoy está en `add-working-memory-layer` y no es núcleo se quita del change, sin crear todavía los otros: la capacidad de inbox, los requirements de `wait`, `list`, `show`, `checkpoint` y `edit`, y en `now` la sección WAITING y la línea INBOX. Cada change siguiente los retoma, y además toca lo que el núcleo ya tiene: `add-notes` suma la línea Notes del brief de `resume`, `add-inbox` la línea INBOX de `now` y `add-initiative-tools` la sección WAITING de `now` y las notas en `show`.

---

## 15. Stack

**Recomendación: Python 3.14 (ya instalado) más un módulo de PowerShell de ~30 líneas.**

Razones:

- La herramienta va a cambiar de forma cada semana durante los primeros meses. Python itera más rápido.
- YAML frontmatter y Markdown tienen librerías maduras.
- El wrapper de shell es necesario con cualquier stack, así que no es un costo extra de Python.

Alternativa considerada: .NET 10 (también instalado). Da un ejecutable único y arranque más rápido. Vale la pena reconsiderarlo si el arranque de Python se vuelve perceptible en `wcm now`, que es el comando que más se ejecuta.

Wrapper, con el protocolo `WCM_CD_FILE` que fija el design de `add-working-memory-layer` (D8). Capturar la salida de la CLI esconde los prompts interactivos del pause y de `wcm note`:

```text
function wcm {
    # crea un archivo temporal y exporta su ruta en WCM_CD_FILE
    # corre la CLI con stdin, stdout y stderr en la consola
    # al terminar, si la CLI escribio una ruta en el archivo,
    # hace Set-Location ahi; borra el archivo y conserva el exit code
}
```

---

## 16. Métricas

```text
  Time To Pause           desde decidir interrumpir hasta "Safe to switch"     < 30 s
  Time To Resume          hasta entender que hacia, que paso y que sigue       < 30 s
  Conversation Dependency veces que hubo que releer un chat para continuar     ~ 0
  Forgotten Work          iniciativas pausadas sin atencion > N dias           visible
  Checkpoint Quality      reanudaciones que necesitaron reconstruccion extra   baja
  Time To Note            desde que se me ocurre hasta "saved"                 < 5 s
```

En F1 se miden a mano con un reloj y una tabla. Instrumentarlas en la herramienta es trabajo de F4.

---

## 17. Invariantes

```text
A lo sumo una iniciativa active.
Toda iniciativa paused tiene Next no vacio.
Toda iniciativa waiting tiene waiting_on.what no vacio.
Una iniciativa puede existir sin sesion.                      siempre
Una iniciativa puede existir sin repositorio.                 siempre
Una iniciativa puede tener varios repositorios.               por diseno
NOW es pequeno. Si crece, se esta usando como historial.
Checkpoints son append-only. Nunca se reescriben.
La evidencia (Git, docs) no se sobrescribe con conclusiones de agentes.
Un agente nunca reescribe notas, fuentes ni iniciativas.      siempre
WCM funciona sin la wiki de ninguna KB.                       siempre
El nombre del archivo de una iniciativa o una nota es su ID.
Una nota pertenece a una sola KB.
```

---

## 18. Seguridad

- No almacenar secretos. El contrato de checkpoint lo dice explícitamente al agente.
- Checkpoints resumen estado; no vuelcan contenido de archivos.
- `config.yaml` permite marcar repos como sensibles: excluidos del snapshot de Git y del Context Builder.
- El almacenamiento global es metadata personal. Lo que se comparte con el equipo vive en el repo, no en `~/.wcm`.
- Separar KBs por lugar permite que el conocimiento de trabajo no salga de la máquina de trabajo: `work` vive en el hub, y una KB personal puede ser un repo aparte. Hasta que llegue el sync (DESPUÉS, §14), WCM no sincroniza ni publica ninguna KB.
- El `AGENTS.md` de cada KB repite la regla de los checkpoints: nada de secretos, tokens ni contenido de archivos en la wiki.

---

## 19. Lo que WCM no es

```text
No es Jira ni Azure DevOps       administra contexto operativo, no backlog
No es un gestor de terminales    puede abrir una; no es el dominio
No es un gestor de Git           Git es evidencia y navegacion
No es un archivo de chats        no almacena conversaciones
No es RAG                        busqueda semantica es futuro, no nucleo;
                                 la KB es una wiki compilada, no un indice
No es Obsidian                   Obsidian es el lector de las KBs; WCM es
                                 la forma rapida de escribirlas
No es un orquestador autonomo    coordina contexto y atencion con humano
```

---

## 20. Riesgos y spikes

**Disciplina del next action.** Si el prompt de pause se siente como un formulario, el usuario lo saltea y el sistema muere. Mitigación: pre-llenado, Enter para mantener, `-n` para el caso urgente. Es hipótesis hasta la F1.

**Copilot no interactivo sobre sesión existente.** No verificado. Si no existe, el checkpoint de agente queda en "pegar el prompt", que igual cumple el contrato.

**Iniciativas sin repositorio.** Válidas por diseño, invisibles para la resolución por CWD. Siempre requieren ID o ser la activa.

**Colisión de nombre "checkpoint".** Decidida en 10; revisar si confunde en la práctica.

**Las notas desplazan al núcleo.** Un gestor de notas es más atractivo de construir que pause y resume, y está menos validado. Mitigación: F1 empieza por el núcleo (§14), y su test de salida sigue midiendo time-to-pause y time-to-resume.

**IDs por KB en varias máquinas.** Derivar `max + 1` asume que una sola máquina escribe cada KB. Si una KB se sincroniza, por ejemplo la de lecturas en un repo personal, y se escribe desde dos máquinas, los IDs pueden chocar. Se resuelve cuando llegue el sync.

**Obsidian y los alias.** Obsidian no resuelve un link a un alias del frontmatter; por eso el archivo se llama como el ID. Si molesta ver IDs en las pestañas, un plugin de títulos lo resuelve sin tocar el formato.

**Diseñar por adelantado lo que F1 debe descubrir.** Este documento deja fuera a propósito: attention queue con prioridades, presupuesto de contexto en tokens, roles de agente detallados, registro de artefactos, índice local. Entran cuando el uso real demuestre que faltan.

---

## 21. Lo que se deja fuera del MVP

```text
embeddings y bases vectoriales
grafo de conocimiento como base de datos (los links [[ID]] y
  Obsidian alcanzan)
aplicacion web
multiusuario
sync propio en la nube
orquestacion autonoma
integracion profunda con multiples runtimes
workflow engine
reemplazo de trackers de work items
```

---

## 22. Test arquitectónico permanente

Periódicamente:

> **Borrar conceptualmente todas las sesiones de agentes. ¿Puede cada iniciativa importante retomarse solo con WCM + repositorios?**

Si no, hay conocimiento atrapado en una sesión y el contrato de checkpoint debe mejorar.

> **Sin abrir IDE ni terminales, ¿la persona sabe en menos de 30 segundos dónde estaba y qué debe hacer?**

Si no, NOW es insuficiente.

---

## 23. La experiencia objetivo

```text
While coding, something worth keeping shows up.

PS> wcm note "el gateway corta a los 30s, no a los 60"
  NOTE-0012 saved, linked to INIT-0007 Payment retries.

Something urgent appears.

PS> wcm pause

  Next action  [Terminar PaymentRetryPolicy y verificar duplicados]
  >
  Checkpoint saved.
  Safe to switch context.

PS> wcm new "Production login failures" --type incident --priority critical
  INIT-0008 active.
```

Días después:

```text
PS> wcm resume INIT-0007

  You were implementing payment retries.
  Backoff is incomplete.
  Idempotency is the main unresolved risk.
  Next: finish PaymentRetryPolicy and verify duplicate handling.
  Notes: 3 (latest: el gateway corta a los 30s, no a los 60)

  C:\wt\payment-retries>
```

La persona no tiene que recordar la conversación, conservar la terminal ni reconstruir el estado mental. Lo que aprendió en el camino está en una nota, a un `wcm notes` de distancia.

**El sistema recuerda dónde quedó el trabajo para que la persona pueda dejar de hacerlo.**
