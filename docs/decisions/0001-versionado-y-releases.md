# 0001 — Versionado, ramas y releases

- **Fecha**: 2026-10-09
- **Estado**: aceptada
- **Origen**: copia adaptada de la convención de `jMautone/worktree-manager` (su ADR 0002), para que los dos productos se trabajen igual.

## Contexto

El repo arrancó sin convención explícita, y se nota:

- Todo se commiteó directo a `main`: el plan, los skills de OpenSpec y la propuesta del change `add-working-memory-layer`.
- Mensajes de commit sin formato fijo, mezclando español e inglés.
- Nadie decidió qué versión produce un merge, ni cómo se publica una versión. No hay `CHANGELOG.md`, ni CI, ni GitHub Releases.
- `openspec/config.yaml` es la plantilla vacía: los artifacts no tienen reglas.

`worktree-manager` ya resolvió lo mismo con una convención que funciona: rama por change, título de PR como fuente de verdad de la versión, una pre-release por merge y un minor por milestone. Esta ADR la adopta, con tres diferencias que vienen del stack y del plan:

| | worktree-manager | working-memory-manager |
|---|---|---|
| Unidad del roadmap | milestones M1..M6 (`docs/design/product.md` §7) | fases F1..F4 (`persistent-working-memory-plan.md` §14) |
| Qué se publica | binarios por OS con GoReleaser | sdist y wheel de Python, más `checksums.txt` |
| `relcheck` | Go | Python, solo biblioteca estándar |

## Decisión

### Versiones

SemVer. **Cada fase es un minor**; `v1.0.0` sale al cerrar F4, la última fase del plan. Lo que el plan deja para "después" (búsqueda, sync, `wcm ask`) no condiciona la 1.0 y se agrega a la tabla cuando se planifique.

| Fase | Versión |
|---|---|
| F1 SWITCH | `0.1.0` |
| F2 GROUND | `0.2.0` |
| F3 DELEGATE | `0.3.0` |
| F4 ATTEND | `1.0.0` |

- Cada change o fix mergeado a `main` publica una pre-release `vX.Y.0-alpha.N` del **minor abierto**, con `N` consecutivo desde 1.
- Cerrar una fase publica `vX.Y.0`, que pasa a ser *latest*.
- Los parches `vX.Y.Z` salen solo desde una rama `vX.Y.x`, creada cuando haga falta. Hasta entonces no tienen automatización.
- No se usan `beta` ni `rc`.

**Minor abierto**: si la última versión publicada es una alpha de `X.Y`, es `X.Y`. Si es un final `vX.Y.0`, es el siguiente minor de la tabla. Si no hay nada publicado, `0.1`.

Consecuencia directa: **las fases son secuenciales**. Un change de F2 no se mergea hasta que se publica `v0.1.0`. Es lo mismo que ya pide el plan: el test de salida de F1 define el alcance de F2 y F3.

### Ramas

| Patrón | Uso | Publica |
|---|---|---|
| `vX.Y/<change>` | Change de OpenSpec. `<change>` == `openspec/changes/<change>/`, kebab-case, inglés. `X.Y` es el minor de la fase del change. | alpha |
| `fix/<slug>` | Bug fuera de un change | alpha |
| `release/vX.Y.0` | Cierre de fase | final |
| `chore/` `docs/` `ci/` `refactor/` `test/` + `<slug>` | Todo lo demás | nada |
| `dependabot/**` | Las crea Dependabot | nada |
| `vX.Y.x` | Líneas de mantenimiento, protegidas | patch |

La versión exacta no va en la rama: `alpha.N` depende del orden de merge y no se conoce al abrirla. Lo que sí se conoce es el minor.

Las ramas de trabajo se borran solas al mergear.

### Títulos de PR

El título del PR es el commit que queda en `main`:

```
<type>(<scope>)[!]: <summary> [<version>]
```

- **type**: `feat` `fix` `docs` `chore` `ci` `refactor` `test` `perf`.
- **scope**: obligatorio, kebab-case.
- **summary**: inglés, imperativo, empieza en minúscula, sin punto final. El título sin el sufijo de versión no pasa de 72 caracteres.
- **`!`**: cambio que rompe el contrato público: exit codes, comandos o flags de la CLI, el protocolo `WCM_CD_FILE`, o el formato de los archivos de `~/.wcm`. Se marca en las notas; no altera la versión (el minor ya lo decide la fase).
- **`[<version>]`**: la versión exacta que publica el merge. **Es la fuente de verdad**: el workflow de release crea el tag que dice el título.

Reglas por rama:

