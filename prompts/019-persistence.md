# 019 — Persistance ancrée au projet (plus jamais vierge)

## Task goal
Garantir que projets, analyses, scripts, voix et vidéos survivent à
tout redémarrage quel que soit le dossier de lancement, en ancrant
`data/` et `.env` à la racine du projet, avec preuve visible au boot.

## Matching plan step
Hors séquence (fiabilisation 002). Touche config, chemins, démarrage.
Aucun changement API, schéma, UI, pipeline.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan

## Existing code inspected
- `backend/core/config.py` — `load_dotenv()` (CWD) + `data_dir()` relatif brut
- `backend/storage/paths.py` — `data_root() = Path.cwd() / data_dir` : la cause directe
- `backend/db/database.py` — `db_path()` idem via CWD
- `backend/api/main.py` — lifespan logge le chemin db (relatif, peu parlant)
- `start.ps1` — suppose lancé depuis la racine (venv, uvicorn relatifs)

## Decisions made
1. **Racine = dossier parent de `backend/`** : `repo_root()` dans
   `config.py` via `Path(__file__).resolve().parent.parent.parent`
   (jamais de CWD). `load_dotenv(repo_root / ".env")`.
2. **`DATA_DIR` absolu ou ancré** : nouveau `config.data_root() -> Path`
   (absolu si l env est absolu, sinon `repo_root / valeur`).
   `storage/paths.py` et `database.py` l utilisent ; `data_dir()` brut
   conservé pour compat (plus aucun appelant interne après ce plan —
   vérifier par grep, supprimer si orphelin... non : le garder, coût
   nul, risque nul. Décision : garder).
3. **Preuve au démarrage** : lifespan logge `[otakuflow] db=<absolu>
   projects=N` (compte via `list_projects`, try/except → `?` si DB
   verrouillée, jamais de crash au boot).
4. **`start.ps1` auto-ancré** : `Set-Location $PSScriptRoot` en première
   ligne (venv et uvicorn toujours créés/lancés au bon endroit).
5. **Tests intacts** : `DATA_DIR` absolus des tests inchangés (ancrage
   transparent). Nouveau test : `chdir` ailleurs + `DATA_DIR` relatif →
   `data_root()` reste sous la racine du projet.

## Assumptions (small, reversible)
- **Une seule racine projet** : le code tourne depuis son repo (vrai en
  localhost ; réversible : `DATA_DIR` absolu pour tout autre montage).

## Files to create / modify

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/core/config.py` | `repo_root()`, `data_root()`, `load_dotenv` ancré |
| `backend/storage/paths.py` | `data_root()` délègue à `config.data_root()` |
| `backend/db/database.py` | `db_path()` via `config.data_root()` |
| `backend/api/main.py` | Log `projects=N` au démarrage |
| `start.ps1` | `Set-Location $PSScriptRoot` en tête |
| `backend/tests/test_paths.py` | Test d ancrage (chdir + relatif → racine projet) |

## Implementation requirements
- `config.py` :
```python
def repo_root() -> Path:
    return Path(__file__).resolve().parent.parent.parent

load_dotenv(repo_root() / ".env")

def data_root() -> Path:
    raw = os.getenv("DATA_DIR", "./data")
    candidate = Path(raw)
    return candidate if candidate.is_absolute() else (repo_root() / candidate).resolve()
```
- `paths.data_root()` : `return config.data_root()`.
- `database.db_path()` : `return config.data_root() / "otakuflow.db"`.
- Lifespan : après `init_db`, `n = len(list_projects())` dans try/except,
  `logger.info("[otakuflow] db=%s projects=%s", db_file, n)`.
- Test :
```python
def test_data_root_anchored_to_repo(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATA_DIR", "./data")
    root = paths.data_root()
    assert root.is_absolute() and root.parent.name != tmp_path.name
    assert root == config.repo_root() / "data"
```
- `start.ps1` : première ligne active `Set-Location $PSScriptRoot`.

## Security requirements
- Aucun (chemins serveur uniquement, garde-fous `safe_join` inchangés ;
  `.env` lu à un seul endroit fixe au lieu du CWD = moins de surprise)

## Acceptance criteria
- [ ] Démarrage depuis un autre dossier (`cd C:\ ; start.ps1` chemin absolu) → mêmes projets visibles, pas de `data/` créé ailleurs
- [ ] Log boot : chemin absolu + `projects=N`
- [ ] Test d ancrage vert
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Créer un projet (upload CBZ) via `.\start.ps1` normal.
2. Arrêter, puis lancer depuis ailleurs :
```powershell
cd C:\; & "C:\Users\king\Desktop\Nouveau dossier\otakuflow_v2\start.ps1"
```
   Résultat attendu : log `projects=1`, aucun dossier `data` créé sous `C:\`, projet visible sur `http://127.0.0.1:8000`.
3. Vérifier qu aucun `otakuflow.db` n existe hors du projet :
```powershell
Get-ChildItem "C:\" -Filter otakuflow.db -ErrorAction SilentlyContinue
```
   Résultat attendu : vide (ou seulement l historique, pas de nouveau).
