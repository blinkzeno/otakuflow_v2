# Tech Architecture — Otakuflow

> Source d'entrée : `docs/PROJECT_BRIEF.md`.
> Type de projet : **outil local mono-utilisateur** (pattern "outil interne", pas SaaS).
> Contraintes dures : 100 % localhost Windows, 1 seul utilisateur, 0 € d'infra, **aucune carte bancaire** (tous les providers IA par défaut fonctionnent en quota gratuit sans carte), solo dev, quotas IA journaliers à respecter et affichés.

## 1. Stack principale

| Couche | Outil choisi | Justification | Alternatives écartées |
|--------|-------------|--------------|----------------------|
| API backend | **FastAPI (Python 3.11+)** | Couvre exactement le besoin : ingestion ZIP, Pillow, subprocess FFmpeg, SDKs IA Python. Validation Pydantic native pour les sorties IA structurées. | Hono/Fastify (Node) — écartés : l'écosystème image/vidéo/IA du MVP est Python ; ajouter Node doublerait le runtime pour rien. |
| UI | **React + Vite + TypeScript** (build statique servi par FastAPI) | Un seul processus, un seul port en prod. React suffit pour : grille d'images, éditeur de segments, lecteurs audio/vidéo, barres de progression. | **Next.js écarté** : SSR inutile en localhost, serveur Node superflu, build plus lent. **Streamlit/Gradio écartés** : modèle d'état inadapté à un workflow éditeur multi-étapes (script ↔ pages ↔ audio). |
| Langage | Python (backend) + TypeScript strict (frontend) | Python = traitement fichiers/IA/vidéo. TS strict = UI éditeur sans `any`. | — |
| Auth | **Aucune** (choix assumé, pas un oubli) | 1 utilisateur, bind `127.0.0.1`, pas de comptes, pas de partage (brief §3, §6). | Clerk / Auth.js / Supabase Auth écartés : contrainte dure — aucune auth requise. Réévaluer si le projet sort du localhost. |
| Base de données | **SQLite (fichier `otakuflow.db`, mode WAL)** | Zéro serveur, backup = copier un fichier, largement suffisant pour 1 user. JSON stocké en TEXT. | Supabase/Neon/Postgres écartés : serveur managé inutile en local, coût et complexité sans bénéfice. Turso écarté : sync cloud inutile. |
| ORM / Query | **SQLAlchemy 2.0 (synchrone)** | Standard, suffisant, requêtes centralisées dans `backend/db/queries/`. Schéma source de vérité : `backend/db/schema.sql` + table `schema_version`. | Prisma/Drizzle écartés : pas de Node côté données. Alembic écarté pour le MVP : migrations versionnées via `schema.sql` + `schema_version` (suffisant à 1 dev, réévaluer en v2). |
| Styling | **Tailwind CSS** | Workspace dense (grilles, panneaux, timeline) : utilitaires rapides, pas de design system custom en MVP. | CSS Modules écarté : plus lent à écrire pour un solo dev sur une UI utilitaire. |
| Jobs longs | **ThreadPoolExecutor in-process + table `jobs` (polling HTTP 1s)** | 1 utilisateur = pas besoin de Celery/Redis/RQ. Annulation coopérative, reprise par étape, progression en %. | Celery + Redis écartés : infra supplémentaire pour zéro bénéfice à 1 user. SSE/WebSocket écartés : polling simple, robuste, suffisant. |
| Déploiement | **Aucun (localhost)** : `uvicorn 127.0.0.1:8000`, front buildé servi en statique | Contrainte dure du brief. Lancement : 1 commande (+ script `.bat`/`.ps1`). | Vercel/Railway/Render/Fly écartés : pas de cloud. Docker optionnel v2, pas requis en MVP (Windows-first). |

## 2. Intégrations tierces

