# 010 — Analyse vision par gros lots + routage par modèle

## Task goal
Faire passer un chapitre de 75 à 120 pages dans les quotas gratuits en
combinant lots de 8 pages et routage par tâche : modèle léger à gros
quota pour l analyse, modèle fort pour la synthèse et le script.

## Contexte recherche (quotas gratuits constatés, sept-oct 2026)
Les quotas varient par modèle et par projet (vérifiables dans AI Studio,
Google les remanie souvent). Ordres de grandeur constatés :

| Modèle | Requêtes/jour gratuites | Rôle prévu |
|--------|------------------------|------------|
| `gemini-3.8-flash` | ~20 | synthèse + script (2 appels/chapitre : largement assez) |
| `gemini-3.5-flash-lite` | ~500 | analyse des pages par lots (15 appels pour 120 pages : à l aise) |
| `gemini-3.1-flash-lite` | ~500 | secours si le 3.5-lite coince |

C est pour ça que le quota partait si vite : `gemini-3.8-flash` seul
n offre qu une vingtaine d appels par jour. Le modèle léger en offre
25 fois plus. La doc Google recommande exactement ce découpage
(tâches volumineuses sur Lite, tâches exigeantes sur Flash).

## Matching plan step
Étape hors séquence initiale (optimisation quota, après 009). Touche
uniquement 005 : ni l API, ni le frontend, ni le schéma ne changent.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotchas 4-7 (payload, schéma + retry, quotas, modèles périssables)

## Existing code inspected
- `backend/providers/gemini_vision.py` — `analyze_page` (1 image + 1 retry),
  `_generate` (schéma JSON imposé), mapping d erreurs 429/401/réseau
- `backend/providers/base.py` — `PageAnalysis`, `ProviderError`
- `backend/services/analysis.py` — boucle page par page, `ai_gate` par page,
  retry réseau ×2, `QuotaPaused` après 3×429, `ai_costs` par appel
- `backend/prompts/analyze_page.txt` — prompt unitaire actuel
- `backend/core/config.py` — `min_interval()`, `vision_model()`
- `backend/tests/test_analysis_schema.py` — tests avec provider moqué

## Decisions made
1. **Un chapitre entier en 1 appel = impossible** : 120 analyses
   dépassent le plafond de sortie du modèle. Lots de
   `VISION_PAGES_PER_CALL` (**défaut 8**) : 120 pages → 15 appels,
   75 pages → 10 appels. Taille réglable par variable d env (4 à 10).
   En dessous de 4 on regaspille le quota, au dessus de 10 la réponse
   touche le plafond et le modèle mélange les pages.
2. **Routage par tâche, 2 modèles** (le cœur du plan) :
   - analyse des pages → `VISION_MODEL` (défaut `gemini-3.5-flash-lite`,
     ~500 req/jour) : volume élevé, tâche d extraction guidée par schéma.
   - synthèse + script → `TEXT_MODEL` (défaut `gemini-3.8-flash`,
     ~20 req/jour mais 2 appels par chapitre suffisent) : qualité
     narrative maximale là où elle compte.
   - secours : si le modèle fort est épuisé sur une tâche texte,
     bascule automatique sur le léger (même interface, qualité un peu
     moindre mais chapitre sauvé). Jamais l inverse (ne pas brûler les
     20 appels du fort sur du volume).
3. **Qualité intacte** : chaque image garde sa résolution actuelle
   (grand côté ≤ 1568 px, JPEG q80). Aucune mosaïque, aucun
   sous-échantillonnage : les pixels envoyés sont les mêmes, seul
   l emballage change. Contact sheet écarté (pages réduites = dialogues
   moins lisibles).
3. **Images étiquetées, index explicite** : le prompt numérote les images
   (`PAGE 1`, `PAGE 2`...) et le schéma de sortie exige `batch_index`
   (1-based dans le lot) par analyse. Pas de confiance dans l ordre seul.
   `batch_index` rejoint `PageAnalysis` (champ stocké, ignoré ailleurs).
