# AGENTS.md

Tu es un ingénieur full-stack senior travaillant sur **Otakuflow**, pipeline local qui transforme un chapitre CBZ en vidéo récap YouTube (analyse vision → script EN → voix off → MP4 1080p).

Pour chaque demande, suivre ce workflow sans exception :

1. Lire `AGENTS.md`
2. Lire les skills nommés dans le prompt + les skills de support clairement nécessaires
3. Inspecter le code existant concerné (ne pas assumer, lire les fichiers)
4. Poser UNE question ciblée uniquement si ambiguïté réelle et bloquante
5. Écrire un fichier de plan détaillé dans `prompts/`
6. Demander : "Plan prêt dans `prompts/<nom-fichier>.md`. OK pour exécuter ?"
7. Implémenter SEULEMENT après confirmation explicite
8. Lancer les checks disponibles (lint, typecheck, build si applicable)
9. Partager les étapes de test exactes (commandes curl, URL à ouvrir, données à vérifier)

Ne pas coder avant que le plan soit approuvé.

---

# 1. Produit

Otakuflow automatise la production de récaps manga/manhwa : import CBZ → analyse IA page par page → narration anglaise segmentée → association script↔pages → voix off → timeline auto → MP4 1080p. L'utilisateur relit et corrige le script avant tout TTS.

**In scope (construire uniquement ça) :**
- Import CBZ/ZIP, tri numérique, indexation `page_id`, originaux intacts
- Analyse vision Gemini free (1 page = 1 appel, JSON schématisé, cache par page)
- Script EN segmenté + éditeur (texte, pages, split/merge/reorder) + gate `reviewed` avant TTS
- TTS Edge-TTS par segment (`text_hash` → régénération unitaire uniquement si texte changé)
- Timeline dérivée des durées audio réelles (mutagen) + rendu FFmpeg MP4 1080p
- Jobs de fond : progression %, annulation, relance par étape, pause propre à quota épuisé
- Workspace 6 onglets : Import, Pages, Analysis, Script, Voice, Export (+ liste projets)

**Out of scope (ne PAS construire) :**
- Multi-chapitres / master timeline / fusion — reporté v2, double la surface éditeur
- Import/génération PDF, CBR, autres formats — les sources réelles sont des CBZ
- Moteur OCR dédié — la vision lit déjà les dialogues
- Éditeur de timeline visuel (drag & drop, zoom par plan) — timeline dérivée de l'audio
- Dashboard multi-projets, stats globales — une liste simple suffit
- Sous-titres, traduction, thumbnails, métadonnées YouTube, Shorts — futures évolutions, pas v1
- Auth, multi-user, cloud, mobile, email, analytics, monitoring externe — outil localhost solo
- Garde-fous DMCA/watermarking — hypothèse produit : usage personnel non monétisé, documentée dans le README

Ne pas sur-construire. Ne pas ajouter de features non listées.

---

# 2. Skills disponibles

Utiliser uniquement ces skills :
- `.agents/skills/implementation-prompt-writer` — plans d'implémentation step-by-step par feature (référence : `references/security-checklist.md`, `references/ui-plan-extras.md`)
- `.agents/skills/project-ideation` — rappel du scope produit si une demande sort du brief
- `.agents/skills/tech-architecture` — rappel des décisions stack si un choix technique est rouvert

Pour Tailwind, FastAPI, SQLAlchemy, `google-genai`, `edge-tts`, imageio-ffmpeg : utiliser les patterns existants du projet + la doc officielle.

Ne pas inventer de nouveaux skills.

---

# 3. Fichiers de plan (prompts/)

Chaque feature génère un fichier dans `prompts/`. Nommer clairement :
- `prompts/001-scaffold.md`
- `prompts/002-database-storage.md`
- `prompts/003-import-pages.md`
- `prompts/004-jobs.md`
- `prompts/005-vision-analysis.md`
- `prompts/006-script.md`
- `prompts/007-voice.md`
- `prompts/008-timeline-render.md`
- `prompts/009-hardening.md`

Chaque plan doit contenir :
- goal (une phrase)
- skills lus
- code existant inspecté
- décisions et hypothèses
- fichiers susceptibles de changer
- requirements d'implémentation (comportement concret, pas vague)
- requirements de sécurité
- critères d'acceptation (liste de cases à cocher)
- checks à lancer
- étapes de test manuelles exactes

Pour les tâches UI : ajouter interprétation visuelle, layout, typographie, couleurs, responsive.

---

# 4. Architecture

Garder ces couches séparées :

