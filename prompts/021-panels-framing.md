# 021 — Cadrage par cases webtoon (focus_regions + tuiles auto)

## Goal
Chaque page produit une suite de plans serrés sur une case ou un groupe de bulles, dans l'ordre de lecture, sans couper le contenu, sans zoom excessif, sans blanc vide, avec fond flou issu du même crop et Ken Burns centré — en une phrase.

## Skills lus
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, requirements concrets
- `.agents/skills/implementation-prompt-writer/references/security-checklist.md` — section "Toujours" + section IA (clé server-only, output validé avant sauvegarde, pas de log de données)
- `.agents/skills/tech-architecture/SKILL.md` — rappel couches Python (services ↔ providers ↔ db/queries)

## Code existant inspecté
- `backend/services/video.py` (324 lignes, lu en entier) — `_framed` force `ratio = "4:3"` (l.161) et ignore `settings["crop_ratio"]` ; zoom statique `LIGHT_ZOOM = 1.05` (l.51, l.165) en plus du Ken Burns ; `zoompan` sans `x`/`y` (l.187-190) ; `_concat`/`_mux`/`render_chapter` réutilisables tels quels ; `LIGHT_ZOOM`, `_focus_center`, `_crop_box` (ancien), `_framed` à remplacer
- `backend/services/timeline.py` (97 lignes, lu en entier) — `page_focus()` + `build_timeline()` : ajouter `focus_regions` à côté de `focus`, rien d'autre
- `backend/providers/base.py` (57 lignes, lu en entier) — `FocusRegion` en `int` sans `order` : passer en `float` + `order: int = 1`
- `backend/services/analysis.py` — **pas de `import json`** (à ajouter) ; branche `done` l.129-134 (`analysis_json=item.model_dump_json()`) où injecter `_clean_regions`
- `backend/prompts/analyze_pages.txt` (13 lignes, lu en entier, en anglais) — ajouter la consigne `focus_regions` **en anglais**
- `backend/providers/gemini_vision.py` — `analyze_pages` valide déjà via Pydantic (`BatchAnalysis.model_validate_json`) : le nouveau champ passe sans autre changement
- `backend/tests/test_montage.py` — `test_crop_box_centered_on_focus` et `test_framed_upscales_small_pages` ciblent les fonctions supprimées : à réécrire vers la nouvelle API (voir § Acceptance)
- `backend/tests/` — pas de dossier `scripts/` en repo : créer `scripts/preview_framing.py` à la racine (nouveau dossier autorisé, usage dev uniquement)

