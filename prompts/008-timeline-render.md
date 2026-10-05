# 008 — Timeline + render (durées réelles, zoompan, concat, MP4 1080p)

## Task goal
Construire la timeline depuis les durées audio réelles et rendre le MP4 1080p (zoom léger, concat), téléchargeable depuis l'onglet Export.

## Matching plan step
**Étape 8 — Timeline + render** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure, comportements concrets
- `.agents/skills/tech-architecture/SKILL.md` — §8 gotchas 2-3 (pas de ffprobe, pattern zoompan imposé)
- `references/security-checklist.md` — section "Toujours" (fichiers servis par ID, pas de chemin client ; settings de rendu validés serveur)

## Existing code inspected
- `backend/db/queries/audio.py` (007) — durées réelles par segment (seule source de vérité temporelle)
- `backend/storage/paths.py` (002) — `render_path()`, `safe_join` pour les listes de concat
- `backend/services/jobs.py` (004) — `enqueue`, progression (reportée par clip terminé)
- `backend/core/config.py` — ajouter `ffmpeg_path()` (imageio-ffmpeg par défaut, `FFMPEG_PATH` en override)
- `frontend/.../WorkspacePage` — ajouter l'onglet Export

## Decisions made
1. **Timeline calculée, jamais éditée** : `build_timeline(chapter_id)` → `[{segment_key, position, start, duration, audio_rel, pages: [rel...]}]`, `start` cumulé des durées mutagen. Stockée dans `renders.timeline_json` à chaque render (reproductible).
2. **1 clip = 1 segment** : image(s) du segment en boucle + zoompan + son MP3. Pages multiples dans un segment → temps partagé équitablement (`duration / n_pages`, sans audio découpé : l'image change, la voix continue).
3. **Filtre zoompan imposé** : entrée upscalée 3840×2160 (Pillow, LANCZOS, pad noir si ratio ≠ 16:9) puis `zoompan=z='min(zoom+0.0015,1.15)':d={frames}:s=1920x1080:fps=30`. `frames = round(duration*30)`. Sortie clip : `libx264 -crf 20 -preset veryfast -pix_fmt yuv420p` + `aac 128k`.
4. **Assemblage par concat demuxer** (`-f concat -safe 0 -i list.txt -c copy`) — pas de ré-encodage global (rapide, sans perte).
5. **Gate render** : 422 si des `draft` restent, si un segment `reviewed|voiced` n'a pas d'audio avec `duration > 0`, ou si `text_hash` a changé depuis l'audio (désynchronisé → demander régénération). Vérifié serveur, pas seulement UI.
6. **`settings_json`** : `{width:1920, height:1080, fps:30, crf:20, preset:"veryfast", kenburns:true}` — validé (whitelist de clés + plages) ; `kenburns:false` = image fixe (utile si zoompan pose problème sur une machine).
7. **Front Export** : tableau timeline (n° segment, pages, début→fin, durée), bouton Render + progression, `<video controls>` sur le MP4 final, boutons "Télécharger MP4" et "Exporter le script JSON".

## Assumptions (small, reversible)
- **Partage équitable du temps entre pages d'un segment** (pas de pondération par `importance`) : simple et prévisible (réversible : pondération en v2, la timeline est recalculée à chaque render).
- **Pas de fondu/noir entre clips** en MVP (concat sec) : le changement de page porte déjà le rythme (réversible : `xfade` ajoutable dans `video.py` sans changer l'API).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `backend/services/timeline.py` | `build_timeline(chapter_id) -> list[Clip]` (+ `Clip` dataclass : key, start, duration, audio_rel, page_rels) |
| `backend/services/video.py` | `render_chapter(chapter_id, settings, progress, should_stop) -> video_rel_path` (clips + concat + vérif mutagen) |
| `backend/api/routers/render.py` | `POST /api/chapters/{id}/render` (job), `GET /api/chapters/{id}/timeline`, `GET /api/renders/{id}/video` |
| `backend/tests/test_timeline.py` | 3 segments (durées 10/20/30) → starts 0/10/30, total 60 ; segment sans audio → ValueError explicite |
| `frontend/src/features/export/ExportPanel.tsx` | Timeline + Render + player + downloads |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `backend/db/queries/` + `renders.py` (nouveau) | `create_render`, `complete_render`, `get_render`, `latest_render` |
| `backend/core/config.py` | `ffmpeg_path()` : `FFMPEG_PATH` ou `imageio_ffmpeg.get_ffmpeg_exe()` |
| `backend/api/main.py` | `include_router(render)` |
| `frontend/.../WorkspacePage` | Onglet Export |
| `frontend/src/services/api.ts`, `types` | `renderChapter`, `getTimeline`, `videoUrl(id)`, `TimelineClip` |

## Implementation requirements
- `build_timeline()` :
```python
# segments voiced ordonnés + audio(duration>0) + pages du chapitre
# pages d'un segment : page_refs filtrés (006) mappés index->rel_path ; si [] -> première page du chapitre (fallback loggé, jamais de clip vide)
# start cumulé arrondi à 3 décimales ; total > 0 sinon ValueError("aucune durée audio")
```
- `render_chapter()` :
```python
# 1. gates (draft / audio manquant / hash désynchronisé) -> ValueError message clair -> job failed
# 2. dossier tmp render (safe_join, nettoyé en fin même en échec)
# 3. par clip : upscale Pillow -> PNG tmp -> ffmpeg loop+zoompan+audio -> clip_NNN.mp4 ; report_progress ; should_stop -> annule + nettoie
# 4. list.txt (chemins relatifs, -safe 0) -> concat -c copy -> renders/final.mp4
# 5. vérif : mutagen MP4 duration ≈ total timeline ±1 s sinon failed ("écart de durée")
# 6. upsert renders(row) + retourne video_rel_path
# subprocess : timeout 600 s par clip, stderr capturé (2000 derniers chars en log en cas d'échec, jamais de secret dedans)
```
- `GET timeline` : timeline calculée à la volée (pas de render requis) pour l'aperçu avant/après.
- `GET renders/{id}/video` : `FileResponse(media_type="video/mp4")` + `Content-Disposition: attachment; filename="otakuflow_ch{id}.mp4"`.
- Front : temps affichés `mm:ss.t` ; bouton Render désactivé tant que `has_draft || missing_audio` (info lue depuis `GET project`) — le serveur re-vérifie.

## Security requirements
- Aucun secret ne touche le bundle client
- `settings_json` validé (clés whitelistées, `crf` 0-51, `fps` ≤ 60, `preset` dans liste ffmpeg) — jamais de fragment de commande issu du client (construction par template, pas de f-string shell ; `subprocess.run(list, shell=False)`)
- `list.txt` du concat : chemins générés serveur uniquement
- Vidéo servie par ID de render uniquement

## Acceptance criteria
- [ ] `GET timeline` : starts cumulés exacts, total = Σ durées mutagen
- [ ] `POST render` → `renders/final.mp4` 1920×1080, lisible, durée ≈ total ±1 s
- [ ] Render avec un segment sans audio → job `failed` avec message explicite (pas de MP4 muet trompeur)
- [ ] Annulation mid-render → statut `cancelled`, fichiers tmp nettoyés
- [ ] Onglet Export : timeline lisible, player fonctionnel, téléchargements OK
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. Chapitre 3 segments voicés → onglet Export → vérifier le tableau timeline (starts cumulés).
2. "Render" → progression par clip → player.
   Résultat attendu : MP4 1080p, voix synchronisée aux changements d'image, durée totale = Σ audios ±1 s :
```powershell
python -c "from mutagen.mp4 import MP4; print(MP4('data/projects/1/renders/final.mp4').info.length)"
```
3. Télécharger via `GET /api/renders/1/video` → lecture VLC/Edge OK.
4. Négatif : supprimer un MP3 segment du disque, relancer Render → `failed` explicite (audio manquant), pas de vidéo partielle servie comme finale.
5. Négatif : `POST render` avec `{"preset": "; rm -rf"}` → 422 (validation), la commande n'est jamais construite.