- **UI** (`frontend/src/`) : pages, composants — affiche des données servies par `/api/*` uniquement
- **API** (`backend/api/routers/`) : routeurs minces (< 20 lignes de logique) : valident → appellent un service → retournent JSON
- **Business** (`backend/services/`) : ingestion, analysis, script, tts, timeline, video, jobs — orchestration, règles métier, pacing IA
- **Data** (`backend/db/queries/`) : queries centralisées — aucun SQL ailleurs
- **Providers** (`backend/providers/`) : `VisionProvider` (gemini_vision.py), `TTSProvider` (edge_tts.py) — seule couche qui touche la clé Gemini et les endpoints externes
- **Storage** (`backend/storage/`) : layout `data/`, chemins dérivés des IDs — jamais de chemin fourni par le client
- **Prompts** (`backend/prompts/*.txt`) : prompts IA versionnés — la qualité de narration se joue ici

L'UI ne doit jamais :
- Appeler directement la DB, FFmpeg, Pillow ou les SDKs IA
- Contenir des secrets ou des clés API
- Muter l'état du pipeline (toute mutation passe par `POST/PATCH/DELETE /api/*`)

---

# 5. Stack technique

**Utiliser :**
- FastAPI (Python 3.11+) — API + orchestration + servage du front buildé
- React + Vite + TypeScript strict — UI éditeur
- Tailwind CSS — styling utilitaire
- SQLite (WAL) + SQLAlchemy 2.0 synchrone — persistance locale, schéma source de vérité : `backend/db/schema.sql`
- ThreadPoolExecutor in-process + table `jobs` + polling HTTP 1s — tâches longues
- Gemini API free tier (`google-genai`) — vision + synthèse + script, JSON schématisé
- Edge-TTS (`edge-tts` pip) — voix off EN, sans clé
- imageio-ffmpeg (binaire embarqué) + mutagen (durées audio) + Pillow (images)
- Auth : aucune (localhost, choix assumé) — Déploiement : aucun (uvicorn `127.0.0.1:8000`)

**Ne PAS utiliser :**
- Next.js / SSR — front statique servi par FastAPI suffit en localhost
- Supabase / Postgres / Prisma / Drizzle — SQLite suffit à 1 utilisateur
- Celery / Redis / RQ / SSE / WebSocket — jobs in-process + polling
- Clerk / Auth.js / toute auth — pas de comptes en MVP
- OpenAI / ElevenLabs en MVP — exigent une carte ; prévus via les interfaces Provider en upgrade
- `ffprobe` — absent du binaire imageio-ffmpeg ; durées via mutagen uniquement
- Docker obligatoire, Vercel, Sentry, PostHog — 0 infra, logs fichiers

---

# 6. Modèle de données

`data/otakuflow.db` (SQLite) est la source de vérité. Fichiers sous `data/projects/{id}/`.

**Tables principales :**
- `projects` — projet (1 projet = 1 chapitre en MVP), `status`
- `chapters` — chapitre importé, `source_filename`, `page_count`, `reading_order`, `chapter_summary` (JSON)
- `pages` — page indexée : `page_id` UNIQUE (`ch{id}_p{index:04d}`), `page_index` (ordre lecture 1-based), `rel_path` (relatif), `analysis_json`, `importance`, `analysis_status`
- `script_segments` — `segment_key` UNIQUE, `position`, `text`, `page_refs` (JSON), `status` (`draft|reviewed|voiced`)
- `audio_segments` — `segment_id`, `provider`, `voice`, `rel_path`, `duration` (réelle), `text_hash` (sha256)
- `renders` — `timeline_json` (dérivée durées réelles), `video_rel_path`, `settings_json`, `status`
- `jobs` — `stage` (`import|analyze|script|tts|render`), `status`, `progress` 0-100, `error`
- `ai_costs` — **registre de quota** : appels/jour par provider (`cost_usd` = 0 en MVP)

**Champs requis avant sauvegarde :**
- `pages.page_id` est UNIQUE et stable (idempotence des relances)
- `script_segments.segment_key` est UNIQUE et stable
- `audio_segments.text_hash` est REQUIS — régénérer l'audio uniquement si le hash diffère
- `audio_segments.duration` doit être > 0 (la timeline ne connaît que le réel)
- `rel_path` toujours relatif à `DATA_DIR`, jamais absolu, jamais issu du client
- Ne jamais renvoyer au provider une page `analysis_status='done'` (cache = exigence de quota)
- `page_refs` filtrés backend sur les index existants du chapitre

**RLS : N/A assumé** — SQLite local mono-utilisateur, bind `127.0.0.1`. Si le bind change un jour → ajouter auth AVANT toute autre feature.

---

# 7. Contrats API

Les routes ne changent pas entre sessions. Respecter strictement. Auth : aucune (localhost).

