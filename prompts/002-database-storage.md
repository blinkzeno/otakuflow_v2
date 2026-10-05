# 002 — Database + storage (schema.sql, WAL, layout data/, garde-fous)

## Task goal
Créer la persistance locale : schéma SQLite complet, moteur WAL, layout disque `data/` avec garde-fous anti-traversée, et tests du tri naturel.

## Matching plan step
**Étape 2 — DB + storage** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/tech-architecture/SKILL.md` — §4 schéma (8 tables), SQLite WAL, `rel_path` relatifs
- `references/security-checklist.md` — section "Toujours" (aucun secret client ; ici : aucun chemin absolu/contrôlé client)

## Existing code inspected
- `backend/api/main.py` (001) — app + `/api/health`, point d'accroche du `startup` pour `init_db()`
- `backend/core/config.py` (001) — `data_dir()`, utilisé pour le chemin du `.db`
- `AGENTS.md` §6 — tables, unicités (`page_id`, `segment_key`), règles `text_hash`/`duration`

## Decisions made
1. **`backend/db/schema.sql` est la source de vérité**, exécuté tel quel par `init_db()` (`executescript`), + table `schema_version(version integer)` pour les évolutions futures — pas d'Alembic en MVP.
2. **Moteur synchrone** (`create_engine("sqlite:///...", connect_args={"check_same_thread": False})`) + `sessionmaker` ; **une session par job/fonction**, jamais partagée entre threads. `PRAGMA journal_mode=WAL` posé via listener `connect`.
3. **Queries minimales en 002** : `queries/projects.py` (create/get/list/delete), `queries/pages.py` (bulk insert, list ordered, get), `queries/jobs.py` (create/update/get) — le reste des modules queries naîtra dans son étape (004 : jobs polling, 005 : analysis/costs...). Pas de CRUD spéculatif.
4. **Tri naturel** : `core/sort.py::natural_key(s)` découpe en segments `(int|str)` via `re.split(r"(\d+)", s)` — `page_2` < `page_10`, fallback ordre d'apparition si aucun chiffre.
5. **`storage/paths.py`** : toutes les résolutions passent par `safe_join(*parts)` qui rejette `..`, chemins absolus, `~`, et vérifie que le résultat reste sous `DATA_DIR` (`Path.resolve()` + `is_relative_to`,log + `ValueError` sinon). Layout : `projects/{pid}/originals|pages|thumbs|audio|renders|logs`.

## Assumptions (small, reversible)
- **IDs entiers autoincrement** (pas d'UUID) : suffisant à 1 utilisateur, URLs plus courtes (réversible : colonne `uuid` ajoutable).
- **`init_db()` au `startup` FastAPI** : recrée si absent, idempotent si présent (réversible : script CLI plus tard si besoin).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/db/schema.sql` | Les 8 tables + index de AGENTS.md §6, `IF NOT EXISTS` |
| `backend/db/__init__.py`, `backend/db/queries/__init__.py`, `backend/storage/__init__.py` | Packages |
| `backend/db/database.py` | `engine`, `SessionLocal`, `init_db()` (WAL + schema.sql + schema_version) |
| `backend/db/queries/projects.py` | `create_project(title)`, `get_project`, `list_projects`, `delete_project` |
| `backend/db/queries/pages.py` | `bulk_insert_pages(chapter_id, rows)`, `list_pages(chapter_id)`, `get_page` |
| `backend/db/queries/jobs.py` | `create_job`, `update_job`, `get_job`, `list_jobs(project_id)` |
| `backend/storage/paths.py` | `safe_join`, `ensure_project_dirs(pid)`, `page_path()`, `thumb_path()`, `audio_path()`, `render_path()`, `log_path()` |
| `backend/core/sort.py` | `natural_key()` |
| `backend/tests/test_schema.py` | Tables + index créés, WAL actif |
| `backend/tests/test_sort.py` | `page_2` < `page_10`, mix alphanumérique, sans chiffres |
| `backend/tests/test_paths.py` | `../evil`, absolu, `~` rejetés ; layout créé |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/api/main.py` | `@app.on_event("startup")` (ou lifespan) : `init_db()` + `ensure DATA_DIR` + log `[otakuflow] db=<path>` |

## Implementation requirements
- `database.py` :
```python
engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
@event.listens_for(engine, "connect")
def _wal(dbapi_conn, _): dbapi_conn.execute("PRAGMA journal_mode=WAL")
def get_session() -> Session: return SessionLocal()  # caller ferme (try/finally)
def init_db() -> None: crée DATA_DIR, executescript(schema.sql), INSERT schema_version si vide
```
- `schema.sql` : reprendre EXACTEMENT les 8 tables + 4 index de AGENTS.md §6 (noms, colonnes, defaults). `jobs.progress` CHECK 0-100 ? Non — validation applicative, pas de CHECK (polling écrit souvent).
- `bulk_insert_pages` : une transaction, `page_id` unique → `IntegrityError` loggé avec contexte puis propagé (jamais silencieux).
- `safe_join` : après `resolve()`, `if not resolved.is_relative_to(DATA_DIR.resolve()): raise ValueError`. Tester aussi le cas lien symbolique ? Non en MVP (Windows, extraction sans liens — cf. 003).
- Logs : `[db] init ok path=...`, `[storage] project dirs pid=...`. Aucun contenu de fichier loggé.

## Security requirements
- Aucun chemin issu du client n'atteint le disque : `safe_join` est le seul constructeur de chemins (sera imposé aux routers en 003+)
- `data/*.db` gitignoré (déjà couvert en 001, vérifier)
- Aucun secret lu/écrit dans cette étape

## Acceptance criteria
- [ ] Supprimer `data/` → redémarrer → `data/otakuflow.db` recréé, `PRAGMA journal_mode` = `wal`
- [ ] `test_sort` : `sorted(["page_10.jpg","page_2.jpg"], key=natural_key)` = `["page_2.jpg","page_10.jpg"]`
- [ ] `test_paths` : `safe_join("..", "x")` lève `ValueError`
- [ ] `pytest backend/tests -q` passe (5 tests au total avec 001)
- [ ] `npx tsc --noEmit`, `npm run lint` passent (front inchangé)

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
```

## Manual test steps
1. `Remove-Item -Recurse -Force data` (si existe), puis `.\start.ps1`.
   Résultat attendu : log `[otakuflow] db=./data/otakuflow.db`, pas d'erreur.
2. Vérifier le mode WAL :
```powershell
python -c "import sqlite3; c=sqlite3.connect('data/otakuflow.db'); print(c.execute('PRAGMA journal_mode').fetchone())"
```
   Résultat attendu : `('wal',)`.
3. Lister les tables :
```powershell
python -c "import sqlite3; c=sqlite3.connect('data/otakuflow.db'); print(sorted(r[0] for r in c.execute(\"SELECT name FROM sqlite_master WHERE type='table'\")))"
```
   Résultat attendu : `ai_costs, chapters, jobs, pages, projects, renders, script_segments, ...` (8 tables + `schema_version`).
4. `pytest backend/tests -q` → tout vert.
