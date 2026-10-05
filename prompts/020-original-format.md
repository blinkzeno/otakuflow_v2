# 020 — Découpage focus + ratio configurable + fond flou

## Task goal
Découper sur le focus avec un ratio rectangulaire configurable (pas
16:9 forcé), petit zoom, fond flou pour combler les espaces.

## Matching plan step
Hors séquence (correction du cadrage 018). Touche `_framed` +
`validate_settings` dans `video.py` + tests. Rien d'autre ne bouge.

## Decisions made
1. **Ratio configurable** : nouveau setting `crop_ratio` (défaut
   `"4:3"`, options `"4:3"`, `"3:2"`, `"1:1"`, `"16:9"`). Le crop est
   centré sur le focus, borné à la page. Pas de forçage 16:9.
2. **Découpage sur le focus** : le centre du crop suit `_focus_y(focus)`
   (et `_focus_x` si implémenté). Si pas de focus → centre de la page.
3. **Petit zoom ×1.05** : appliqué APRÈS le crop, en une passe
   (scale + crop centré). Subtil, pas de forçage.
4. **Fond flou partout** : image originale en cover + blur + darken,
   derrière le crop zoomé. Plus de zones noires.
5. **Sortie toujours 1920×1080** (YouTube) : le crop 4:3 est placé
   sur le fond flou 16:9, ou étiré si `crop_ratio` = 16:9.

## Implementation requirements
- `validate_settings` : `crop_ratio` dans `DEFAULT_SETTINGS` (défaut
  `"4:3"`), validé contre la liste des options.
- `_framed(page_rel, focus, project_id, workdir)` :
```python
# 1. Charger l'image (exif_transpose, RGB)
# 2. Calculer le crop box selon crop_ratio, centré sur focus (ou centre)
# 3. Crop, puis zoom ×1.05 (scale + crop centré)
# 4. Fit contain dans 3840x2160 (le crop 4:3 est plus carré que 16:9)
# 5. Fond flou : image originale en cover 3840x2160 + GaussianBlur(40) + darken 0.6
# 6. Coller le crop zoomé centré sur le fond flou
# 7. Sauvegarder PNG 3840x2160
```
- Constantes `LIGHT_ZOOM = 1.05`, `CROP_RATIOS = {"4:3", "3:2", "1:1", "16:9"}`.
- Tests : image verticale 400×600 + focus centré → sortie 3840×2160,
  coins flous (moyenne > 10), crop 4:3 présent (pas de page entière),
  `crop_ratio` invalide → 422.

## Acceptance criteria
- [ ] Crop 4:3 centré sur le focus (pas de page entière)
- [ ] Zoom léger visible (~5%)
- [ ] Coins flous (fond), pas de noir
- [ ] `crop_ratio` configurable (4:3, 3:2, 1:1, 16:9)
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur, chapitre avec pages + voix.
2. `POST render {"settings": {"crop_ratio": "4:3"}}`, télécharger,
   extraire une frame. Résultat attendu : zone rectangulaire 4:3 centrée
   sur le focus, fond flou autour, pas de page entière.
3. Essayer `"3:2"` et `"1:1"` → crops différents.