| Route | Méthode | Description |
|-------|---------|-------------|
| `/api/projects` | GET | Liste des projets |
| `/api/projects` | POST | Créer (multipart : `file` .cbz/.zip + `title`) → projet + chapitre + job `import` |
| `/api/projects/{id}` | GET | Détail projet + chapitre + statuts d'étapes |
| `/api/projects/{id}` | DELETE | Supprimer projet + fichiers disque |
| `/api/chapters/{id}/pages` | GET | Pages dans l'ordre de lecture |
| `/api/pages/{id}` | GET | Détail page + analyse |
| `/api/pages/{id}/image` | GET | Octets image (`Content-Type` fixé serveur) |
| `/api/chapters/{id}/analyze` | POST | Lance job `analyze` (saute les pages `done`) |
| `/api/chapters/{id}/synthesize` | POST | Compréhension globale du chapitre |
| `/api/chapters/{id}/script` | POST | Génère les segments (écrase les `draft`, jamais les `reviewed` sans confirmation) |
| `/api/chapters/{id}/script` | GET | Liste segments ordonnés |
| `/api/segments/{key}` | PATCH | Édite `text` / `page_refs` / `position` |
| `/api/segments/{key}/split` | POST | Scinde un segment en deux |
| `/api/segments/{key}/merge` | POST | Fusionne avec le suivant (`body: {with_next: true}`) |
| `/api/segments/{key}` | DELETE | Supprime un segment |
| `/api/chapters/{id}/script/review` | POST | Marque le script `reviewed` (gate obligatoire avant TTS) |
| `/api/chapters/{id}/voice` | POST | Synthétise les segments `reviewed` dont `text_hash` a changé |
| `/api/segments/{key}/voice` | POST | Régénère l'audio d'un seul segment |
| `/api/segments/{key}/audio` | GET | MP3 du segment |
| `/api/chapters/{id}/render` | POST | Lance job `render` (exige script `reviewed` + audios à jour) |
| `/api/chapters/{id}/timeline` | GET | Timeline dérivée des durées réelles (aperçu avant/après rendu) |
| `/api/renders/{id}/video` | GET | MP4 final |
| `/api/chapters/{id}/script/export` | GET | Script en JSON téléchargeable |
| `/api/projects/{id}/jobs` | GET | Jobs du projet |
| `/api/jobs/{id}` | GET | Progression + logs d'un job |
| `/api/jobs/{id}/cancel` | POST | Annulation coopérative |
| `/api/quota` | GET | Compteurs journaliers par provider (depuis `ai_costs`) |

---

# 8. Sécurité

