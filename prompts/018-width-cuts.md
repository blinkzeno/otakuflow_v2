# 018 — Découpes plein-largeur + zoompan + concat (retour 008 amélioré)

## Task goal
Restaurer les découpes par page et les effets du montage 008 (zoompan,
concat) avec cadrage qui garde toute la largeur du plan et fond flou en
repli, sans zoom ni crop latéral.

## Matching plan step
Hors séquence (retour partiel sur 013/014/016/017). Touche `video.py` +
tests. Timeline, jobs, UI, API inchangés.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan
- `prompts/008-timeline-render.md` — référence exacte (décisions 2, 3, 4, 6)

## Existing code inspected
- `prompts/008` : 1 clip = 1 segment, pages multiples à temps partagé,
  zoompan `z='min(zoom+0.0015,1.15)'` sur entrée 3840×2160, concat
  demuxer sans fondu, `kenburns` (false = fixe), gates, vérif ±1 s
- `backend/services/video.py` actuel : 1 image/segment, fit exact +
  flou, xfade, `_framed` 3840×2160, upscale réel (correctif conservé)

## Decisions made
1. **Découpes restaurées** : chaque page citée redevient un sous-clip
   (`duration / n`, voix continue par dessus, mux audio par segment
   comme en 008). Annule 017 sur ce point uniquement.
2. **Largeur intégrale conservée** : cadrage « plein-largeur » —
   mise à l échelle sur 3840 de large (LANCZOS, upscale autorisé),
   puis crop vertical seul si dépassement (jamais les côtés). Le
   centre vertical suit le `focus` (centre-y de la boîte) si valide,
   sinon le centre. Images plus larges que 16:9 (rare) : fit + fond
   flou existant, jamais de noir.
3. **Zoompan 008 restauré** : `zoompan=z='min(zoom+0.0015,1.15)':d=<frames>:s=WxH:fps=F`
   sur chaque sous-clip, `frames = round(part * fps)`, sortie
   libx264/crf/preset/yuv420p + aac 128k. Clé `kenburns` restaurée
   (défaut true, `false` = image fixe exacte comme en 008).
4. **Concat sec, fin du xfade** : assemblage final par demuxer concat
   `-c copy` (008 décision 4). Clé `xfade` supprimée (inconnue → 422).
   Vérification durée ±1 s SANS ajustement de fondu (concat exact).
5. **Conservé des étapes récentes** : fond flou (repli), upscale réel,
   gates (draft/audio/stale), `settings` validés, 30 ips forcés,
   progression par clip, tmp nettoyé. Timeline et `focus` inchangés
   (le focus ne sert qu au centrage vertical).

## Assumptions (small, reversible)
- **Bandes verticales = le bon découpage manga** : pages hautes →
   tranches 16:9 plein-largeur, panoramique vertical implicite via le
   choix de la tranche par page (pas de pan animé, le zoom suffit).
   Réversible : recentrage sans focus (centre systématique).

## Files to create / modify

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/services/video.py` | `_framed(page_rel, focus_y|None, project_id, workdir)` plein-largeur ; zoompan par sous-clip ; concat final ; `kenburns` restauré, `xfade` supprimé |
| `backend/tests/test_montage.py` | Découpes : N appels `_framed` pour N pages ; zoompan présent (true) / absent (false) ; `xfade` rejeté ; focus hors cadre → centré |
| `frontend` | Rien (aucun contrôle xfade/kenburns en UI) |

## Implementation requirements
- `_framed(page_rel, focus, project_id, workdir)` :
```python
# focus = dict focus timeline ou None ; focus_y = (y + h/2)/1000 si valide sinon 0.5
# scale = 3840 / w (LANCZOS, upscale ok) -> H = h * scale
# si H >= 2160 : fenêtre 2160 centrée sur focus_y*H (bornée 0..H-2160)
# sinon : fit contain + fond flou existant (_blurred_fill)
# sortie PNG 3840x2160 dans tous les cas
```
- Sous-clips : `share = clip.duration / max(len(pages),1)`, zoompan par
  sous-clip muet, concat des sous-clips du segment, `_mux` audio entier
  (inchangé), puis concat global des segments (inchangé).
- `DEFAULT_SETTINGS` : `{..., kenburns: True}` (sans `xfade`,
  sans `smart_crop`) ; `validate_settings` : `kenburns` booléen.
- `_page_clip` : branche `kenburns` true = zoompan 008 exact ;
  false = fit exact existant (conservé).
- Tests : mock `_run`/`_framed` : 3 pages → 3 `_framed` (focus transmis),
  commande avec `zoompan` (true) ; `validate_settings({"xfade": 1})`
  → 422 ; focus `y` absurde → centrage ( psi via crop ? tester
  `_framed` réel sur image blanche 400×600 : moyenne > 60).
- Grep final : `xfade|smart_crop|SUBTLE_ZOOM` → 0 match (code).

## Security requirements
- Aucun (même construction par liste, réglages validés)

## Acceptance criteria
- [ ] Segment 3 pages → 3 sous-clips, durées égales, voix continue
- [ ] Frame : pleine largeur conservée (bords gauche/droit = contenu flou ou page, jamais noir franc sur toute la hauteur)
- [ ] `zoompan` présent (true) / absent (false) dans les commandes
- [ ] `xfade`/`smart_crop` rejetés en 422
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live : MP4 1080p, durée = timeline ±1 s, changements de plan visibles par page

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur, chapitre 2 segments multi-pages + voix.
2. `POST render`, télécharger, extraire frames à t=1 / t=4 / t=7 :
   plans différents (pages différentes), plein-largeur, nets.
3. Durée via mutagen ≈ total timeline ±1 s.
