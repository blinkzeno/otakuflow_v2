# 023 — Vision-First V2 (audit + migration par phases, corrige)

## Task goal
Auditer la V1 puis migrer vers un moteur vision-first mesure et borne pour 8 Go RAM / 2 Go VRAM, en commencant par une Phase 0 de calibration puis une Phase 1 webtoon 16:9 sans casser la V1.

## Matching plan step
**Etape hors-serie V2** — s'insere apres 009-hardening, ne remplace aucune etape 001-009. V1 reste le fallback via `PIPELINE=v1|v2`.

## Skills read
- `project-ideation` — cadrage discussion, reponses : webtoon-first, flag v1|v2, Edge puis local, 16:9 d'abord. Correction ulterieure : CPU par defaut (pas GPU dev), 8 Go RAM / 2 Go VRAM.
- `implementation-prompt-writer` — structure du present plan, decisions explicites, criteres mesurables.
- `tech-architecture` (a lire avant Phase 0) — choix modeles ONNX CPU int8 mesures avant adoption.

## Existing code inspected
- `backend/services/ingestion.py` — extract ZIP/CBZ, tri `natural_key`, `page_id=ch{id}_p{index:04d}` index-based, RGB + exif_transpose, thumbs 480px.
- `backend/providers/gemini_vision.py` — `analyze_pages(images,prompt,model)` batch N pages/appel, `synthesize`, `generate_script`, `complete_json`, Pydantic + 1 retry.
- `backend/providers/base.py` — `PageAnalysis` : focus {x,y,w,h 0-1000}, focus_regions [{x,y,w,h,order,kind}], page_kind, importance 0-10. Pas de bbox sujet fiable.
- `backend/services/analysis.py` — `_payload` thumbnail 1568 + JPEG q80, batch 8, `ai_gate` + backoff 429, skip `pending_pages`, log `ai_costs`.
- `backend/services/script.py` — `generate()` depuis analyses JSON, `page_refs` filtres sur index valides, split/merge/reindex `ch{id}_s{pos:03d}`, gate `reviewed`.
- `backend/services/tts.py` + `backend/providers/edge_tts.py` (edge-tts~=7.0) — Edge-TTS par segment, `text_hash`, durees mutagen. A verifier : evenements de frontiere mots/phrases en streaming avant tout Whisper Phase 3.
- `backend/services/timeline.py` — `build_timeline()` durees audio reelles uniquement, joint focus/focus_regions/page_kind.
- `backend/services/video.py` — `_art_regions` (projection lignes papier/dessin), `_regions_for_page`, `_crop_box` (MIN_CROP_W=0.6, WIDE_LIMIT=16/9), `_still` fond flou type fit, `_page_clip` zoompan 3840x2160 -> 1920x1080 couteux et saccade. Constate : fenetre 16:9 pleine largeur 800px = 800x450 upscale 2.4x vers 1920.
- `backend/core/config.py` + `.env` — VISION_MODEL light, TEXT_MODEL strong, seuils disperses dans video.py.
- `backend/db/database.py` — SQLite WAL via `PRAGMA journal_mode=WAL`, `check_same_thread=False`, une session par job. Exigence : transactions courtes en V2.
- `backend/services/jobs.py` — `ThreadPoolExecutor(JOB_WORKERS=2)`, `_project_locks` un writer/projet, `enqueue`, cancel cooperatif, `ai_gate`. Exigence V2 : file heavy exclusive (vision/TTS/render jamais en meme temps).
- `backend/db/schema.sql` — pas de visual DB. A creer a part.