| Besoin | Service choisi | Pourquoi | Coût estimé MVP | Alternative |
|--------|--------------|---------|----------------|------------|
| Vision + synthèse + script (LLM) | **Gemini API free tier (clé AI Studio, sans carte)**, routée par tâche derrière interface `VisionProvider` : extraction des pages en lots sur le modèle léger (`VISION_MODEL`, quota ~500 req/jour), synthèse + script sur le modèle fort (`TEXT_MODEL`, ~20 req/jour, 2 appels/chapitre) avec secours léger | Les quotas gratuits se comptent en requêtes/jour **par modèle** : le fort (~20) ne tient pas le volume des pages, le léger (~500) si. Sortie JSON schématisée dans les deux cas. Billing Google exigé uniquement pour passer au payant. | **0 $** (chiffres constatés sept-oct 2026, à vérifier dans AI Studio : Google remanie souvent) | **OpenRouter `:free`** (sans carte aussi, endpoint OpenAI-compatible → même interface : fallback documenté, mais 50 req/jour sans achat = ~1 chapitre/jour max, catalogue tournant). **Groq free** (sans carte, 30 RPM/1000 req/jour : excellent pour les étapes *texte* synthèse+script, mais vision encore en preview → option `TEXT_PROVIDER=groq` en v2, pas en MVP). Ollama local écarté : qualité vision insuffisante pour bulles + scènes. |
| TTS voix off | **Edge-TTS** (`edge-tts` pip, voix neurales EN, **sans clé, sans carte**) derrière interface `TTSProvider` (1 segment = 1 MP3) | Seule voix EN publiable à 0 $ sans compte. Durées lues depuis l'audio réel via mutagen. Sous-titres retirés sur retour utilisateur (013 puis 014) : ni SRT ni incrustation. | **0 $** | **OpenAI TTS / ElevenLabs** : prévus par l'interface, pas implémentés en MVP (exigent une carte). |
| Binaire vidéo | **FFmpeg via package `imageio-ffmpeg`** (binaire statique embarqué) | Évite le cauchemar `PATH` Windows : `ffmpeg_path = imageio_ffmpeg.get_ffmpeg_exe()`. Appels en subprocess avec graphes de filtres explicites. | 0 $ | FFmpeg système (winget) : supporté en fallback via `FFMPEG_PATH`, mais pas le défaut. |
| Durée audio | **`mutagen`** (pur Python, lit les MP3) | `imageio-ffmpeg` ne fournit **pas** `ffprobe` : ne jamais en dépendre. Durée = vérité terrain pour la timeline. | 0 $ | ffprobe écarté (absent du binaire embarqué). |
| Images | **Pillow** | Extraction métadonnées, redimensionnement, pad 16:9, vignettes web. | 0 $ | — |
| Email / paiement / analytics / monitoring / search / scraping | **Aucun** | Hors scope : pas de users, pas de billing, pas de web, pas d'emails. Logs = fichiers + table `jobs`. | 0 $ | Sentry/PostHog écartés : 1 utilisateur local, les logs fichiers suffisent en MVP. |

**Interfaces d'abstraction obligatoires dès le MVP** (pas de rework en v2) :
`VisionProvider.analyze_page(image) -> PageAnalysis` / `.synthesize(pages) -> ChapterSummary` / `.generate_script(summary) -> Segments[]`, et `TTSProvider.synthesize(text, voice) -> mp3_bytes`. Implémentés en MVP : `gemini_vision.py` (SDK `google-genai`, schéma JSON de réponse) et `edge_tts.py` (lib `edge-tts`, voix épinglée dans `.env.example`). Les alternatives payantes (OpenAI, ElevenLabs) se branchent plus tard sur les mêmes interfaces quand une carte est disponible.

## 3. Architecture des couches

```
frontend/ (React+TS, build statique — n'affiche que des données servies par l'API)
    │  HTTP JSON uniquement (+ polling /api/jobs)
    ▼
backend/api/routers/     → routeurs minces : valident, appellent un service, retournent JSON
backend/services/        → orchestration métier : ingestion, analysis, script, tts, timeline, video, jobs
backend/providers/       → VisionProvider / TTSProvider (seule couche qui touche les clés API)
backend/db/              → SQLAlchemy + queries centralisées (seule couche qui touche SQLite)
backend/storage/         → layout disque data/, chemins dérivés des IDs (jamais du client)
backend/core/            → config (.env), logging, erreurs, tri naturel, images utils
```

