# 022 — Cadrage dessin d'abord (papier retiré, crédits ignorés)

## Task goal
Montrer le dessin dans chaque plan en retirant le papier blanc et en ignorant les pages de crédits/pub, sans changer le montage (durées, audio, concat).

## Matching plan step
Étape 8 — Timeline + render (ordre de construction AGENTS.md §12), itération cadrage après 021.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, requirements concrets, acceptance mesurables
- `.agents/skills/implementation-prompt-writer/references/security-checklist.md` — clé server-only, output IA validé avant sauvegarde, pas de chemin client

## Existing code inspected
- `backend/services/video.py` (421 lignes, lu en entier) — `_crop_box` (l.179-194) étend au ratio demandé ; `_regions_for_page` (l.152-176) garde bulles + texte, `_is_blank` par stddev ; `_auto_tiles` (l.135-149) dernier recours ; `_page_clip` (l.242-273) zoom avant seul ; `_segment_clips` (l.317-343) sans filtre page ; pas de `import math`
- `backend/providers/base.py` (59 lignes, lu en entier) — `FocusRegion` : x/y/w/h float + order, sans `kind` ; `PageAnalysis` : sans `page_kind`, `focus_regions: list[FocusRegion]`
- `backend/providers/gemini_vision.py` (161 lignes, lu en entier) — `analyze_pages` valide via `BatchAnalysis.model_validate_json` : nouveaux champs passent sans autre changement ; rien à modifier dans ce fichier
- `backend/services/analysis.py` (209 lignes, lu en entier) — `_clean_regions` (l.42-57) sans `kind`, sans garde `isinstance(region, dict)` avant accès ; branche `done` (l.148-155) où valider `page_kind`
- `backend/services/timeline.py` (124 lignes, lu en entier) — `page_regions` (l.46-69) sans `kind` ; `build_timeline` (l.72-120) remplit `focus` + `focus_regions`, sans `page_kind`
- `backend/prompts/analyze_pages.txt` (14 lignes, lu en entier, en anglais) — consigne `focus_regions` existante (l.13) à étendre avec `kind` + `page_kind`
- `backend/tests/test_framing.py` (65 lignes, lu en entier) — 6 tests existants ; `test_crop_is_never_a_thin_strip` et `test_full_page_focus_falls_back_to_tiles_without_blank_bands` devront être adaptés au nouveau comportement

