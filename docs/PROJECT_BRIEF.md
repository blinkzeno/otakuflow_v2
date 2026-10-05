# Project Brief — Otakuflow

## 1. Problème résolu
Produire une vidéo de récap YouTube à partir d'un chapitre CBZ prend aujourd'hui des heures de travail manuel : lecture du chapitre, rédaction de la narration, tri des images, enregistrement de la voix, montage. Otakuflow automatise cette chaîne et livre un MP4 regardable, tout en gardant la main sur chaque étape.

## 2. Solution proposée
Un pipeline local qui importe un chapitre CBZ, analyse ses pages, génère une narration anglaise fidèle au chapitre, l'associe aux pages pertinentes, la synthétise en voix off, et rend une vidéo 1080p — avec la possibilité de corriger le script, les associations et l'audio avant l'export.

## 3. Utilisateurs cibles
- **Utilisateur principal** : un créateur YouTube solo qui publie des récaps de manga/manhwa/webtoon en anglais, sur une chaîne de hobby non monétisée. Compétence technique : il sait utiliser un terminal et une clé d'API IA. Il importe ses propres scanlations.
- **Utilisateurs secondaires** : aucun pour le MVP. Pas de comptes, pas de partage, pas de collaboration.
- **Contexte d'utilisation** : application web locale (localhost),mono-utilisateur, PC Windows avec GPU. Traitements longs en arrière-plan avec progression visible. Usage en anglais (narration + interface).

## 4. User Stories principales
- [ ] **US-01** : En tant que créateur, je veux déposer un fichier CBZ afin que le système en extraire, trie et indexe toutes les pages dans le bon ordre.
- [ ] **US-02** : En tant que créateur, je veux que chaque page soit analysée et décrite de façon structurée afin que je puisse vérifier ce que la machine a compris avant de la croire.
- [ ] **US-03** : En tant que créateur, je veux recevoir une narration anglaise qui raconte le chapitre sans rien inventer, segment par segment, afin d'avoir une base solide à publier.
- [ ] **US-04** : En tant que créateur, je veux voir quels segments de narration renvoient à quelles pages afin de corriger une association erronée en un clic.
- [ ] **US-05** : En tant que créateur, je veux pouvoir modifier le texte d'un segment et régénérer uniquement son audio afin de corriger une phrase sans refaire le chapitre.
- [ ] **US-06** : En tant que créateur, je veux que la voix off soit synchronisée avec les images sans réglage manuel afin d'éviter le montage fastidieux.
- [ ] **US-07** : En tant que créateur, je veux exporter un MP4 1080p standard afin de pouvoir l'uploader directement.
- [ ] **US-08** : En tant que créateur, je veux voir la progression de chaque étape longue et pouvoir la relancer sans tout refaire afin de ne jamais bloquer sur une erreur.

## 5. In Scope (MVP)

**Import & normalisation**
- ✅ Import d'archives **CBZ et ZIP** uniquement (détection automatique du type).
- ✅ Extraction des images, filtrage des fichiers parasites, **tri numérique** des noms (`page_2` avant `page_10`).
- ✅ Attribution d'un `page_id` unique par page + métadonnées (index, filename, dimensions).
- ✅ Conservation des fichiers originaux, jamais écrasés ; artefacts intermédiaires versionnés sur disque.
- ✅ Génération d'un aperçu web de chaque page dans l'interface.

**Analyse IA**
- ✅ Analyse **page par page, dans l'ordre de lecture** via un modèle vision, sans moteur OCR dédié (le modèle vision lit directement les dialogues).
- ✅ Sortie structurée par page : personnages, actions, dialogues, événements, lieu, importance (score), résumé, description visuelle.
- ✅ Compréhension globale du chapitre à partir de l'ensemble des pages.
- ✅ Cache de l'analyse : une page déjà analysée n'est jamais réanalysée.

**Narration**
- ✅ Génération d'un script de récap **anglais**, culminating en segments (texte + pages citées + durée estimée).
- ✅ Contraintes d'écriture : fidèle au chapitre, ordre chronologique, oral et captivant, aucune invention, aucune information clé omise.
- ✅ Relecture et édition du script avant toute génération vocale (garde-fou obligatoire).

**Association & audio**
- ✅ Association automatique segment ↔ pages, **éditable au niveau du segment** (changer les pages, réordonner, scinder, fusionner, supprimer).
- ✅ Génération voix off via un fournisseur TTS, **un segment = un fichier audio**.
- ✅ Architecture TTS à fournisseur interchangeable (un seul fournisseur en MVP).