| Rama | type | scope | Sufijo de versión |
|---|---|---|---|
| `vX.Y/<change>` | cualquiera | `<change>` | obligatorio: `vX.Y.0-alpha.N`, donde `X.Y` es el de la rama y tiene que ser el minor abierto |
| `fix/<slug>` | `fix` | libre | obligatorio: `vX.Y.0-alpha.N` del minor abierto |
| `release/vX.Y.0` | `chore` | `release` | obligatorio: `vX.Y.0`, igual a la rama, del minor abierto y con al menos una alpha publicada |
| `chore/` `docs/` `ci/` `refactor/` `test/` | igual al prefijo | libre | prohibido |
| `dependabot/**` | cualquiera | libre | prohibido |

Ejemplos:

```
feat(add-working-memory-layer): add wcm pause, resume and now [v0.1.0-alpha.1]
fix(now): sort waiting initiatives by priority [v0.1.0-alpha.2]
chore(release): close F1 [v0.1.0]
chore(ci): bump actions/checkout from 6 to 7
ci(release): add branch, title and release conventions
```

### Merge

Solo **squash**. El commit en `main` es `<título del PR> (#N)`, sin cuerpo. El cuerpo del PR va en español, con la plantilla de `.github/pull_request_template.md`; el detalle se lee en el PR. Los commits dentro de la rama son libres, porque el squash los descarta; se recomienda Conventional Commits.

### Releases

Cada versión publicada es un GitHub Release con:

- el sdist (`.tar.gz`) y el wheel (`.whl`) de `wcm`, construidos con `python -m build`, más `checksums.txt` (SHA-256);
- en una alpha: pre-release, con notas generadas agrupando los títulos desde la versión anterior en *Features*, *Fixes* y *Other*;
- en un final: *latest*, con la sección `[X.Y.0]` de `CHANGELOG.md` como notas.

**La versión se inyecta al publicar**, igual que el `-X main.version` de un binario de Go. `pyproject.toml` declara un `version = "0.0.0.dev0"` estático en `[project]`; el release lo reescribe con la versión del título en forma PEP 440 (`v0.1.0-alpha.2` → `0.1.0a2`) antes de construir, y no commitea el cambio. La CLI lee su versión de los metadatos del paquete instalado, así que un `pip install -e .` del repo dice `0.0.0.dev0` y un wheel del Release dice la versión publicada.

Se instala con `py -3.14 -m pip install <url-del-wheel>`. Publicar en PyPI no está previsto.

### CHANGELOG

Formato *Keep a Changelog*. Cada PR que publica suma sus líneas bajo `## [Unreleased]`. El PR `release/vX.Y.0` renombra esa sección a `## [X.Y.0] — <fecha>` y abre un `[Unreleased]` vacío. Las alphas no tocan el CHANGELOG.

### Automatización

```
PR abierto/editado ──► check pr-conventions ──► rama + título + versión
        │                                          (bloquea el merge si falla)
   squash merge
        ▼
push a main ──► release.yml ──► ¿el commit tiene [vX.Y.Z…]?
                                   no → termina
                                   sí → re-valida → tag anotado → stamp → build → Release
```

- **`tools/relcheck.py`** (Python, solo biblioteca estándar, porque corre antes de instalar el proyecto): funciones puras que reciben rama, título, versiones ya publicadas y dos hechos del árbol (si existe el change de OpenSpec, si `CHANGELOG.md` tiene la sección del final) y devuelven los errores. Además genera las notas de una alpha y estampa la versión en `pyproject.toml`. Tiene tests (`tools/test_relcheck.py`) y corre en la matrix como el resto. Las versiones publicadas salen de los sufijos `[v…]` de los títulos en `main`, no de los tags, para no depender de que el workflow de release ya haya terminado.
- **`pr-conventions`** (workflow en cada PR a `main`): valida las tablas de arriba con `relcheck`. Para `vX.Y/<change>` exige que exista `openspec/changes/<change>/` o `openspec/changes/archive/*-<change>/`. Para `release/vX.Y.0` exige la sección `## [X.Y.0]` en `CHANGELOG.md` y al menos una alpha publicada de `X.Y`.
- **`release.yml`** (push a `main`, y `workflow_dispatch` en modo dry-run): si el commit trae sufijo de versión, re-valida, crea el tag anotado, estampa la versión, construye y publica con `gh release` en el **mismo job**. Un tag creado con `GITHUB_TOKEN` no dispara otros workflows. Re-ejecutarlo después de una falla es seguro: el tag se crea solo si falta y un Release existente recibe sus archivos y notas de nuevo.
- **CI**: el job `test` corre `ruff check`, `ruff format --check`, los tests de `relcheck` y `pytest` en `windows-latest`, `macos-latest` y `ubuntu-latest`. El job `build` estampa una versión de prueba y construye sdist y wheel, así que el CI construye lo mismo que se publica. Los pasos del producto se activan solos cuando existe `pyproject.toml`. El push dispara en `main`, `v*/**`, `fix/**` y `release/**`.

