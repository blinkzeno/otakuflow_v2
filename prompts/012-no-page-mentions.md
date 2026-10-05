# 012 — Bannir les mentions de pages dans la narration

## Task goal
Garantir qu aucun segment ne mentionne pages, numéros ou cases à voix
haute (« on page 5 »), par interdiction prompt + détection serveur avec
réparation automatique ciblée, sans changer l API ni le schéma.

## Matching plan step
Hors séquence (correction qualité de 006/011 après retour). Touche le
prompt, `services/script.py`, les tests. Aucun changement d endpoint,
de schéma, d éditeur ou de TTS (la voix lit le texte corrigé tel quel).

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotcha 5 (sortie schématisée + retry, même philosophie)

## Existing code inspected
- `backend/prompts/generate_script.txt` — aucune règle contre les
  mentions de pages ; le modèle cite donc ses sources (« on page 5 »)
- `backend/services/script.py` (`generate`) — filtre les `page_refs`
  mais ne lit jamais le texte ; aucun contrôle du contenu narré
- `backend/services/tts.py` — lit `segment.text` tel quel : corriger la
  génération corrige la voix automatiquement, rien à changer ici
- `backend/providers/base.py` (`ScriptDraft`) — schéma inchangé

## Decisions made
1. **Interdiction prompt d abord** : nouvelle règle dans
   `generate_script.txt` — « Never mention pages, page numbers, panels,
   or the analysis itself. The listener must never hear where a fact
   comes from. » Prévient ~95 % des cas, 0 appel en plus.
2. **Détection serveur systématique** : après validation Pydantic,
   chaque texte est scanné par regex (`\bpages?\s+\d+`, `\bpage\s+\d+`,
   `\bpanels?\b`, `on page`, `in chapter \d`...). Insensible à la casse.
   Si rien ne matche, le flux actuel continue à l identique.
3. **Réparation ciblée, pas régénération globale** : si des segments
   fautifs existent, UN seul appel (`TEXT_MODEL`, même secours léger)
   demande leur réécriture : « Rewrite these segments with the same
   meaning and same page_refs, but remove every mention of pages,
   numbers or panels. Keep names, events and visual details. » Seuls
   les segments fautifs sont remplacés (match par position). Coût max :
   +1 appel, seulement quand le prompt a failli.
4. **Échec propre si la réparation échoue** : segmens encore fautifs
   après réparation → `ValueError` listant les positions (« page
   mention survives in segments 3, 7 ») → 422. Jamais de narration
   polluée sauvegardée en silence. L utilisateur peut aussi régénérer
   ou corriger à la main dans l éditeur (cas existants : régénérer avec
   `confirm_overwrite`, aucun script de migration).
5. **Pas de stripping regex aveugle** : supprimer « on page 5 » au
   milieu d une phrase casse la grammaire une fois sur deux. Seul le
   modèle réécrit, le serveur ne fait que détecter.

## Assumptions (small, reversible)
- **Le prompt suffit dans la plupart des cas** : l appel de réparation
  reste exceptionnel (budget TEXT_MODEL préservé). Réversible : si les
  violations dépassent ~1 génération sur 3, durcir le prompt d abord.
- **Anglais uniquement pour la détection** : motifs EN (`page`, `panel`).
  La narration est EN par contrat produit, rien d autre à couvrir.

## Files to create / modify

### Créer
Aucun.

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/prompts/generate_script.txt` | Ajouter la règle d interdiction (2 lignes, texte exact ci-dessous) |
| `backend/services/script.py` | `PAGE_MENTION_RE` + `_strip_check()` + réparation ciblée dans `generate` (détail ci-dessous) |
| `backend/tests/test_script_ops.py` | 3 tests : détection, réparation appelée une fois, échec si persistant |

## Implementation requirements
- Règle prompt exacte à ajouter avant « Answer with JSON only. » :
```text
- Never mention pages, page numbers, panels, or the analysis itself. The listener must never hear where a fact comes from: no "on page 5", no "as seen in panel 3", no "the analysis shows".
```
- `script.py` :
```python
PAGE_MENTION_RE = re.compile(
    r"\bpages?\s+\d+|\bon\s+pages?\b|\bpanels?\b|\bchapter\s+\d+",
    re.IGNORECASE,
)

def _repair_mentions(draft_texts: list[str]) -> list[str]:
    # 1 appel TEXT_MODEL (+ secours léger comme generate) :
    # "Rewrite each of these narration segments, same meaning, same length,
    #  but remove every mention of pages, numbers or panels. Keep all names,
    #  events and visual details. Answer JSON: {"texts": [...]} (same order)."
    # Retourne la liste réécrite (validée : même longueur, sinon ValueError).
```
  Dans `generate`, après validation Pydantic et avant filtrage des refs :
  détecter les index fautifs ; si aucun → continuer ; sinon 1 appel
  `_repair_mentions` sur ces textes, remplacer, re-scanner ; si encore
  fautif → `ValueError("page mention survives in segments [...]")`.
  Compter l appel de réparation dans `ai_costs` (`kind: "script_repair"`).
- La réparation réutilise le circuit modèles de `generate` (fort puis
  léger). Factoriser un helper `_call_with_fallback(fn)` si cela évite
  la duplication, sans changer le comportement existant.
- Tests :
  - draft moqué avec « on page 5 » dans 1 segment sur 2 → `generate`
    appelle la réparation 1 fois, le segment est remplacé, l autre intact
  - réparation moquée qui persiste → `ValueError` avec les positions
  - aucun match → 0 appel de réparation (compteur mock à zéro)

## Security requirements
- Aucun secret, aucun endpoint, aucun changement de schéma
- Textes envoyés à la réparation = narration déjà générée (même niveau
  de sensibilité que la génération, rien de privé)
- Compteur `ai_costs` exact (réparation logguée avec son modèle réel)

## Acceptance criteria
- [ ] Le prompt contient l interdiction exacte (motifs page/panel/analyse)
- [ ] `PAGE_MENTION_RE` détecte « on page 5 », « pages 3 to 5 », « in panel 2 » (test unitaire dédié)
- [ ] 1 segment fautif sur 2 → 1 seul appel de réparation, segment remplacé, positions et `page_refs` conservés
- [ ] Violation persistante → 422 avec les positions, rien de sauvegardé
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live (si quota dispo) : régénérer le chapitre manga → 0 mention de page dans tous les segments (vérifié par scan)

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur avec clé, chapitre déjà analysé.
2. `POST /api/chapters/{id}/script` avec `{"confirm_overwrite": true}`.
3. Scanner le résultat :
```powershell
curl.exe http://127.0.0.1:8000/api/chapters/1/script | Select-String -Pattern "page \d+|panel" -CaseSensitive:$false
```
   Résultat attendu : aucune ligne (hors `page_refs` JSON qui reste
   légitime en métadonnée, jamais dans `text`).
4. Forcer le cas : éditer temporairement le prompt ? Non, ne pas
   toucher au prompt en test. Vérifier via les logs que la réparation
   ne s est déclenchée que si besoin (`[script] repaired N segments`).
