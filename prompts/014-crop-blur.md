# 014 — Retrait sous-titres, focus dessin, fond flou 16:9

## Task goal
Supprimer l option sous-titres, recadrer sur le dessin (pas les
bulles), remplir le 16:9 avec fond flou façon CapCut, sans nouvelle
dépendance.

## Matching plan step
Hors séquence (retour sur 013). Suppression nette + recadrage revu.
Rien d autre ne change (timeline, jobs, UI hors Export).

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes

## Existing code inspected
- `backend/services/subtitles.py` — builder SRT (à supprimer, usage unique endpoint + burn)
- `backend/services/video.py` — `_subs_filter`, `_find_font`, plomberie `subs`, settings `burn_subtitles` ; `_framed` (crop libre + fond noir)
- `backend/api/routers/render.py` — `GET .../subtitles`
- `backend/services/tts.py` — sidecar `words.json` (usage unique sous-titres)
- `backend/providers/edge_tts.py` — `synthesize_with_timings` (usage unique mots)
- `frontend` (`ExportPanel` : case à cocher + lien SRT)
- `backend/prompts/analyze_pages.txt` — règle focus actuelle (sans consigne anti-bulles)
- `backend/tests/test_montage.py` — tests SRT/mots à retirer avec le code

## Decisions made
1. **Suppression complète, pas de code mort** : endpoint SRT, `subtitles.py`,
   incrustation (`_subs_filter`, `_find_font`, `FONT_CANDIDATES`, paramètre
   `subs`), clé `burn_subtitles`, case + lien SRT, capture des mots
   (`synthesize_with_timings` → `synthesize` simple comme avant 013,
   sidecar `words.json`, tests associés). La timeline garde `focus`
   (utilisé par le recadrage). Vérifier par grep final : 0 occurrence
   de `subtitle`, `words.json`, `libass` hors docs/historique.
2. **Focus = dessin, pas bulles** : règle prompt — « Frame the artwork:
   faces, action, scenery. Avoid speech bubbles unless the bubble
   itself carries the key story beat; prefer areas with no text or few
   bubbles. » Validation serveur impossible (pas de coordonnées de
   bulles) : consigne modèle uniquement, contrôle visuel via l aperçu.
3. **Crop 16:9 centré sur le focus** : la boîte est étendue à l aspect
   16:9 autour de son centre (bornée au cadre), puis crop + upscale.
   Résultat : quasi plein cadre 16:9, zoomé sur le dessin, comme demandé.
4. **Fond flou CapCut en Pillow** : au lieu du noir, fond = même image
   en mode cover 3840×2160 + `GaussianBlur(40)` + assombrie ×0.6, puis
   l image nette ajustée par dessus, centrée. 100 % Pillow embarqué,
   aucun filtre ffmpeg en plus, aucun coût.
5. **Repli inchangé dans l esprit** : focus absent/invalide/trop petit →
   page entière (avec fond flou aussi, jamais de noir). Log warning
   existant conservé.

## Assumptions (small, reversible)
- **Flou 40 + assombri 0.6** : valeurs CapCut usuelles, ajustables en
  constantes nommées (`BLUR_RADIUS`, `BLUR_DARKEN`) en haut de `video.py`
  (réversible : 1 ligne).
- **Bulles parfois cadrées quand même** : le modèle peut garder une bulle
  clé (consigne explicite) ; l utilisateur voit les rectangles dans
  l aperçu et peut désactiver le recadrage (`smart_crop: false` via API,
  comportement page entière + flou).

## Files to create / modify

### Supprimer
| Fichier | Pourquoi |
|---------|----------|
| `backend/services/subtitles.py` | Usage unique sous-titres |
| (dans `video.py`) `_subs_filter`, `_find_font`, `FONT_CANDIDATES`, param `subs`, branches burn | Plus d incrustation |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/api/routers/render.py` | Supprimer `GET .../subtitles` (+ import devenu inutile) |
| `backend/services/video.py` | `validate_settings` : retirer `burn_subtitles` (inconnu → 422 comme les autres) ; `_framed` : box 16:9 + fond flou ; `_join_faded`/concat : sans `subs` |
| `backend/services/tts.py` | Retour à `synthesize_fn` bytes (supprimer words), pas de sidecar |
| `backend/providers/edge_tts.py` | Supprimer `synthesize_with_timings`, `synthesize` redevient directe |
| `backend/prompts/analyze_pages.txt` | Règle focus dessin anti-bulles (texte exact ci-dessous) |
| `frontend` (`ExportPanel`, `api.ts`) | Retirer case + lien SRT (`subtitlesUrl` supprimé) ; aperçu rectangles conservé |
| `backend/tests/` | Retirer tests SRT/mots/sidecar ; ajouter : box 16:9, fond non noir, prompt anti-bulles présent |
| `docs/TECH_ARCHITECTURE.md` | §2 : ligne sous-titres supprimée (option retirée sur retour) |

## Implementation requirements
- Règle focus exacte (remplace la phrase actuelle sur focus) :
```text
- For each page also return focus: the {x, y, w, h} box (0-1000) of the single most important ARTWORK to show (main face, key action, scenery). Avoid speech bubbles unless the bubble itself carries the key story beat; prefer areas with no text or few bubbles. Suggest suggest_zoom 1.0 to 1.5. If nothing stands out, return the full frame {x:0, y:0, w:1000, h:1000} and 1.0.
```
- `_framed` :
```python
# 1. box valide (règle existante) -> centre (cx, cy)
# 2. boîte 16:9 : partir de max(w, h*16/9 ...) : prendre h_box = max(box.h, box.w*9/16), w_box = h_box*16/9, centrée sur (cx, cy), bornée au cadre image
# 3. crop, puis fit (contain, LANCZOS, upscale autorisé) vers 3840x2160
# 4. fond : image originale en cover 3840x2160 (resize + crop centré), GaussianBlur(40), point(x*0.6), coller le net centré
# 5. si pas de box valide : page entière en fit + même fond flou (jamais de noir)
```
- Vérifier qu aucun test restant ne référence `synthesize_words_fn`,
  `words.json`, `build_chapter_srt`, `burn_subtitles`, `subtitlesUrl`
  (grep de contrôle avant les checks).
- `validate_settings` : `burn_subtitles` devient clé inconnue → 422
  (cohérent avec les autres clés).

## Security requirements
- Endpoint supprimé = surface réduite, rien à sécuriser en plus
- Aucun secret, aucun chemin client (inchangé)

## Acceptance criteria
- [ ] Grep `subtitle|words.json|libass|burn_subtitles|subtitlesUrl` → 0 match dans `backend/` + `frontend/src`
- [ ] Crop d une boîte 500×600 → région 16:9 (ex. 1066×600) centrée, bornée
- [ ] `_framed` sans box : coins du canvas non noirs (flou > 10 de moyenne)
- [ ] Le prompt contient la consigne anti-bulles (test : la chaîne « Avoid speech bubbles » présente)
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live : rendu 2 segments → MP4 sans barres noires (coins flous, moyenne > 10), aperçu rectangles OK

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur, chapitre 2 pages + voix (seed ou parcours normal).
2. `POST render` (défauts), télécharger le MP4, extraire une frame :
   coins = fond flou (pas noir), sujet centré et zoomé.
3. Onglet Export : rectangles verts sur les zones de dessin (pas sur
   les bulles après nouvelle analyse).
4. Négatif : `GET /api/chapters/1/subtitles` → 404 (route supprimée).
5. Négatif : `POST render {"settings": {"burn_subtitles": true}}` → 422
   (clé inconnue).
