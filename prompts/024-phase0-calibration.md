# 024 — Phase 0 calibration (mesures avant seuils)

## Task goal
Mesurer un chapitre webtoon reel (largeurs, upscale fill theorique, ms/operation, pic RAM) pour figer les seuils Phase 1 sur des faits, sans ecrire de seuils en dur.

## Matching plan step
**Phase 0 de 023** — bloquant avant 025 (vision-min). Ne touche ni Gemini, ni script, ni TTS, ni render V1.

## Skills read
- `implementation-prompt-writer` — plan actionnable, signatures exactes, criteres mesurables.
- `tech-architecture` — CPU par defaut, ONNX int8 seulement si mesure, 1 modele a la fois, WAL transactions courtes.
- `project-ideation` — corrections utilisateur : fill/fit, proxy sujet, texte restreint, metrique non circulaire, mapping explicite.

## Existing code inspected
- `backend/services/video.py:48-64,125-191` — constantes BLANK_STDDEV, WHITE_LEVEL, `_row_flags`, `_art_regions` (projection lignes) a reutiliser en basse-res ; `_still` = reference mode `fit`.
- `backend/services/ingestion.py:55-63` — pages normalisees JPEG q88 `p_{index:04d}.jpg`, dimensions stockees ; calibration lit ces fichiers via `storage/paths.safe_join`.
- `backend/storage/paths.py:20-26` — `safe_join` obligatoire, rejet `..` et absolus ; `project_dir`, `page_path`.
- `backend/core/config.py` — `data_root()`, `job_workers()` ; a etendre avec `PIPELINE`, `OUTPUT_ASPECT`, `COMPUTE_MODE`.
- `backend/services/jobs.py:104-146` — `enqueue`, `_project_locks`, cancel cooperatif ; Phase 0 ajoute `heavy_lock` global sans changer l'API.
- `backend/db/database.py:39-42` — WAL actif ; Phase 0 = lectures seules + 1 ecriture JSON, aucune migration.
- `backend/providers/edge_tts.py:20-26` — `Communicate.stream()` ne conserve que `type==audio` ; Phase 0 sonde les autres `type` (boundary/word) en lecture seule.
- `scripts/preview_framing.py` — pattern CLI `sys.path.insert(0, root)` + reuse `video._open_frame` ; a imiter pour `scripts/calibrate.py`.
- `backend/requirements.txt` — pas de `psutil`, pas de `numpy`/`opencv` ; a ajouter et epingler.

