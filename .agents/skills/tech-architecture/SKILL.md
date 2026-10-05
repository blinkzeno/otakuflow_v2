---
name: tech-architecture
description: Choisit la stack technique, les intégrations tierces, le schéma de base de données et l'architecture des couches logicielles adaptées à un projet spécifique. Utilise ce skill après la phase d'idéation ou quand l'utilisateur demande "quelle stack utiliser", "comment structurer le backend", "quelle base de données choisir", "comment architecturer mon projet", "quels outils utiliser pour...". Produit un Tech Architecture Document complet qui devient la source de vérité pour AGENTS.md. Déclenche aussi pour "j'ai un brief produit, aide-moi à choisir les technos".
---

# Skill 2 — Tech Architecture
## De la spec produit aux choix techniques

Ce skill traduit le **Project Brief** (output du skill Ideation) en décisions techniques documentées. Il couvre : stack, intégrations, schéma DB, architecture des couches, contraintes de sécurité, et variables d'environnement.

**Position dans le workflow :**
```
[Ideation] → ► SKILL 2 : Tech Architecture ◄ → [AGENTS.md Builder] → [Implementation]
```

---

## Ton rôle

Tu es un **Architect Engineer senior**. Tu choisis les outils en fonction des contraintes réelles du projet (budget, équipe, délai, marché, contraintes techniques). Tu justifies chaque choix ET chaque exclusion. Tu identifies les gotchas et pièges connus de chaque outil avant que le développement commence.

---

## Processus en 4 phases

### Phase 1 — Lire le Project Brief

Si un brief est fourni (output du skill Ideation), l'analyser. Extraire :
- Type de projet (SaaS, marketplace, outil interne, API...)
- Contraintes (budget, délai, équipe solo ou team, marché géographique)
- Fonctionnalités clés (scraping, AI, paiement, temps réel, fichiers...)
- Utilisateurs (grand public, pros, développeurs)

Si pas de brief → demander le contexte minimum (5 questions max, voir `references/context-questions.md`).

### Phase 2 — Stack Selection (décision outillée)

Consulter `references/stack-decision-tree.md` pour guider les choix.  
Chaque choix doit répondre à : **"Pourquoi cet outil ET pourquoi pas les alternatives ?"**

### Phase 3 — Production du Tech Architecture Document

Produire le document complet (structure ci-dessous).

### Phase 4 — Validation et passage au skill suivant

> "✅ Architecture définie. Prochaine étape : **AGENTS.md Builder** (règles de l'agent IA pour ce projet)."

---

## Structure du Tech Architecture Document (output obligatoire)

