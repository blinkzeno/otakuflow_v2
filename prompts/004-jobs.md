# 004 — Jobs (workers, progression, annulation, pacing IA, pause quota)

## Task goal
Exécuter les étapes longues en arrière-plan avec progression %, annulation coopérative, relance par étape, et pacing centralisé des appels IA avec pause propre à quota épuisé.

## Matching plan step
**Étape 4 — Jobs** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, comportements concrets
- `.agents/skills/implementation-prompt-writer/references/ui-plan-extras.md` — barre de progression, états (running/failed/cancelled), responsive
- `references/security-checklist.md` — section "Toujours" (pas de secret client ; les logs de jobs ne contiendront jamais prompts/clés — règle posée ici pour 005+)

## Existing code inspected
- `backend/db/queries/jobs.py` (002) — CRUD à étendre (`update_progress`, `append_log` ? logs en fichiers, pas en DB)
- `backend/services/ingestion.py` (003) — `ingest_upload()` devient la 1re fonction exécutée via `run_background` (signature inchangée)
- `backend/api/routers/projects.py` (003) — `POST /api/projects` passe de sync à `enqueue` (réponse immédiate `202 + job_id`)
- `frontend/.../WorkspacePage` (003) — brancher le polling sur l'onglet Import

## Decisions made
1. **`ThreadPoolExecutor(max_workers=JOB_WORKERS)` global**, un seul writer DB à la fois par projet (jobs d'un même projet sérialisés via verrou `threading.Lock` par `project_id`) — les jobs de projets différents peuvent coexister.
2. **Session SQLAlchemy par exécution** (`get_session()` dans le worker, `close()` en `finally`) — jamais de session partagée entre threads.
3. **Annulation coopérative** : `cancel_flags: dict[job_id, threading.Event]` ; chaque runner vérifie `should_stop(job_id)` entre deux unités de travail (page/segment) et marque `cancelled`. Pas de `kill` de thread.
4. **Logs en fichiers** (`logs/job_{id}.log`, append thread-safe via lock) ; `GET /api/jobs/{id}` retourne les 200 dernières lignes (`tail`), pas tout le fichier.
5. **Pacing IA centralisé ici** (utilisé en 005+) : `ai_gate(provider)` bloque jusqu'à `VISION_MIN_INTERVAL_SEC` écoulé depuis le dernier appel ; `ai_backoff(attempt)` = 2^attempt secondes plafonné à 60, max 3 tentatives sur HTTP 429 puis `PauseQuota` (job → `paused`, message "quota journalier épuisé — reprenez demain", reprise = relance du même job qui saute le déjà-fait).
6. **Statut `paused` ajouté** aux statuts de `jobs.status` (valeurs : `queued|running|done|failed|cancelled|paused`) — sans migration (colonne TEXT libre).
7. **Front** : hook `useJobsPolling(projectId, intervalMs=1000)` — stop aux statuts terminaux (`done|failed|cancelled`), `document.visibilitychange` → pause quand caché ; composant `JobProgress { job }` (barre %, statut, bouton Annuler si `running`, Relancer si `failed|cancelled|paused` → rappelle l'endpoint d'étape d'origine).

## Assumptions (small, reversible)
- **Pas de persistance des cancel_flags au redémarrage** : un job `running` au boot est marqué `failed` ("interrompu par redémarrage") — reprise manuelle, simple et sûr (réversible : reprise auto plus tard).
- **Progression = unités terminées / total** reportée par le runner via callback `progress(done, total)` (réversible : granularité affinée par étape).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/services/jobs.py` | Executor, `enqueue(job_id, fn)`, `should_stop`, `report_progress`, `ai_gate`, `ai_backoff`, verrous par projet, marquage `running` au boot → `failed` |
| `backend/api/routers/jobs.py` | `GET /api/projects/{id}/jobs`, `GET /api/jobs/{id}` (+ `log_tail`), `POST /api/jobs/{id}/cancel` |
| `backend/tests/test_jobs.py` | Runner factice 10 unités : progression 0→100, cancel à ~50 % → `cancelled`, `ai_gate` espace 2 appels rapides |
| `frontend/src/hooks/useJobsPolling.ts` | `({ jobs, reload })`, polling 1 s, cleanup, pause onglet caché |
| `frontend/src/components/JobProgress.tsx` | `props { job: Job, onCancel, onRetry }` |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/api/routers/projects.py` | `POST /api/projects` : crée projet + job `queued`, `enqueue(ingest_upload)`, retourne `202 {"project_id","job_id"}` |
| `backend/services/ingestion.py` | Accepte `progress`/`should_stop` optionnels (défaut no-op) + écrit `update_job` aux jalons (10/50/90/100 %) |
| `backend/api/main.py` | `include_router(jobs)`, appel `mark_interrupted_jobs()` au startup |
| `frontend/.../WorkspacePage` (onglet Import) | Affiche `JobProgress` du job `import` via polling |
| `frontend/src/services/api.ts`, `types` | `Job`, `getJobs`, `getJob`, `cancelJob` |

## Implementation requirements
- `jobs.py` :
```python
_executor = ThreadPoolExecutor(max_workers=config.job_workers())
_cancel: dict[int, threading.Event] = {}
_project_locks: dict[int, threading.Lock] = defaultdict(threading.Lock)
def enqueue(job_id: int, fn, *args) -> None:  # marque queued->running dans le worker, try/except -> failed + error
def should_stop(job_id: int) -> bool
def report_progress(job_id: int, done: int, total: int) -> None  # update_job progress=int(100*done/total)
def append_log(job_id: int, line: str) -> None  # fichier logs/job_{id}.log, préfixe "[HH:MM:SS] "
_last_call: dict[str, float] = {}
def ai_gate(provider: str) -> None:  # sleep jusqu'à MIN_INTERVAL écoulé
def ai_backoff(attempt: int) -> None  # min(2**attempt, 60)
class QuotaPaused(Exception): pass     # levée après 3x429 -> job paused + message FR/EN clair
```
- `POST cancel` : pose le flag, retourne immédiatement `{"status":"cancelling"}` (le worker confirmera `cancelled`) ; cancel d'un job terminal → 409.
- `GET /api/jobs/{id}` : `{..., "log_tail": [...200 dernières lignes...]}` — jamais le log entier.
- Ingestion : vérifie `should_stop` toutes les 5 pages ; `report_progress` à chaque page (pas cher en local).
- Front `useJobsPolling` : `useEffect` + `setInterval(1000)`, `clearInterval` au démontage et aux statuts terminaux ; `document.hidden` → `clearInterval`, visible → reprise.

## Security requirements
- Aucun secret ne touche le bundle client
- Les logs de jobs ne contiennent jamais : clés, prompts IA intégraux, chemins absolus (noms relatifs uniquement)
- `log_tail` borné (200 lignes) — pas d'exfiltration de gros fichiers via l'API
- Cancel/relance sans auth (localhost assumé, cf. AGENTS.md §6 RLS)

## Acceptance criteria
- [ ] Upload CBZ → `202` immédiat, polling `progress` 0→100, grille visible à `done`
- [ ] Cancel pendant l'import → statut `cancelled`, pas de projet à moitié affiché comme complet
- [ ] Redémarrage backend avec job `running` → job marqué `failed` ("interrompu par redémarrage") au boot
- [ ] `ai_gate` : 2 appels consécutifs espacés d'au moins `VISION_MIN_INTERVAL_SEC`
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. `.\start.ps1`, uploader un CBZ via `/`.
   Résultat attendu : redirection immédiate, barre 0→100 %, puis grille.
2. Progression API :
```powershell
curl.exe http://127.0.0.1:8000/api/projects/1/jobs
curl.exe http://127.0.0.1:8000/api/jobs/1
```
   Résultat attendu : job `stage=import`, `status=done`, `progress=100`, `log_tail` non vide.
3. Cancel : uploader un gros CBZ, cliquer Annuler à ~50 %.
   Résultat attendu : `status=cancelled`, bouton Relancer visible.
4. Redémarrage : tuer uvicorn pendant un import, relancer → job `failed` avec message d'interruption.