## Decisions made
1. `FocusRegion.kind` et `PageAnalysis.page_kind` vivent dans `backend/providers/base.py` (pas dans `gemini_vision.py`) : un seul endroit, validation Pydantic existante inchangée, défauts `kind="art"` / `page_kind="story"` = rétrocompat totale.
2. Constantes exactes de la spec (WHITE_LEVEL=235, MID 40-215, PAPER_WHITE_MIN=0.30, PAPER_MID_MAX=0.15, ART_MIN_SHARE=0.25, WIDE_LIMIT=16/9, SKIP_KINDS) : seuils réglables sans toucher à la logique.
3. `crop_ratio` devient limite portrait (jamais d'extension verticale pour atteindre le ratio, plancher 16:9) : corrige les captures 1:57 et 2:38 à la racine.
4. `_auto_tiles` conservé comme dernier recours uniquement (page sans dessin détecté) : garantit ≥ 1 plan par segment, pas de `render length off`.
5. Zoom alterné avant/arrière par numéro de plan (`number % 2 == 0` → zoom_out) + gain progressif au-delà de 6 s : plans longs vivants, montage inchangé.
6. Filtrage `kind="text"` seulement quand de l'`art` existe ; filtrage `page_kind` avec double passe (skip puis reprise) : jamais d'audio sans image.
7. Aucun changement frontend/API : `page_kind` transite dans le JSON `pages[]` de la timeline (consommé par `video.py` uniquement), pas de route modifiée.

## Assumptions (small, reversible)
- `PAPER_MID_MAX=0.15` et `ART_MIN_SHARE=0.25` calibrés sur scans avec texte noir sur blanc ; ciel blanc uni peu texturé peut être pris pour du papier → réversible par constantes, ou sauvé par `kind` Gemini.
- Fenêtres système sur fond sombre gardées si part importante du plan (font partie de l'histoire) ; exclusion via `kind: "text"` Gemini si besoin.
- Ré-analyse nécessaire pour `kind`/`page_kind` ; le filtrage local (trim + art_regions) marche immédiatement sans ré-analyse.

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `prompts/022-art-first-framing.md` | Ce plan |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/services/video.py` | `import math` ; constantes papier ; nouveau `_crop_box` ; `_row_flags` + `_trim_to_art` + `_art_regions` ; nouveau `_regions_for_page` ; `zoom_out` dans `_page_clip` ; nouveau `_segment_clips` |
| `backend/providers/base.py` | `FocusRegion.kind: str = "art"` ; `PageAnalysis.page_kind: str = "story"` |
| `backend/prompts/analyze_pages.txt` | Consignes `page_kind` + `focus_regions` avec `kind` (en anglais) |
| `backend/services/analysis.py` | `_clean_regions` conserve `kind` (+ garde dict) ; `VALID_PAGE_KINDS` ; validation `page_kind` dans branche `done` |
| `backend/services/timeline.py` | `page_regions` conserve `kind` ; `build_timeline` ajoute `page_kind` (défaut `"story"`) |
| `backend/tests/test_framing.py` | 4 nouveaux tests (spec §5) + adaptation éventuelle de 2 tests existants |

## Implementation requirements

### `backend/services/video.py`
- Ajouter `import math` en haut ; ajouter constantes exactes :
```python
WHITE_LEVEL = 235
MID_LOW, MID_HIGH = 40, 215
PAPER_WHITE_MIN = 0.30
PAPER_MID_MAX = 0.15
ART_MIN_SHARE = 0.25
WIDE_LIMIT = 16 / 9
SKIP_KINDS = {"credits", "ad", "blank"}
```
- Remplacer `_crop_box` par la version limite-portrait de la spec (largeur = max(focus, MIN_CROP_W), hauteur = max(focus_h, crop_w / WIDE_LIMIT), élargir seulement si plus étroit que le ratio).
- Ajouter `_row_flags`, `_trim_to_art`, `_art_regions` au code exact de la spec, placés après `_is_blank`.
- Remplacer `_regions_for_page` par la version de la spec (filtre `kind`, tri `order`, trim papier, repli `_art_regions`, garde `unusable` page haute).
- `_page_clip(still, seconds, settings, out, zoom_out=False)` : branches kenburns `zoom = 1+gain*(1-on/frames)` si zoom_out sinon `1+gain*on/frames`, avec `gain = min(0.10, (KENBURNS_END - 1.0) + 0.004 * max(seconds - 6.0, 0.0))` ; reste de la branche (cmd, `-frames:v`, libx264) inchangé.
- Remplacer `_segment_clips` par la version double-passe de la spec (`collect(True) or collect(False)`, repli `_auto_tiles`, `share = duration / len(items)`, `zoom_out=(number % 2 == 0)`).
- Ne pas toucher : `_blurred_fill` (fond calculé sur le crop — déjà resserré sur le dessin), `_still`, `_mux`, `_concat`, `_reduce`, `render_chapter`, commandes ffmpeg en listes.

### `backend/providers/base.py`
- `FocusRegion` : ajouter `kind: str = "art"`. `PageAnalysis` : ajouter `page_kind: str = "story"`. Rien retirer.

### `backend/prompts/analyze_pages.txt`
- Ajouter en anglais le bloc `page_kind` (story/credits/ad/blank) et les règles `focus_regions` avec `kind` (priorité dessin, `text` seulement si aucun dessin, coords 0-1000, ne jamais couper un visage).

### `backend/services/analysis.py`
- `_clean_regions` : garder `isinstance(region, dict)` check, conserver `kind` (`"text"` si `"text"` sinon `"art"`), code exact de la spec.
- Ajouter `VALID_PAGE_KINDS = {"story", "credits", "ad", "blank"}` ; dans la branche `done`, après `_clean_regions`, forcer `page_kind="story"` si hors ensemble.

### `backend/services/timeline.py`
- `page_regions` : propager `kind` (`"text"` si `"text"` sinon `"art"`). `build_timeline` : ajouter `"page_kind": <analysis page_kind ou "story">` dans chaque dict page. Ne rien changer d'autre.

### `backend/tests/test_framing.py`
- Ajouter les 4 tests exacts de la spec (`test_art_regions_skip_text_bands`, `test_text_only_page_has_no_regions`, `test_text_kind_regions_are_dropped_when_art_exists`, `test_crop_does_not_add_height_to_reach_ratio`) avec `ImageDraw` importé.
- Si `test_crop_is_never_a_thin_strip` ou `test_full_page_focus_falls_back_to_tiles_without_blank_bands` échouent : adapter l'assertion au nouveau comportement (zones de dessin au lieu de tuiles), sans affaiblir le contrôle « aucune zone blanche ».

### Cas d'erreur explicites
- Page image manquante → `ValueError("page ... is gone")` conservé ; segment sans plan impossible par construction (double-passe + tuiles).
- Région invalide → skip silencieux ; page `failed` → statut + log, chapitre continue (inchangé).
- `render length off` conservé tel quel.

## Security requirements
- `GEMINI_API_KEY` reste server-only (`providers/` + `core/config.py`) ; aucun secret dans `VITE_*` ni log.
- Nouveaux champs IA validés avant sauvegarde (Pydantic + `_clean_regions` + `VALID_PAGE_KINDS`).
- Aucun chemin fourni par le client ; `rel_path` relatif à `DATA_DIR` uniquement ; commandes ffmpeg en listes d'arguments.
- Aucun changement frontend/API : rien n'expose chemins absolus, prompts ou logs bruts.

## Acceptance criteria
- [ ] `pytest backend/tests/test_framing.py` passe (6 anciens adaptés + 4 nouveaux)
- [ ] `pytest backend/tests -q` passe sans régression
- [ ] Preview `python scripts/preview_framing.py data/tmp/preview 2:3 <pages>` : page crédits absente (après ré-analyse), boîte « TO EVERYONE HERE... » hors cadre, colonne blanche « YOU HAVE LEVELED UP » hors cadre
- [ ] Aucun plan ne contient plus d'un tiers de papier blanc
- [ ] Chapitre analysé sans `kind`/`page_kind` se rend sans erreur
- [ ] Chaque segment a ≥ 1 plan ; pas de `render length off`
- [ ] `npx tsc --noEmit` passe (depuis `frontend/`)
- [ ] `npm run lint` passe (depuis `frontend/`)

## Checks to run
```bash
pytest backend/tests -q          # backend (toujours)
npx tsc --noEmit                 # TypeScript (toujours, depuis frontend/)
npm run lint                     # ESLint (toujours, depuis frontend/)
```

## Manual test steps
1. Lancer le backend : `.\start.ps1` (port 8000) ; ouvrir `http://127.0.0.1:8000`
2. Tests unitaires :
```powershell
pytest backend/tests/test_framing.py -q
pytest backend/tests -q
```
   Résultat attendu : tout vert.
3. Filtrage local immédiat (sans ré-analyse) — preview sur les pages des trois captures :
```powershell
python scripts/preview_framing.py data/tmp/preview 2:3 <chemin_page_credits> <chemin_page_narration> <chemin_page_levelup>
```
   Vérifier dans `data/tmp/preview/` (PNG + MP4) : pas de colonne blanche, boîte de narration rognée, dessin seul.
4. Ré-analyse pour `kind`/`page_kind` : UI → onglet Analysis → Analyze ; vérifier `Vision 46/500` avance puis `GET /api/chapters/{id}/timeline` contient `page_kind` par page.
5. Rendu complet : onglet Export → Render → `GET /api/renders/{id}/video` → lecture VLC : page « READ AT ASURASCANS.COM » absente, durée ≈ timeline, pas de `render length off`.
6. Rétrocompat : chapitre analysé avant (sans `kind`/`page_kind`) → Render direct sans ré-analyse → MP4 OK.
7. Négatif : segment sans audio → `POST /api/chapters/{id}/render` → 400 avec message `audio is stale` (inchangé).