## Decisions made
1. **Webtoon d'abord, 16:9 fige** — Phase 1 = format_detector + strip_slicer + text-box + candidats. 9:16 = parametre `OUTPUT_ASPECT` non prioritaire.
2. **Flag `PIPELINE=v1|v2`** — V1 intacte, branche V2 dans video.py/timeline.py, fallback V1 si visual DB vide.
3. **COMPUTE_MODE=cpu par defaut** — 2 Go VRAM ne justifient pas de complexite GPU. Pas de branche GPU en Phase 0/1. `h264_nvenc` teste seulement si NVIDIA Pascal+ detecte, sinon libx264 veryfast 2-3 threads.
4. **Deux modes candidats (correction upscale)** — `fill` (remplit cadre, upscale calibre en Phase 0, ex. plafond a fixer entre 2.5-3.5x selon mesures) et `fit` (segment centre sur fond flou comme `_still` V1, upscale ~1.0x). `upscale_max=2.0` abandonne car il rejetterait ~tout un webtoon 700-1000px de large.
5. **Sujet = proxy, pas de bbox en Phase 1** — `cut_guard` et `taille sujet` calcules depuis saliency OpenCV ou zone de dessin `_art_regions` existante. `focus_regions` Gemini = a priori faible pondere, jamais verite.
6. **Texte Phase 1 = `text_box` + `watermark` uniquement** — OpenCV trouve bulles/cadres mais ne distingue pas dialogue/narration/SFX ni texte sur dessin. Classification fine reportee (petit ONNX seulement si mesure Phase 0 le justifie). Watermark = position + repetition inter-pages.
7. **Metrique non circulaire** — jeu etiquete main 30 plans (avec/sans bulle) pour precision/rappel du detecteur, en plus du taux global.
8. **Lien page_refs -> candidats defini** — Gemini inchange Phase 1. Regle code : pour chaque segment/script, candidats des segments visuels dont `page_spans` intersectent `page_refs`, puis budget visuel + dedup cosinus + alternance cadrages.
9. **Edge-TTS conserve Phases 0-2** — verifier d'abord les boundary events edge-tts 7.0 en streaming ; Whisper/alignement force seulement si absents.
10. **Chiffres par code, sens par LLM** — scores/bbox/crops/durees calcules ; Gemini juge emotion/importance sur shortlist, IDs en enum fermee, fallback embedding.

## Assumptions (small, reversible)
- **content_hash ajoute sans casser page_id** : `ch{id}_p{index:04d}` conserve, hash contenu en colonne pour cache re-import.
- **Bande jamais recollee en pixels** : profils 1D par page concatenes, image source rouverte seulement pour crops. Si trop lent, on re-mesure.
- **Analyse basse-res 640px large** : coordonnees normalisees 0-1000, appliquees plein format au rendu. Reversible si precision insuffisante.

## Garde-fous materiel (8 Go RAM / 2 Go VRAM, normatifs)
- `COMPUTE_MODE=cpu` par defaut dans `.env.example` et `config.py`.
- Ne jamais recoller la bande en pixels ; profils lignes page par page (grayscale 640px), concat tableaux 1D numpy.
- Candidats = coordonnees uniquement + miniature 320px pour UI ; crops rendus a la demande, jamais stockes en masse.
- File heavy exclusive : `jobs.py` `_project_locks` + verrou global `heavy_lock` — vision, TTS lourd, render ne tournent jamais en meme temps. Un seul modele charge a la fois, decharge (`del` + `gc`) apres usage.
- SQLite WAL, transactions courtes (un commit par page/segment, pas de transaction chapitre).
- Phase 2+ : ONNX Runtime CPU quantifies int8 mesures avant adoption ; embeddings CLIP ViT-B/32 seulement sur ~100-200 meilleurs candidats ; pas de SigLIP, pas de SAM, pas de VLM local, pas d'OCR lourd. Semantique = Gemini en lot sur shortlist.
- Rendu Phase 3 : abandon zoompan 3840 ; crop d'abord puis `warpAffine` sub-pixel 1080p en Python, pipe rawvideo -> FFmpeg libx264 veryfast threads 2-3 ; preview 540p.

## Files to create / modify