**Montage & export**
- ✅ Timeline calculée automatiquement depuis la durée réelle de chaque audio (zoom léger type Ken Burns, pagination au rythme de la voix).
- ✅ Rendu MP4 H.264 / AAC 1920×1080, résolution et paramètres configurables.
- ✅ Export du MP4 + export du script (.srt de référence hors MVP, cf. Out of Scope).

**Traitement**
- ✅ Toutes les étapes longues (import, analyse, script, TTS, rendu) exécutées en tâches de fond avec **pourcentage de progression, annulation et relance par étape**.
- ✅ Persistance locale des projets, chapitres et étapes.
- ✅ Journalisation des logs et surface d'erreurs explicite : une page en échec n'arrête pas le chapitre.

**Interface**
- ✅ Liste simple des projets + création d'un projet depuis un CBZ.
- ✅ Workspace en 6 étapes : Import, Pages, Analysis, Script, Voice, Export.
- ✅ Visionneuse de pages avec l'analyse associée (lecture seule).
- ✅ Éditeur de script segment par segment, avec lecture de l'audio associé.

## 6. Out of Scope (explicitement exclus)

**Cut du MVP (reporté à v2)**
- ❌ **Multi-chapitres / master timeline / fusion** — le MVP traite **un seul chapitre par vidéo**. Pourquoi : c'est la phase la plus coûteuse et elle double la surface de l'éditeur sans valider la valeur du pipeline.
- ❌ **Génération de PDF** depuis un CBZ — pourquoi : aucun usage dans la chaîne de production ; l'archive source fait déjà office de référence.
- ❌ **Import PDF** — pourquoi : les sources réelles sont des CBZ ; chemin d'import supplémentaire à maintenir.
- ❌ **Moteur OCR dédié** (type Tesseract) — pourquoi : le modèle vision retourne déjà les dialogues ; un OCR séparé dégraderait la qualité sur les bulles.
- ❌ **Dashboard multi-projets** (stats, progression globale, fichiers récents) — pourquoi : un seul utilisateur, un projet à la fois ; une liste simple suffit.

**Éditions reportées (hors MVP)**
- ❌ **Éditeur de timeline visuel** (drag & drop, duração par clip, réglage du zoom/pan par plan) — pourquoi : la timeline est dérivée de l'audio ; le contrôle fin est manuel et il est plus rentable de valider le narratif d'abord.
- ❌ **Édition de l'analyse par page** (re-saisir personnages/événements à la main) — pourquoi : on corrige en amont, sur le script.
- ❌ **Gestion de personnages / bible de série** — pourquoi : non nécessaire tant que la narration est générée chapitre par chapitre de façon indépendante.

**Jamais dans ce projet**
- ❌ Application mobile, multi-utilisateur, authentification, cloud, hébergement partagé — pourquoi : usage mono-utilisateur local.
- ❌ CBR, formats d'archive additionnels.
- ❌ Sous-titres (SRT/VTTburné), traduction multilingue, génération de thumbnails, génération de titres/descriptions YouTube, génération de Shorts — pourquoi : annoncés comme évolutions futures, pas parties du cœur produit.
- ❌ Suppression de filigranes, téléchargement de scanlations depuis une source en ligne, catalogage massif — pourquoi : hors périmètre, l'utilisateur fournit ses fichiers.
- ❌ Moteur de recommandation, recherche sémantique, embeddings — pourquoi : aucune valeur à ce stade.

**Explicitement exclu par hypothèse produit**
- ❌ Garde-fous de contenu, watermarking, détection de Rights Manager, conformité DMCA — pourquoi : hypothèse retenue = usage personnel, chaîne **non monétisée**. Le risque est traité comme une **limitation documentée** dans le README, pas comme une feature.

## 7. Contraintes et contexte
- **Marché cible** : YouTube international anglophone. Narration et scans en anglais. UI en anglais.
- **Déploiement** : 100 % local, mono-utilisateur, pas de cloud, pas d'auth, clés API en local.
- **Budget IA : 0 €, sans carte bancaire** : tous les providers par défaut fonctionnent en quota gratuit (vision + voix). Le redimensionnement des images avant envoi, le cache par page et le respect des quotas journaliers (pause propre + reprise) sont des exigences, pas des optimisations. Le quota consommé est affiché dans l'interface.
- **Cadre légal** : scanlations personnelles, chaîne non monétisée. Limitation assumée et documentée. Aucun système de retrait de contenu ou de protection des droits dans le MVP.
- **Matériel** : PC Windows personnel avec GPU. Les étapes longues tournent en tâche de fond et doivent pouvoir être interrompues et relancées.
- **Contexte technique existant** : projet neuf, aucun code existant.