4. **Échec partiel = page en échec, pas lot en échec** : réponse globale
   invalide → 1 retry du lot ; item invalide après retry → seule sa page
   passe en `failed`, les autres sont sauvegardées. Même politique
   429 (backoff ×3 → `QuotaPaused`) et réseau (×2 → `failed`).
5. **Nouvelle méthode provider, ancienne supprimée** :
   `analyze_pages(images: list[bytes], prompt, model) -> ...`.
   Pas de coexistence : `analyze_page` disparaît, `analyze_pages.txt`
   remplace `analyze_page.txt`. `synthesize` et `generate_script`
   prennent aussi un paramètre `model` (défaut = `TEXT_MODEL`).
6. **Pacing par lot** : un seul `ai_gate` par lot (plus de sommeil
   inutile entre pages d un même appel). `ai_costs` loggue le lot avec
   `{"images": N}` : le compteur de quota reste exact par modèle.

## Assumptions (small, reversible)
- **Lot de 8 par défaut** : le plus grand lot qui reste fiable
  (réponse ≈ 4 000 à 5 000 mots, sous le plafond). Réglable 4 à 10 par
  env sans changer le code. Si les échecs par item dépassent 1 page par
  lot en pratique, redescendre à 6 puis 4 (réversible, 1 variable).
- **Ordre des pages préservé par le tri existant** : le découpage en lots
  suit `pending_pages` (déjà ordonné), aucune renumérotation.

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/prompts/analyze_pages.txt` | Prompt EN : N images étiquetées → tableau d analyses avec `batch_index` |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/providers/base.py` | Ajouter `batch_index: int` à `PageAnalysis` |
| `backend/providers/gemini_vision.py` | `analyze_pages(images, prompt, model)`, `synthesize` et `generate_script` prennent `model` ; supprimer `analyze_page` |
| `backend/services/analysis.py` | Découpage en lots avec `VISION_MODEL`, distribution, échec par item |
| `backend/services/script.py` | `generate` appelle avec `TEXT_MODEL`, secours léger si fort épuisé |
| `backend/prompts/analyze_page.txt` | Supprimer (remplacé) |
| `backend/core/config.py` | `pages_per_call()` (défaut 8, plage 1 à 10) + `VISION_MODEL` (défaut `gemini-3.5-flash-lite`) + `TEXT_MODEL` (défaut `gemini-3.8-flash`) + `TEXT_DAILY_CAP` (défaut 20) |
| `backend/api/routers/analysis.py` | `GET /api/quota` retourne les 2 seaux (`vision` + `text` avec modèle, used, cap) |
| `frontend` (`api.ts`, `QuotaBadge`, types) | Badge 2 seaux (`Vision x/500 · Text y/20`) |
| `backend/tests/test_analysis_schema.py` | Tests lots : ordre, item invalide isolé, découpage 17 pages en 8+8+1, routage des modèles (mock), secours texte |
| `docs/TECH_ARCHITECTURE.md` | Routage 2 modèles + nouveau calcul de quota (§2, §5, §8.6) |
| `.env.example` | `VISION_MODEL`, `TEXT_MODEL`, `TEXT_DAILY_CAP`, `VISION_PAGES_PER_CALL=8` commentés |

## Implementation requirements
- `gemini_vision.py` :
```python
def analyze_pages(images: list[bytes], prompt: str, model: str) -> tuple[list[PageAnalysis], list[int]]:
    # contents = [prompt, Part(image 1), Part(image 2), ...], config model=model
    # schéma = {"analyses": list[PageAnalysis]} via wrapper BatchAnalysis (Pydantic, local au provider)
    # 1 retry global si validation totale impossible
    # retourne (valid, failed) où failed = batch_index invalides après retry
    # valid vide -> ProviderError("invalid") comme aujourd hui
def synthesize(texts: str, prompt: str, model: str) -> ChapterSummary: ...  # même retry, model param
def generate_script(summary_json: str, prompt: str, model: str) -> ScriptDraft: ...  # idem
```
- `analysis.py` : lots de N avec `model=config.vision_model()` ;
  `log_call(..., model, "vision", {"images": len(lot)})`.