### Creer (Phase 0 — calibration, nouveau)
| Fichier | But |
|---------|-----|
| `backend/vision/__init__.py` | package vision |
| `backend/vision/calibrate.py` | `run_calibration(chapter_id)` : distribution largeurs, temps/operation, pic RAM psutil, sort seuils proposes |
| `backend/vision/profiles.py` | profils 1D basse-res + concat sans recollage pixels |
| `backend/vision/format_detector.py` | `detect_format(dims) -> webtoon\|manga_page\|mixed` + confiance, log `[vision]` |
| `backend/vision/strip_slicer.py` | segments webtoon + `page_spans` + `pan_vertical` (>1.5x hauteur sortie) |
| `backend/vision/text_detector.py` | `text_box` + `watermark` uniquement {bbox_px, bbox_norm, remove_for_video} |
| `backend/vision/candidate_generator.py` | modes `fill`/`fit`, `pan_vertical`, gardes calibrees |
| `backend/vision/visual_scorer.py` | heuristiques code + proxy sujet + poids `defaults.yaml` + `rejected_reason` |
| `backend/vision/vision_pipeline.py` | orchestration idempotente + cache version modeles, 1 echec != arret chapitre |
| `backend/vision/heavy_lock.py` | verrou global vision/TTS/render exclusifs |
| `backend/config/defaults.yaml` | seuils/poids/budgets/modeles, jamais en dur |
| `backend/database/visual_schema.sql` | tables visual (pages, segments_panels, text_regions, candidates, scores) + version modeles |
| `backend/tests/test_calibration.py` | test distribution + budgets mesurables |
| `backend/tests/test_page_mapping.py` | test page_refs -> candidats via page_spans |
| `eval/text_boxes_30/` | jeu etiquete 30 plans + script `eval_text.py` precision/rappel |
| `prompts/024-phase0-calibration.md` | plan execution Phase 0 detaille |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/core/config.py` | ajouter `PIPELINE`, `OUTPUT_ASPECT`, `COMPUTE_MODE=cpu`, lecture `defaults.yaml` |
| `backend/services/jobs.py` | ajouter `heavy_lock` exclusif + mesure psutil temps/pic RAM par job |
| `backend/services/video.py` | branche V2 (fill/fit) derriere flag, V1 inchange sinon ; preparer pipe warpAffine Phase 3 (non actif) |
| `backend/services/timeline.py` | regle mapping page_refs->candidats + budget/dedup/alternance + `reason` tracabilite, fallback pages |
| `backend/providers/edge_tts.py` | sonder boundary events streaming (log capabilities, sans changer API) |
| `.env.example` | documenter nouvelles vars, placeholders uniquement |

## Implementation requirements

### Phase 0 calibration (bloquant avant seuils)
- `calibrate.py::run_calibration(chapter_id) -> CalibrationReport` avec : histogramme largeurs pages (min/p50/p95/max), temps moyen par operation (profil 1D, slice, text_box, candidat, score) en ms, pic RAM process (psutil) et par page, upscale theorique fill 16:9 (1920/largeur) distribution.
- Sortie `data/projects/{id}/calibration.json` + log `[vision] calib width_p50=.. upscale_p95=.. ms/page=.. ram_peak_mb=..`.
- Seuils proposes : `fill.upscale_max` (defaut provisoire 3.0, ajuste d'apres p95 mesure, jamais 2.0 impose), `fit` toujours accepte, `text_max_ratio`, `gutter_thresh`.
- Aucun seuil Phase 1 fige sans ce rapport sur 1 vrai chapitre webtoon.

### strip_slicer sans recollage pixels
- `profiles.py::page_profile(img640_gray) -> np.ndarray[float32]` (variance/gradient par ligne) ; `concat_profiles(list) -> band_profile` ; `slice_band(band_profile) -> segments` avec `page_spans=[(page_index,y0,y1)]`, coords normalisees 0-1000 + px plein format.
- Image source rouverte uniquement dans `candidate_generator` pour crop demande.

### text_detector restreint
- `detect_text(img640) -> list[{kind: text_box\|watermark, bbox_px, bbox_norm, remove_for_video:true}]`. Pas de dialogue/narration/sfx en Phase 1.
- `watermark` = composante repetee meme zone sur >=3 pages (IOU + position basse/haute), toujours exclu.
- Precision/rappel mesures sur `eval/text_boxes_30` (30 crops etiquetes main) ; seuils ajustes pour rappel >= precision (mieux vaut sur-exclure une bulle que la rater).

### candidate_generator fill/fit
- `generate(segment, aspect="16:9") -> list[Candidate]` ou `Candidate={candidate_id=sha1(content_hash+coords+kind)[:12], panel_id, mode: fill\|fit, kind: full\|medium\|detail\|pan_vertical, crop_norm, crop_px_fullres, thumb320_rel, upscale_fill, text_ratio, proxy_subject_ratio}`.
- `fill` : crop exact aspect, `upscale_fill=1920/crop_w_fullres` ; rejet si `upscale_fill > fill.upscale_max` calibre -> marque `needs_upscale`, bascule `fit` possible.
- `fit` : segment entier centre sur fond flou (reuse `_still` V1), upscale ~1.0, jamais rejete sur resolution.
- `pan_vertical` si segment >1.5x hauteur sortie.

### visual_scorer avec proxy sujet
- Metriques code 0-1 : `proxy_subject` (saliency spectral OpenCV ou part zone `_art_regions` dans crop), `text_ratio` (surface text_box), nettete Laplacian, contraste/entropie, adequation ratio, marge resolution. Poids dans `defaults.yaml`.
- `focus_regions` Gemini : bonus faible (+0.1 max) si IOU>0.3, jamais determinant.
- `rejected_reason` obligatoire : `upscale_exceeded|text_heavy|empty|low_sharpness`.

### Mapping page_refs -> candidats (explicite)
```python
def candidates_for_segment(page_refs: list[int], visual_index: dict) -> list[Candidate]:
    # 1. segments visuels dont page_spans intersecte page_refs
    # 2. filtre text_ratio <= seuil + tri score desc
    # 3. dedup : similarite cosinus embeddings (Phase 1 = pHash/histogramme, CLIP seulement Phase 2 sur top 100-200) seuil 0.92 garde meilleur
    # 4. budget visuel par duree audio : calme 1 plan/3-5s, tension 2-4s, action 0.8-2.5s (intensite Gemini, duree reelle audio)
    # 5. alternance : jamais 2x meme kind ni meme panel_id a la suite sauf cadrage clairement different
    # 6. chaque plan = {timeline_shot_id, visual_id, scene_id, start/end, crop, camera:intention, reason}
