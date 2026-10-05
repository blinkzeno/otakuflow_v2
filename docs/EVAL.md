# Protocole d évaluation — 5 chapitres (brief §9)

But : prouver la qualité de narration avant de publier. Un chapitre =
30 à 50 pages, traitement complet chronométré (objectif ≤ 30 min).

## Grille par chapitre

| Chapitre | Pages | Appels vision | Durée totale | Inventions | Assoc. invalides | Note /5 |
|----------|-------|---------------|--------------|------------|------------------|---------|
| 1 | | | | | | |
| 2 | | | | | | |
| 3 | | | | | | |
| 4 | | | | | | |
| 5 | | | | | | |

- **Inventions** : affirmation du script introuvable dans les pages citées.
  Objectif : **zéro** sur les 5 chapitres.
- **Assoc. invalides** : segment dont les pages citées ne soutiennent pas
  le texte. Objectif : **zéro**.
- **Note /5** : « je publie sans réenregistrer ». Objectif : moyenne ≥ 4/5.

## Critère de sortie

Go si et seulement si : 0 invention ET 0 association invalide
ET moyenne ≥ 4/5. Sinon retour aux prompts (`backend/prompts/*.txt`),
jamais de nouvelle feature.

## Checklist rejouabilité (sur un chapitre)

- [ ] Relancer Analyze : `ai_costs` inchangé (cache par page)
- [ ] Éditer 1 segment → Voice : seul son MP3 est régénéré
- [ ] Ajouter un segment → Render : timeline recalculée, vidéo remplacée
- [ ] Couper le serveur en plein import → job `failed` avec reprise
- [ ] Écouter le MP4 final en entier une fois avant upload
