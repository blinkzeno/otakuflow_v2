# 009 — Hardening (README, protocole 5 chapitres, garde-fous finaux)

## Task goal
Durcir le MVP : README complet (avec limitation légale), protocole d'évaluation sur 5 chapitres, test de sécurité smoke, et vérification de la rejouabilité indépendante des étapes.

## Matching plan step
**Étape 9 — Hardening** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, critères mesurables
- `docs/PROJECT_BRIEF.md` §9 — critères de succès à transformer en protocole exécutable
- `references/security-checklist.md` — section "Toujours" (dernier balayage : secrets, logs, erreurs safe)

## Existing code inspected
- Toutes les étapes 001-008 : relire `backend/api/routers/*.py` (erreurs safe ?), `providers/*.py` (retry + statuts `failed` ?), `services/jobs.py` (pause quota ?), `.env.example` (complet ?)
- `AGENTS.md` §7/§8 — contrats et env à ne pas casser

## Decisions made
1. **Aucune feature dans 009** : uniquement docs, tests smoke et micro-corrections de robustesse trouvées pendant la relecture (chaque correction > 10 lignes → plan séparé, pas ici).
2. **`README.md`** (français, 80 lignes max) : présentation 3 lignes, prérequis (Python 3.11+, Node 20, clé Gemini gratuite), `start.ps1`, parcours Import→Export en 9 puces, quotas gratuits, upgrade payant (OpenAI/ElevenLabs via interfaces), **encadré légal** : usage personnel non monétisé, scanlations fournies par l'utilisateur, aucune feature de contournement de droits.
3. **`docs/EVAL.md`** : protocole des 5 chapitres (brief §9) — grille par chapitre : zéro invention (traçabilité page), associations valides (%), note /5 "regardable sans réenregistrement", durée traitement. Critère de sortie : 5/5 chapitres, note moyenne ≥ 4/5.
4. **Test smoke sécurité** : upload `.exe→.cbz` (422), `GET /api/pages/999999/image` (404), `GET` avec `..` impossible par construction (pas de param chemin — test d'absence : aucune route n'accepte de chemin), réponse d'erreur `analyze` sans clé → pas de secret dans le JSON.
5. **Rejouabilité** : matrice vérifiée manuellement — relance `analyze` (0 appel), édition 1 segment → seul son audio régénéré, render après ajout d'un segment → nouvelle timeline complète. Documentée dans `EVAL.md` comme checklist.

## Assumptions (small, reversible)
- **README en français** alors que l'UI est en anglais : le dev/lecteur est francophone, l'audience YouTube est anglophone (cohérent avec AGENTS.md §9).
- **Pas de benchmark de vitesse machine** : le critère ≤ 30 min est mesuré sur la machine de dev et noté tel quel dans EVAL.md (réversible : ajusté si autre machine).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `README.md` | Setup, usage, quotas, upgrades, encadré légal (≤ 80 lignes) |
| `docs/EVAL.md` | Protocole 5 chapitres + grille de notation + checklist rejouabilité |
| `backend/tests/test_security_smoke.py` | 422 mauvais fichier, 404 page inconnue, erreur sans-clé sans secret, `.env` ignoré par git |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `.env.example` | Vérification finale : les 13 variables présentes avec commentaires (aucune valeur réelle) |
| Micro-corrections | Uniquement si la relecture révèle : log contenant un prompt/clé (tronquer), message d'erreur exposant un chemin absolu (relativiser), statut `failed` manquant (ajouter). Rien d'autre. |

## Implementation requirements
- `test_security_smoke.py` (concret) :
```python
def test_upload_exe_rejected(client):  # POST /api/projects, fichier binaire nommé x.cbz -> 422
def test_unknown_page_404(client):     # GET /api/pages/999999/image -> 404
def test_no_key_no_secret(client, monkeypatch):  # GEMINI_API_KEY vide -> POST analyze -> failed, et "AIza" absent de toute la réponse
def test_env_ignored():  # lit .gitignore, assert ".env" présent (test de garde anti-fuite)
```
- `README.md` : commandes exactes (`.\start.ps1`, `cd frontend; npm run dev`), tableau des 6 onglets → action, section "Quotas gratuits" (Gemini ~1 chapitre/jour confort, pause/reprise), section "Passer au payant" (où brancher OpenAI/ElevenLabs : `providers/` + `.env`).
- `docs/EVAL.md` : tableau à remplir par chapitre (titre, pages, appels vision, durée totale, inventions trouvées, associations invalides, note /5) + décision Go/No-Go (moyenne ≥ 4/5 ET 0 invention).
- Relecture routers : chaque `except` retourne `{"detail": message_safe}` (pas de `str(e)` brut contenant un chemin absolu ou une clé) — corriger si trouvé.

## Security requirements
- Dernier balayage : `grep -r "AIza\|sk-\|BEGIN.*KEY" backend/ frontend/src/` → 0 résultat (hors tests smoke qui utilisent des faux)
- Aucun log applicatif n'écrit : clé, prompt intégral, chemin absolu (relatifs uniquement)
- `.env` toujours ignoré ; `.env.example` sans valeur réelle
- Encadré légal présent dans le README (hypothèse produit documentée)

## Acceptance criteria
- [ ] `README.md` permet à un tiers de démarrer (prérequis + 2 commandes + parcours) sans poser de question
- [ ] Encadré légal présent (non monétisé, fichiers fournis par l'utilisateur)
- [ ] `docs/EVAL.md` contient la grille + critères de sortie mesurables
- [ ] `pytest backend/tests -q` : tous les tests 001-009 verts, dont les 4 smoke sécurité
- [ ] Relecture : 0 secret/chemin absolu dans les réponses d'erreur et les logs
- [ ] `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Suivre le README à la lettre sur une machine "propre" (nouveau clone ou dossier copié sans `data/` ni `.env`) jusqu'à la grille des pages.
   Résultat attendu : 0 question, 0 erreur non documentée.
2. Exécuter le protocole EVAL sur 1 chapitre réel (30-50 pages) de bout en bout en chronométrant.
   Résultat attendu : MP4 8-12 min, ≤ 30 min de traitement, grille EVAL remplie.
3. Matrice rejouabilité (sur ce même chapitre) :
   - Relancer Analyze → `ai_costs` inchangé (quota) ;
   - Éditer 1 segment → Voice → 1 seul MP3 régénéré ;
   - Render → timeline recalculée, vidéo remplacée.
4. Balayage secrets :
```powershell
Select-String -Path backend,frontend\src -Pattern 'AIza|sk-|BEGIN.*KEY' -Recurse
```
   Résultat attendu : 0 match hors tests smoke.