**Règles de séparation strictes :**
- Le frontend n'appelle jamais la DB, FFmpeg, Pillow ou les SDKs IA — uniquement `GET/POST /api/*`.
- Les routeurs restent minces (< 20 lignes de logique) : tout le métier va dans `services/`, toute la donnée dans `db/queries/`.
- Les secrets (clé Gemini) ne vivent que dans `providers/` + `core/config.py`, lus depuis l'env serveur. **Aucune variable `VITE_*` ne contient un secret** (le front n'a besoin que de l'URL API, même origine en prod).
- Les appels IA passent par un **pacing centralisé** (dans `services/jobs.py`) : intervalle minimal entre deux appels vision (`VISION_MIN_INTERVAL_SEC`), backoff exponentiel sur `429`, compteur d'appels journaliers lu depuis `ai_costs`. À l'épuisement du quota : job mis en pause avec message explicite (« quota journalier épuisé, reprenez demain »), jamais de boucle de retry infinie.
- Les sorties IA sont validées par schéma Pydantic **avant** insertion : 1 retry, puis page/segment marqué `failed` avec log — jamais d'arrêt du chapitre (brief §9).

## 4. Schéma de base de données (SQLite)

```sql
-- Chapitres : 1 projet = 1 chapitre en MVP (la table existe pour la v2 multi-chapitres, non construite)
create table projects (
  id integer primary key autoincrement,
  title text not null,
  status text not null default 'created',          -- created|imported|analyzed|scripted|voiced|rendered|failed
  created_at datetime not null default current_timestamp
);
create table chapters (
  id integer primary key autoincrement,
  project_id integer not null references projects(id) on delete cascade,
  title text not null,
  source_filename text not null,
  page_count integer not null default 0,
  reading_order text not null default 'ltr',       -- ltr | vertical (webtoon)
  chapter_summary text,                            -- compréhension globale (JSON TEXT)
  created_at datetime not null default current_timestamp
);
create table pages (
  id integer primary key autoincrement,
  chapter_id integer not null references chapters(id) on delete cascade,
  page_index integer not null,                     -- ordre de lecture réel, 1-based
  page_id text not null unique,                    -- ch{chapter_id}_p{index:04d}
  filename text not null,
  rel_path text not null,                          -- chemin relatif sous data/, jamais absolu
  width integer, height integer,
  analysis_json text,                              -- sortie vision validée (JSON TEXT)
  importance integer,                              -- dénormalisé pour tri rapide (0-10)
  analysis_status text not null default 'pending',  -- pending|done|failed
  analysis_error text
);
create table script_segments (
  id integer primary key autoincrement,
  chapter_id integer not null references chapters(id) on delete cascade,
  position integer not null,                       -- ordre narration
  segment_key text not null unique,                -- ch{id}_s{position:03d}
  text text not null,
  page_refs text not null default '[]',            -- [page_index...] (JSON TEXT)
  duration_estimate real,
  status text not null default 'draft'             -- draft|reviewed|voiced
);
create table audio_segments (
  id integer primary key autoincrement,
  segment_id integer not null references script_segments(id) on delete cascade,
  provider text not null, voice text not null,
  rel_path text not null,
  duration real not null,                           -- lue via mutagen, JAMAIS estimée
  text_hash text not null,                          -- régénère uniquement si le texte a changé
  created_at datetime not null default current_timestamp
);
create table renders (
  id integer primary key autoincrement,
  chapter_id integer not null references chapters(id) on delete cascade,
  timeline_json text not null,                      -- dérivée des durées audio réelles
  video_rel_path text,
  settings_json text not null default '{}',         -- résolution, fps, preset, kenburns
  status text not null default 'pending',
  created_at datetime not null default current_timestamp
);
create table jobs (
  id integer primary key autoincrement,
  project_id integer references projects(id) on delete cascade,
  stage text not null,                              -- import|analyze|script|tts|render
  status text not null default 'queued',            -- queued|running|done|failed|cancelled
  progress integer not null default 0,              -- 0-100
  log_path text, error text,
  created_at datetime not null default current_timestamp
);
create table ai_costs (
  id integer primary key autoincrement,
  chapter_id integer references chapters(id) on delete cascade,
  provider text not null, model text not null, kind text not null,  -- vision|synthesis|script|tts
  units_json text not null default '{}',            -- tokens in/out, images, chars
  cost_usd real not null default 0,                 -- 0 en MVP (quotas gratuits) ; colonne conservée pour le passage au payant
  created_at datetime not null default current_timestamp
);
-- En MVP cette table est le REGISTRE DE QUOTA : l'UI affiche « X / Y appels aujourd'hui » par provider,
-- et le pacing bloque proprement avant le dépassement (cf. §3).
```

