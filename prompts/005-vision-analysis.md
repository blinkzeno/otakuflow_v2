# 005 — Analyse vision (Gemini free, prompts versionnés, synthèse, quota affiché)

## Task goal
Analyser chaque page avec Gemini (JSON schématisé, cache par page, pacing quota), produire la compréhension globale du chapitre, et l'afficher en lecture seule avec le compteur de quota.

## Matching plan step
**Étape 5 — Analyse vision** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, comportements concrets
- `.agents/skills/tech-architecture/SKILL.md` — §2 provider Gemini, §8 gotchas 4-7 (payload, schéma+retry, quotas, modèles périssables)
- `references/security-checklist.md` — section "Toujours" + esprit "Si le plan touche l'IA" (clé server-only, output validé avant sauvegarde, pas de contenu privé loggé — transposé à Python/Pydantic)

## Existing code inspected
- `backend/services/jobs.py` (004) — `enqueue`, `report_progress`, `should_stop`, `ai_gate`, `ai_backoff`, `QuotaPaused`, `append_log`
- `backend/db/queries/pages.py` (002) — à étendre (`update_analysis`, `pending_pages`)
- `backend/db/schema.sql` (002) — `pages.analysis_json/status`, `chapters.chapter_summary`, `ai_costs` (registre de quota)
- `frontend/.../WorkspacePage` + `PageDetail` (003) — ajouter l'onglet Analysis + section analyse dans le détail

