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

De ahí salen exactamente tres necesidades:

```text
  +--------------------------------------------------------------+
  |  1. SOLTAR      pause:  externalizar el estado en < 30 s     |
  |  2. VER         now:    que requiere mi atencion, global     |
  |  3. RETOMAR     resume: recuperar contexto en < 30 s         |
  +--------------------------------------------------------------+
        Todo lo demas (Git, sesiones, agentes, findings,
        decisiones, busqueda) existe para hacer estas tres
        cosas mas baratas o mas confiables. No al reves.
```

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

---

## 4. Siete decisiones estructurales

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

### 4.3 Un archivo por iniciativa

Frontmatter YAML para lo mecánico. Cuerpo Markdown para el contexto humano. Sin índice derivado hasta que duela: escanear 20 frontmatters es instantáneo.

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

Un proceso hijo no puede hacer `cd` en el shell padre. `wcm resume` promete llevarte al worktree. Se distribuye una función de PowerShell `wcm` que envuelve al binario y ejecuta el `cd` que este le indique. Es parte del producto desde el día uno.

---

## 5. Modelo

### 5.1 Entidades de Fase 1

```text
Initiative     unidad de trabajo con estado, contexto humano y next action
Capture        una linea en el inbox; puede promoverse a Initiative
Checkpoint     fotografia semantica append-only de una Initiative
```

### 5.2 Entidades de Fase 2 en adelante

```text
Workspace      repo + branch + worktree vinculados a una Initiative
Session        referencia descubierta o vinculada a una sesion de agente
Decision       solo si el simulacro de F1 muestra que hace falta
Finding        idem
```

### 5.3 Tres niveles de memoria

```text
  NIVEL 1  Working Set        wcm now         que requiere mi atencion
  NIVEL 2  Initiative Memory  initiative.md   que pasa con esta iniciativa
  NIVEL 3  Evidencia          Git, checkpoints, sesiones, docs en repo
```

Ni humanos ni agentes cargan el nivel 3 completo por defecto.

---

## 6. Almacenamiento

```text
~/.wcm/
  config.yaml
  inbox.md                          # append-only, una captura por linea
  initiatives/
    INIT-0007-payment-retries/
      initiative.md                 # frontmatter + NOW; se reescribe
      checkpoints/
        2026-09-16T1640.md          # append-only; HOW WE GOT HERE
    INIT-0008-login-incident/
      initiative.md
  done/                             # initiatives movidas al cerrar
```

Reglas:

- El ID se deriva del máximo existente en `initiatives/` y `done/`. No hay contador que se pueda corromper.
- El slug del directorio es cosmético. El ID es la identidad.
- Nada de esto vive en un repositorio de código. Lo que el equipo deba compartir (planes, decisiones) puede vivir en `repo/.ai/` y ser referenciado desde WCM.

### 6.1 `initiative.md`

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
workspaces: []           # Fase 2
sessions: []             # Fase 2
links: []                # work items externos, PRs, docs
---

# NOW

**Focus:** Implementar la política de retry para autorizaciones de pago.

**Stopped at:** Clasificación de reintentos hecha; el backoff está incompleto.

**Why it matters:** El proveedor puede devolver el mismo transaction ID después de un timeout.

**Important:** Validar idempotencia antes de habilitar retries.

**Next:** Terminar `PaymentRetryPolicy` y verificar el comportamiento con transacciones duplicadas.
```

Restricciones del bloque NOW:

- Cinco campos fijos. Solo `Next` es obligatorio.
- Se reescribe en cada pause. Nunca crece como timeline.
- Si supera ~15 líneas, `wcm now` lo advierte.

### 6.2 `inbox.md`

```markdown
- 2026-09-16T15:02 CAP-0027 Revisar posible leak de refresh tokens
- 2026-09-16T15:40 CAP-0028 Preguntar a infra por el timeout del gateway
```

`wcm promote CAP-0027` corta la línea y crea una iniciativa con ese título.

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

---

## 7. Las tres operaciones

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

### 7.2 `wcm resume ID`

```text
PS> wcm resume INIT-0007

INIT-0007 Payment retries
paused 2 days ago

  Focus:       Implementar la politica de retry para autorizaciones.
  Stopped at:  Clasificacion hecha; backoff incompleto.
  Important:   Validar idempotencia antes de habilitar retries.
  Next:        Terminar PaymentRetryPolicy y verificar duplicados.

  Workspace:   payments  feature/payment-retries  C:\wt\payment-retries
  Sessions:    2 (last active 2d ago)                       <- Fase 2
```

- Si había otra activa, corre el flujo de pause sobre ella primero.
- El wrapper de shell hace `cd` al worktree primario si existe.
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

---

## 8. Comandos por fase

```text
FASE 1   new, now, capture, inbox, promote, pause, resume, list, show,
         wait, done, checkpoint, edit
FASE 2   workspace add|list, status, session list|link
FASE 3   context --role, resume --agent, checkpoint --from-agent
FASE 4   attention, wrap
DESPUES  search, ask, sync
```

`edit` abre `initiative.md` en `$EDITOR`. Es la válvula de escape: todo lo que la CLI no cubre se hace a mano.

---

## 9. Workspaces y resolución por CWD (Fase 2)

```yaml
workspaces:
  - repo: payments
    root: C:/src/payments
    branch: feature/payment-retries
    worktree: C:/wt/payment-retries
    primary: true
```

Resolución cuando falta el ID:

```text
  1. flag explicito             --initiative INIT-0007
  2. CWD dentro de un worktree  match por path
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

