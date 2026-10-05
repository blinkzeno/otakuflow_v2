---
name: agents-md-builder
description: Génère un fichier AGENTS.md complet et prêt à l'emploi pour diriger un agent IA dans l'implémentation d'un projet. Utilise ce skill quand l'utilisateur a un Project Brief ET un Tech Architecture Document et veut créer le fichier de règles pour son agent (Cursor, Windsurf, Claude Code, etc.). Déclenche aussi pour "crée mon AGENTS.md", "génère les règles pour mon agent IA", "configure Cursor/Windsurf pour mon projet", "je veux que l'IA respecte mes conventions". C'est l'étape qui précède directement le code.
---

# Skill 3 — AGENTS.md Builder
## Générer les règles de l'agent IA

Ce skill génère le `AGENTS.md` — le fichier que l'agent IA lit avant chaque tâche. Il encode toutes les décisions du Project Brief et du Tech Architecture Document en règles stables et réutilisables.

**Position dans le workflow :**
```
[Ideation] → [Tech Architecture] → ► SKILL 3 : AGENTS.md Builder ◄ → [Implementation Prompts]
```

---

## Ton rôle

Tu es un **Staff Engineer** qui écrit les règles de travail pour un agent IA. Le fichier que tu génères sera lu automatiquement par l'agent à chaque tâche — il remplace les 40 lignes de contexte que le développeur devrait sinon répéter dans chaque prompt.

**Principe directeur :** si tu devrais le répéter dans plus d'un prompt, ça va dans `AGENTS.md`.

---

## Processus

### Phase 1 — Vérification des inputs

Avant de générer, vérifier que tu as :
- ✅ Le nom du projet et sa description en 1-2 lignes
- ✅ La liste des features (in scope / out of scope)
- ✅ La stack technique choisie avec les exclusions
- ✅ Le modèle de données (tables principales et champs requis)
- ✅ Les contrats API (routes + méthodes HTTP)
- ✅ Les variables d'environnement et leur niveau d'exposition
- ✅ L'architecture des couches (qui fait quoi)

Si des éléments manquent → poser 1-2 questions ciblées ou proposer des valeurs par défaut raisonnables.

### Phase 2 — Génération du AGENTS.md

Générer le fichier complet selon la structure ci-dessous. Personnaliser chaque section avec les informations du projet — jamais de placeholder générique.

### Phase 3 — Validation et passage au skill suivant

> "✅ AGENTS.md généré. Prochaine étape : **Implementation Prompt Writer** (créer les prompts step-by-step pour chaque feature)."

---

## Template AGENTS.md à personnaliser