```markdown
# Tech Architecture — [Nom du Projet]

## 1. Stack principale

| Couche | Outil choisi | Justification | Alternatives écartées |
|--------|-------------|--------------|----------------------|
| Framework frontend/fullstack | Next.js / Nuxt / SvelteKit / ... | [raison] | [alt écartée + pourquoi] |
| Langage | TypeScript / Python / ... | [raison] | |
| Auth | Clerk / NextAuth / Supabase Auth / ... | [raison] | [alt écartée] |
| Base de données | Supabase / PlanetScale / MongoDB / ... | [raison] | |
| ORM / Query | Prisma / Drizzle / Supabase-js / ... | [raison] | |
| Styling | Tailwind / CSS Modules / ... | [raison] | |
| Déploiement | Vercel / Railway / Render / ... | [raison] | |

## 2. Intégrations tierces

| Besoin | Service choisi | Pourquoi | Coût estimé MVP | Alternative |
|--------|--------------|---------|----------------|------------|
| Email transactionnel | Resend / SendGrid / ... | | | |
| Paiement | Stripe / LemonSqueezy / ... | | | |
| Fichiers/Storage | Cloudflare R2 / Supabase Storage / ... | | | |
| AI/LLM | OpenAI / Anthropic / Gemini / ... | | | |
| Scraping | Oxylabs / Apify / Playwright / ... | | | |
| Search | Algolia / Typesense / pgvector / ... | | | |
| Analytics | Posthog / Plausible / Mixpanel / ... | | | |
| Monitoring | Sentry / Axiom / ... | | | |

## 3. Architecture des couches

```
[Décrire les couches séparées de l'application]

Couche UI         → pages, composants — affiche données stockées uniquement
Couche API        → route handlers minces — pas de logique métier
Couche Business   → lib/pipeline/, lib/services/ — orchestration, règles métier
Couche Data       → lib/db/, lib/supabase/ — queries centralisées
Couche AI/ML      → lib/ai/ — appels modèles, validation output
Couche Scraping   → lib/scraping/ — extraction, parsing, validation
```

**Règles de séparation strictes :**
- L'UI n'appelle jamais directement la DB, le scraper ou l'IA
- Les route handlers restent minces (< 20 lignes de logique)
- Les secrets ne touchent jamais le bundle client

## 4. Schéma de base de données

### Tables principales

```sql
-- [table 1]
create table [nom] (
  id uuid primary key default gen_random_uuid(),
  -- champs...
  created_at timestamptz not null default now()
);

-- [table 2]
...
```

### Règles de sauvegarde
- [champ X] est REQUIS avant toute insertion (jamais null)
- [champ Y] est unique (contrainte d'unicité)
- Déduplique par [champ Z]

### Index recommandés
- `[table]([champ])` — pour les lectures fréquentes par [critère]

### RLS (Row Level Security)
- Public peut lire : [tables]
- Admin seulement : [tables]
- Service role bypass : oui/non

## 5. Variables d'environnement

| Variable | Usage | Exposition | Obligatoire |
|----------|-------|-----------|-------------|
| `NEXT_PUBLIC_APP_URL` | URL base de l'app | client + server | oui |
| `DATABASE_URL` | Connexion DB | server only | oui |
| `[AUTH]_SECRET_KEY` | Auth provider | server only | oui |
| `OPENAI_API_KEY` | Appels AI | server only | si AI |
| `[SERVICE]_KEY` | Intégration X | server only | si X utilisé |

**Règle :** seul `NEXT_PUBLIC_*` peut être exposé au navigateur.

## 6. Structure des dossiers

```
[nom-projet]/
├── app/                    # Pages et route handlers (Next.js App Router)
│   ├── (public)/           # Routes publiques
│   ├── (auth)/             # Routes protégées
│   └── api/                # Route handlers API
├── components/
│   ├── ui/                 # Composants génériques (boutons, inputs...)
│   └── [feature]/          # Composants spécifiques à une feature
├── lib/
│   ├── [db]/               # Clients DB + queries centralisées
│   │   ├── client.ts
│   │   └── queries/
│   ├── [auth]/             # Helpers auth
│   ├── ai/                 # Appels AI (si applicable)
│   ├── scraping/           # Pipeline scraping (si applicable)
│   └── utils/              # Utilitaires partagés
├── [db-tool]/
│   └── schema.sql          # Source de vérité du schéma
├── AGENTS.md               # (généré par le skill suivant)
├── .env.example            # Template env (commité, sans secrets)
└── .env.local              # Secrets locaux (gitignore)
```

## 7. Contraintes de sécurité

- Ne jamais exposer : [liste des secrets]
- Ne jamais exécuter côté client : [liste des opérations sensibles]
- RLS activé sur toutes les tables : oui/non
- Clé service role : server-only via `import "server-only"`

## 8. Gotchas et pièges connus

[Liste des pièges spécifiques aux outils choisis — lire references/gotchas/ pour chaque outil]

## 9. Ordre de construction recommandé

1. Design system et tokens
2. UI sur mock data
3. Auth ([outil choisi])
4. Schéma DB + migrations
5. Seed / données initiales
6. Connexion UI → données réelles
7. [Core feature principale]
8. [Features secondaires]
9. Automation / cron (si applicable)
10. Deploy + hardening
```

---

## Règles de décision technique

**Pour chaque outil, évaluer dans cet ordre :**
1. **Contrainte dure** : est-ce que le projet a une contrainte qui élimine cet outil ? (coût, région, compliance, infra existante)
2. **Fit fonctionnel** : est-ce que l'outil couvre exactement le besoin, ni plus ni moins ?
3. **DX et maintenance** : est-ce que l'équipe (solo ou petite) peut le maintenir sans expertise spécialisée ?
4. **Coût MVP** : est-ce que le plan gratuit ou basique suffit pour valider ?
5. **Scalabilité** : est-ce que ça tient si ça marche × 100 ?

**Règle d'or :** l'outil le plus simple qui couvre le besoin > l'outil le plus puissant du marché.

---

## Références complémentaires

→ `references/stack-decision-tree.md` — arbre de décision pour chaque couche
→ `references/gotchas/supabase.md` — pièges Supabase connus
→ `references/gotchas/clerk.md` — pièges Clerk/Auth connus
→ `references/gotchas/nextjs.md` — pièges Next.js App Router connus
→ `references/gotchas/ai-sdk.md` — pièges Vercel AI SDK / OpenAI connus
→ `references/cost-calculator.md` — estimation coûts par service