```
- Gemini inchange Phase 1 ; Director = cette fonction, pas de LLM libre.

### Budgets et locks
- `heavy_lock = threading.Lock()` global ; `vision_pipeline`, `tts.ensure_voices` lourd, `video.render_chapter` l'acquierent ; log `[jobs] heavy_wait=..s`.
- Mesure par job : `time/page`, `ram_peak_mb` (psutil), ecrits dans `renders.timeline_json.meta` et logs. Plafonds fixes apres Phase 0 (ex. `ram_peak < 1500 MB`, `ms/page < 800` en CPU — a confirmer par calibration).

## Security requirements
- `GEMINI_API_KEY` serveur uniquement, jamais `VITE_*`, jamais `/api/*`.
- Chemins derives IDs via `safe_join`, jamais client. Uploads allowlist + sniff ZIP + anti-traversee conserves.
- Logs sans prompts ni chemins absolus (masquage `data/`).
- `defaults.yaml` + `.env.example` sans secrets ; `.env` gitignore.

## Acceptance criteria
- [ ] Phase 0 : `calibration.json` sur 1 webtoon reel avec distribution largeurs, ms/operation, ram_peak_mb, et `fill.upscale_max` justifie par mesure (pas 2.0 impose).
- [ ] Candidats `fill` + `fit` generes, coords uniquement + thumb 320px, aucun crop masse stocke.
- [ ] Texte : precision/rappel sur jeu 30 plans etiquetes main publies (`eval/text_boxes_30` + `eval_text.py`), rappel >= 0.85 vise.
- [ ] Proxy sujet documente (saliency ou art-ratio), `focus_regions` bonus faible uniquement.
- [ ] Mapping page_refs->candidats teste (`test_page_mapping`) : intersection page_spans, budget, dedup, alternance.
- [ ] `PIPELINE=v1` non-regression (1 chapitre MP4 identique ±1s).
- [ ] Heavy exclusif verifie : 2 jobs lourds simultanes = second attend (log `heavy_wait`).
- [ ] `pytest backend/tests -q` passe ; seuils/modeles en `defaults.yaml`, rien en dur.
- [ ] Edge-TTS boundary : rapport ecrit (evenements dispo ou non dans edge-tts 7.0) pour decider Whisper Phase 3.

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
```

## Manual test steps
1. Lancer : `powershell -ExecutionPolicy Bypass -File start.ps1` puis `http://127.0.0.1:8000`.
2. Import 1 CBZ webtoon -> noter `chapter_id`, Analyze V1 OK.
3. Lancer calibration : `python scripts/calibrate.py --chapter <id>` -> verifier `data/projects/<id>/calibration.json` (largeurs, upscale_p95, ms/page, ram_peak_mb).
4. Fixer `fill.upscale_max` dans `backend/config/defaults.yaml` d'apres rapport, relire `COMPUTE_MODE=cpu`.
5. Lancer `vision_pipeline` V2 -> inspecter DB visual (segments, text_box/watermark, candidats fill/fit + thumbs 320).
6. Lancer `eval_text.py` sur `eval/text_boxes_30` -> noter precision/rappel.
7. Generer script/review/voice/render V1 avec `PIPELINE=v1` -> MP4 OK ; basculer `PIPELINE=v2` -> timeline avec `reason` + fallback V1 si vide.
8. Concurrence : lancer vision + render simultanes -> verifier second attend (`heavy_wait` dans log job).
9. Negatif : CBZ 700px large + `fill.upscale_max` bas -> verifier bascule auto `fit` sans rejet massif, `rejected_reason` present.
