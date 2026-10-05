# 013 — Montage pertinent (cadrages intelligents, transitions, sous-titres)

## Task goal
Rendre le montage pertinent pour YouTube long : cadrer sur l essentiel
de chaque page, adoucir les changements de plan, sous-titrer la voix,
sans nouveau service payant ni quota supplémentaire.

## Matching plan step
Hors séquence (amélioration du rendu 008 après retour). Touche vision
(champ en plus), voix (mots horodatés), rendu (recadrage, xfade,
sous-titres) et export (SRT). Aucun changement d éditeur ni de gate.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotchas 2-3 (ffmpeg embarqué, zoompan)

## Existing code inspected
- `backend/providers/gemini_vision.py` — `_generate` (schéma imposé),
  `analyze_pages` (batch + `batch_index`) ; vérifié : binaire embarqué
  contient `xfade`, `subtitles` (libass), `ass`, `drawtext`
- `backend/providers/edge_tts.py` — ne garde que l audio ; vérifié : la
  lib émet `WordBoundary` + `SentenceBoundary` (offset/durée par mot)
- `backend/services/video.py` — clips full page + zoompan, concat `-c copy`
- `backend/services/timeline.py` — durées réelles par segment
- `backend/services/tts.py` — 1 MP3 par segment, hash, durées mutagen
- Format cible inchangé : 1920×1080, YouTube longue (paysage)

## Decisions made
1. **Région d intérêt dans le même appel batch (0 appel en plus)** :
   `PageAnalysis` gagne `focus: {x, y, w, h}` (coordonnées 0-1000 de la
   zone la plus importante : visage, action, bulle clé) + `suggest_zoom`
   (1.0 à 1.5). Demandé dans `analyze_pages.txt` pour chaque page.
   Le renderer cadre dessus ; si absent/invalide → repli page entière
   (comportement actuel, jamais d échec). Pas d OpenCV, pas de nouveau
   appel : le quota ne bouge pas. Précision spatiale du modèle à valider
   en live, repli garanti.
2. **Transitions xfade (0.5 s, fondu)** : chaîne `xfade` entre clips au
   lieu du concat sec. Coût assumé : ré-encodage global (rendu plus
   lent, ~2×), qualité identique (même crf/preset). Durée du fondu
   configurable (`settings.xfade`, 0 = concat sec d avant).
3. **Sous-titres en 2 niveaux** :
   - (a) **SRT téléchargeable** (`GET /api/chapters/{id}/subtitles`) :
     construit depuis les mots horodatés, YouTube l accepte en upload.
   - (b) **Incrustation optionnelle** (`settings.burn_subtitles`, défaut
     false) via filtre `subtitles` (libass présent ✓). Police Arial
     Windows avec repli propre si absente (rendu sans incrustation +
     warning, jamais d échec).
4. **Mots horodatés sans migration schéma** : `synthesize_with_timings`
   retourne `(bytes, words[{text, start, end}])` (secondes, offset/1e7) ;
   `synthesize()` reste un wrapper (aucun appelant cassé). Stockage en
   sidecar `audio/sg_XXXX.words.json` dérivé du `rel_path` (pas de
   colonne DB, pas de migration). SRT découpé en répliques (≤ 42 signes,
   coupure aux fins de phrase, horodatage des mots, repli
   proportionnel au segment si mots absents).
5. **Timeline enrichie, pas remplacée** : les clips gagnent `focus` et
   `subtitles` (chemin SRT du segment) ; total et starts inchangés.
   L aperçu Export affiche les zones cadrées (rectangle sur la vignette)
   pour contrôle visuel avant rendu.

## Assumptions (small, reversible)
- **Précision du focus modèle suffisante** : à valider en live sur 3
  pages (le rectangle doit contenir le sujet). Si faux > 1 fois sur 3,
  repli : recentrage auto désactivé par défaut (`settings.smart_crop`
  false), xfade + sous-titres seuls. Réversible par variable.
- **Police Arial présente** : standard Windows. Sinon repli sans
  incrustation (jamais bloquant).
- **Échappement Windows pour libass** : chemins en slashs + `:` échappés
  (`C\:/...`), pattern imposé dans le plan, test live obligatoire.

## Files to create / modify

