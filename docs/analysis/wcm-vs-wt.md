# WCM y wt: ¿un producto o dos?

> Informe de decisión. Fecha: 2026-10-07. No cambia código ni specs de ninguno de los dos repos.
>
> **Qué se leyó**
>
> - `wcm:` es `jMautone/working-memory-manager`, rama `main` (`c47aa9f`): plan completo y change `add-working-memory-layer` (proposal, design, tasks y las 6 delta specs).
> - `wt:` es `jMautone/worktree-manager`, rama `release/v0.1.0` (`1ccbf76`): `docs/design/product.md`, `docs/decisions/0000`–`0002`, `openspec/config.yaml`, las 9 specs de `openspec/specs/`, los 4 changes archivados, `internal/shell/`, `internal/workspace/`, `internal/config/`, `internal/cli/`, `README.md`, `CLAUDE.md` y `CHANGELOG.md`.
>
> **Sobre la rama de wt.** La rama `v0.1/remove-worktree` que pedía el encargo ya no existe. Se mergeó a `main` como `v0.1.0-alpha.5` ([jMautone/worktree-manager#13](https://github.com/jMautone/worktree-manager/pull/13), `181ccf4`), y su change está en `wt:openspec/changes/archive/2026-10-04-remove-worktree/`. Lo más reciente es `release/v0.1.0`, que es `main` más el cierre de M1 en el CHANGELOG ([jMautone/worktree-manager#14](https://github.com/jMautone/worktree-manager/pull/14), todavía sin mergear a `main` cuando lo leí). Analicé esa rama. Por lo tanto M1 está **cerrado en el código**, no "casi cerrado".
>
> **Cómo se cita.** `repo:ruta:línea` o `repo:ruta §sección`. Lo que es deducción mía y no está escrito en un repo va marcado **(inferencia)**.

---

## 1. Veredicto

**Opción F (nueva): separadas, con fronteras escritas desde ahora y un contrato opcional en un solo sentido (WCM lee de wt) que se activa recién en la Fase 2 de WCM. La fusión se reevalúa en un evento fijo: el test de salida de F1 de WCM junto con la publicación de `v0.2.0` de wt.**

La razón principal es que no modelan lo mismo: la iniciativa de WCM tiene de 0 a N repos, y wt gira alrededor del worktree. Lo que de verdad se duplica es chico: un wrapper de shell de unas 30 líneas y tres lecturas de Git. Fusionar ahora ataría una hipótesis sin validar a un producto con contrato público, y obligaría a romper un piso de plataforma: PowerShell 5.1 en WCM, pwsh 7.4 en wt. **La pregunta que puede dar vuelta el veredicto es si la máquina corporativa tiene o admite pwsh 7.**

---

## 2. Qué es cada producto

- **WCM** es una memoria externa y personal, guardada fuera de cualquier repo, de las iniciativas entre las que se reparte la atención de una persona. Su operación central es cambiar de una iniciativa a otra (pausar dejando una próxima acción y retomar) en menos de 30 segundos. Git y las sesiones de agentes entran recién después, como evidencia.
- **wt** es un binario multiplataforma que administra worktrees de Git repartidos en varios repos, desde la terminal: los crea, salta entre ellos, los lista, los borra y, más adelante, los cierra y opera en lote. Su contrato de CLI es público y estable.

En una línea: WCM contesta *"¿qué estaba haciendo y qué sigue?"* y wt contesta *"¿dónde está ese worktree y en qué estado está?"*.

---

## 3. Matriz de capacidades

Estado: ✅ construido · 📄 especificado (spec o design) · 📝 solo nombrado (una fila de una tabla, sin spec) · — no existe.

Las filas 1 a 25 son las 23 capabilities de `wt:docs/design/product.md §6` más las dos "de contrato" de esa misma sección. Las filas 26 a 31 son las 6 capabilities del change de WCM. Las filas 32 a 46 son las fases 2 a 4 y lo que el plan llama "DESPUÉS" (`wcm:persistent-working-memory-plan.md §8, §9–§14`).

| # | Capacidad | WCM | wt | Solapamiento | Dueño |
|---|---|---|---|---|---|
| 1 | `cli-contract` | Contrato propio, exit 0/1/2 (📄 `design.md` D1) | M1 ✅ exit 0–8, `--json` versionado | ninguno | cada uno el suyo |
| 2 | `config-layers` | Sin config en F1, solo `WCM_HOME` (📄 proposal); `config.yaml` en F2 para repos sensibles (📝 plan §18) | M1 ✅ TOML por capas | ninguno | cada uno |
| 3 | `path-templates` | — | M1 ✅ | ninguno | wt |
| 4 | `git-worktrees` | F2: lee Git de una ruta ya conocida (📝 plan §9) | M1 ✅ | parcial (§4.3) | wt enumera; WCM lee `git -C <ruta>` |
| 5 | `shell-integration` | F1: `WCM_CD_FILE` + módulo PS 5.1 (📄) | M1 ✅ en 4 shells | **total en el mecanismo** (§4.1) | cada uno su wrapper, con reglas alineadas |
| 6 | `create-worktree` | — (`wcm new --path` registra una ruta, no crea nada) | M1 ✅ | ninguno | wt |
| 7 | `navigate` | `resume` hace `cd` al `path` registrado (📄) | M1 ✅, solo dentro del repo actual | parcial (§4.2) | wt salta por nombre; WCM aterriza al retomar |
| 8 | `list-worktrees` | `now` lista iniciativas, no worktrees | M1 básico ✅, M4 completo 📝 | ninguno en datos | wt |
| 9 | `remove-worktree` | `done` no toca worktrees; `now` avisa si el `path` ya no existe (📄) | M1 ✅ | ninguno (solo interacción) | wt |
| 10 | `merge-worktree` | — | M3 📝 | ninguno | wt |
| 11 | `merge-steps` | — | M4 📝 | ninguno | wt |
| 12 | `sync-worktrees` | — | M3 📝 | ninguno | wt |
| 13 | `workspace-discovery` | No descubre repos: guarda vínculos declarados | M2 📝 (solo `doc.go`) | ninguno | wt |
| 14 | `cross-repo-resolution` | Solo si `workspace add` aceptara nombres (no especificado) | M2 📝 | parcial, potencial (§4.4) | wt |
| 15 | `batch-execution` | — | M2 📝 | ninguno | wt |
| 16 | `hooks` | — | M3 📝 | ninguno | wt |
| 17 | `project-hooks-approval` | — | M5 📝 | ninguno | wt |
| 18 | `launchers` | F3 `resume --agent` lanza una sesión (📝) | M5 📝 | parcial (§4.8) | wt lanza; WCM arma el contexto |
| 19 | `branch-state` (`mark`, `var`) | Vínculo iniciativa↔workspace en el frontmatter (📝 F2) | M4 📝 | parcial (§4.5) | wt: estado por rama; WCM: estado por iniciativa |
| 20 | `aliases-plugins` | — | M5 📝 | ninguno; además no sirve para alojar a WCM (H8) | wt |
| 21 | `statusline` | `wcm status` (📝 F2) | M4 📝 | parcial (§4.5) | cada uno; se combinan en el prompt del usuario |
| 22 | `agent-integrations` | F2: descubre sesiones de Copilot; F3: contrato de checkpoint (📝) | M6 📝 | parcial (§4.6) | wt: estado vivo por worktree; WCM: sesión↔iniciativa |
| 23 | `dashboard` | `now` (📄 F1) + `attention` (📝 F4) | M6 📝 | parcial, en la presentación (§4.7) | cada uno; WCM consume señales de wt |
| 24 | `distribution` | `pip install -e .` desde el clone (📄 design) | GitHub Releases ✅; brew/scoop/winget M6 📝 | ninguno | cada uno |
| 25 | `docs-generation` | README (📄 tasks 8.3) | M6 📝 | ninguno | cada uno |
| 26 | `initiative-lifecycle` | F1 📄 | — | ninguno | WCM |
| 27 | `initiative-context` (NOW, checkpoints) | F1 📄 | — | ninguno | WCM |
| 28 | `working-set-view` (`now`) | F1 📄 | `list` y `dash` son por worktree | conceptual ("una sola vista") | WCM |
| 29 | `inbox-capture` | F1 📄 | — | ninguno | WCM |
| 30 | `memory-store` (`~/.wcm`, Markdown + YAML) | F1 📄 | `git config` (M4) y TOML: otros datos | ninguno | WCM |
| 31 | `shell-integration` (WCM) | F1 📄 | ver fila 5 | total | ver fila 5 |
| 32 | `workspace add\|list` | F2 📝 | identidad de worktree: NAME, path, branch | parcial (§4.4) | WCM es dueño del vínculo; wt, del worktree |
| 33 | Resolución por CWD (ruta → iniciativa) | F2 📝 | "Current worktree" (ruta → worktree) ✅ | parcial: la regla de comparar rutas (§4.3) | WCM, copiando la regla de wt |
| 34 | Snapshot de Git al pausar | F2 📝 | `wt.list.v1` no trae archivos sucios ni commits | parcial (§4.3) | WCM, vía `git` |
| 35 | Detección de deriva | F2 📝 | `prunable` y `branch` en `wt.list.v1` ✅ | parcial (§4.3) | WCM |
| 36 | Descubrimiento de sesiones Copilot | F2 📝 | `agent-integrations` M6 (otro mecanismo) | parcial (§4.6) | WCM |
| 37 | `status`, `session list\|link` | F2 📝 | `statusline` M4 📝 | parcial (§4.5) | WCM |
| 38 | Contrato de checkpoint para agentes | F3 📝 | — | ninguno | WCM |
| 39 | Context builder `--role` | F3 📝 | — | ninguno | WCM |
| 40 | `resume --agent` | F3 📝 | `-x` ✅, `exec` M2 📝, launchers M5 📝 | parcial (§4.8) | wt ejecuta; WCM provee el contexto |
| 41 | `checkpoint --from-agent` | F3 📝 | — | ninguno | WCM |
| 42 | `attention` | F4 📝 | marcadores 🤖/💬 y `dash` M6 📝 | parcial (§4.7) | WCM, consumiendo la señal de wt |
| 43 | `wrap` (cierre del día) | F4 📝 | `list --all-repos` M2 + estado sucio M4 📝 | parcial (§4.7) | WCM |
| 44 | Decisiones y findings | F4, condicional 📝 | — | ninguno | WCM |
| 45 | `search`, `ask` | DESPUÉS 📝 | — | ninguno | WCM |
| 46 | Sync entre máquinas | DESPUÉS 📝 (plan:525) | non-goal (product.md:289) | ninguno, pero choca si se fusionan (§6.1) | WCM |

Resumen: de 46 filas hay **1 solapamiento total** (el mecanismo de `cd`, que aparece en las filas 5 y 31), **17 parciales** y 1 conceptual (fila 28). Casi todos son *de presentación o de vecindad*: los dos productos miran el mismo worktree desde lados opuestos. Ninguna fila tiene a los dos productos queriendo **ser dueños del mismo dato**.

---

## 4. Solapamientos confirmados

### 4.1 Cambio de directorio con archivo-directiva: total en el mecanismo, distinto en los detalles

- **WCM:** `wcm:openspec/changes/add-working-memory-layer/design.md:88-92` (D8), `:94-113` (D9); `.../specs/shell-integration/spec.md:7-24` ("Directory-change request protocol").
- **wt:** `wt:docs/design/product.md:177-188` (§5 "Shell integration"); `wt:openspec/specs/shell-integration/spec.md:98` ("Directive file"), `:117` ("Writing the directive"); `wt:internal/shell/directive.go:14-24`.

El patrón es el mismo: el wrapper crea un temporal, exporta su ruta en una variable, corre el binario con la consola conectada, lee el archivo, hace `cd` y lo borra. Los dos descartaron capturar stdout **por la misma razón de fondo**, que es que el binario necesita la consola. En WCM, porque los prompts del pause quedarían en buffer (`design.md:90`). En wt, porque se pierde la TTY: sin color, sin picker, sin `-x claude` interactivo (`wt:openspec/changes/archive/2026-10-02-shell-integration/design.md:32-37`).

| | WCM | wt |
|---|---|---|
| Variables | `WCM_CD_FILE` | `WT_DIRECTIVE_CD_FILE` y `WT_PREVIOUS_DIR` |
| Contenido | ruta y salto de línea (`wcm:.../shell-integration/spec.md:12`) | ruta sin salto (`wt:internal/shell/directive.go:14-16`) |
| ¿El binario puede crear el archivo? | no se especifica | no; si falta, exit 1 (`wt:.../shell-integration/spec.md:117-118`) |
| Procesos hijos | heredan la variable: D9 la exporta durante toda la llamada, así que el editor de `wcm edit` la ve **(inferencia)** | se la quitan (`wt:.../shell-integration/spec.md:145`; `wt:internal/shell/shell.go:106-118`) |
| Si el `cd` falla | el wrapper ni lo intenta si la ruta no existe (`design.md:104`) | resultado ≠ 0 (`wt:.../shell-integration/spec.md:98-99`) |
| Shells | solo Windows PowerShell 5.1 en F1 (`design.md:9`, `:27`) | zsh, bash, fish y pwsh ≥ 7.4; en Windows, solo pwsh 7.4 (`wt:.../shell-integration/spec.md:9-10`) |
| Volver atrás (`-`) | no | sí, con `WT_PREVIOUS_DIR` |

Resuelven el mismo problema con la misma solución y dos implementaciones. Para compartir *la función* habría que tener un wrapper que conozca dos ejecutables (uno Python y uno Go) y un único piso de shell, y hoy ese piso no existe: 5.1 contra 7.4. Mantener los dos cuesta unas 30 líneas de PowerShell, más unas 20 de zsh cuando WCM llegue a macOS **(inferencia, por el tamaño de `wt:internal/shell/scripts/wt.zsh`)**. Lo que sí conviene compartir son **las reglas** (§7.4).

### 4.2 `wcm resume` y `wt cd`: parcial

- **WCM:** `wcm:persistent-working-memory-plan.md:160-162` (§4.7), `:334` ("El wrapper de shell hace `cd` al worktree primario si existe"); `wcm:.../proposal.md:29-30` y `:38-41` (un único `path` por iniciativa, sin validar contra Git).
- **wt:** `wt:docs/design/product.md:66`; `wt:openspec/specs/navigate/spec.md:54` ("Resolving a name": solo entre los worktrees del repo actual); `wt:openspec/changes/archive/2026-10-02-shell-integration/proposal.md:37` (la resolución entre repos queda para M2).

Los dos terminan con la shell parada en un directorio, pero hacen cosas distintas. `resume` es un cambio de atención: corre el flujo de pausa sobre la iniciativa activa, marca `last_resumed`, imprime el brief y, al final, hace `cd` a una **ruta absoluta que ya estaba guardada**, sin resolver nada. `wt cd` es **resolución por nombre**, y hoy solo dentro del repo actual. WCM no necesita a wt para su `cd`. A lo sumo lo necesitaría para traducir un nombre a una ruta al *registrar* un workspace.

### 4.3 Git en la F2 de WCM y `git-worktrees` de wt: parcial

- **WCM:** `wcm:persistent-working-memory-plan.md:381-413` (§9: workspaces; resolución por CWD en los pasos 2 y 3; snapshot con repo, branch, worktree, archivos modificados y sin trackear, y últimos 5 commits; deriva cuando la branch difiere, el worktree ya no existe o hay cambios sin commitear).
- **wt:** `wt:openspec/specs/git-worktrees/spec.md:74` ("Current worktree": resuelve symlinks, gana la coincidencia más profunda, no distingue mayúsculas en macOS ni en Windows) y `:67` ("Native paths"); `wt:openspec/specs/list-worktrees/spec.md:51-52` (`wt.list.v1`: `name`, `path`, `branch`, `head`, `detached`, `bare`, `main`, `current`, `locked`, `prunable` y sus motivos).

Lo que cruza:

1. **La regla para decidir si una ruta está dentro de un worktree.** wt la tiene especificada y testeada en los 3 sistemas operativos. WCM necesita la misma regla, pero en el sentido inverso: de ruta a iniciativa.
2. **Si el worktree existe y en qué rama está.** `wt.list.v1` lo dice (`prunable`, `branch`).

Lo que no cruza:

- **Los archivos sucios y los últimos commits.** No están en `wt.list.v1`. El `list` completo de M4 está solo nombrado (`wt:docs/design/product.md:243`), y el análisis previo lo describe como símbolos de estado, no como listas de archivos (`wt:docs/decisions/0000-analisis-worktrunk.md §2.5`) **(inferencia sobre el contenido de M4)**.
- **El descubrimiento.** WCM no enumera worktrees ni descubre repos: lee una ruta que ya conoce.

Lo que WCM "reimplementaría" son tres llamadas a `git` y una regla de comparación de rutas. No es reimplementar wt.

### 4.4 `cross-repo-resolution` y `wcm workspace add`: parcial y potencial

- **WCM:** `wcm:persistent-working-memory-plan.md:371` (`workspace add|list`) y `:383-390` (YAML con `repo`, `root`, `branch`, `worktree`, `primary`).
- **wt:** `wt:docs/design/product.md:211` (capability), `:236-237` (M2), `:112` (exit 4: nombre ambiguo entre repos); `wt:internal/workspace/doc.go` (el paquete tiene solo el comentario: no hay código); `wt:internal/config/keys.go:69-116` (5 claves y ninguna es `repos_root`).

El plan no dice cómo recibe `workspace add` su argumento. Si aceptara "un nombre" y lo buscara entre repos, WCM reconstruiría el M2 de wt. El riesgo está abierto porque F2 no tiene spec **(inferencia)**, y se cierra con una frontera escrita (§7.2).

### 4.5 Estado por rama y estado por iniciativa: parcial

- **WCM:** `wcm:persistent-working-memory-plan.md:70` (la iniciativa por encima del repo), `:234-235` (`workspaces` y `sessions` en el frontmatter), `:371` (`status`); `wcm:.../specs/memory-store/spec.md:7-20` (todo vive fuera de cualquier repo; escenario "Current directory is irrelevant", `:18`).
- **wt:** `wt:docs/design/product.md:88` (`mark` y `var` en `git config`), `:92` (`statusline`), `:216` y `:218`, `:243-244` (M4). **Solo nombrados**: no hay spec en `wt:openspec/specs/`.

Los dos le cuelgan metadatos a una rama o worktree, cada uno desde su lado. wt lo guarda en `git config`, que vive en el `.git/config` del repo. WCM lo guarda en `~/.wcm`. De ahí sale algo concreto: **WCM no puede escribir con `wt var` sin violar su propia spec** ("no file is created or modified inside that repository", `memory-store/spec.md:18-20`).

### 4.6 Agentes: marcadores en vivo y descubrimiento de sesiones, parcial

- **WCM:** `wcm:persistent-working-memory-plan.md:146-154` (§4.5), `:417-437` (§10), `:441-456` (§11).
- **wt:** `wt:docs/design/product.md:93` (`wt agent install`), `:219`, `:250` (M6).

wt pregunta: *¿el agente está trabajando o esperándome ahora, en este worktree?* Lo responde con hooks del agente que llaman a `wt mark`, en vivo. WCM pregunta: *¿qué sesiones fueron de esta iniciativa y qué aprendieron?* Lo responde leyendo `~/.copilot/session-state/*/workspace.yaml` (histórico y de solo lectura) y con checkpoints escritos según un contrato de archivo. Usan mecanismos distintos para preguntas distintas, y solo se cruzan en la atención (§4.7).

### 4.7 "¿Qué requiere mi atención?": parcial, en la presentación

- **WCM:** `wcm:persistent-working-memory-plan.md:338-362` (`now`), `:479-493` (§13, `attention` y `wrap`); `wcm:.../specs/working-set-view/spec.md`.
- **wt:** `wt:docs/design/product.md:19-22` (ver el estado de todos en una tabla), `:67` y `:95` (`list` y `dash`), `:220` (dashboard, M6).

La unidad de WCM es la iniciativa, incluidas las que no tienen repo, y el estado lo declara la persona. La de wt es el worktree, y el estado es de la máquina: cambios sin commitear, ahead/behind, 🤖/💬. `dash` (M6) y `attention` (F4) están lejos y sin especificar. La integración natural va en un solo sentido: **la atención de WCM consume la señal de agente de wt** (💬 en un workspace de la iniciativa X quiere decir que X necesita atención). Al revés no hace falta.

### 4.8 Lanzar un agente: parcial

- **WCM:** `wcm:persistent-working-memory-plan.md:336` (F3: `--agent` lanza una sesión nueva), `:435`, `:460-475` (§12).
- **wt:** `wt:openspec/specs/create-worktree/spec.md:236` (`-x` en primer plano, propaga el exit code, no pasa las variables del protocolo); `wt:docs/design/product.md:30-31` (principios 2 y 3), `:82` (`exec`), `:143` (clave `agent`).

Si la F3 de WCM arma "cómo lanzar el agente X en la terminal Y", duplica los launchers de wt y además rompe WCM §19: "No es un gestor de terminales" (`wcm:persistent-working-memory-plan.md:611`). Lo que le toca a WCM es **producir el contexto** (un archivo o un texto) y dejar que el usuario, o wt, corran el agente.

---

## 5. Hipótesis: refutadas, matizadas y nuevas

### Las cinco del encargo

**H1. Mismo mecanismo de `cd`: confirmada, con matices.** Ver §4.1. El mecanismo es el mismo y viene del mismo linaje: worktrunk lo usa y `0000 §2.6` lo describe (`wt:docs/decisions/0000-analisis-worktrunk.md:168-183`). Los detalles difieren en seis puntos. La conclusión "hoy son dos wrappers para el mismo problema" es cierta, pero no alcanza para fusionar: el wrapper es la parte más barata de duplicar y la más cara de unificar, porque los pisos de shell son distintos.

**H2. La F2 de WCM reimplementaría parte de wt: refutada en lo esencial.** WCM no descubre repos ni resuelve nombres (§4.3, §4.4). Lee Git de rutas que ya conoce y resuelve en el sentido inverso (de ruta a iniciativa). Lo único que comparte es una regla de comparación de rutas, que puede copiarse como texto de spec. El riesgo de duplicar existe solo si `workspace add` crece hacia la resolución por nombre, y se cierra con una frontera.

**H3. Estado por rama contra estado por iniciativa: confirmada, con un matiz importante.** Del lado de wt, `mark`, `var`, `statusline`, `agent install` y `dash` están **solo nombrados**: una fila cada uno en `product.md §4` y `§6`, en M4 y M6, sin spec. Del lado de WCM, `attention` y `wrap` (F4) son una lista de candidatos (`plan:483-489`). Se está comparando un plan con otro plan. Las preguntas son distintas (§4.6, §4.7) y se complementan. El riesgo real es que `dash` empiece a mostrar "qué sigue", o que `attention` empiece a vigilar agentes en vivo.

**H4. `resume` y `cd` hacen lo mismo: refutada en lo que importa.**

- `wt cd <name>` **no resuelve entre repos hoy**: `wt:openspec/specs/navigate/spec.md:54` resuelve solo en el repo del directorio actual, y lo entre repos es M2, que todavía no está construido.
- `wcm resume` no necesita resolver nada, porque hace `cd` a una ruta absoluta guardada (`wcm:.../shell-integration/spec.md:7-12`).
- `wt cd` no se puede usar desde otro proceso: sin la función de shell falla con exit 1, aunque se pasen `--json` o `--dry-run` (`wt:openspec/specs/navigate/spec.md:31-32`).
- El comando que serviría para eso, `wt path <name>`, está en el contrato (`wt:docs/design/product.md:72`), pero **no tiene milestone** (§7 no lo nombra), **no está construido** (no hay comando `path` en `wt:internal/cli/`) y quedó fuera del change de shell integration (`wt:openspec/changes/archive/2026-10-02-shell-integration/proposal.md:38`).

**H5. Mismo proceso: confirmada, pero no decide nada.** Los dos usan OpenSpec con los mismos skills (`.claude/skills/openspec-*` en los dos repos), y los dos tienen un test de salida de "una semana de uso real" (`wcm:persistent-working-memory-plan.md:500-507`; `wt:docs/design/product.md:267`). Eso baja el costo de tener dos repos, porque cambiar de uno a otro no exige cambiar de forma de trabajar, pero no es un argumento para fusionarlos. Una diferencia útil: wt convirtió el proceso en reglas (`wt:openspec/config.yaml:3-112`), y WCM tiene la plantilla vacía (`wcm:openspec/config.yaml:1-32`). Ver H11.

### Hipótesis nuevas

**H6. Las dos herramientas casi no coinciden hoy en la misma máquina.**

- WCM F1 está pensado para la máquina Windows corporativa: el design describe "the target machine" con Python 3.14 por `py` y Windows PowerShell 5.1 (`wcm:.../design.md:5-10`), y el plan toma la evidencia de "esta máquina" con 327 sesiones de Copilot CLI (`wcm:persistent-working-memory-plan.md:19`). Además, F1 no trae wrapper para zsh (`design.md:27`). Que F1 se pruebe en Windows es **(inferencia)** de esas citas.
- wt v1 está pensado primero para macOS (`wt:docs/decisions/0001-de-cero-en-go.md:13`). La máquina Windows sigue con wt v0.9 en PowerShell hasta M2 (`0001:53`), y wt v1 en Windows exige pwsh 7.4 (`wt:docs/design/product.md:287`; `wt:openspec/specs/shell-integration/spec.md:9-10`).

Consecuencia: durante la F1 de WCM, en la máquina corporativa conviven WCM y wt v0.9; en la Mac, wt v1 y un WCM sin `cd` automático. **Un contrato de integración escrito hoy no tendría dónde correr.**

**H7. El código de wt no se puede reusar como librería.** Todo el código Go está bajo `internal/` (`wt:internal/*`), y Go no deja importar esos paquetes desde otro módulo. WCM además es Python. La opción D solo se puede hacer con specs o protocolo compartidos, no con código, salvo que wt mueva paquetes a uno público y WCM pase a Go.

**H8. Los plugins de wt (`wt-<x>`, M5) no sirven para alojar a WCM.** Los procesos que wt lanza no reciben las variables del protocolo (`wt:openspec/specs/shell-integration/spec.md:145-146`; `wt:openspec/specs/create-worktree/spec.md:236`), y el motivo es de seguridad: "a program they run must not be able to write to the shell's directive file" (`wt:internal/shell/shell.go:106-108`). Un plugin `wt-wcm` no podría mover la shell en `resume`. **(Inferencia:** la regla está escrita para git y para `-x`, y M5 no tiene spec, pero el motivo se aplica igual.)

**H9. El nombre de un worktree en wt no es una identidad global.** El `NAME` es el último componente de la ruta (`wt:openspec/specs/list-worktrees/spec.md:23`), y la ambigüedad entre repos es un resultado de primera clase, con su propio exit code (`wt:docs/design/product.md:112`; `wt:internal/workspace/doc.go`). Si WCM guardara referencias "por nombre de wt", serían frágiles. Tiene que guardar la ruta absoluta.

**H10. Los hooks `post-*` de wt corren en segundo plano** (`wt:docs/design/product.md:173`). Un `post-cd` que llamara a `wcm` no le mostraría nada al usuario. La dirección "wt avisa a WCM" por hooks no sirve para mostrar información.

**H11. Las specs de WCM todavía no son agnósticas del lenguaje.** `wcm:openspec/config.yaml` es la plantilla vacía (`:1-32`), y `wcm:.../specs/shell-integration/spec.md:45-50` nombra `py -3.14` y `pip install`. wt hizo del agnosticismo una regla (`wt:openspec/config.yaml:91`) y le atribuye haber sobrevivido a un cambio de lenguaje (`wt:docs/decisions/0001-de-cero-en-go.md:62-63`). Para WCM, adoptar esa regla es la forma más barata de que un cambio de stack, o una fusión futura, sean reversibles.

**H12. El README de wt quedó viejo:** dice que `main` "has no working commands yet" y recomienda `@v0.1.0-alpha.3` (`wt:README.md:5-17`, `:79`). No pesa en la decisión, pero se anota en §8.

---

## 6. Evaluación de opciones

### 6.1 Abogado del diablo, dos veces

**Defensa de la fusión, como si fuera obvia**

1. *Un dolor, un usuario.* Los dos nacen de "varios agentes en paralelo en worktrees de varios repos". Tener dos herramientas significa dos instalaciones, dos líneas en el perfil, dos CI, dos flujos de release y dos `openspec/`. Para un desarrollador solo, el costo fijo de cada proyecto es alto, y wt ya pagó el suyo: `relcheck`, GoReleaser, rulesets y CI en 3 sistemas (`wt:docs/decisions/0002-versionado-y-releases.md:110-144`).
2. *WCM tiene cero líneas de código.* Elegir Go hoy no tira nada a la basura. Y un binario Go resuelve de una vez los cuatro riesgos técnicos que WCM declara: `pip` bloqueado (`design.md:130`), arranque lento (`:131`), el `python` del Store (`:132`) y la falta de wrapper en macOS (`:27`).
3. *La shell integration es la parte riesgosa, y wt ya la pagó.* Es el riesgo número 1 de wt (`wt:docs/design/product.md:306`), y hoy está testeada en 4 shells reales en CI (`wt:.github/workflows/ci.yml`). WCM la pagaría de nuevo: PS 5.1 ahora y zsh después.
4. *La F2 de WCM necesita Git, reglas de rutas y worktrees.* wt ya tiene un runner de git, un parser de porcelain, rutas nativas y la regla del worktree actual, unas 5.400 líneas de Go y 8.500 de tests (medido con `wc -l` en `release/v0.1.0`).
5. *La atención converge.* `dash` (M6) y `now`/`attention` (F4) terminan siendo la misma pantalla.
6. *wt ya planea la mitad del "grounding" de WCM:* estado por rama y agentes.

**Defensa de la separación, como si fuera obvia**

1. *Unidades distintas.* La iniciativa tiene de 0 a N repos, incluidas las que no tienen ninguno (`wcm:persistent-working-memory-plan.md:70`, `:403`, `:589`). wt es un gestor de worktrees, y WCM dice explícitamente que "No es un gestor de Git" (`:612`). Fusionar pone un concepto sin repo dentro de una herramienta de Git, o al revés.
2. *Validación distinta.* La hipótesis central de WCM, que el ritual de pausa se sostiene, "Es hipótesis hasta la F1" (`plan:622`). wt tiene M1 cerrado. Meter un producto sin validar en el contrato público de wt (`--json` versionado, exit codes, CHANGELOG) crea contrato que quizás haya que tirar. Si F1 falla, un WCM separado se borra sin tocar a wt.
3. *Pisos de plataforma incompatibles.* WCM tiene que correr en PS 5.1 (`design.md:9`), y wt excluye PS 5.1 explícitamente (`wt:docs/design/product.md:287`). Fusionar obliga a romper uno de los dos.
4. *La secuencia de wt.* Los milestones son secuenciales (`wt:docs/decisions/0002-versionado-y-releases.md:41`). Meter WCM atrasa M2, que es el diferencial (`wt:docs/design/product.md:309`), o deforma el esquema de versiones. wt ya registra como riesgo que el alcance crezca y nunca termine (`:309`).
5. *Principios que chocan.* La sincronización entre máquinas es "DESPUÉS" en WCM (`plan:525`) y non-goal en wt (`product.md:289`). WCM guarda todo fuera de cualquier repo (`memory-store/spec.md:7-20`), y wt guarda el estado por rama en `git config` (`product.md:88`). wt está pensado para distribuirse en inglés y por brew/scoop/winget (`wt:openspec/config.yaml:60-63`), y WCM es metadata personal (`plan:603`).
6. *Lo duplicado es chico* (§4.1, §4.3), y *deshacer una fusión es caro*, mientras que no fusionar no cuesta nada deshacerlo.

**Lo que sobrevive a las dos defensas**

| Argumento | Sobrevive porque… |
|---|---|
| Las unidades son distintas (iniciativa ⊃ 0..N worktrees) | La defensa de la fusión no lo refuta; solo lo esquiva. |
| La hipótesis de WCM no está validada | Incluso a favor de la fusión, el *momento* es malo. |
| Choque PS 5.1 contra pwsh 7.4 | Es un hecho de los dos repos, y solo lo cambia un dato externo (§9, pregunta 1). |
| Lo duplicado es chico | Está medido: un wrapper y tres llamadas a git. |
| Los riesgos de stack de WCM son reales y Go los resuelve | Es cierto, pero **es una decisión de stack de WCM, no de fusión**: se puede pasar a Go sin fusionarse. |
| La shell integration de wt ya está probada | Cierto, y se aprovecha copiando las reglas y el script de zsh (licencia MIT, mismo autor: `wt:LICENSE`), sin acoplar. |
| El costo fijo de dos proyectos | Cierto pero chico para WCM en F1: se instala desde el clone y no necesita releases (`design.md:142`). |
| La atención converge | Cierto, pero en M6 y F4, sin specs. Se resuelve con una señal que WCM consume, no fusionando. |

### 6.2 Costo real de cada combinación de stack

| Combinación | macOS | Windows corporativo | Costo para el autor |
|---|---|---|---|
| **WCM en Python + módulo PS 5.1** (plan actual) | Hay que instalar Python 3.14 **(inferencia)**. Sin `cd` salvo con pwsh; el wrapper de zsh queda pendiente (`design.md:27`). | Python 3.14.4 ya instalado (`design.md:7`). `pip` sin verificar; plan B: vendorizar PyYAML (`:130`). PS 5.1 funciona. | Bajo para F1. El arranque se mide en la tarea 8.2 (<300 ms). |
| **WCM en Go, producto separado** | Binario único; el zsh se copia de wt. | `.exe` sin firmar: ¿lo permite la política? (§9). Wrapper PS 5.1 propio. | Medio: rehacer `design.md` y `tasks.md`; las specs se mantienen si se vuelven agnósticas (H11). La infra de release se copia de wt. |
| **WCM dentro de wt (Go)** | El mejor caso: el wrapper ya existe. | Exige pwsh ≥ 7.4 (wt no soporta 5.1) y además un `.exe` sin firmar hasta M6 (`product.md:222`). WCM dejaría de correr en PS 5.1. | Alto ahora: encajar en M2–M6, contrato público, salida en inglés, CI en 3 sistemas. Más bajo a largo plazo. |
| **wt dentro de WCM (Python)** | Un runtime arrancando en cada `cd`, lo que 0001 descartó explícitamente (`wt:docs/decisions/0001-de-cero-en-go.md:13`, `:69`). | Igual. | Tirar M1. **Descartada.** |
| **WCM en .NET** (alternativa de `plan:554`) | Requiere `dotnet` **(inferencia)**. | Instalado (`plan:554`). | No cambia la decisión de fusión. Solo vale si Python falla y Go no se puede ejecutar ahí. |

### 6.3 Las opciones contra los seis criterios

✔ cumple · ~ cumple con costo o condición · ✘ no cumple

| Opción | 1. North Stars | 2. Costo | 3. Riesgo de no terminar | 4. Portabilidad | 5. Principios | 6. Reversibilidad |
|---|---|---|---|---|---|---|
| **A.** Separadas sin relación | ✔ hoy; ~ en F2 y F4 (deriva silenciosa) | ✔ mínimo | ✔ | ~ igual que hoy | ✔ | ✔ |
| **B.** Contrato completo ahora | ~ WCM: `resume` y F2 dependen de otra herramienta en la máquina donde wt v1 no está | ~ tests de contrato en dos repos | ✘ F2 de WCM queda atada a M2 de wt, que no puede mergear antes de `v0.1.0` | ✘ WCM en Windows pasa a exigir pwsh 7.4 y wt v1 | ~ | ~ |
| **C1.** WCM como subcomandos de wt (Go) | ✘ WCM: F1 se atrasa por la infra de wt; wt: M2 se atrasa | ✘ alto ahora | ✘✘ suma alcance al riesgo #4 de wt | ✘ sin pwsh 7 en la máquina corporativa / ✔ con pwsh 7 | ✘ WCM §19 "no es gestor de Git"; wt §8 (5.1 y sync) | ✘ contrato público, versiones, historia |
| **C2.** wt absorbido por WCM | ✘ | ✘ | ✘ | ✘ | ✘ contradice 0001 | ✘ |
| **D.** Piezas compartidas (código) | ✔ | ✘ imposible hoy (H7) | ~ | ~ | ✔ | ~ |
| **D'.** Piezas compartidas (protocolo y spec) | ✔ | ✔ unas horas | ✔ | ✔ cada uno con su shell | ✔ | ✔ |
| **E.** Postergar | ✔ | ✔ | ✔ | ✔ | ✔ | ✔ |
| **F.** E + fronteras + D' + B diferido y opcional | ✔ | ✔ docs hoy; F2 a demanda | ✔ ningún roadmap espera al otro | ✔ WCM nunca exige wt | ✔ | ✔ |

**A. Separadas sin relación.** No rompe nada, pero deja implícito lo que debería quedar escrito. Sin fronteras, la F2 de WCM puede crecer hacia la resolución por nombre (§4.4) y el `dash` de wt hacia "qué sigue" (§4.7), y la duplicación aparecería justo donde es más cara: en M4–M6 y F3–F4. Tampoco aprovecha nada de lo que wt ya resolvió.

**B. Contrato completo ahora** (WCM consume `wt list --json`, `wt path` y `wt repos --json` en F2). Hoy no hay de qué colgarlo: `wt path` y `wt repos` no existen (H4; §4.4), y `wt.list.v1` no trae lo que WCM necesita para el snapshot (§4.3). Además, ata WCM F2 a wt M2, y M2 no puede mergear nada hasta que salga `v0.1.0` (`0002:41`). Y en la máquina donde WCM se valida, wt v1 no está (H6). Empeora el North Star de WCM, porque un `resume` que depende de otro binario no es "cambiar de contexto barato" en la máquina corporativa.

**C1. WCM como subcomandos de wt** (`wt now`, `wt pause`, …). Es la mejor versión de la fusión y tiene un argumento serio: WCM no tiene código, así que elegir Go cuesta poco. Pero:

- Exige pwsh 7.4 en la máquina corporativa (wt `§8`), o que wt vuelva a soportar 5.1, que es lo que 0001 dejó atrás.
- Mete una hipótesis sin validar en un contrato público.
- No tiene lugar en la secuencia M1→M6 sin atrasar M2.
- Pone iniciativas sin repo bajo un comando cuya identidad es "worktree": los principios de wt (`openspec/config.yaml:20-30`) hablan todos de worktrees, y WCM §19 niega ser un gestor de Git.
- Deshacerla dentro de seis meses es caro: habría esquemas `wt.*.v1` publicados, CHANGELOG y versiones.

**C2. wt absorbido por WCM.** Descartada. Reescribe en Python algo cuyo verbo central es `cd`, que es justo lo que `0001` descartó por latencia.

**D. Piezas compartidas.** Compartir *código* no es posible hoy (H7). Compartir un *wrapper único* que despache a los dos binarios acopla el perfil del usuario a los dos y choca con los pisos de shell **(inferencia)**. Lo que sí sirve es **D'**: compartir *reglas*. WCM adopta las del protocolo de wt (§7.4) y su regla de specs agnósticas (H11), y copia el script de zsh cuando llegue a macOS. Cuesta horas y no crea dependencias.

**E. Postergar.** Correcta en dirección, pero sola no alcanza: postergar sin decir *qué no construir mientras tanto* deja abierta la duplicación de §4.4, §4.7 y §4.8.

**F. Opción recomendada.** Es E, más las fronteras escritas, más D', más un B mínimo, opcional y diferido. Ninguno de los dos North Stars empeora:

- WCM nunca depende de wt para cambiar de contexto.
- wt no se entera de que WCM existe. El único pedido es que construya `wt path --json`, que ya está en su contrato.
- Ningún roadmap espera al otro.
- Se deshace borrando un párrafo de cada repo.

---

## 7. Recomendación detallada (opción F)

### 7.1 Qué se decide hoy y qué no

- **Se decide:** dos productos, dos repos y dos binarios. WCM sigue en Python con el módulo PS 5.1 para F1, como está diseñado. wt sigue con M2 como está planeado.
- **Se escribe hoy, en documentos:** las fronteras (§7.2), las reglas compartidas del protocolo de `cd` (§7.4) y el evento de reevaluación (§7.5).
- **Se escribe hoy y se implementa recién en F2, solo si hace falta:** el contrato WCM → wt (§7.3).
- **No se decide hoy:** la fusión ni el stack definitivo de WCM. Las dos se deciden juntas en §7.5.

### 7.2 Fronteras: qué no construye cada uno

**WCM no construye:**

1. Descubrimiento de repos, ni recorrer raíces o directorios buscando `.git`.
2. Resolución de nombres de worktree entre repos. `workspace add` recibe una ruta, o el CWD por defecto. Un nombre solo se acepta delegándolo en wt (§7.3).
3. Crear, borrar, mover, bloquear o sincronizar worktrees o ramas.
4. Escrituras dentro de un repo, incluido `git config` (`memory-store/spec.md:18-20`). Por eso WCM nunca llama a `wt mark` ni a `wt var`.
5. Un modelo de launchers (terminal, tab, editor) para `resume --agent`. WCM produce el paquete de contexto (stdout o un archivo); el agente lo lanza la persona, `wt create -x` o `wt exec` (M2).
6. Monitoreo en vivo de agentes. Si F4 quiere esa señal, la lee de wt (§7.3, llamada 3).

**wt no construye:**

1. Ningún concepto por encima del worktree: iniciativa, próxima acción, pausa o retome.
2. Un `dash` ni una `statusline` que muestren "qué sigue" o "por qué". Muestran el estado del worktree y de sus agentes.
3. Una lectura de `~/.wcm` ni de ningún dato de WCM. wt sigue sin "nada hardcodeado a una herramienta" (`wt:openspec/config.yaml:26-27`).
4. Sincronización de estado entre máquinas: ya es non-goal (`product.md:289`).

**Composición permitida sin contrato:** el usuario puede combinar las dos en su prompt de shell (`wt statusline` y `wcm status`) o en su `$PROFILE`. Ninguno de los dos productos implementa esa combinación.

### 7.3 Contrato WCM → wt (escrito ahora, se activa en F2 si hace falta)

**Dirección.** Solo **WCM → wt**. WCM puede ejecutar `git-wt` como subproceso, únicamente para leer. wt no sabe que WCM existe.

**Ejecutable.** Siempre `git-wt`, nunca `wt`. `wt` es una función de shell, invisible para un subproceso, y en Windows `wt` es Windows Terminal (`wt:docs/design/product.md:37-45`; `wt:openspec/specs/shell-integration/spec.md:152-157`).

**Detección.** Hay que encontrar `git-wt` en el `PATH`, y además `git-wt version --json` tiene que devolver `{"schema":"wt.version.v1","version":…}` (`wt:openspec/specs/cli-contract/spec.md:140-141`) con una versión igual o mayor a la mínima que declare WCM. Si no se cumple, WCM se comporta como si wt no estuviera.

**Llamadas permitidas** (todas de solo lectura):

| # | Llamada | Esquema | Existe desde | Para qué la usa WCM |
|---|---|---|---|---|
| 1 | `git-wt -C <dir> list --json` | `wt.list.v1` (`list-worktrees/spec.md:51-52`) | `v0.1.0-alpha.1` | En `workspace add --wt <name>` mientras no exista la llamada 2: busca el `name` exacto en el repo de `<dir>`. Opcional en `now` para marcar `prunable` o `locked`. |
| 2 | `git-wt path <name> --json` | `wt.path.v1` (**a crear en wt**) | M2 (propuesta) | `workspace add --wt <name>` resolviendo entre repos. |
| 3 | `git-wt list --all-repos --json` con el marcador de agente | `wt.list.vN` (**futuro**) | M2 + M6 | Señal de atención en F4: hay un agente esperando (💬) en un workspace de la iniciativa. |

Propuesta para `wt.path.v1`, en la misma forma que `wt.cd.v1` (`navigate/spec.md:134-135`):

```json
{"schema":"wt.path.v1","path":"C:\\src\\payments.worktrees\\retries","name":"retries","branch":"feature/payment-retries","repo_path":"C:\\src\\payments"}
```

**Prohibido en el contrato:** `cd` (falla sin la función, `navigate/spec.md:31`), `create`, `remove`, `lock`, `mark`, `var` y cualquier comando que escriba.

**Lo que guarda WCM** (forma propuesta para el frontmatter de F2; corrige `plan:383-390`):

```yaml
workspaces:
  - worktree: C:/wt/payment-retries    # identidad: ruta absoluta. Única fuente para resume y CWD
    branch: feature/payment-retries    # la esperada; sirve para detectar deriva
    primary: true
    wt_name: payment-retries           # opcional, solo para mostrar. Nunca se usa para resolver
```

`repo` y `root` se derivan de Git a partir de `worktree` **(inferencia: se puede con `git -C <worktree> rev-parse`)**. Si se guardan, son caché, no identidad.

**Variables de entorno.**

- WCM ejecuta `git-wt` **sin** `WCM_CD_FILE`, `WT_DIRECTIVE_CD_FILE` ni `WT_PREVIOUS_DIR` en el entorno del hijo.
- WCM nunca escribe `WT_DIRECTIVE_CD_FILE`, y wt nunca escribe `WCM_CD_FILE`.
- Las dos funciones de shell conviven en el mismo perfil sin interferirse, porque cada una usa su propia variable.

**Errores y ausencia.**

| Caso | Comportamiento de WCM |
|---|---|
| `git-wt` no está, o la versión es menor a la mínima | Todo funciona con rutas. `--wt <name>` falla con exit 1 y el mensaje "pasá una ruta o ejecutá desde el worktree". `now` no se degrada. |
| exit 3 (no encontrado) | "no hay un worktree con ese nombre", exit 1. |
| exit 4 (ambiguo) | Muestra los `hints` de `wt.error.v1` (`cli-contract/spec.md:96-97`) y **no elige**, igual que la resolución de WCM (`plan:399`). Exit 1. |
| `schema` desconocido o cualquier otro código | Trata a wt como ausente y escribe un aviso en stderr. Nunca bloquea `pause`, `resume` ni `now`. |
| WCM no está instalado | wt no cambia en nada. |

**Versionado.** WCM depende solo de los campos que usa. Ignora los campos desconocidos y respeta la regla de versionado de wt: un cambio incompatible sube el sufijo `vN` (`cli-contract/spec.md:96-97`).

**Lo que el contrato no incluye a propósito:** el snapshot de Git de WCM (archivos sucios, últimos 5 commits, branch real). Eso lo lee WCM directamente con `git -C <worktree>`, porque Git es la evidencia (`plan:74`), wt no lo expone (§4.3) y tiene que funcionar en la máquina corporativa sin wt v1 (H6).

### 7.4 Protocolo de `cd` alineado (la pieza que se comparte, como spec)

WCM adopta las reglas de wt sin cambiar sus nombres de variable:

1. El wrapper crea el archivo y el binario **nunca** lo crea. Si no existe, el binario falla y no deja nada (`wt:.../shell-integration/spec.md:117-118`).
2. El contenido es **una ruta absoluta nativa, nunca código de shell** (`wt:.../archive/2026-10-02-shell-integration/design.md:32-37`). El wrapper tolera un salto de línea final.
3. La variable existe **solo para esa invocación** (ya está así en los dos).
4. **Los procesos que lanza el binario no la heredan.** En WCM eso es el editor de `wcm edit` y `checkpoint --edit` (`wt:.../shell-integration/spec.md:145-146`).
5. Si el `cd` falla, el resultado de la función es distinto de 0 (`wt:.../shell-integration/spec.md:98-99`).
6. Cuando WCM llegue a macOS, su función de zsh se **copia y adapta** de `wt:internal/shell/scripts/wt.zsh` (MIT, mismo autor), incluido el uso de `command` y `builtin` para esquivar alias (`wt:.../archive/2026-10-02-shell-integration/design.md:66`).

No se propone un wrapper común. Por los pisos distintos (5.1 y 7.4) y por la independencia de instalación, cada producto mantiene el suyo.

### 7.5 Evento de reevaluación y criterios

**Cuándo.** Reevaluar la fusión cuando se cumplan **las dos** condiciones:

1. Existe `phase-1-exit-test.md` de WCM con las respuestas del §14 del plan (`wcm:.../tasks.md`, tarea 8.4).
2. wt publicó `v0.2.0`, o sea, cerró M2.

**Adelantar** la reevaluación si pasa **cualquiera** de estas:

- (a) El diseño de la F2 de WCM necesita descubrir repos o resolver nombres entre repos más allá de lo que da el §7.3.
- (b) Se confirma pwsh ≥ 7.4 en la máquina corporativa **y además** `wcm now` mide más de 300 ms o `pip` está bloqueado. En ese caso el stack de WCM se mueve igual, y elegir entre "Go separado" y "Go dentro de wt" es la misma decisión.
- (c) wt empieza a especificar `dash` o `statusline` con datos que no son del worktree.

**Criterios para fusionar en ese momento** (tienen que cumplirse todos):

1. F1 validada: pause y resume por debajo de 30 s sostenidos durante la semana, con "Conversation Dependency ~ 0" (`plan:568-576`).
2. Un único piso de shell que funcione en las dos máquinas (pwsh 7.4).
3. Más de la mitad de lo que necesita la F2 de WCM se resuelve con llamadas a wt.
4. Las iniciativas sin repo siguen siendo de primera clase. Si el test de F1 muestra que casi no existen, ver el punto siguiente.
5. wt cerró M2.

**Desenlace alternativo que hay que tener presente.** Si F1 falla porque el ritual pesa, pero lo que sí sirvió fue anotar "qué sigue" por worktree, el destino natural de esa parte es `wt var <name> next=…` y `wt mark` (M4). Eso no es fusionar productos: es absorber una porción chica en wt y abandonar WCM.

Si no se cumplen los criterios, siguen separados, y se vuelve a mirar al cerrar M4 de wt o F3 de WCM, lo que llegue primero.

---

## 8. Cambios concretos sugeridos (no aplicados)

### En `working-memory-manager`

1. **Plan §19** (`persistent-working-memory-plan.md:607-616`): agregar dos filas.
   - "No es un gestor de worktrees: crear, borrar, descubrir repos y resolver nombres entre repos es de wt."
   - "No escribe dentro de un repo, tampoco en `git config`."
2. **Plan §9** (`:381-413`): la identidad de un workspace es la **ruta absoluta del worktree**; `repo` y `root` se derivan de Git; se suma un `wt_name` opcional solo para mostrar. La regla de "CWD dentro de un worktree" cita la de `wt:openspec/specs/git-worktrees/spec.md:74` (symlinks, la coincidencia más profunda, mayúsculas según el sistema).
3. **Plan §9**: aclarar que `workspace add` toma el CWD o una ruta, y que un nombre solo se acepta delegándolo en `git-wt` (§7.3).
4. **Plan §12 y §7.2 (F3)**: `resume --agent` produce el contexto y, como mucho, ejecuta un único comando configurable. No hay modelo de terminales ni de tabs.
5. **Plan §14** (preguntas posteriores a F1, `:529-538`): agregar tres preguntas para alimentar §7.5.
   - "¿Cuántas iniciativas no tenían repo?"
   - "¿Cuántas veces llegué al worktree con `wt cd` en vez de con `wcm resume`, y por qué?"
   - "¿En qué máquina usé cada herramienta?"
6. **Plan §15** (`:544-564`): dejar el criterio de §7.5(b). Si el stack cambia, en ese mismo momento se decide si es "Go separado" o "Go dentro de wt".
7. **`openspec/config.yaml`** (hoy es la plantilla, `:1-32`): agregar el contexto del producto, los principios de §3 y §19, y la regla de **specs agnósticas del lenguaje** (copiada de `wt:openspec/config.yaml:90-94`).
8. **Change `add-working-memory-layer`, `specs/shell-integration/spec.md`**:
   - agregar las reglas 1, 2, 4 y 5 de §7.4;
   - sacar `py -3.14` y `pip install` de los requirements (`:45-50`) y llevarlos a `design.md`, para que la spec quede agnóstica.
9. **Change `add-working-memory-layer`, `design.md` Non-goals** (`:27`): anotar que el wrapper de zsh es el primer follow-up después de F1, adaptado de `wt.zsh`, y que la regla de §7.4.4 se aplica al editor.
10. **Nuevo:** este informe en `docs/analysis/wcm-vs-wt.md`.

### En `worktree-manager`

1. **`docs/design/product.md` §8** (`:284-291`): agregar el non-goal "Modelar trabajo por encima del worktree (iniciativas, próxima acción, pausa y retome). `mark`, `var`, `statusline` y `dash` describen worktrees y agentes, no iniciativas."
2. **`docs/design/product.md` §7**: asignarle milestone a `wt path <name> [--json]`. Está en §4 (`:72`) pero en ningún milestone. Proponer M2, junto a `cross-repo-resolution`, porque comparten el resolver, y con esquema `wt.path.v1` (§7.3).
3. **`docs/design/product.md` §10** (`:302-309`): agregar el riesgo "Duplicar WCM: si `dash` o `statusline` empiezan a mostrar 'qué sigue'", mitigado con la frontera del punto 1.
4. **`docs/decisions/0001-de-cero-en-go.md`** (`:53`) o **`product.md` §3**: dejar explícito que adoptar wt v1 en la máquina corporativa depende de que haya pwsh ≥ 7.4 ahí. Es la misma incógnita que tiene WCM.
5. **`README.md`** (`:5-17`, `:79`): actualizar el aviso "no working commands yet" y la versión de ejemplo, porque M1 está cerrado. No pesa en la decisión.
6. Nada en specs ni en código. El contrato de §7.3 no le pide a wt nada que no esté ya en su contrato.

---

## 9. Preguntas abiertas (solo el autor puede responderlas)

1. **¿La máquina corporativa tiene pwsh 7.4 o más, o se puede instalar?** Es la pregunta que más pesa: decide si wt v1 corre ahí y si la fusión es siquiera posible. Una pista que hay que verificar: Copilot CLI corre en esa máquina (`plan:19`) y su documentación pide PowerShell 6 o más en Windows. **(Dato externo, no verificado en los repos.)**
2. **¿La política de esa máquina deja ejecutar un `.exe` sin firmar bajado de GitHub Releases?** ¿Y `pip install`? Las dos respuestas definen el costo real de "WCM en Go" y de "wt v1 en el trabajo".
3. **¿En qué máquina vas a correr el test de salida de F1?** ¿Necesitás WCM en la Mac durante F1? Si sí, el wrapper de zsh (§7.4.6) entra en F1, no después.
4. **De tus iniciativas reales, ¿qué parte no tiene repo** (investigación, incidentes, gestiones)? Si es casi ninguna, el principio "la iniciativa está por encima del repo" pesa menos y el desenlace alternativo de §7.5 gana fuerza.
5. **¿Una iniciativa típica toca un worktree o varios repos a la vez?** Si es casi siempre uno a uno, la F2 de WCM puede ser mucho más chica.
6. **Con tres agentes andando, ¿la pregunta "qué requiere mi atención" la querés por agente (`dash`) o por iniciativa (`now`)?** ¿O en una sola pantalla? Esto decide si la señal de §7.3 (llamada 3) vale la pena.
7. **¿Las iniciativas viven en una máquina o en las dos?** `~/.wcm` es local, wt excluye la sincronización y la de WCM es "DESPUÉS".
8. **¿wt sigue apuntando a que lo instale otra gente (M6, en inglés, brew/scoop/winget) y WCM sigue siendo personal?** Si los dos son personales para siempre, el argumento del contrato público de wt pierde peso a favor de la fusión.
9. **¿Cuánto tiempo semanal real tenés para los dos?** Si alcanza para uno solo, la pregunta deja de ser "fusionar o no" y pasa a ser "cuál primero". Este informe no contesta eso. Solo deja dicho que, con la opción F, ninguno de los dos roadmaps espera al otro, así que el orden se puede elegir libremente.