### Règles de sauvegarde
- `pages.page_id` et `script_segments.segment_key` sont UNIQUES et stables (idempotence des relances).
- `audio_segments.text_hash` (sha256 du texte) est REQUIS : régénération d'un segment **uniquement** si le hash diffère (brief §9 : rejouabilité indépendante).
- `rel_path` toujours **relatif** à `DATA_DIR`, jamais absolu, jamais fourni par le client.
- `audio_segments.duration` : insertion refusée si `duration <= 0` (la timeline ne connaît que le réel).
- Déduplique l'analyse par `page_id` : une page `done` n'est jamais réenvoyée au provider (cache = exigence de coût).

### Index recommandés
- `pages(chapter_id, page_index)` — lecture ordre de lecture.
- `script_segments(chapter_id, position)` — éditeur de script.
- `jobs(project_id, stage)` — polling progression.
- `ai_costs(chapter_id)` — coût par chapitre affiché dans l'UI.

### RLS / Auth base
- **N/A assumé** : SQLite local mono-utilisateur, pas d'accès réseau autre que localhost. Toute exposition réseau future impose de réécrire cette section (auth + RLS équivalent applicatif).

## 5. Variables d'environnement

| Variable | Usage | Exposition | Obligatoire |
|----------|-------|-----------|-------------|
| `DATA_DIR` | Racine stockage (`./data` par défaut) | serveur seul | non (défaut `./data`) |
| `HOST` / `PORT` | Bind uvicorn (`127.0.0.1` / `8000` par défaut ; ne jamais mettre `0.0.0.0` sans auth) | serveur seul | non |
| `GEMINI_API_KEY` | Vision + synthèse + script (clé gratuite AI Studio, sans carte) | serveur seul | **oui** |
| `VISION_PROVIDER` | `gemini` (défaut) — `openrouter-free` = fallback documenté v2 | serveur seul | non |
| `VISION_MODEL` | ID exact du modèle épinglé à l'implémentation (ex. classe Flash vision ; les noms tournent vite — ne jamais coder en dur, cf. §8) | serveur seul | non |
| `VISION_MIN_INTERVAL_SEC` | Pacing entre appels vision (défaut 5, pour rester sous les RPM gratuits) | serveur seul | non |
| `VISION_DAILY_CAP` | Plafond d'appels vision/jour avant pause propre (défaut selon quota AI Studio constaté) | serveur seul | non |
| `TTS_PROVIDER` | `edge` (défaut, sans clé) — `openai`/`elevenlabs` = upgrade payant v2 | serveur seul | non |
| `EDGE_TTS_VOICE` | Voix narrative EN par défaut (ex. `en-US-AriaNeural`, épinglée à l'implémentation) | serveur seul | non |
| `FFMPEG_PATH` | Override du binaire embarqué (optionnel) | serveur seul | non |
| `MAX_UPLOAD_MB` | Garde-fou upload (défaut 500) | serveur seul | non |
| `JOB_WORKERS` | Threads workers (défaut 2) | serveur seul | non |
| `VITE_API_URL` | URL API pour le dev front (`http://127.0.0.1:8000`, vide en prod = même origine) | build front | non |

**Règles :** `.env` gitignoré, `.env.example` commité sans secret. Aucune clé dans les logs, les réponses API ou le bundle front. Les compteurs de quota IA sont lus depuis `ai_costs`, pas recalculés côté client.

## 6. Structure des dossiers

```
otakuflow_v2/
├── backend/
│   ├── api/
│   │   ├── main.py            # app FastAPI, CORS localhost, montage /api + statique front
│   │   └── routers/           # projects.py, chapters.py, pages.py, analysis.py,
│   │                          # script.py, voice.py, render.py, jobs.py, export.py (minces)
│   ├── services/              # ingestion.py, analysis.py, script.py, tts.py,
│   │                          # timeline.py, video.py, jobs.py (métier + orchestration)
│   ├── providers/             # base.py (interfaces), gemini_vision.py, edge_tts.py
│   ├── prompts/               # analyze_page.txt, synthesize_chapter.txt, generate_script.txt
│   │                          # (prompts versionnés = la qualité de narration se relit ici)
│   ├── db/
│   │   ├── schema.sql         # source de vérité du schéma (§4)
│   │   ├── database.py        # engine SQLite WAL + session
│   │   └── queries/           # une fonction = une requête, aucun SQL dans services/
│   ├── storage/               # layout data/, résolution rel_path, garde-fous chemins
│   ├── core/                  # config.py, logging.py, errors.py, sort.py (tri naturel), images.py
│   └── tests/                 # ingestion (tri numérique), validation schémas, timeline durées
├── frontend/
│   ├── src/
│   │   ├── pages/             # ProjectsPage, WorkspacePage (6 onglets : Import Pages Analysis Script Voice Export)
│   │   ├── features/          # projects/, pages/, analysis/, script/, voice/, export/, jobs/
│   │   ├── components/ui/     # Button, ProgressBar, AudioPlayer, PageCard, SegmentEditor...
│   │   ├── services/api.ts    # seul point d'appel HTTP (+ hook useJobsPolling)
│   │   └── types/             # miroirs TS des schémas Pydantic (aucun any)
│   └── vite.config.ts         # proxy /api → 127.0.0.1:8000 en dev
├── data/                      # GITIGNORÉ : otakuflow.db + projects/{id}/originals|pages|thumbs|audio|renders|logs
├── docs/
│   ├── PROJECT_BRIEF.md
│   └── TECH_ARCHITECTURE.md   # ce document
├── AGENTS.md                  # (skill suivant)
├── .env.example
└── start.ps1 / start.bat      # 1 commande : venv → uvicorn (+ build front en prod)
```

Layout disque par projet : `data/projects/{project_id}/originals/<fichier source intact>/`, `pages/p_{index:04d}.jpg`, `thumbs/`, `audio/s_{pos:03d}.mp3`, `renders/final.mp4`, `logs/<job>.log`.

## 7. Contraintes de sécurité (périmètre = localhost, à réécrire si exposé)

- Ne jamais exposer : `GEMINI_API_KEY`, contenu de `.env`, chemins absolus disque, logs bruts avec prompts.
- Ne jamais exécuter côté client : appels IA/TTS, FFmpeg, Pillow, accès fichiers — tout passe par `/api/*`.
- Uploads : extensions allowlistées (`.cbz`, `.zip` ; sniff ZIP réel, pas que l'extension), taille ≤ `MAX_UPLOAD_MB`, extraction **sans** traversée de chemin (`..`, liens, `__MACOSX/`, fichiers cachés ignorés ; chaque membre résolu sous le dossier cible).
- Fichiers servis uniquement par ID (`/api/pages/{id}/image`) avec `Content-Type` fixé serveur — jamais de chemin client.
- CORS verrouillé sur l'origine locale ; bind `127.0.0.1` par défaut.
- Pas de RLS : assumé et documenté (§4). Si le bind change → ajouter auth avant toute autre feature.

## 8. Gotchas et pièges connus (à relire avant chaque étape)

1. **SQLite + threads** : `check_same_thread=False`, une session par job, `PRAGMA journal_mode=WAL`, un seul writer à la fois (jobs séquentiels par projet) — sinon `database is locked` en plein rendu.
2. **FFmpeg embarqué ≠ ffprobe** : `imageio-ffmpeg` ne fournit que `ffmpeg`. Durées audio via `mutagen` uniquement ; durée vidéo finale via `mutagen` (MP4) ou parse `ffmpeg -i` stderr.
3. **zoompan saccadé** : pattern imposé — upscale l'image en entrée (ex. 3840×2160), `zoompan=z='min(zoom+0.0015,1.15)':d=<frames>:s=1920x1080:fps=30`, jamais de zoom calculé en flottant libre. Tester le rendu sur 1 segment avant le chapitre entier.
4. **Taille payload vision** : redimensionner grand côté ≤ 1568 px, JPEG q80 avant envoi ; au-delà : tokens ×3 et refus API. Une page = un appel (pas de batch multi-images : un échec ne doit pas coûter 10 pages).
5. **Sortie IA non garantie sans schéma** : toujours réponse JSON schématisée (Gemini `response_json_schema`) + validation Pydantic + **1 retry**, puis `analysis_status='failed'` + log, chapitre continue (gotcha AI-SDK transposé à Python).
6. **Quotas gratuits = plafond réel par modèle, pas optionnel** : un chapitre de 120 pages ≈ 15 appels vision + 2 texte. Le léger (~500 req/jour) absorbe le volume, le fort (~20) suffit pour 2 appels — d où le routage par tâche. `VISION_PAGES_PER_CALL` (défaut 8), backoff exponentiel sur `429` avec limite de tentatives, compteurs journaliers **par modèle** dans `ai_costs`, pause propre + reprise le lendemain. Ne jamais paralléliser les appels vision en MVP. Chiffres à re-vérifier dans AI Studio : Google remanie les quotas (précédent : coupes de déc. 2025).
7. **Noms de modèles gratuits = denrée périssable** : les providers retirent/renomment les modèles free tous les quelques mois. ID épinglé uniquement dans `.env`/`README`, jamais codé en dur ; à chaque upgrade de modèle, rejouer 2-3 pages de test avant le chapitre entier.
8. **Edge-TTS = endpoint non officiel** : gratuit et sans clé, mais sans SLA — Microsoft peut le modifier. Mitigation : épingler la version `edge-tts` dans `requirements.txt`, timeout 60 s par segment, 1 retry, voix par défaut configurable (`EDGE_TTS_VOICE`). Si un segment échoue : `audio_status='failed'` + régénération unitaire, pas d'arrêt du chapitre.
9. **Scores/indices calculés serveur** : `importance`, `page_index`, `position`, `duration` ne sont jamais crus depuis l'IA ou le client — recalculés/validés backend (ex. `page_refs` filtrés sur les index existants du chapitre).
10. **TTS chunking** : seuil de sécurité ~4000 signes par requête → découper au niveau phrase, jamais au milieu d'un mot ; concat MP3 via ffmpeg demuxer, pas par collage binaire.
11. **Tri numérique** : tri naturel obligatoire (`page_2` < `page_10`) sur **tous** les listages (backup si noms sans chiffres : ordre ZIP). Test unitaire dédié, c'est le bug silencieux n°1 des CBZ.
12. **Pillow** : `ImageOps.exif_transpose` systématique + `.convert("RGB")` avant tout JPEG (sinon pages tournées ou crash CMYK). `verify()` tolérant : une image corrompue = page `failed`, pas chapitre mort.
13. **Lecture webtoon verticale** : `reading_order` stocké par chapitre ; si `vertical`, ordre = haut→bas des bandes et signalement des transitions incertaines dans l'UI (brief §10).
14. **Polling jobs** : `setInterval` 1s avec cleanup, stop à `done/failed/cancelled`, backoff si l'onglet est caché — sinon requêtes fantômes + SQLite verrouillé.
15. **Vite dev vs prod** : dev = proxy `/api` ; prod = même origine (front servi par FastAPI). Aucune URL codée en dur côté front en dehors de `VITE_API_URL`.

## 9. Ordre de construction recommandé

1. **Scaffold** : venv + `backend/` + `frontend/` + `.env.example` + `start.ps1` + check FFmpeg embarqué (import + version loggée).
2. **DB + storage** : `schema.sql`, engine WAL, layout `data/`, garde-fous chemins, tests tri naturel + extraction ZIP sécurisée.
3. **Import + pages** : upload CBZ/ZIP → extraction/filtrage/tri/indexation → `GET pages` + visionneuse grille (US-01).
4. **Jobs** : table + workers + polling + progression/annulation/relance par étape + logs (US-08, transverse).
5. **Analyse vision** : `analyze_page` (Gemini free, pacing + schéma JSON) + prompts versionnés + validation Pydantic + synthèse chapitre + UI lecture seule + cache + quota affiché (US-02).
6. **Script** : `generate_script` + segments + éditeur (texte, pages, split/merge/reorder) + gate "reviewed avant TTS" (US-03, US-04).
7. **Voix** : Edge-TTS par segment + `text_hash` + réécoute + régénération unitaire (US-05).
8. **Timeline + render** : calcul depuis durées mutagen + zoompan + concat + MP4 1080p + export (US-06, US-07).
9. **Hardening** : erreurs par page, quota/chapitre, reprise jobs + pause quota, jeu de **5 chapitres de test** (brief §9), README avec limitation légale documentée.
10. **Revue** : rejouabilité indépendante vérifiée étape par étape, ≤ 30 min sur 40 pages, note narration ≥ 4/5 — sinon retour étape 5/6, pas de nouvelle feature.