### Créer
Aucun (sidecars dérivés, pas de nouveaux modules).

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/providers/base.py` | `FocusRegion` + `focus`, `suggest_zoom` dans `PageAnalysis` |
| `backend/prompts/analyze_pages.txt` | Règle focus : zone 0-1000 du sujet principal + zoom conseillé |
| `backend/services/analysis.py` | Sauvegarde inchangée (JSON validé tel quel) ; rien d autre |
| `backend/providers/edge_tts.py` | `synthesize_with_timings` (+ wrapper `synthesize` inchangé) |
| `backend/services/tts.py` | Écrit `sg_XXXX.words.json` à chaque synthèse réussie |
| `backend/services/timeline.py` | Clips + `focus` (depuis l analyse) |
| `backend/services/video.py` | Recadrage ROI, chaîne xfade, incrustation optionnelle, SRT par segment |
| `backend/api/routers/render.py` | `GET /api/chapters/{id}/subtitles` (fichier .srt en téléchargement) |
| `backend/db/queries/` | Rien (sidecars, pas de migration) |
| `frontend` (`ExportPanel`, `api.ts`, types) | Tableau + zones cadrées, lecteur, boutons Render / SRT / MP4 |
| `backend/tests/` | Tests ROI/repli, xfade settings, SRT, mots horodatés moqués |
| `.env.example` | Rien (police et fondus en `settings_json` par rendu) |

## Implementation requirements
- `analyze_pages.txt` (ajout) :
```text
- For each page also return focus: the {x, y, w, h} box (0-1000) of the single most important thing to show (main face, key action, key bubble), and suggest_zoom 1.0 to 1.5 (wider scene to tight close-up). If nothing stands out, return the full frame {x:0, y:0, w:1000, h:1000} and 1.0.
```
- Recadrage (`video.py`) : convertir le box 0-1000 en pixels de l image
  upscalée, `crop=w:h:x:y` AVANT zoompan ; valider (dans l image, surface
  ≥ 20 % sinon repli page entière + warning). Zoom final = zoompan
  existant (inchangé) appliqué sur le crop.
- xfade : construire la chaîne
  `[0][1]xfade=transition=fade:duration=0.5:offset=O1[x1]; [x1][2]xfade=...`
  avec offsets cumulés (durées − 0.5) ; audio concaténé à part puis muxé
  (`-c:a aac`, pas de `-c copy` global). `xfade: 0` → ancien chemin
  concat, conservé tel quel.
- SRT : `start,end --> ` au format `HH:MM:SS,mmm` ; répliques par phrase
  (borne `SentenceBoundary` si présente, sinon regroupement ≤ 42 signes
  sur les mots) ; repli : texte du segment réparti au prorata des mots.
- Incrustation : `subtitles='C\:/path/seg.srt':fontsdir='C\:/Windows/Fonts':force_style='FontName=Arial,FontSize=22,PrimaryColour=&HFFFFFF,OutlineColour=&H80000000,BorderStyle=1,Outline=2,MarginV=40'`.
  Police absente → skip + warning `[render] no font, subtitles SRT only`.
- `settings` étendus : `{..., "xfade": 0.5, "smart_crop": true, "burn_subtitles": false}` validés comme le reste (plages : xfade 0-2).
- Aperçu Export : vignette avec rectangle du focus (style inline,
  proportionnel 0-1000 → %), tableau existant + colonne durée inchangée.
- Tests : ROI valide → crop appelé avec les pixels attendus (mock
  `_upscaled` ?) ; ROI absurde → repli ; SRT d un segment à mots connus
  (fakes) ; `validate_settings` rejette `xfade: 99`.

## Security requirements
- Aucun secret, aucun endpoint sensible nouveau (SRT/MP4 servis par ID comme avant)
- Chemins SRT générés serveur uniquement, jamais depuis le client
- `settings` validés par liste blanche (3 clés en plus, mêmes règles)

## Acceptance criteria
- [ ] `focus` présent dans les analyses batch (mock), repli page entière si absent
- [ ] MP4 avec xfade : durée totale ≈ timeline − 0.5×(clips−1) ± 1 s, 1 seul flux vidéo continu (pas de cut sec)
- [ ] `GET subtitles` → .srt valide (horodatages croissants, texte complet des segments)
- [ ] Mots horodatés : 1 phrase de test → N mots avec starts croissants
- [ ] `pytest`, `tsc`, `lint`, `build` passent
- [ ] Live : rendu 2 segments avec xfade + SRT incrusté, lecture VLC OK, sous-titres visibles et synchrones

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Serveur avec clé, chapitre 2 pages analysées + voix existantes.
2. Relancer Analyze (nouveau champ focus), vérifier l aperçu Export
   (rectangles sur vignettes).
3. `POST render` (défauts), attendre `done`, télécharger MP4 + SRT.
   Résultat attendu : fondus entre plans, SRT qui colle à la voix,
   durée ≈ timeline − 0.5 s.
4. `POST render` avec `{"settings": {"burn_subtitles": true}}` →
   sous-titres visibles dans l image.
5. Négatif : `{"settings": {"xfade": 99}}` → 422.
