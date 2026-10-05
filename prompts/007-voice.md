# 007 — Voix (Edge-TTS par segment, text_hash, réécoute, régénération unitaire)

## Task goal
Synthétiser chaque segment `reviewed` en MP3 via Edge-TTS (sans clé), ne régénérer que si le texte a changé (`text_hash`), avec réécoute et régénération unitaire.

## Matching plan step
**Étape 7 — Voix** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, cas d'erreur explicites
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotcha 8/10 (Edge-TTS non officiel, chunking) ; §2 (0 $, sans clé)
- `references/security-checklist.md` — section "Toujours" (aucun secret — ici trivialement vrai : pas de clé TTS ; le texte envoyé à Microsoft est du contenu éditorial, pas privé)

## Existing code inspected
- `backend/providers/base.py` (005) — pattern `ProviderError` à réutiliser pour `TTSProvider`
- `backend/db/schema.sql` (002) — `audio_segments` (`text_hash` REQUIS, `duration` > 0)
- `backend/services/jobs.py` (004) — `enqueue`, progression par segment, `should_stop`
- `backend/services/script.py` (006) — `has_draft()` pour le gate (TTS refuse si draft restants)
- `frontend/.../WorkspacePage` — ajouter l'onglet Voice

## Decisions made
1. **Lib `edge-tts` (`Communicate(text, voice).save(path)`)**, voix `EDGE_TTS_VOICE` (défaut `en-US-AriaNeural`), timeout 60 s, 1 retry, puis segment `failed` + log — le chapitre continue sans lui (rendu 008 sautera les segments sans audio ? Non : 008 exigera tous les audios ; le `failed` se régénère unitairement ici).
2. **Gate** : `POST chapters/{id}/voice` → 422 si `has_draft` ("script non relué — lancez /script/review"). `voiced` existants conservés sauf texte changé.
3. **`text_hash = sha256(text.strip())`** comparé au `audio_segments.text_hash` du dernier audio du segment : identique → skip (0 appel réseau) ; différent → régénère (UPDATE ligne : nouveau fichier + hash + durée). Historique non conservé (1 ligne par segment, `UPDATE`).
4. **Durée via `mutagen.MP3(path).info.length`** ; `<= 0` ou illisible → `failed` ("durée invalide"), fichier supprimé.
5. **Découpage** : segments > 4000 signes découpés au niveau phrase, synthétisés séparément, concaténés via ffmpeg demuxer (`-f concat -safe 0 -c copy`) — cas rare (segments ≈ 600-1200 signes), code présent mais simple.
6. **Fichiers** : `audio/s_{pos:03d}.mp3` (recréé à chaque régénération, écrasé). `provider='edge'`, `voice=<nom voix>`.
7. **Front** : carte par segment (texte tronqué, `<audio controls src=.../audio>`, durée réelle, bouton Régénérer) ; synthèse globale par lot avec progression du job.

## Assumptions (small, reversible)
- **1 ligne audio par segment (UPDATE)** plutôt qu'historique versionné : le MP3 précédent est jetable (réversible : table d'historique si besoin v2).
- **Vitesse/débit Edge-TTS par défaut** (pas de `rate` custom) : la voix narrative par défaut convient (réversible : champ `settings` en 008 si le rendu sonne trop vite/lent).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/providers/edge_tts.py` | `synthesize(text, voice) -> bytes` (timeout 60, 1 retry, `TTSError`) |
| `backend/services/tts.py` | `ensure_voices(chapter_id, ...)`, `regenerate_one(segment_key)`, `_synthesize_fn`/`_duration_fn` injectables (tests) |
| `backend/api/routers/voice.py` | `POST /api/chapters/{id}/voice` (job), `POST /api/segments/{key}/voice`, `GET /api/segments/{key}/audio` |
| `backend/tests/test_tts_hash.py` | Fakes injectés : texte inchangé → 0 appel ; texte changé → 1 appel + hash maj ; durée ≤ 0 → `failed` |
| `frontend/src/features/voice/VoicePanel.tsx` | Liste segments + players + boutons régénérer + progression |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/db/queries/` + `audio.py` (nouveau) | `get_by_segment`, `upsert_audio`, `chapter_audio_status` |
| `backend/api/main.py` | `include_router(voice)` |
| `backend/core/config.py` | `tts_voice()` (défaut `en-US-AriaNeural`) |
| `frontend/.../WorkspacePage` | Onglet Voice |
| `frontend/src/services/api.ts`, `types` | `synthesizeVoices`, `regenerateVoice`, `audioUrl(key)`, `AudioStatus` |

## Implementation requirements
- `edge_tts.py` :
```python
async def synthesize(text: str, voice: str) -> bytes:
    # edge_tts.Communicate(text, voice), timeout=60 ; 1 retry sur exception réseau
    # retourne les octets MP3 (collecte des chunks audio) ; lève TTSError("edge_tts ...") sinon
    # texte vide/whitespace -> ValueError AVANT tout appel réseau
```
- `ensure_voices` : segments `reviewed|voiced` uniquement ; gate `has_draft` → 422 ; par segment : hash compare → skip ; sinon synthétise → écrit `audio/s_NNN.mp3` → mutagen → upsert ; `report_progress` par segment ; `should_stop` entre segments ; segment → `voiced` si audio OK.
- `GET .../audio` : jointure segment→audio, `FileResponse(media_type="audio/mpeg")`, 404 si pas d'audio ("pas encore synthétisé").
- `POST segments/{key}/voice` : synchrone (1 segment ≈ 5-15 s, acceptable hors job) + retourne `{duration}`.
- Front : `<audio controls preload="none">` (pas de préchargement de 15 MP3) ; durée affichée depuis l'API, pas estimée.

## Security requirements
- Aucune clé (Edge-TTS sans auth) — ne PAS ajouter de champ clé "au cas où"
- Le texte envoyé à Microsoft = narration éditoriale de l'utilisateur (pas de données privées ; le signaler dans le README en 009)
- Fichiers audio servis par clé de segment uniquement, `Content-Type: audio/mpeg` fixé serveur
- Gate `reviewed` appliqué serveur (pas seulement caché côté UI)

## Acceptance criteria
- [ ] `POST voice` (script reviewed) → 1 MP3 par segment, `duration > 0` en DB, segments `voiced`
- [ ] Relance sans changement → 0 appel réseau (prouvé : test + log "skip unchanged")
- [ ] Édition d'un texte → relance → seul ce segment régénéré
- [ ] `POST voice` avec des `draft` restants → HTTP 422 explicite
- [ ] Onglet Voice : lecture de chaque MP3 + régénération unitaire fonctionnelle
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Script `reviewed` (006) → onglet Voice → "Generate voice".
   Résultat attendu : progression par segment, players fonctionnels, durées réelles affichées (ex. `12.4 s`).
2. Vérifier un MP3 :
```powershell
curl.exe http://127.0.0.1:8000/api/segments/ch1_s001/audio -o seg1.mp3
```
   L'écouter → narration EN conforme au texte du segment.
3. Régénération unitaire : modifier le texte du segment 2 (onglet Script), retourner en Voice → seul le segment 2 affiche un nouvel horodatage/progression ; les autres sont skippés (log job : `skip unchanged`).
4. Négatif : remettre un segment en `draft` (éditer son texte) puis "Generate voice" global → 422 "script non relu".
