# 003 — Import + pages (upload CBZ/ZIP, indexation, visionneuse)

## Task goal
Importer un CBZ/ZIP (extraction sûre, tri numérique, indexation `page_id`) et afficher la grille des pages, avec les originaux intacts.

## Matching plan step
**Étape 3 — Import + pages** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, tests exacts
- `.agents/skills/implementation-prompt-writer/references/ui-plan-extras.md` — grille responsive, composants listés avec props
- `references/security-checklist.md` — section "Toujours" (allowlist extensions, pas de traversée, fichiers par ID)

## Existing code inspected
- `backend/db/queries/{projects,pages,jobs}.py` (002) — CRUD à réutiliser, pas de SQL dans le service
- `backend/storage/paths.py` (002) — `safe_join`, `ensure_project_dirs`, constructeurs de chemins
- `backend/core/sort.py` (002) — `natural_key` pour le tri des membres ZIP
- `backend/core/config.py` (001) — ajouter `max_upload_mb()` (défaut 500)
- `backend/api/main.py` (001) — inclure les nouveaux routers
- `frontend/src/services/api.ts`, `App.tsx` (001) — étendre `api.ts`, router vers pages

## Decisions made
1. **Extensions acceptées** : `.cbz`, `.zip` (upload) ; images `.jpg/.jpeg/.png/.webp/.bmp` (extraites). Le reste est ignoré et compté (`skipped_files` loggé). Pas de RAR/CBR/PDF en MVP.
2. **Sniff réel** : `zipfile.is_zipfile()` sur le fichier reçu — l'extension seule ne suffit pas (un `.cbz` renommé `.exe` est rejeté en 422).
3. **Extraction sans traversée** : chaque membre est validé (pas absolu, pas de `..` après normalisation, pas de lien), `__MACOSX/`, fichiers cachés (`.`-préfixe) et dossiers `__MACOSX` ignorés ; écriture via `safe_join` uniquement.
4. **Normalisation** : `ImageOps.exif_transpose` + `.convert("RGB")` + sauvegarde JPEG q88 sous `pages/p_{index:04d}.jpg` + vignette q70 max 480px sous `thumbs/`. L'upload original est conservé tel quel sous `originals/<nom-fichier>`.
5. **`page_id = f"ch{chapter_id}_p{index:04d}"`**, `page_index` 1-based dans l'ordre de tri. `width/height` lus via Pillow. Image corrompue (`verify()` échoue) → page sautée + comptée, jamais d'arrêt.
6. **Sync en 003, job `done` immédiat** : `POST /api/projects` crée le projet, exécute l'ingestion dans la requête, puis marque le job `done` progress 100. L'étape 004 transformera l'appel en `enqueue` **sans changer la signature de l'endpoint** ni le service (déjà découpé en fonction pure `ingest_upload()`).
7. **Front** : `react-router-dom` (`/` liste, `/p/:id` workspace), onglets Import/Pages en 003 (Analysis/Script/Voice/Export ajoutés par leurs étapes). Grille : 2 col mobile → 4 (md) → 6 (lg) ; clic → panneau détail (image + métadonnées + statut analyse "pending").

## Assumptions (small, reversible)
- **Limite 500 Mo contrôlée après écriture du temp** (pas de streaming) : simple et suffisant en local (réversible : streaming si besoin).
- **Ordre ZIP = ordre de secours** si aucun membre ne contient de chiffre (réversible : flag `reading_order` déjà en schéma pour 005+).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/services/__init__.py`, `backend/api/routers/__init__.py` | Packages |
| `backend/services/ingestion.py` | `ingest_upload(tmp_path, filename, title) -> dict` (projet+chapitre+pages+job done) |
| `backend/api/routers/projects.py` | `GET /api/projects`, `POST /api/projects` (multipart), `GET /api/projects/{id}`, `DELETE /api/projects/{id}` (+ suppression disque via `shutil.rmtree` du dossier projet) |
| `backend/api/routers/pages.py` | `GET /api/chapters/{id}/pages`, `GET /api/pages/{id}`, `GET /api/pages/{id}/image` (FileResponse, media type selon suffixe) |
| `backend/tests/test_ingestion.py` | CBZ synthétique : `page_2`, `page_10`, `__MACOSX/._x`, `notes.txt`, 1 PNG corrompu → assertions d'ordre/comptes/`page_id` |
| `frontend/src/pages/ProjectsPage.tsx` | Liste + formulaire d'upload (file + title) |
| `frontend/src/pages/WorkspacePage.tsx` | Coquille onglets (Import, Pages actifs ; autres en "bientôt" disabled) |
| `frontend/src/features/pages/PageGrid.tsx` | Grille + `props { pages: Page[], onSelect(id) }` |
| `frontend/src/features/pages/PageDetail.tsx` | `props { page: PageDetail }` : image, index, dimensions, statut |
| `frontend/src/types/index.ts` | `Project`, `Chapter`, `Page`, `PageDetail` (miroirs JSON API, aucun `any`) |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/api/main.py` | `include_router(projects)`, `include_router(pages)` |
| `backend/core/config.py` | Ajouter `max_upload_mb()` |
| `frontend/src/services/api.ts` | `listProjects`, `createProject(file,title)`, `getProject`, `deleteProject`, `listPages`, `getPage`, `pageImageUrl(id)` |
| `frontend/src/App.tsx` | Router `/` → ProjectsPage, `/p/:id` → WorkspacePage |

