# 001 — Scaffold (venv, backend/, frontend/, env, checks, FFmpeg)

## Task goal
Mettre en place le squelette exécutable du projet : backend FastAPI qui démarre, frontend Vite qui s'affiche et parle à l'API, variables d'environnement versionnées, et les 4 checks verts.

## Matching plan step
**Étape 1 — Scaffold** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure obligatoire du plan, règles goal/décisions/tests exacts
- `.agents/skills/implementation-prompt-writer/references/security-checklist.md` — section "Toujours" (aucun secret côté client, `.env` gitignoré)
- `.agents/skills/tech-architecture/SKILL.md` — stack validée (FastAPI + SQLite + React/Vite, imageio-ffmpeg, pas de Next.js/Supabase)

## Existing code inspected
- Repo quasi-vide : seuls `AGENTS.md` (conventions, contrats API, §10 checks), `docs/PROJECT_BRIEF.md`, `docs/TECH_ARCHITECTURE.md` et `.agents/skills/*` existent. Rien à modifier, tout à créer.

## Decisions made
1. **Python 3.11+ via `py -m venv .venv`** — version arrivée par défaut sur Windows via python.org/Microsoft Store ; ne pas imposer 3.12 (certaines wheels IA en retard).
2. **Dépendances épinglées en `~=` dans `backend/requirements.txt`** (liste fermée dès 001 pour ne plus y toucher) : `fastapi`, `uvicorn[standard]`, `sqlalchemy`, `pydantic`, `python-dotenv`, `pillow`, `mutagen`, `imageio-ffmpeg`, `google-genai`, `edge-tts`, `pytest`, `httpx` (TestClient).
3. **Tailwind CSS v4 via `@tailwindcss/vite`** — pas de `postcss.config`, juste `@import "tailwindcss"` dans `src/index.css`. Standard actuel, moins de fichiers.
4. **Node 20 LTS+, `npm`** — pas de pnpm/yarn (1 dev, 0 doc à écrire en plus).
5. **Config backend : `python-dotenv` + getters typés dans `backend/core/config.py`** — pas de `pydantic-settings` (dépendance en moins pour 13 variables simples).
6. **`GET /api/health → {"status": "ok"}`** est la seule route de 001 — le front placeholder l'appelle et affiche "API : ok". Preuve de vie du câblage complet.
7. **Le front buildé est servi par FastAPI uniquement si `frontend/dist/` existe** (montage conditionnel + log warning sinon) — le dev front reste sur `npm run dev` + proxy.