## Decisions made
1. **SDK `google-genai`**, modèle `VISION_MODEL` lu depuis l'env (ex. Flash vision — ID exact fixé à l'implémentation dans `.env.example`, jamais codé en dur).
2. **Schéma JSON imposé via `response_json_schema`** : `{characters[], actions[], dialogues[] ({speaker?, text}), events[], location, importance (0-10), summary, visual_description}` — validé par **Pydantic** (`PageAnalysis`), 1 retry avec rappel "return valid JSON only", puis `analysis_status='failed'` + `analysis_error` (tronqué 300 signes), chapitre continue.
3. **Payload** : grand côté redimensionné ≤ 1568 px, JPEG q80 en mémoire (jamais écrit sur disque — l'original normalisé reste la référence).
4. **Cache strict** : `POST analyze` saute les pages `done` ; `pending_pages()` = `pending|failed` uniquement. Relance = ne retraite que l'échec.
5. **Synthèse séparée** (`POST synthesize`, texte seul) : `{title?, main_characters[], plot_summary, key_events[], tone}` → `chapters.chapter_summary`. Étape distincte pour être rejouée sans repayer les 40 pages.
6. **Compteur quota** : chaque appel écrit `ai_costs` (provider, model, kind, units `{images, in_tokens?, out_tokens?}`) ; `GET /api/quota` agrège "aujourd'hui" par provider ; badge UI `X / CAP` (`CAP = VISION_DAILY_CAP`, pause auto quand atteint).
7. **Prompts en anglais**, versionnés dans `backend/prompts/*.txt`, chargés au démarrage (échec de lecture = erreur au boot, pas à l'exécution).

## Assumptions (small, reversible)
- **`importance` 0-10 notée par le modèle mais re-normalisée serveur** (clamp) — l'IA propose, le backend dispose (réversible : pondération affinée en 006).
- **3 pages de test manuel suffisent pour valider un (nouveau) modèle** avant un chapitre entier (réversible : jeu de 5 chapitres en 009).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/providers/__init__.py`, `backend/providers/base.py` | `ProviderError(kind: rate_limit\|invalid\|auth\|network)`, dataclasses Pydantic `PageAnalysis`, `ChapterSummary` |
| `backend/providers/gemini_vision.py` | `analyze_page(image_bytes, prompt)`, `synthesize(texts, prompt)`, `generate_script(...)` (003e méthode : utilisée en 006, implémentée ici car même provider) |
| `backend/prompts/analyze_page.txt`, `synthesize_chapter.txt`, `generate_script.txt` | Prompts EN versionnés (le 3e actif seulement en 006) |
| `backend/services/analysis.py` | `analyze_chapter(chapter_id, progress, should_stop)`, `synthesize_chapter(chapter_id)` |
| `backend/api/routers/analysis.py` | `POST /api/chapters/{id}/analyze`, `POST /api/chapters/{id}/synthesize`, `GET /api/quota` |
| `backend/tests/test_analysis_schema.py` | Fixtures JSON valide/invalide → Pydantic accepte/rejette ; service avec provider mocké écrit `done`/`failed` |
| `frontend/src/features/analysis/AnalysisPanel.tsx` | `props { page }` : personnages, actions, dialogues, événements, lieu, badge importance, résumé |
| `frontend/src/components/QuotaBadge.tsx` | `props { quota }` : `X / CAP appels aujourd'hui` |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/db/queries/pages.py` | `pending_pages(chapter_id)`, `update_analysis(page_id, json|error)`, `get_page_with_analysis` |
| `backend/db/queries/` + `costs.py` (nouveau, déclaré ici) | `log_call(...)`, `daily_usage()` |
| `backend/core/config.py` | `gemini_api_key()` (REQUIS, erreur claire si vide), `vision_model()`, `min_interval()`, `daily_cap()` |
| `backend/api/main.py` | `include_router(analysis)`, erreur boot explicite si prompts illisibles |
| `frontend/.../WorkspacePage` | Onglet Analysis (sélecteur page + AnalysisPanel) + QuotaBadge dans l'en-tête |
| `frontend/src/services/api.ts`, `types` | `analyzeChapter`, `synthesizeChapter`, `getQuota`, types `PageAnalysis`, `Quota` |

## Implementation requirements
- `gemini_vision.py` :
```python
def analyze_page(image_bytes: bytes, prompt: str) -> PageAnalysis:
    # response_json_schema=PageAnalysis.model_json_schema(), 1 retry si ValidationError
    # 429/5xx -> ProviderError("rate_limit") ; 401/403 -> ProviderError("auth") ; le reste -> ProviderError("network")
    # ne JAMAIS logger image_bytes ni la clé ; logger "[vision] page ok/failed reason=..."
```
- `analyze_chapter` : pour chaque page pending → `ai_gate("gemini")` → appel → try `429` : `ai_backoff(n)` max 3 puis `raise QuotaPaused` ; `should_stop` entre pages ; `report_progress` par page ; `log_call` à chaque appel (même échec).
- `synthesize_chapter` : concatène `summary` des pages `done` (tronqué 12000 signes, cf. gotcha "texte trop long") → 1 appel → `chapter_summary`.
- `GET /api/quota` : `{"gemini": {"used": N, "cap": CAP}}` depuis `ai_costs` (jour UTC).
- Front : page `failed` = badge rouge + message (pas de JSON brut) ; dialogues affichés `speaker: text`.

## Security requirements
- `GEMINI_API_KEY` lue uniquement dans `providers/gemini_vision.py` via `core/config.py` — jamais importée côté front, jamais loggée, jamais dans une réponse d'erreur (erreurs provider → messages génériques côté API)
- Outputs IA validés Pydantic AVANT insertion (jamais de JSON brut du modèle en DB)
- Contenu des pages/prompts : loggés par longueur uniquement (`prompt_len=...`), jamais intégraux
- `GET /api/pages/{id}/image` réutilisé pour les vignettes (pas de nouvelle route fichier)

## Acceptance criteria
- [ ] `POST analyze` sur 3 pages (clé valide) → 3 `done`, `analysis_json` valides, `ai_costs` = 3 lignes
- [ ] Page qui fait échouer la validation 2× → `failed` + message, chapitre `done` quand même
- [ ] Relance `analyze` → 0 nouvel appel (tout `done`, prouvé par `ai_costs` inchangé)
- [ ] `GET /api/quota` reflète les appels du jour
- [ ] Onglet Analysis affiche personnages/actions/dialogues/importance sans JSON brut
- [ ] `pytest`, `tsc`, `lint`, `build` passent (tests avec provider mocké, sans clé)

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Ajouter `GEMINI_API_KEY=<clé>` dans `.env`, relancer `.\start.ps1`.
2. Importer un CBZ de 3 pages, onglet Analysis → cliquer "Analyze".
   Résultat attendu : progression 0→100 %, chaque page affiche résumé + dialogues + importance.
3. Vérifier le cache :
```powershell
curl.exe http://127.0.0.1:8000/api/quota
```
   Relancer "Analyze" → `used` inchangé.
4. Synthèse : `POST /api/chapters/1/synthesize` → `chapter_summary` visible (détail projet).
5. Négatif : `.env` sans clé → `POST analyze` → job `failed` avec "GEMINI_API_KEY manquante" (message clair, pas de traceback, pas de clé dans la réponse).
