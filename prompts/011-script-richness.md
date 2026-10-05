# 011 — Script plus visuel (prompt seul, 0 appel en plus)

## Task goal
Rendre la narration visuellement dense (chaque page citée se voit dans
le texte) en corrigeant le prompt, la densité et la troncature, sans
changer l API, le schéma, l éditeur ni le nombre d appels IA.

## Matching plan step
Hors séquence (amélioration de 006 après retour qualité). Ne touche que
le prompt et 2 lignes de `services/script.py`.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotcha 5 (sortie schématisée + retry, inchangé)

## Existing code inspected
- `backend/prompts/generate_script.txt` — demande une histoire, jamais de
  description visuelle ; 10-16 segments fixes quel que soit le chapitre ;
  aucune densité par page
- `backend/services/script.py` (`generate`) — `json.dumps(blob)[:30000]` :
  pour 120 pages les analyses des dernières pages sont coupées AVANT
  l envoi, le modèle ne les voit jamais ; filtre `page_refs` existant
  (conservé tel quel)
- `backend/providers/base.py` (`ScriptDraft`) — schéma inchangé, aucun
  champ à ajouter

## Decisions made
1. **Ancrage visuel obligatoire par page citée** : chaque index de
   `page_refs` doit apporter au moins un détail concret visible
   (expression, cadrage, action vue, lumière, atmosphère). Un auditeur
   qui n a pas les images doit quand même « voir » la scène. Le reste
   des règles (fidélité, chronologie, zéro invention) est inchangé.
2. **Densité proportionnelle au chapitre** : max 4 pages par segment ;
   nombre de segments ≈ pages/4 (min 10, max 40) ; chaque texte garde
   400 à 900 signes. Un chapitre de 120 pages donne ~30 segments au
   lieu de 16 maigres. Conséquence acceptée : vidéo plus longue.
3. **Plus de troncature aveugle** : plafond payload 30 000 → 120 000
   signes (≈ 120 pages d analyse, dans le contexte 1M). Le blob inclut
   `page_count` pour que le modèle calibre le découpage. Au delà,
   tronquer les pages d `importance` la plus basse en dernier recours
   (log warning avec le nombre de pages écartées).
4. **Zéro changement structurel** : même schéma `ScriptDraft`, même
   endpoint, même éditeur, même gate `reviewed`, même nombre d appels
   (1 par génération). Rollback = restaurer l ancien fichier prompt.
5. **La passe d enrichissement (+1 appel) reste en réserve** : évaluée
   seulement si le nouveau prompt reste maigre sur 1 chapitre test
   (voir EVAL ci-dessous). Pas de code anticipé pour elle.

## Assumptions (small, reversible)
- **Vidéo plus longue acceptée** : la densité demandée allonge la
  narration (~85 signes/page aujourd hui vers ~150+). Réversible :
  resserrer la fourchette 400-900 si trop long.
- **120 000 signes tiennent le contexte** : analyses ~800 signes/page
  × 120 + consignes ≈ 100k, sous la limite 1M avec marge (réversible :
  baisser si refus du provider).

## Files to create / modify

### Créer
Aucun.

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/prompts/generate_script.txt` | Réécriture complète (texte exact ci-dessous) |
| `backend/services/script.py` | `payload = json.dumps(blob)[:120000]` + `"page_count": len(pages)` dans le blob + tri par importance avant troncature + warning si écartées |
| `backend/tests/test_script_ops.py` | 1 test : le payload transmis contient `page_count` et n est pas tronqué à 30k |

## Implementation requirements
- Nouveau `generate_script.txt` exact :
```text
You are a YouTube recap narrator. Below is the analyzed data of one manga chapter: N pages (page_count), a global summary, plus per page analyses (visual descriptions, dialogues, actions, events).

Write an English voiceover script as JSON: a list of segments, each with text and page_refs (the 1 based page indexes that support the text).

Rules:
- Spoken, vivid, present tense English. Hook in the first segment.
- Follow the chapter chronology strictly.
- SHOW what happens, do not summarize it: every page index in page_refs must contribute at least one concrete visible detail (a face, a gesture, a framing, light, atmosphere, onomatopoeia drawn on the page). A listener who cannot see the images must still picture the scene.
- Every claim must come from a cited page. Never invent events, names or dialogue.
- Density: at most 4 pages per segment. Aim for about page_count / 4 segments (minimum 10, maximum 40). Each text is 400 to 900 characters.
- Skip pure filler, keep every turning point and every striking visual.
- page_refs must only contain indexes present in the data, in reading order.
- Answer with JSON only.
```
- `script.py` : constante `PAYLOAD_MAX_CHARS = 120000` en haut de fichier
  (pas de nombre magique inline). Tri : `done_pages` triées par
  `importance` décroissante AVANT `json.dumps` ? Non : l ordre chronologique
  doit rester pour le modèle. Décision : garder l ordre chronologique,
  et si `len(payload) > MAX`, retirer les pages d importance la plus
  basse (en gardant au moins 50 % des pages) puis logguer
  `[script] truncated N low importance pages`. Implémenter exactement ça.
- Test : mocker `generate_script` avec capture du `summary_json` argument,
  assert `json.loads(payload)["page_count"] == 5` et `len(payload) > 30000`
  possible (pas de coupe à 30k). Utiliser le helper `_chapter_with_pages`
  existant (5 pages).

## Security requirements
- Aucun secret, aucun endpoint, aucun changement de schéma
- Sortie toujours validée par `ScriptDraft` avant insertion (inchangé)
- `page_refs` toujours filtrés serveur (inchangé)

## Acceptance criteria
- [ ] Le prompt contient : ancrage visuel par page, max 4 pages/segment, formule pages/4 min 10 max 40, fourchette 400-900
- [ ] `PAYLOAD_MAX_CHARS = 120000`, `page_count` dans le blob, troncature par importance basse avec warning (test unitaire vert)
- [ ] `pytest`, `tsc`, `lint`, `build` passent (aucun changement frontend attendu)
- [ ] Live (si quota dispo) : régénérer sur un chapitre test → chaque page citée apporte ≥ 1 détail visuel vérifiable dans son analyse, moyenne ≥ 150 signes par page citée

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur avec clé, chapitre déjà analysé (ex. manga 2 pages ou plus).
2. `POST /api/chapters/{id}/script` avec `{"confirm_overwrite": true}`.
   Résultat attendu : segments dont le texte décrit du visible
   (expressions, cadrage, atmosphère), pas seulement l intrigue.
3. Compter : signes totaux / pages citées distinctes.
   Résultat attendu : ≥ 150 signes par page citée (contre ~85 avant).
4. Négatif : chapitre de 120 pages simulé (analyses factices) →
   génération demandée avec ~30 segments, pas 16 ; payload non tronqué
   sous 120k (vérifié dans les logs si truncation warning absent).