## Assumptions (small, reversible)
- **Python accessible via `py`** : si absent, le message d'erreur de `start.ps1` indique d'installer Python 3.11+ (réversible : changer l'invocation).
- **`google-genai` et `edge-tts` s'installent mais ne sont pas appelés en 001** : présents pour figer les versions tôt (réversible : versions bumpées plus tard si conflit).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/requirements.txt` | Dépendances épinglées `~=` (voir Décisions §2) |
| `backend/api/__init__.py`, `backend/core/__init__.py`, `backend/tests/__init__.py` | Packages Python |
| `backend/api/main.py` | App FastAPI : CORS localhost, `GET /api/health`, montage statique conditionnel de `frontend/dist` |
| `backend/core/config.py` | `DATA_DIR`, `HOST`, `PORT` (getters typés, défauts `./data`, `127.0.0.1`, `8000`) |
| `backend/tests/test_health.py` | TestClient : `GET /api/health` → 200 + `{"status":"ok"}` |
| `backend/tests/test_ffmpeg.py` | `imageio_ffmpeg.get_ffmpeg_exe()` existe + `ffmpeg -version` (timeout 30 s) retourne 0 |
| `frontend/package.json` | Scripts `dev`, `build`, `lint`, `preview` ; deps react, react-dom, react-router-dom ; devDeps vite, typescript, eslint, tailwindcss v4, @tailwindcss/vite |
| `frontend/vite.config.ts` | Plugin react + tailwindcss, proxy `/api` → `http://127.0.0.1:8000`, `server.port` 5173 |
| `frontend/tsconfig.json` | Strict + `noUnusedLocals` + `noUnusedParameters` (issu du template `react-ts`, inchangé sauf vérification) |
| `frontend/src/main.tsx`, `frontend/src/App.tsx`, `frontend/src/index.css`, `frontend/src/services/api.ts` | Entrée + placeholder "Otakuflow — API : ok/ko" + `API_BASE = import.meta.env.VITE_API_URL ?? ""` |
| `frontend/index.html` | Titre `Otakuflow`, `<div id="root">` |
| `.env.example` | Les 13 variables de AGENTS.md §8 avec placeholders (`GEMINI_API_KEY=` vide) |
| `.gitignore` | `.venv/`, `__pycache__/`, `node_modules/`, `.env`, `data/`, `frontend/dist/` |
| `start.ps1` | Crée `.venv` si absent → `pip install -r backend/requirements.txt` → `uvicorn backend.api.main:app --host 127.0.0.1 --port 8000` |

### Modifier
| Fichier | Changement |
|---------|-----------|
| _(aucun)_ | Repo vide : création uniquement |

## Implementation requirements

### `backend/api/main.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
# comportement :
# - CORS : allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"] uniquement
# - GET /api/health -> {"status": "ok"}
# - si frontend/dist/index.html existe : mount StaticFiles(html=True) sur "/"
#   sinon : logger warning "frontend/dist missing — run npm run build in frontend/"
# - logger au démarrage : "[otakuflow] DATA_DIR=<...>" (jamais de secret)
```

### `backend/core/config.py`
```python
# getters typés, ex. :
def data_dir() -> str: ...   # os.getenv("DATA_DIR", "./data")
def host() -> str: ...       # "127.0.0.1"
def port() -> int: ...       # 8000
# + load_dotenv() appelé à l'import. Aucune clé IA lue en 001.
```

### `frontend/src/services/api.ts`
```typescript
export const API_BASE: string = import.meta.env.VITE_API_URL ?? "";
export async function getHealth(): Promise<{ status: string }> {
  const res = await fetch(`${API_BASE}/api/health`);
  if (!res.ok) throw new Error(`health failed: ${res.status}`);
  return (await res.json()) as { status: string };
}
```

### `frontend/src/App.tsx`
- Affiche `Otakuflow` + statut API via `getHealth()` (`"API : ok"` vert / `"API : ko — <message>"` rouge). Pas de router en 001 (une seule vue).

### `start.ps1`
- `$ErrorActionPreference = "Stop"` ; vérifie `py --version` (message clair si absent) ; crée `.venv` si absent ; installe requirements ; lance uvicorn au premier plan (logs visibles).

### Cas d'erreur explicites
- `frontend/dist` absent → warning log, pas de crash.
- Port 8000 occupé → uvicorn échoue avec son message natif (ne pas masquer).

## Security requirements
- Aucun secret ne touche le bundle client (`VITE_API_URL` seul, vide en prod)
- `.env` gitignoré, `.env.example` sans valeur réelle (`GEMINI_API_KEY=` vide)
- CORS verrouillé aux 2 origines dev locales, bind `127.0.0.1` uniquement
- `data/` gitignoré dès 001 (les CBZ de test n'iront jamais dans git)

## Acceptance criteria
- [ ] `GET http://127.0.0.1:8000/api/health` retourne `{"status":"ok"}` en < 1 s
- [ ] `http://localhost:5173` affiche "Otakuflow" + "API : ok" (via proxy Vite)
- [ ] `python -c "import imageio_ffmpeg; print(imageio_ffmpeg.get_ffmpeg_exe())"` retourne un chemin existant
- [ ] `pytest backend/tests -q` passe (2 tests : health + ffmpeg)
- [ ] `npx tsc --noEmit` passe (depuis `frontend/`)
- [ ] `npm run lint` passe (depuis `frontend/`)
- [ ] `npm run build` passe et le backend sert `frontend/dist` sans warning après build
- [ ] `git status --short` ne montre ni `.env`, ni `data/`, ni `dist/`, ni `.venv/`

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Prérequis : Python 3.11+ (`py --version`) et Node 20+ (`node --version`).
2. Backend : exécuter `.\start.ps1` depuis la racine.
   Résultat attendu : logs uvicorn sur `http://127.0.0.1:8000` + ligne `[otakuflow] DATA_DIR=./data`.
3. Health check :
```powershell
curl.exe http://127.0.0.1:8000/api/health
```
   Résultat attendu : `{"status":"ok"}`.
4. Frontend dev (second terminal) :
```powershell
cd frontend; npm install; npm run dev
```
   Ouvrir `http://localhost:5173` → voir "Otakuflow" + "API : ok".
5. Build + servage statique :
```powershell
cd frontend; npm run build; cd ..
```
   Relancer `.\start.ps1`, ouvrir `http://127.0.0.1:8000` → même page servie sans warning `frontend/dist missing`.
6. Test négatif : créer un `.env` local avec `GEMINI_API_KEY=fake` → `git status --short` ne doit PAS le lister.
7. Test négatif : arrêter le backend, recharger `:5173` → la page affiche "API : ko" (pas d'écran blanc).