- `script.py` (`generate`) : `model=config.text_model()` ; si
  `QuotaPaused` sur le fort → 1 tentative avec `config.vision_model()`
  (log `[script] fallback to light model`), puis échec propre.
  `synthesize_chapter` : pareil (fort puis léger).
- `GET /api/quota` :
```json
{"vision": {"model": "gemini-3.5-flash-lite", "used": 12, "cap": 500},
 "text": {"model": "gemini-3.8-flash", "used": 2, "cap": 20}}
```
  `used` = appels du jour **pour ce modèle** (`ai_costs` filtré par modèle,
  pas par provider) ; ajouter `calls_today_for_model(model)` dans
  `queries/costs.py`.
- Front : `QuotaBadge` affiche `Vision 12/500 · Text 2/20`.
- `analyze_pages.txt` : reprend les règles de l actuel + « You receive N
  numbered page images (PAGE 1..N). Answer one analysis per image, in a
  JSON array, each with its batch_index. Never merge two pages. »
- Erreurs : `batch_index` hors plage ou doublon → item invalide (page en
  `failed`, message `bad batch_index`).
- Logs : `[analysis] batch ok pages=8/8 model=...`, jamais de contenu
  d image ni de prompt intégral.

## Security requirements
- Aucun secret ne touche le bundle client (inchangé, aucun endpoint modifié)
- Payloads images toujours redimensionnés en mémoire avant envoi (inchangé)
- `batch_index` validé serveur (entier, dans la plage du lot) avant usage

## Acceptance criteria
- [ ] 17 pages en attente + lot de 8 → 3 appels provider (prouvé par mock compteur : 8 + 8 + 1), toutes `done`, modèle léger utilisé
- [ ] Item invalide après retry → seule sa page en `failed`, les 7 autres `done`
- [ ] `batch_index` menteur (99) ou doublon → page en `failed`, pas de mélange avec une autre page
- [ ] Relance après succès partiel : seules les pages non `done` repartent
- [ ] Synthèse et script appellent le modèle fort (mock : vérifier le paramètre) ; fort épuisé → secours léger automatique, chapitre sauvé
- [ ] `GET /api/quota` retourne les 2 seaux avec le bon modèle et les bons compteurs
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live (si quota dispo) : **parité léger vs fort** — les 2 pages manga analysées en 1 appel sur `gemini-3.5-flash-lite`, dialogues transcrits mot à mot comme la référence 005 ; sinon le léger est disqualifié et le plan bascule sur lots de 8 en `gemini-3.8-flash` + étalement

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur avec clé (mémoire uniquement) : `VISION_MODEL=gemini-3.5-flash-lite`,
  `TEXT_MODEL=gemini-3.8-flash`, `VISION_PAGES_PER_CALL=8`.
2. Importer le CBZ manga 2 pages, lancer Analyze.
   Résultat attendu : 1 seul appel sur le léger, 2 pages `done`,
   transcriptions mot à mot identiques à la référence 005
   (« The gate is open. Move now! », « Behind you! »).
   Si un dialogue manque ou est inventé → léger disqualifié, noter
   dans le rapport et basculer le défaut sur le fort + étalement.
3. Vérifier les 2 seaux :
```powershell
curl.exe http://127.0.0.1:8000/api/quota
```
   Résultat attendu : `vision.used` +1 avec le modèle léger,
   puis synthèse + script → `text.used` +2 avec le modèle fort.
4. Négatif : `VISION_PAGES_PER_CALL=99` → refus clair au démarrage.
5. Négatif : `VISION_PAGES_PER_CALL=abc` → idem.
