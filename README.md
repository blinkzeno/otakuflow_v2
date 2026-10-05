# Otakuflow

Pipeline local qui transforme un chapitre CBZ en vidéo récap YouTube :
import → analyse vision → narration anglaise → voix off → MP4 1080p.
Vous relisez le script avant toute voix. Un chapitre à la fois.

## Prérequis

- Python 3.11+ (`py --version`) et Node 20+ (`node --version`)
- Une clé gratuite Gemini (AI Studio, sans carte) dans `.env` :
  copiez `.env.example` vers `.env` et renseignez `GEMINI_API_KEY`

## Démarrer

```powershell
.\start.ps1            # backend http://127.0.0.1:8000
cd frontend; npm run dev   # interface http://localhost:5173
```

## Parcours (6 onglets)

1. Import : déposez le `.cbz`, suivi en %
2. Pages : grille, tri numérique garanti
3. Analysis : `Analyze`, lecture seule, quota affiché
4. Script : `Generate`, corrigez, `Mark reviewed` (verrou avant voix)
5. Voice : `Generate voice`, réécoutez, régénérez un segment si besoin
6. Export : `Render MP4`, lecteur + téléchargement

Relance par étape : chaque étape saute ce qui est déjà fait.
Échec d une page : statut `failed` + log, le chapitre continue.

## Quotas gratuits

Vision ≈ 1 appel par page, voix et rendu = 0 appel, 0 €, sans carte.
Compteur dans l interface (`Vision X/Y today`). À épuisement : pause
propre, reprise le lendemain. Textes et images réduites avant envoi.

## Passer au payant (plus tard)

Mêmes prises : `VisionProvider` et `TTSProvider` dans `backend/providers/`
(OpenAI, ElevenLabs). Seuls `.env` et le nom du modèle changent.

## Cadre d usage

> Usage personnel, chaîne non monétisée. Vous fournissez vos fichiers.
> L outil ne télécharge rien, ne retire aucun filigrane, ne contourne
> aucune protection. Monétiser impose de revoir ce point avant tout.

## Vérifier

```powershell
.\.venv\Scripts\python -m pytest backend/tests -q
cd frontend; npx tsc --noEmit; npm run lint; npm run build
```