Deriva detectable: branch declarada distinta a la real, worktree que ya no existe, working tree sucio en una iniciativa pausada hace días.

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
  C:\Users\...\.wcm\initiatives\INIT-0007-payment-retries\checkpoints\<ts>.md
using this template: <plantilla de 6.3>.
Only include what Git cannot know: intent, discoveries, open questions,
incomplete reasoning, and the single most useful next action.
Do not include secrets, tokens, or file contents.
```

Después del checkpoint, `wcm pause` ofrece extraer `Next` y `Stopped at` desde ese archivo hacia NOW. El humano confirma o edita. El resultado siempre queda editable a mano.

Spike pendiente: verificar si Copilot CLI admite modo no interactivo sobre una sesión existente. Si sí, `wcm pause` puede lanzarlo solo. Si no, el flujo "pegar el prompt" es el definitivo y alcanza.

---

## 12. Context Builder (Fase 3)

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

`wcm context INIT-0007 --role reviewer` imprime el paquete y su tamaño estimado. Más contexto no es mejor contexto.

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

`wcm wrap` al final del día: checkpoint de la activa, listado de lo sucio, inbox pendiente, y confirmación de que todo es seguro de retomar mañana.

Decisiones y findings como objetos de primera clase entran acá **solo si** el simulacro de F1 y el uso de F2 y F3 muestran que se pierden. Hasta entonces viven en el cuerpo de `initiative.md` o en `repo/.ai/`.

---

## 14. Fases con test de salida

```text
  F1  SWITCH    esquema de archivos, wrapper de shell, comandos de Fase 1
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
                `resume --agent`
                TEST: "borrar todas las sesiones". Un agente nuevo
                      continua cada iniciativa importante con WCM +
                      repos solamente.

  F4  ATTEND    attention, wrap, y decisiones/findings si hicieron falta
                TEST: `wcm now` un lunes a la manana responde que estaba
                      haciendo, que requiere atencion, que esta
                      bloqueado y que puedo retomar, sin abrir nada mas.

  DESPUES       busqueda textual, sync entre maquinas via repo privado,
                `wcm ask`, grafo de conocimiento.
```

Después del test de F1, responder por escrito:

```text
Que informacion falto para retomar?
Que informacion sobro?
Que podria haber obtenido Git automaticamente?
Que deberia haber escrito el agente?
Que dato fue dificil de localizar?
Cuanto tomo recuperar mentalmente cada tarea?
```

Esas respuestas definen el alcance de F2 y F3, no este documento.

---

## 15. Stack

**Recomendación: Python 3.14 (ya instalado) más un módulo de PowerShell de ~30 líneas.**

Razones:

- La herramienta va a cambiar de forma cada semana durante los primeros meses. Python itera más rápido.
- YAML frontmatter y Markdown tienen librerías maduras.
- El wrapper de shell es necesario con cualquier stack, así que no es un costo extra de Python.

Alternativa considerada: .NET 10 (también instalado). Da un ejecutable único y arranque más rápido. Vale la pena reconsiderarlo si el arranque de Python se vuelve perceptible en `wcm now`, que es el comando que más se ejecuta.

Wrapper:

```text
function wcm {
    $out = & python -m wcm @args
    # el binario imprime una linea "@@cd <path>" cuando corresponde
    # el wrapper la consume, hace Set-Location y muestra el resto
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
```

---

## 18. Seguridad

- No almacenar secretos. El contrato de checkpoint lo dice explícitamente al agente.
- Checkpoints resumen estado; no vuelcan contenido de archivos.
- `config.yaml` permite marcar repos como sensibles: excluidos del snapshot de Git y del Context Builder.
- El almacenamiento global es metadata personal. Lo que se comparte con el equipo vive en el repo, no en `~/.wcm`.

---

## 19. Lo que WCM no es

```text
No es Jira ni Azure DevOps       administra contexto operativo, no backlog
No es un gestor de terminales    puede abrir una; no es el dominio
No es un gestor de Git           Git es evidencia y navegacion
No es un archivo de chats        no almacena conversaciones
No es RAG                        busqueda semantica es futuro, no nucleo
No es un orquestador autonomo    coordina contexto y atencion con humano
```

---

## 20. Riesgos y spikes

**Disciplina del next action.** Si el prompt de pause se siente como un formulario, el usuario lo saltea y el sistema muere. Mitigación: pre-llenado, Enter para mantener, `-n` para el caso urgente. Es hipótesis hasta la F1.

**Copilot no interactivo sobre sesión existente.** No verificado. Si no existe, el checkpoint de agente queda en "pegar el prompt", que igual cumple el contrato.

**Iniciativas sin repositorio.** Válidas por diseño, invisibles para la resolución por CWD. Siempre requieren ID o ser la activa.

**Colisión de nombre "checkpoint".** Decidida en 10; revisar si confunde en la práctica.

**Diseñar por adelantado lo que F1 debe descubrir.** Este documento deja fuera a propósito: attention queue con prioridades, presupuesto de contexto en tokens, roles de agente detallados, registro de artefactos, índice local. Entran cuando el uso real demuestre que faltan.

---

## 21. Lo que se deja fuera del MVP

```text
embeddings y bases vectoriales
grafo de conocimiento
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

  C:\wt\payment-retries>
```

La persona no tiene que recordar la conversación, conservar la terminal ni reconstruir el estado mental.

**El sistema recuerda dónde quedó el trabajo para que la persona pueda dejar de hacerlo.**