## Decisions made
1. **Basse-res 640px large, coords normalisees 0-1000** — profils 1D par page concatenes, jamais de recollage pixels. Plein format rouvert seulement pour verification ponctuelle.
2. **fill.upscale_max provisoire 3.0** — ajuste d'apres p95 mesure (`1920 / largeur`), jamais 2.0 impose. `fit` toujours accepte.
3. **psutil pour RAM** — `Process.memory_info().rss` echantillonne avant/apres chaque operation ; pic conserve. Pas de profiler lourd.
4. **heavy_lock des Phase 0** — `threading.Lock()` global non bloquant pour calibration (lecture seule), obligatoire pour vision/render Phase 1+.
5. **Jeu 30 plans en scaffold vide** — Phase 0 cree `eval/text_boxes_30/` + `eval_text.py` avec 0 image (l'utilisateur etiquette apres), pas de seuil precision/rappel fige ici.

## Assumptions (small, reversible)
- **1 chapitre webtoon suffit** : calibration sur le chapitre courant ; si mixed/manga, on recalibre (script `--chapter` generique).
- **OpenCV + numpy suffisent** : `opencv-python-headless~=4.x` + `numpy~=1.26` + `psutil~=5.9` ajoutes ; si conflit, versions ajustees sans changer le code.

## Files to create / modify

### Creer
| Fichier | But |
|---------|-----|
| `backend/vision/__init__.py` | package vide + docstring garde-fous |
| `backend/vision/profiles.py` | profils 1D basse-res + concat |
| `backend/vision/calibrate.py` | `run_calibration(chapter_id)` -> rapport + JSON |
| `backend/vision/heavy_lock.py` | verrou global exclusif |
| `backend/config/defaults.yaml` | seuils provisoires + budgets vides a remplir par mesure |
| `scripts/calibrate.py` | CLI `--chapter ID [--limit N]` |
| `eval/text_boxes_30/README.md` | protocole etiquetage 30 plans |
| `eval/eval_text.py` | calcul precision/rappel (scaffold, dataset vide = skip) |
| `backend/tests/test_calibration.py` | tests unitaires profils + rapport |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/core/config.py` | ajouter `pipeline()`, `output_aspect()`, `compute_mode()` (defaut `cpu`), `load_defaults()` YAML |
| `backend/requirements.txt` | ajouter `numpy`, `opencv-python-headless`, `psutil` epingles |
| `.env.example` | ajouter `PIPELINE=v1`, `OUTPUT_ASPECT=16:9`, `COMPUTE_MODE=cpu` |
| `backend/providers/edge_tts.py` | ajouter `probe_stream_types(text, voice)` log-only (ne change pas `synthesize`) |

## Implementation requirements

### `backend/vision/profiles.py`
```python
import numpy as np
from PIL import Image

TARGET_W = 640  # largeur analyse, jamais plein format en boucle

def page_profile(gray640: Image.Image) -> np.ndarray:
    """Variance + gradient horizontal par ligne, float32 [H]."""
    # entree : Image L 640px large ; sortie : vecteur 1D contigu

def concat_profiles(profiles: list[np.ndarray]) -> np.ndarray:
    """Concat 1D sans recoller pixels. Retourne bande virtuelle."""

def gutter_cuts(band: np.ndarray, gutter_thresh: float, min_gap: int, min_run: int) -> list[tuple[int,int]]:
    """Decoupe segments (y0,y1) en coords bande 640px. Pur code, aucun LLM."""
```
- Reuse seuils `video.py` (`WHITE_LEVEL=235`, `BLANK_STDDEV=6.0`) comme valeurs initiales lues depuis `defaults.yaml`, pas importees en dur.
- Aucun `Image.open` plein format en boucle ; `page_profile` recoit deja le resize 640.

### `backend/vision/calibrate.py`
```python
def run_calibration(chapter_id: int, limit: int | None = None) -> dict:
    """Lit pages via safe_join, mesure et ecrit data/projects/{pid}/calibration.json.
    Retourne dict JSON-seralisable. 1 image corrompue = skip + log, jamais d'arret."""
```
- Metriques obligatoires : `widths {min,p50,p95,max,n}`, `upscale_fill_p95 = 1920/p50` et distribution, `ms_per_op {profile,slice,text_probe,candidate_probe,score_probe}`, `ram_peak_mb`, `pages_measured`, `compute_mode`, `output_aspect`.
- `text_probe` = reuse `_row_flags` basse-res (compte lignes papier, pas de classification) ; `candidate_probe` = 1 crop fill + 1 fit par segment (coords seules, pas de PNG masse).
- Ecriture : `paths.safe_join("projects", str(pid), "calibration.json")`. Log : `[vision] calib chapter=X pages=N width_p50=W upscale_p95=U ms/page=M ram_peak_mb=R`.
- Duree cible : < 60s pour 100 pages en CPU.

### `backend/vision/heavy_lock.py`
```python
import threading
heavy_lock = threading.Lock()
def heavy_acquire(blocking: bool = True, timeout: float = -1) -> bool: ...
def heavy_release() -> None: ...
```
- Log `heavy_wait` par l'appelant (jobs Phase 1), pas ici.

### `backend/config/defaults.yaml`
```yaml
output_aspect: "16:9"
compute_mode: "cpu"
fill: {upscale_max: 3.0, provisional: true}
fit: {always_allowed: true}
gutter: {thresh: 235, min_gap_ratio: 12, min_run_ratio: 8}
text: {kinds: ["text_box", "watermark"], max_ratio: 0.25}
proxy_subject: {method: "art_ratio", gemini_bonus_max: 0.1}
budgets: {ram_peak_mb_max: null, ms_per_page_max: null}  # remplis apres calibration
```
- `config.load_defaults()` lit ce YAML une fois (cache), surchargeable par env. Aucun seuil vision en dur ailleurs apres Phase 0.

### `scripts/calibrate.py`
- Usage : `.\.venv\Scripts\python scripts/calibrate.py --chapter <id> [--limit 20]`. Pattern `sys.path.insert` comme `preview_framing.py`. Print resume 5 lignes + chemin JSON.

### `eval/` scaffold
- `eval/text_boxes_30/README.md` : protocole (30 crops 320px, label `has_bubble true/false`, watermark exclu, 10 faciles / 10 moyens / 10 difficiles).
- `eval/eval_text.py` : si dossier vide -> `print("empty eval set, skipping")` exit 0 ; sinon precision/rappel vs `detect_text` futur.

### `backend/providers/edge_tts.py` probe
```python
def probe_stream_types(text: str = "Hello world. Second sentence.", voice: str | None = None) -> list[str]:
    """Retourne sorted(set(types vus dans stream)). Log-only, aucun changement synthesize."""
```
- Reponse attendue : `["audio"]` ou `["audio","boundary",...]` selon edge-tts 7.0 ; le rapport decide Whisper Phase 3.

## Security requirements
- Aucun secret touche. `calibration.json` sans chemins absolus (relatifs `projects/...`).
- `safe_join` obligatoire pour chaque lecture image ; rejet `..`.
- Deps ajoutees sans code reseau nouveau ; `opencv-headless` (pas de GUI).

## Acceptance criteria
- [ ] `scripts/calibrate.py --chapter <id>` produit `calibration.json` avec widths, upscale distribution, ms/op, ram_peak_mb sur 1 vrai chapitre.
- [ ] `fill.upscale_max` justifie par p95 dans le rapport (pas 2.0 impose) ; `defaults.yaml` charge via `config.load_defaults()`.
- [ ] Aucun recollage pixels : `profiles.py` n'ouvre jamais d'image plein format en boucle (verifie par lecture code).
- [ ] `heavy_lock` importe et acquis/rejete sans deadlock (test unitaire).
- [ ] `probe_stream_types` retourne la liste des types vus (log screenshot/console).
- [ ] `pytest backend/tests -q` passe (inclut `test_calibration.py`).
- [ ] `eval/eval_text.py` exit 0 sur set vide.

## Checks to run
```bash
.\.venv\Scripts\python -m pytest backend/tests -q
.\.venv\Scripts\python scripts/calibrate.py --chapter <id>
.\.venv\Scripts\python eval/eval_text.py
```

## Manual test steps
1. Preparer : 1 projet avec CBZ webtoon importe (onglet Import), noter `chapter_id` via `/api/projects/{id}` (`GET http://127.0.0.1:8000/api/projects`).
2. Lancer serveur : `powershell -ExecutionPolicy Bypass -File start.ps1` -> `http://127.0.0.1:8000`.
3. Calibration limitee : `.\.venv\Scripts\python scripts/calibrate.py --chapter <id> --limit 20`
   Attendu : console `[vision] calib chapter=<id> pages=20 width_p50=... upscale_p95=... ms/page=... ram_peak_mb=...` + fichier `data/projects/<pid>/calibration.json` valide JSON.
4. Calibration complete : sans `--limit`. Attendu : < 60s / 100 pages, `ram_peak_mb` < 1500 (a confirmer selon machine 8Go).
5. Verifier `defaults.yaml` : `.\.venv\Scripts\python -c "from backend.core.config import load_defaults; print(load_defaults())"` -> `fill.upscale_max=3.0 provisional=true`.
6. Probe TTS : `.\.venv\Scripts\python -c "from backend.providers.edge_tts import probe_stream_types; print(probe_stream_types())"` -> liste types (ex. `['audio']` ou avec `boundary`) ; noter pour Phase 3.
7. Eval vide : `.\.venv\Scripts\python eval/eval_text.py` -> `empty eval set, skipping` exit 0.
8. Negatif : `--chapter 99999` inexistant -> erreur claire `chapter not found`, pas de traceback brut ni chemin absolu.
