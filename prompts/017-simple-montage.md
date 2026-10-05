# 017 — Montage simple (1 image par segment, sans découpe ni zoom)

## Task goal
Revenir à un montage simple : une image fixe par segment (première
page citée), ajustée sans zoom, fond flou conservé, sortie toujours
horizontale. Supprimer la découpe par page et tout résidu de zoom.

## Matching plan step
Hors séquence (retour après 013/014/016). Touche `video.py` + tests.
Timeline, jobs, UI, API inchangés dans leur comportement.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan

## Existing code inspected
- `backend/services/video.py` — boucle par page avec `share = duration/n`
  (à supprimer), `_page_clip` avec zoom ×1.05 (à passer en cadre exact),
  `_sixteen_nine` + `_valid_box` (devenus inutiles), `_framed` (fit +
  flou : conservé, sans crop), xfade + concat (conservés, non critiqués)
- Réglages `smart_crop`, `kenburns` : plus aucun effet après ce plan

## Decisions made
1. **1 segment = 1 image** : première page citée du clip (repli page 1
   du chapitre existant conservé). Fin des sous-clips, du partage du
   temps et du concat intermédiaire par segment.
2. **Zéro zoom, zéro crop** : `_framed` fait fit exact + fond flou,
   `_page_clip` cadre exact sans mise à l échelle. Supprimer
   `_sixteen_nine`, `_valid_box`, `SUBTLE_ZOOM` (grep final à 0).
3. **Flou gardé, horizontal garanti** : fond flou CapCut conservé ;
   sortie verrouillée aux couples paysage (validation existante
   1920×1080 / 1280×720, inchangée). Aucun format vertical possible.
4. **Réglages sans effet = réglages supprimés** : `smart_crop` et
   `kenburns` retirés de `DEFAULT_SETTINGS` (inconnus → 422 comme les
   autres). Pas de clé fantôme.
5. **Transitions et timeline intactes** : xfade, durées réelles,
   gates, pastilles d aperçu conservés. Les rectangles de focus restent
   affichés comme indication d analyse (renommés « Focus », pas de crop).

## Assumptions (small, reversible)
- **Première page = la bonne image** : l ordre de `page_refs` suit la
  lecture, la première porte l accroche du segment (réversible : choix
  par `importance` si un jour prouvé meilleur).

## Files to create / modify

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/services/video.py` | 1 clip/segment (première page) ; `_framed(page_rel, project_id, workdir)` sans box ; fit exact sans zoom ; supprimer `_sixteen_nine`, `_valid_box`, `SUBTLE_ZOOM`, clés `smart_crop`/`kenburns` |
| `backend/tests/test_montage.py` | Retirer tests crop/box ; ajouter : 1 seul appel `_framed` par segment multi-pages (mock), pas de `scale=` avec zoom, clés inconnues rejetées |
| `frontend` (`ExportPanel`) | Infobulle « Smart crop » → « Focus » (texte seul) |

## Implementation requirements
- Boucle segment : `page = clip["pages"][0]` (+ repli existant si vide),
  `still = _framed(page_rel, ...)`, `silent` unique, `_mux` direct.
  Supprimer `share`, `page_videos`, concat intermédiaire.
- `_framed(page_rel, project_id, workdir)` : fit contain LANCZOS
  (upscale autorisé, correctif 013 conservé) + fond flou (conservé).
- `validate_settings` : `DEFAULT_SETTINGS` sans `smart_crop`/`kenburns`.
- Grep final : `zoompan|SUBTLE_ZOOM|_sixteen_nine|_valid_box|smart_crop|kenburns` → 0 match hors docs/historique prompts.
- Tooltip Export : `Smart crop on page X` → `Focus on page X`, `Full frame` inchangé.

## Security requirements
- Aucun (même construction par liste, réglages validés)

## Acceptance criteria
- [ ] Grep ci-dessus à 0 match (code)
- [ ] Segment de 3 pages → 1 seul clip (mock `_framed` : 1 appel, première page)
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live : MP4 1920×1080, image fixe nette, fond flou, durée = timeline − fondus

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur, chapitre 2 segments + voix.
2. `POST render`, télécharger, extraire 2 frames à 1 s d intervalle
   dans le même segment : identiques à ~0 % près (fixe).
3. Vérifier 1920×1080, pas de bandes noires, sujet non amputé.