## Décisions et hypothèses
- Décisions :
  1. `focus_regions` coexiste avec `focus` (jamais supprimé) : `timeline.py` expose les deux, le renderer préfère `focus_regions`, repli `focus` → tuiles auto. Zéro migration DB (colonne `analysis_json` inchangée, JSON enrichi).
  2. Tests en `backend/tests/test_framing.py` (convention repo : tests sous `backend/tests/`, pas `tests/`).
  3. `crop_ratio` devient un vrai setting : défaut `"2:3"` (pages verticales = cas dominant, choix vertical déjà acté), validé contre `CROP_RATIOS`. Le test existant `test_crop_ratio_rejected` (`"5:7"` → `ValueError` match `"crop_ratio"`) reste vert tel quel.
  4. `kenburns` reste dans `DEFAULT_SETTINGS` (défaut `True`, test existant conservé) ; le zoom devient `KENBURNS_END = 1.06` centré (`x`/`y` explicites).
  5. Mémoire bornée : `_segment_clips` charge les frames du segment en mémoire ; un segment de 120 pages ≈ 120 images Pillow — acceptable en local, pas de streaming (hypothèse : chapitres ≤ 150 pages).
  6. Aucun changement frontend : l'ajout d'un champ JSON ne casse pas les types TS existants (vérifié à l'exécution via `tsc --noEmit`).
- Hypothèses (petites, réversibles) :
  - `BLANK_STDDEV = 6.0` calibré sur scans propres ; si faux positifs sur pages sombres, monter à 10 sans toucher au reste.
  - `MIN_REGION_SECONDS = 1.5` : en dessous, la fusion `_reduce` s'applique ; réversible par constante.

## Fichiers susceptibles de changer
- `backend/services/video.py` — constantes + `_num`, `_is_blank`, `_rect_from_focus`, `_auto_tiles`, `_regions_for_page`, `_crop_box` (nouvelle signature), `_blurred_fill` (rapide), `_open_frame`, `_load_frame`, `_still`, `_page_clip` (zoompan centré), `_union`, `_reduce`, `_segment_clips`, boucle `render_chapter` (remplacer bloc `page_videos`) ; import `ImageStat` ajouté ; `LIGHT_ZOOM`, `_focus_center`, `_framed` supprimés
- `backend/providers/base.py` — `FocusRegion` en `float` + `order`
- `backend/prompts/analyze_pages.txt` — consigne `focus_regions` en anglais
- `backend/services/analysis.py` — `import json` + `_clean_regions` + branche `done`
- `backend/services/timeline.py` — champ `focus_regions` par page
- `backend/tests/test_framing.py` — nouveau (code exact § 6 de la spec, chemins adaptés : aucun import à changer, `video` importé depuis `backend.services`)
- `backend/tests/test_montage.py` — réécrire `test_crop_box_centered_on_focus` + `test_framed_upscales_small_pages` vers nouvelle API (`_crop_box(496, 2560, "2:3", rect-tuple)`, `_regions_for_page`/`_still`) ; le reste inchangé
- `scripts/preview_framing.py` — nouveau (code exact § 6, `sys.path` racine déjà prévu)
- `prompts/021-panels-framing.md` — ce fichier

## Requirements d'implémentation
- Comportement concret : code exact fourni en § 5 de la spec utilisateur, appliqué tel quel à l'exception de `DEFAULT_SETTINGS["crop_ratio"] = "2:3"` + validation `crop_ratio must be one of [...]` dans `validate_settings`.
- Cas d'erreur explicites : image manquante → `ValueError("page image missing")` (déjà couvert) ; `_rect_from_focus` invalide → `None` (skip silencieux + tuiles auto en dernier recours) ; `render length off` conservé ; `chunk_dead`/retry quota inchangés.
- Logs requis : `logger.warning("[render] full frame kept (no usable focus)")` supprimé avec l'ancien `_framed` ; ajouter `logger.info("[render] page %s: %s regions", ...)` ? Non — pas de log par page (bruit) : conserver uniquement les logs existants (`[render] chapter=... seconds=...`).
- Performance : `_blurred_fill` en petit (480×270) comme spécifié ; timeouts ffmpeg inchangés (900 s) ; `_page_clip` inchangé côté timeout.

## Requirements de sécurité
- Aucun secret ne touche le bundle client (aucun changement frontend/API).
- `GEMINI_API_KEY` reste server-only dans `providers/` (le nouveau champ `focus_regions` transite par la validation Pydantic existante avant sauvegarde).
- Output IA validé avant sauvegarde (Pydantic + `_clean_regions` : bornes 0-1000, taille mini 50, `order` par défaut = position).
- Pas de chemin fourni par le client : `preview_framing.py` lit des chemins CLI locaux (outil dev, jamais exposé) ; `safe_join` inchangé pour le pipeline.
- Erreurs API sans secrets (patterns existants conservés).

## Critères d'acceptation
- [ ] `pytest backend/tests/test_framing.py` passe entièrement (6 tests)
- [ ] `pytest backend/tests/` complet passe (montage réécrit inclus, aucune régression)
- [ ] Preview `data/tmp/preview 2:3` : personnage+bulles entiers par plan, pas de bande blanche, pas de bordure noire, fond = flou du crop
- [ ] Rendu complet : pas de dérive vers un coin (zoom centré), pas de `render length off`, page sans focus ni regions rend quand même
- [ ] `GET /api/chapters/{id}/timeline` inclut `focus_regions: []` par défaut sur anciennes analyses (rétrocompat JSON)

## Checks à lancer
```bash
pytest backend/tests -q          # backend (toujours)
npx tsc --noEmit                 # TypeScript (toujours, depuis frontend/)
npm run lint                     # ESLint (toujours, depuis frontend/)
npm run build                    # build Vite (front inchangé : smoke uniquement)
```

## Étapes de test manuelles exactes
1. Lancer le backend : `.\start.ps1` (port 8000) ; ouvrir `http://127.0.0.1:8000`
2. Preview cadrage (sans ffmpeg) :
```powershell
python scripts/preview_framing.py data/tmp/preview 2:3 data/projects/1/pages/p_0004.jpg data/projects/1/pages/p_0020.jpg
```
   Vérifier : plans serrés entiers, pas de blanc vide, fond flou (ouvrir les PNG générés).
3. Rendu complet via UI : onglet Export → Render → `GET /api/renders/{id}/video` → lecture VLC : pas de dérive en coin, durée ≈ timeline.
4. Cas repli : chapitre dont les pages n'ont que `focus` (anciennes analyses) → rendu OK sans relancer l'analyse.
5. Négatif : `POST /api/chapters/{id}/render` avec `{"settings": {"crop_ratio": "5:7"}}` → 422.