### Protecciones

Settings del repo:

- solo squash (sin rebase ni merge commit);
- título del squash `PR_TITLE`, cuerpo `BLANK`;
- borrar la rama al mergear.

Rulesets:

| Ruleset | Cubre | Reglas |
|---|---|---|
| `main` | rama por defecto | sin borrar, sin force-push, historia lineal, PR con solo squash, checks requeridos (los 3 `test`, `build`, `pr-conventions`) con la rama al día |
| `protect-maintenance-branches` | `v*.*.x` | sin borrar, sin force-push |
| `protect-release-tags` | `v*` | sin borrar, sin mover |

"Rama al día" evita que dos PR abiertos tomen la misma alpha: al mergear uno, el otro tiene que actualizarse, el check corre de nuevo y ve la versión ya usada. Cuesta un click en *Update branch*.

## Transición

El orden importa: el paso 3 exige un check que tiene que existir antes en `main`.

1. **PR de la convención**, que no publica: esta ADR, `CONTRIBUTING.md`, `CLAUDE.md`, `CHANGELOG.md`, `tools/relcheck.py`, workflows, `ruff.toml`, Dependabot, plantilla de PR, `openspec/config.yaml` y el anexo de versiones del plan §14. Título `ci(release): add branch, title and release conventions`, squash.
2. **Settings y rulesets** de arriba, a mano, todavía sin `pr-conventions` como requerido.
3. **Activar el candado**: `pr-conventions` como check requerido, con la rama al día.
4. **`add-working-memory-layer` → `v0.1.0-alpha.1`**: rama `v0.1/add-working-memory-layer` desde `main`. Antes de aplicar, `/opsx:update` alinea sus `tasks.md` con esta convención:
   - la tarea del scaffold declara `version = "0.0.0.dev0"` en `[project]` y suma `ruff` a las dependencias de desarrollo;
   - la última tarea suma sus líneas bajo `[Unreleased]` y abre el PR `feat(add-working-memory-layer): <summary> [v0.1.0-alpha.1]`;
   - el test de salida de F1 (tarea 8.4) sale del change: es la definición de "listo" de F1 y se hace antes de `release/v0.1.0`, no dentro del PR del change.

   Al mergear se verifica que el Release sea pre-release, que tenga sdist, wheel y `checksums.txt`, y que el wheel instalado diga `0.1.0a1`.

Los artifacts de `add-working-memory-layer` están en inglés y se commitearon en `main` antes de esta convención; se dejan así, porque es historia. Los changes nuevos siguen la tabla de idiomas de `CONTRIBUTING.md`.

## Consecuencias

- Cada versión es trazable de punta a punta: rama `v0.1/<change>` → título `[v0.1.0-alpha.N]` → tag → Release → versión del paquete.
- La versión dice en qué fase está el producto.
- Las fases no se solapan: F2 no arranca a mergear hasta publicar `v0.1.0`.
- Un merge a `main` con PR abiertos obliga a actualizar los demás antes de mergearlos.
- `main` deja de recibir commits directos.
- Los proposals de OpenSpec declaran su rama `vX.Y/<change>` en la sección Fase (regla en `openspec/config.yaml`).
- Las sesiones de agentes que crean ramas con otro prefijo (por ejemplo `claude/…`) no pasan `pr-conventions`: la rama se renombra a un patrón válido antes de abrir el PR.

## Alternativas descartadas

- **Copiar `relcheck` en Go tal cual**: obliga a tener Go en un repo Python solo para validar títulos.
- **`relcheck` en bash**: difícil de testear; contradice la regla de que toda tarea lleva su test.
- **Versión dinámica con `setuptools-scm` o `hatch-vcs`**: ata la convención a un backend de build concreto y lee la versión del tag, no del título; el estampado funciona con cualquier backend.
- **`v1.0.0` al cerrar F1**: compromete el contrato de CLI y el formato de archivos demasiado temprano.
- **`v1.0.0` al cerrar F3**: F4 es parte del plan; la 1.0 tiene que incluir la vista de atención.
- **Releases sin artefactos (solo tag)**: obliga a clonar para instalar una versión concreta en la máquina de uso.
- **Publicar en PyPI**: es una herramienta personal; el GitHub Release alcanza.
- **Ramas `fN/<change>`**: no se leen como versión y obligan a recordar que `f4` es `1.0`.
- **Merge por rebase**: cada commit de la rama llega a `main` y las notas se llenan de ruido.
- **Que todo merge publique**: una alpha por cada bump de Dependabot.
- **CHANGELOG automático**: pierde la prosa curada.
- **release-please**: calcula la versión desde los commits; choca con "el título es la fuente de verdad" y con el salto de F4 a 1.0.
- **Taguear a mano**: no garantiza que título y tag coincidan.