## 8. Flux utilisateur principal (Happy Path)
1. L'utilisateur arrive sur la liste de ses projets et clique sur **New Project**.
2. Il choisit un fichier `.cbz` / `.zip` et saisit un titre de chapitre.
3. Le système crée le projet, extrait les images, les trie numériquement, les indexe et affiche la barre de progression de l'import.
4. Il clique sur **Analyze**. Le système envoie chaque page au modèle vision, dans l'ordre, puis construit la compréhension du chapitre. La barre de progression avance et chaque page est consultable avec son analyse.
5. Il clique sur **Generate Script**. Le système produit la narration anglaise en segments, chacun rattaché à ses pages.
6. **Il relit le script** (étape obligatoire). Il corrige un texte, change une association de pages, scinde ou fusionne un segment.
7. Il clique sur **Generate Voice**. Le système synthétise chaque segment et mesure sa durée réelle. Il peut réécouter et régénérer le son d'un seul segment.
8. Il clique sur **Render**. Le système construit la timeline depuis les durées audio et rend le MP4 1080p. La progression est visible.
9. Il récupère le fichier vidéo exporté et l'uploade. Les sources originales, le script et tous les intermédiaires sont conservés et réutilisables pour une correction ultérieure.

## 9. Critères de succès (MVP terminé quand...)
- [ ] Un CBZ de 30-50 pages produit un **MP4 1080p de 8 à 12 minutes**, sans réédition manuelle du rendu.
- [ ] Le traitement complet (import → export) tient en **≤ 30 minutes** sur la machine de développement, avec progression visible à chaque étape.
- [ ] **Qualité de narration, mesurée sur un jeu de 5 chapitres de test :**
  - **Zéro événement inventé** — chaque affirmation du script est traçable à une page citée.
  - **100 % des associations segment ↔ page sont vérifiables** : les pages citées soutiennent réellement le texte du segment.
  - **Note moyenne ≥ 4/5** sur le critère « je peux regarder cette vidéo sans réenregistrer la voix », évaluée par l'utilisateur.
- [ ] **Chaque étape est rejouable indépendamment** : relancer l'analyse ne relance ni le TTS ni le rendu ; un changement de texte sur un segment ne regénère que son audio.
- [ ] Une **erreur sur une page** n'interrompt pas le chapitre : elle est journalisée, signalée dans l'interface, et le chapitre continue.

## 10. Risques identifiés
- ⚠️ **La narration invente des faits** (hallucination) — c'est le risque n°1, il tue la crédibilité de la chaîne. Mitigation : génération ancrée sur les pages citées, sortie structurée validée avant usage, refus explicite de combler un trou, **lecture humaine obligatoire avant le TTS**, et mesure sur les 5 chapitres de test.
- ⚠️ **Coût des APIs IA par chapitre** — mitigation : redimensionner les images avant envoi, cache strict par page, réutilisation des artefacts intermédiaires, un seul fournisseur en MVP, coût par chapitre affiché dans l'interface.
- ⚠️ **Ordre de lecture incorrect sur les webtoons** (bandes verticales, sens de lecture) — mitigation : détection/paramétrage du sens de lecture, signalement explicite des pages dont l'ordre est incertain, vérification humaine sur les pages de transition.
- ⚠️ **Tâches longues sur un laptop** (coupure, surchauffe, RAM) — mitigation : annulable, reprise au niveau de l'étape, artefacts intermédiaires écrits au fur et à mesure, aucune étape ne recharge tout en mémoire.
- ⚠️ **Voix TTS limitée par les quotas et les licences** — mitigation : un seul fournisseur en MVP derrière une interface interchangeable, durée lue depuis l'audio réel et jamais estimée.
- ⚠️ **Rendu vidéo lent ou instable** sur 12 min en 1080p — mitigation : réEncoder les images une seule fois, rééquilibrage mémoire, paramètres d'encodage réglables.
- ⚠️ **Cadre légal du contenu** — mitigation : hypothèse documentée (usage personnel, non monétisé), README explicite sur les limites, aucune feature de retrait de contenu. Une décision de monétisation imposerait de revoir ce point.
