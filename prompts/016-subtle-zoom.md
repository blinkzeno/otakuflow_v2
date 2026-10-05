# 016 — Zoom statique léger (fin du zoompan animé)

## Task goal
Supprimer le zoom animé qui dégrade l image, garder le fond flou, et
appliquer un petit zoom statique sur la planche.

## Matching plan step
Hors séquence (correction qualité du rendu 008/014). Touche uniquement
`_page_clip` dans `video.py` + 1 test. Rien d autre ne bouge.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan

## Existing code inspected
- `backend/services/video.py` (`_page_clip`) — zoompan `z=min(zoom+0.0015,1.15)`
  : rééchantillonne chaque frame (scintillement + perte), même à `d` fixe
- `backend/services/video.py` (`_framed`) — crop 16:9 + fond flou : conservé tel quel
- `DEFAULT_SETTINGS.kenburns` — conservé comme interrupteur, sens précisé ci-dessous

## Decisions made
1. **Plus d animation** : suppression du filtre zoompan. Image fixe par
   plan (comme en 008), fond flou conservé (014).
2. **`kenburns: true` = zoom statique ×1.05** : `scale=ceil(iw*1.05):ceil(ih*1.05)`
   puis `crop=largeur:hauteur` sur le still 3840×2160, en UNE passe
   LANCZOS via ffmpeg (pas de shimmer, pas de surcoût). `false` = cadre
   exact sans zoom. API et réglages inchangés (même clé, même défaut).
3. **Constante nommée** `SUBTLE_ZOOM = 1.05` en haut de `video.py`
   (réglable 1.00-1.20, validée comme les autres réglages si exposée ;
   non exposée en MVP : constante seule).

## Assumptions (small, reversible)
- **1.05 suffit à « remplir »** : avec les crops 16:9 déjà au format,
  le zoom ne sert qu au punch visuel, pas au remplissage (réversible :
  monter à 1.08 en 1 ligne).

## Files to create / modify

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/services/video.py` | `_page_clip` : branche zoompan remplacée par scale+crop statiques ; constante `SUBTLE_ZOOM` |
| `backend/tests/test_montage.py` | 1 test : la commande ne contient plus `zoompan` (mock `_run`, vérifie `scale` + `crop`) |

## Implementation requirements
- `_page_clip` branche animée remplacée par :
```python
filt = (
    f"scale=ceil(iw*{SUBTLE_ZOOM}):ceil(ih*{SUBTLE_ZOOM}),"
    f"crop={settings['width']}:{settings['height']}"
)
cmd = [_ffmpeg(), "-y", "-loop", "1", "-i", str(still), "-vf", filt,
       "-t", str(seconds), ...libx264 identique...]
```
  Branche `kenburns: false` inchangée (fit exact existant).
- Test : monkeypatch `video_service._run` capturant `cmd`, assert
  `"zoompan" not in " ".join(cmd)` et `"crop=" in ...` pour `kenburns`
  true ; assert pas de `crop=` parasite pour false (filtre scale/pad
  existant conservé).
- Vérifier qu aucun autre appel à zoompan ne subsiste (`grep zoompan`).

## Security requirements
- Aucun (même construction par liste, mêmes réglages validés)

## Acceptance criteria
- [ ] `grep -rn zoompan backend/` → 0 match
- [ ] Test commande : scale+crop présents (true), absents (false)
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live : rendu 2 segments → frame nette (transitions nettes > 50 par ligne sur zone texte à défaut de texte : comparer netteté bords page vs ancien MP4), durée inchangée

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur, chapitre 2 pages + voix (seed ou parcours).
2. `POST render`, télécharger, extraire une frame à t=2.
   Résultat attendu : page nette et légèrement agrandie, fond flou,
   aucun scintillement (comparer 2 frames à 1 s d intervalle :
   quasi identiques, pas de zoom progressif).
