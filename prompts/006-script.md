# 006 — Script (génération segmentée, éditeur, gate reviewed)

## Task goal
Générer la narration anglaise segmentée depuis l'analyse, l'éditer (texte, pages, split/merge/reorder), et verrouiller la relecture (`reviewed`) avant tout TTS.

## Matching plan step
**Étape 6 — Script** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, critères mesurables
- `.agents/skills/implementation-prompt-writer/references/ui-plan-extras.md` — éditeur : composants + props, états, responsive
- `references/security-checklist.md` — section "Toujours" (validation `page_refs` côté serveur, jamais de confiance au client)

## Existing code inspected
- `backend/providers/gemini_vision.py` (005) — `generate_script(summary_json, prompt)` à appeler (déjà implémentée, inactive)
- `backend/prompts/generate_script.txt` (005) — prompt EN à utiliser tel quel
- `backend/db/schema.sql` (002) — `script_segments` (`segment_key` UNIQUE, `position`, `page_refs`, `status`)
- `frontend/.../WorkspacePage` (003-005) — ajouter l'onglet Script

## Decisions made
1. **Entrée = `chapter_summary` + résumés des pages `done`** (pas les images) : la génération coûte 1 appel, pas 40. Si < 50 % des pages sont `done` → 422 explicite ("analyse incomplète").
2. **Sortie modèle** : `[{text, page_refs: [index...]}]` ; le backend assigne `position` (ordre du tableau), `segment_key = f"ch{id}_s{pos:03d}"`, `duration_estimate = len(text)/900*60` (900 signes/min EN, estimation affichée, jamais utilisée pour la timeline).
3. **`page_refs` filtrés serveur** : on garde uniquement les index existants du chapitre ; segment sans ref valide → `failed` ? Non : conservé avec `[]` + warning log (l'utilisateur corrige, cf. US-04). Jamais de 500 pour une ref invalide du modèle.
4. **Régénération** : `POST script` remplace les segments `draft` uniquement ; les `reviewed|voiced` sont préservés sauf `body: {"confirm_overwrite": true}`.
5. **Gate** : `POST script/review` passe tous les `draft` → `reviewed` (un seul appel, pas de revue partielle en MVP) ; le TTS (007) refuse tout chapitre contenant encore des `draft` (422).
6. **Ops segment** : `split` coupe au niveau phrase la plus proche du milieu (texte1/texte2, mêmes pages, réindexe `position` après) ; `merge` concatène avec le suivant (`" "` + texte, union des pages, réindexe) ; `PATCH` édite `text` et/ou `page_refs` et/ou `position` (reorder = PATCH position + renormalisation 1..N) ; `DELETE` + réindexe. Toute mutation texte/pages repasse le segment en `draft`.
7. **Front** : liste verticale de cartes segment (n° + textarea + chips pages modifiables + durée estimée + boutons Split/Merge/Delete + drag ? Non — reorder par boutons ↑/↓, pas de drag & drop en MVP), bouton "Mark reviewed" avec confirmation.

## Assumptions (small, reversible)
- **Reorder par boutons ↑/↓** suffit en MVP (réversible : drag & drop en v2 sans changer l'API, `PATCH position` existe déjà).
- **Pas de revue partielle** : tout ou rien (réversible : statut par segment déjà en schéma).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/services/script.py` | `generate(chapter_id)`, `patch_segment`, `split_segment`, `merge_next`, `delete_segment`, `mark_reviewed`, `_reindex` |
| `backend/api/routers/script.py` | `POST/GET /api/chapters/{id}/script`, `PATCH/DELETE /api/segments/{key}`, `POST .../split`, `POST .../merge`, `POST .../script/review`, `GET .../script/export` |
| `backend/tests/test_script_ops.py` | Split/merge/reorder/delete + réindex, filtre `page_refs`, préservation `reviewed` sans confirm |
| `frontend/src/features/script/SegmentCard.tsx` | `props { seg, pageCount, onPatch, onSplit, onMerge, onDelete, onMove }` |
| `frontend/src/features/script/ScriptEditor.tsx` | Liste + bouton review + export download |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/db/queries/` + `segments.py` (nouveau) | CRUD segments, `list_ordered`, `reindex_positions`, `has_draft` |
| `backend/api/main.py` | `include_router(script)` |
| `frontend/.../WorkspacePage` | Onglet Script |
| `frontend/src/services/api.ts`, `types` | Endpoints segments + `ScriptSegment` |

## Implementation requirements
- `generate()` :
```python
# 1. pages done < 50 % -> ValueError("analyse incomplète") -> API 422
# 2. ai_gate + provider.generate_script(...) + log_call(kind="script")
# 3. filtre page_refs sur set(index existants) ; warning si segment vidé
# 4. supprime les draft existants, insère avec positions 1..N (une transaction)
# 5. retourne {"segments": N}
```
- `split_segment(key)` : phrases via `re.split(r"(?<=[.!?])\s+")`, coupe au plus près du milieu (texte1 ≥ 1 phrase, texte2 ≥ 1 phrase sinon 400) ; nouvelles clés `s{pos:03d}a/b` ? Non — réindexation globale après insert (clés régénérables, unicité maintenue par DELETE+INSERT en transaction).
- `mark_reviewed` : `UPDATE ... SET status='reviewed' WHERE status='draft'` + retourne le compte.
- `GET script/export` : JSON `{"chapter":..., "segments":[{position,text,pages}]}` en téléchargement (`Content-Disposition: attachment`).
- Front : `PATCH` debouncé (500 ms) sur le textarea ; chips pages = input numérique + ajout/suppression ; merge désactivé sur le dernier segment.

## Security requirements
- Aucun secret ne touche le bundle client
- `page_refs` fournis par le front revalidés (entiers, index existants) — jamais crus tels quels
- `segment_key` de l'URL : format validé (`ch\d+_s\d+`), 404 si inconnu (pas de fuite d'existence inter-chapitres : vérifier l'appartenance au chapitre via jointure)
- Export = JSON du chapitre demandé uniquement

## Acceptance criteria
- [ ] `POST script` (analyse complète) → N segments ordonnés, `page_refs` ⊆ index existants
- [ ] Relance sans confirm → `reviewed` intacts, `draft` remplacés
- [ ] Split → 2 segments, textes non vides, positions 1..N continues ; Merge inverse
- [ ] `PATCH text` → segment repasse `draft` ; `review` → tout `reviewed`
- [ ] Onglet Script : édition + split/merge/↑↓ fonctionnels, review avec confirmation
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Chapitre analysé (005) → onglet Script → "Generate".
   Résultat attendu : segments affichés avec pages citées et durées estimées.
2. Éditer le texte du segment 1 (ajouter "XXX").
3. Split le segment 2 au milieu, puis Merge du segment 2 avec le 3.
   Résultat attendu : positions toujours 1..N, aucun trou.
4. `PATCH` avec page inexistante :
```powershell
curl.exe -X PATCH http://127.0.0.1:8000/api/segments/ch1_s001 -H "Content-Type: application/json" -d '{"page_refs":[1,999]}'
```
   Résultat attendu : `page_refs` sauvegardé = `[1]` (999 filtré), pas d'erreur.
5. "Mark reviewed" (confirmer) → badge `reviewed` ; "Generate" à nouveau → segments `reviewed` inchangés.