## Implementation requirements
- `ingest_upload()` :
```python
def ingest_upload(tmp_path: str, filename: str, title: str) -> dict:
    # 1. vérifie taille <= MAX + is_zipfile sinon ValueError("not a CBZ/ZIP archive")
    # 2. create_project/create_chapter (titre), ensure_project_dirs
    # 3. shutil.copy upload -> originals/<filename assaini (basename uniquement)>
    # 4. liste membres -> filtre -> tri natural_key -> pour chaque : safe extract vers temp,
    #    Pillow verify/transpose/RGB -> pages/p_NNNN.jpg + thumbs/t_NNNN.jpg, bulk rows
    # 5. update page_count, create_job(status done, progress 100)
    # 6. retourne {"project_id":..., "chapter_id":..., "page_count":..., "skipped":...}
    # Toute erreur inattendue : job failed + error message, dossier projet supprimé (pas de projet à moitié créé)
```
- `POST /api/projects` : `UploadFile` + `Form(title)` ; extension dans {`.cbz`,`.zip`} sinon 422 ; écrit le fichier sous `data/tmp/` (créé, `safe_join`) puis appelle le service ; job `failed` → HTTP 500 avec `{"detail": message}` safe (pas de traceback).
- `GET /api/pages/{id}/image` : `page.rel_path` → `safe_join` → `FileResponse(media_type={"jpg":"image/jpeg",...}[suffix])`, 404 si fichier manquant (DB et disque désynchronisés → 404 explicite, pas 500).
- `DELETE /api/projects/{id}` : supprime DB (cascade) + `shutil.rmtree(project_dir, ignore_errors=False)` avec try/except loggé (disque partiellement supprimé → 500 explicite).
- Front : upload via `FormData`, barre d'état simple "Import..." (polling du job = étape 004, pas ici) ; erreurs affichées depuis `detail`.

## Security requirements
- Aucun secret ne touche le bundle client ; `VITE_API_URL` seul
- Allowlist extensions + sniff `is_zipfile` ; taille ≤ `MAX_UPLOAD_MB`
- Extraction : pas de `..`/absolu/liens, `__MACOSX/` et cachés ignorés, écriture via `safe_join` uniquement
- Images servies par ID (`/api/pages/{id}/image`), jamais de chemin client ; `Content-Type` fixé serveur
- `filename` de l'upload : `basename` uniquement pour `originals/`

## Acceptance criteria
- [ ] Upload d'un CBZ 40 pages → `page_count=40`, `page_index` 1..40, `p_0001.jpg`..`p_0040.jpg` + thumbs présents
- [ ] `page_2` triée avant `page_10` (couvert par test + CBZ réel en test manuel)
- [ ] `__MACOSX/`, `.DS_Store`, `.txt`, PNG corrompu → ignorés/comptés, import vert
- [ ] Upload d'un `.exe` renommé `.cbz` → HTTP 422, aucun fichier écrit
- [ ] `GET /p/:id` affiche la grille ; clic → détail avec image lisible
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. `.\start.ps1` + `cd frontend; npm run dev`.
2. Fabriquer un CBZ de test (noms piégeux) :
```powershell
python -c "import zipfile; z=zipfile.ZipFile('test_ch.zip','w'); [z.write(f) for f in @('page_10.jpg','page_2.jpg')]"
```
   (utiliser 3-4 vraies images renommées + 1 `.txt` + dossier `__MACOSX/` vide.)
3. Upload via la page `/` (titre "Test Ch.1").
   Résultat attendu : projet créé, redirection `/p/<id>`, onglet Pages = grille dans l'ordre `page_2` avant `page_10`.
4. Négatif :
```powershell
curl.exe -X POST http://127.0.0.1:8000/api/projects -F "file=@C:\Windows\System32\notepad.exe;filename=evil.cbz" -F "title=Evil"
```
   Résultat attendu : HTTP 422, rien sous `data/projects/`.
5. `DELETE` le projet via l'UI → dossier `data/projects/<id>` disparu du disque.