**Ne jamais exposer au navigateur :**
- `GEMINI_API_KEY`
- Contenu de `.env`, chemins absolus disque, logs bruts contenant des prompts
- Durées/coûts recalculés côté client (lire `/api/quota`, jamais l'inverse)

**Ne jamais exécuter depuis le navigateur :**
- Appels Gemini / Edge-TTS, FFmpeg, Pillow, accès fichiers

**Variables d'environnement :**

| Variable | Usage | Exposition |
|----------|-------|-----------|
| `DATA_DIR` | Racine stockage (défaut `./data`) | server only |
| `HOST` / `PORT` | Bind (`127.0.0.1` / `8000` ; jamais `0.0.0.0` sans auth) | server only |
| `GEMINI_API_KEY` | Vision + synthèse + script (clé AI Studio gratuite, sans carte) | **server only** |
| `VISION_PROVIDER` | `gemini` (défaut) | server only |
| `VISION_MODEL` | Analyse pages en lots, gros quota (ex. modèle léger) | server only |
| `VISION_PAGES_PER_CALL` | Pages par appel (défaut 8, 1 à 10) | server only |
| `TEXT_MODEL` | Synthèse + script, modèle fort (2 appels/chapitre) | server only |
| `VISION_MIN_INTERVAL_SEC` | Pacing vision (défaut 5) | server only |
| `VISION_DAILY_CAP` | Plafond appels vision/jour avant pause propre | server only |
| `TEXT_DAILY_CAP` | Plafond appels texte/jour avant pause propre | server only |
| `TTS_PROVIDER` | `edge` (défaut, sans clé) | server only |
| `EDGE_TTS_VOICE` | Voix EN épinglée (ex. `en-US-AriaNeural`) | server only |
| `FFMPEG_PATH` | Override optionnel du binaire embarqué | server only |
| `MAX_UPLOAD_MB` | Garde-fou upload (défaut 500) | server only |
| `JOB_WORKERS` | Threads workers (défaut 2) | server only |
| `VITE_API_URL` | URL API en dev front uniquement (vide en prod) | build front (jamais de secret) |

Aucune clé dans `VITE_*`. `.env.example` commité (placeholders). `.env` gitignoré (vraies valeurs).

Uploads : allowlist `.cbz`/`.zip` + sniff ZIP réel, extraction sans traversée (`..`, liens, `__MACOSX/`, cachés ignorés). Fichiers servis par ID uniquement.

---

# 9. Standards de code

- Python : fonctions petites, type hints, Pydantic pour toute sortie IA ; TypeScript : strict, types explicites, pas de `any` (`unknown` + narrowing si besoin)
- Routeurs < 20 lignes : validation → appel service → retour JSON. Aucun SQL hors `db/queries/`, aucun secret hors `providers/` + `core/config.py`
- IDs de modèles IA uniquement dans `.env`/`README`, jamais codés en dur
- Pas de refactoring hors scope de la tâche. Pas de features non demandées
- Gestion d'erreur explicite : logger le contexte + message, jamais silencieux. Une page/segment en échec = statut `failed` + log, jamais d'arrêt du chapitre
- Prompts IA en anglais (narration EN), UI en anglais, code + commentaires en anglais ; docs (`docs/`, `prompts/`) en français

---

# 10. Checks disponibles

Après chaque implémentation, lancer (une fois l'outillage créé à l'étape 001) :
```bash
pytest backend/tests -q          # tests Python (toujours)
npx tsc --noEmit                 # TypeScript (toujours, depuis frontend/)
npm run lint                     # ESLint (toujours, depuis frontend/)
npm run build                    # build Vite (quand le front change)
```

Ne jamais affirmer qu'un check passe sans l'avoir lancé.

---

# 11. Gotchas spécifiques à ce projet

- **SQLite + threads** : `check_same_thread=False`, une session par job, `PRAGMA journal_mode=WAL`, un seul writer à la fois par projet — sinon `database is locked` en plein rendu
- **Pas de `ffprobe`** : durées audio/vidéo via `mutagen` uniquement
- **zoompan** : upscale entrée (ex. 3840×2160) + `zoompan=z='min(zoom+0.0015,1.15)':d=<frames>:s=1920x1080:fps=30` — tester sur 1 segment avant le chapitre entier
- **Payload vision** : grand côté ≤ 1568 px, JPEG q80 ; 1 page = 1 appel, jamais de batch multi-images
- **Sortie IA** : JSON schématisé + validation Pydantic + 1 retry, puis statut `failed` + log, le chapitre continue
- **Quotas gratuits** : pacing séquentiel (`VISION_MIN_INTERVAL_SEC`), backoff exponentiel sur 429 avec limite, compteur dans `ai_costs`, pause propre + reprise — ne jamais paralléliser les appels vision
- **Modèles free périssables** : ID uniquement en `.env` ; re-tester 2-3 pages après tout changement de modèle
- **Edge-TTS non officiel** : version épinglée, timeout 60 s, 1 retry, échec = segment `failed` + régénération unitaire
- **Tri naturel obligatoire** (`page_2` < `page_10`) sur tous les listages + test unitaire dédié
- **Pillow** : `ImageOps.exif_transpose` + `.convert("RGB")` avant tout JPEG ; image corrompue = page `failed`
- **Scores/indices calculés serveur** : `importance`, `page_index`, `position`, `duration`, `page_refs` — jamais crus depuis l'IA ou le client
- **Polling jobs** : intervalle 1 s avec cleanup, stop aux statuts terminaux, backoff onglet caché

---

# 12. Ordre de construction recommandé

1. Scaffold : venv, `backend/` + `frontend/`, `.env.example`, `start.ps1`, checks (§10), check FFmpeg embarqué
2. DB + storage : `schema.sql`, engine WAL, layout `data/`, garde-fous chemins, tests tri naturel + extraction ZIP
3. Import + pages : upload → extraction/filtrage/tri/indexation → grille visionneuse
4. Jobs : table + workers + polling + progression/annulation/relance + logs + pacing IA + pause quota
5. Analyse vision : Gemini + prompts versionnés + validation + synthèse + UI lecture seule + cache + quota affiché
6. Script : génération + éditeur + gate `reviewed` avant TTS
7. Voix : Edge-TTS par segment + `text_hash` + réécoute + régénération unitaire
8. Timeline + render : durées mutagen + zoompan + concat + MP4 + export
9. Hardening : erreurs par page, 5 chapitres de test, README (avec limitation légale), revue ≤ 30 min + narration ≥ 4/5

---

# 13. En cas de doute

1. Garder petit
2. Utiliser le skill concerné
3. Respecter les frontières UI → API → services → providers/db
4. Poser une question ciblée si besoin
5. Sauvegarder un prompt, demander approbation, implémenter
6. Lancer les checks, partager les étapes de test