```markdown
# AGENTS.md

Tu es un ingénieur full-stack senior travaillant sur **[NOM_PROJET]**, [DESCRIPTION_1_LIGNE].

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

[NOM_PROJET] [DESCRIPTION_2_LIGNES_MAX].

**In scope (construire uniquement ça) :**
- [feature 1]
- [feature 2]
- [feature 3]

**Out of scope (ne PAS construire) :**
- [exclusion 1] — [raison courte]
- [exclusion 2] — [raison courte]

Ne pas sur-construire. Ne pas ajouter de features non listées.

---

# 2. Skills disponibles

Utiliser uniquement ces skills :
- `.agents/skills/[skill-1]` — [ce qu'il couvre]
- `.agents/skills/[skill-2]` — [ce qu'il couvre]

Pour [Zod / Tailwind / Cheerio / autre lib], utiliser les patterns existants du projet + la doc officielle.

Ne pas inventer de nouveaux skills.

---

# 3. Fichiers de plan (prompts/)

Chaque feature génère un fichier dans `prompts/`. Nommer clairement :
- `prompts/001-design-system.md`
- `prompts/002-auth.md`
- `prompts/003-database-schema.md`
- ...

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

- **UI** : pages, composants — affiche des données stockées uniquement
- **API** : route handlers minces (< 20 lignes de logique)
- **Business** : `lib/[service]/` — orchestration, règles métier
- **Data** : `lib/[db]/queries/` — queries centralisées et typées
[Ajouter selon le projet :]
- **AI** : `lib/ai/` — appels modèles, validation output Zod
- **Scraping** : `lib/scraping/` — extraction, parsing, validation
- **Pipeline** : `lib/pipeline/` — orchestration scrape + analyse

L'UI ne doit jamais :
- Appeler directement la base de données
- Déclencher du scraping ou de l'analyse
- Contenir des secrets ou des clés API
- Muter l'état du pipeline

---

# 5. Stack technique

**Utiliser :**
- [Framework] — [rôle]
- [Auth] — [rôle]
- [DB] — [rôle]
- [ORM/Client] — [rôle]
- [Styling] — [rôle]
- [Déploiement] — [rôle]
[Ajouter selon le projet :]
- [AI SDK] — appels modèles et structured output
- [Scraper] — extraction web
- [Email] — transactionnel

**Ne PAS utiliser :**
- [Alternative auth] — on utilise [Auth choisi]
- [Backend séparé] — tout dans Next.js
- [Autre ORM] — on utilise [ORM choisi]

---

# 6. Modèle de données

[NOM_DB] est la source de vérité pour toutes les données de l'application.

**Tables principales :**
- `[table_1]` — [rôle]
- `[table_2]` — [rôle]
- `[table_3]` — [rôle]

**Champs requis avant sauvegarde :**
- `[table].[champ]` est REQUIS (jamais null)
- `[table].[url]` est UNIQUE (déduplique par ce champ)
- Ne jamais sauvegarder [objet] sans [champ critique]

**RLS (Row Level Security) :**
- Activé sur toutes les tables
- Lecture publique : `[tables accessibles]`
- Écriture : service role seulement (bypass RLS)
- Tables privées (aucun accès public) : `[tables internes]`

---

# 7. Contrats API

Les routes ne changent pas entre sessions. Respecter strictement :

| Route | Méthode | Description | Auth requise |
|-------|---------|-------------|-------------|
| `/api/[action]` | POST | [description] | x-admin-secret |
| `/api/[resource]` | GET | [description] | public |
| `/api/cron/[job]` | GET | [description] | CRON_SECRET (Vercel) |

---

# 8. Sécurité

**Ne jamais exposer au navigateur :**
- Clé service role [DB]
- [Credentials service externe]
- Clé [AI provider]
- Secrets admin

**Ne jamais exécuter depuis le navigateur :**
- Appels [service externe / scraper]
- Appels AI / modèles
- Traitement pipeline

**Variables d'environnement :**

| Variable | Usage | Exposition |
|----------|-------|-----------|
| `NEXT_PUBLIC_APP_URL` | URL base | client + server |
| `[AUTH]_SECRET_KEY` | Auth | server only |
| `[DB]_SERVICE_KEY` | DB writes | **server only** |
| `OPENAI_API_KEY` | AI calls | **server only** |
| `[SERVICE]_KEY` | Service X | **server only** |
| `ADMIN_SECRET` | Routes action | **server only** |
| `CRON_SECRET` | Route cron | server only (Vercel inject) |

Seul `NEXT_PUBLIC_*` peut toucher le navigateur. Le reste = `import "server-only"`.

`.env.example` commité (placeholders). `.env.local` gitignored (vraies valeurs).

---

# 9. Standards de code

- TypeScript partout
- Fonctions petites, types explicites
- Pas de `any`
- `import "server-only"` sur tous les modules qui lisent des secrets
- Route handlers minces : validation du secret → appel lib → retour JSON
- Pas de refactoring hors scope de la tâche
- Pas de features non demandées
- Gestion d'erreur explicite : logger le contexte + message, jamais silencieux

---

# 10. Checks disponibles

Après chaque implémentation, lancer :
```bash
npx tsc --noEmit      # TypeScript (toujours)
npm run lint          # ESLint (toujours)
npm run build         # Next.js build (quand routes ou modules serveur changent)
```

Ne jamais affirmer qu'un check passe sans l'avoir lancé.

---

# 11. Gotchas spécifiques à ce projet

[Lister les pièges connus des outils utilisés — extraits du Tech Architecture Document]

Exemple :
- Ne pas utiliser `.eq('foreignTable.column', value)` avec [DB] — filtrer en JS après la requête
- Les IDs de [service] sont des 64-bit integers — extraire de la réponse brute avant JSON.parse
- Fichier middleware = `proxy.ts` (pas `middleware.ts`) dans Next.js 16+

---

# 12. Ordre de construction recommandé

1. Design system (tokens, typographie, couleurs)
2. Pages UI sur mock data (voir le produit tôt)
3. Auth ([outil choisi])
4. Schéma DB + seed data
5. Connexion UI → données réelles
6. [Feature core 1]
7. [Feature core 2]
8. [AI / intelligence si applicable]
9. Automation / cron (si applicable)
10. Deploy → polish

---

# 13. En cas de doute

1. Garder petit
2. Utiliser le skill concerné
3. Respecter les frontières server/client
4. Poser une question ciblée si besoin
5. Sauvegarder un prompt, demander approbation, implémenter
6. Lancer les checks, partager les étapes de test
```

---

## Règles de génération

**Personnaliser, ne pas laisser de placeholders vides.** Chaque section doit refléter le projet réel.

**La section "Out of scope" est aussi importante que "In scope."** Si vide → l'agent ajoutera des features non demandées.

**Les gotchas (section 11) sauvent des heures de debug.** Toujours inclure ceux des outils choisis.

**L'ordre de construction (section 12) est votre plan d'exécution.** L'agent s'y réfère quand il hésite sur quoi faire ensuite.

---

## Références complémentaires

→ `references/agents-md-examples/` — exemples complets par type de projet (SaaS, marketplace, outil AI, API)
→ `references/skills-templates/` — templates de skills par outil (Clerk, Supabase, OpenAI, etc.)
