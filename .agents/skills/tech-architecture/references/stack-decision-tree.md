# Stack Decision Tree

## Framework fullstack

```
Besoin d'un site web / app web ?
├── Contenu statique ou peu dynamique → Astro
├── App React avec SSR/SSG + API routes ?
│   ├── Équipe JS/TS → Next.js (App Router)
│   ├── Préférence Vue → Nuxt
│   └── Préférence Svelte → SvelteKit
├── API seulement (pas de frontend) ?
│   ├── Node.js → Hono / Fastify
│   ├── Python → FastAPI
│   └── Déploiement serverless → Vercel Functions / Cloudflare Workers
└── App mobile ?
    ├── React Native → Expo
    └── Flutter → Flutter
```

**Choix par défaut pour un solo dev :** Next.js + TypeScript

---

## Auth (Authentification)

```
Besoin d'auth ?
├── Solo dev, go-fast → Clerk (DX +++, gratuit jusqu'à 10k users)
├── Open source préféré → NextAuth v5 / Auth.js (plus de config)
├── Déjà sur Supabase et auth simple → Supabase Auth (éviter si Clerk déjà utilisé)
├── Entreprise avec SSO/SAML → WorkOS / Clerk Enterprise
└── Auth custom complète → Lucia Auth (plus de code, contrôle total)
```

**Règle :** ne jamais mixer 2 providers auth sur le même projet.  
**Choix par défaut :** Clerk pour les projets solo/startup, NextAuth pour open source.

---

## Base de données

```
Type de données ?
├── Relationnelles (la majorité des projets) ?
│   ├── Solo dev, go-fast, besoin de realtime → Supabase (Postgres managé + Storage + RLS)
│   ├── Edge/serverless partout → PlanetScale (MySQL, branching) ou Turso (SQLite)
│   ├── Contrôle total, self-hosted → Neon (Postgres serverless)
│   └── Déjà sur Railway/Render → Postgres direct
├── Documents/JSON → MongoDB Atlas ou Supabase jsonb columns
├── Cache/sessions → Upstash Redis
├── Vecteurs (embeddings AI) → pgvector sur Supabase ou Pinecone
└── Fichiers/Storage → Cloudflare R2 ou Supabase Storage
```

**Choix par défaut :** Supabase (Postgres + Storage + RLS + realtime en un)

---

## ORM / Accès DB

```
Stack DB choisie ?
├── Supabase → supabase-js (client typé généré, RLS natif)
├── Postgres direct → Drizzle ORM (TypeScript-first, léger) ou Prisma (DX +++, lourd)
├── MongoDB → Mongoose ou client MongoDB natif
└── SQLite/Turso → Drizzle ORM
```

**Choix par défaut avec Supabase :** supabase-js uniquement (pas de Prisma par-dessus)

---

## Déploiement

```
Type de projet ?
├── Next.js → Vercel (natif, cron intégré, Edge functions)
├── Fullstack Node.js → Railway ou Render
├── Static → Cloudflare Pages (gratuit, CDN mondial)
├── Backend Python → Railway ou Fly.io
└── Docker → Fly.io ou VPS (Hetzner, DigitalOcean)
```

**Choix par défaut :** Vercel pour Next.js (intégration parfaite + cron jobs)

---

## Email transactionnel

```
Volume ?
├── < 3000 emails/mois → Resend (DX +++, 3k/mois gratuit, React Email)
├── > 3000 emails/mois → Postmark (delivrabilité ++) ou SendGrid
└── Newsletter + transactionnel → Loops ou Brevo
```

---

## Paiement

```
Modèle business ?
├── Abonnement SaaS → Stripe Billing + Stripe Checkout
├── One-time payment → Stripe Checkout ou LemonSqueezy
├── Marketplace avec sellers → Stripe Connect
├── Info-produit / digital downloads → LemonSqueezy (gère TVA européenne)
└── Afrique/marchés émergents → Stripe + Flutterwave ou Notchpay
```

---

## AI / LLM

```
Type d'usage ?
├── Structured output (JSON validé) → OpenAI gpt-4o-mini + Vercel AI SDK generateObject + Zod
├── Chat conversationnel → Vercel AI SDK useChat + streamText
├── Embeddings → OpenAI text-embedding-3-small
├── Vision / analyse d'images → GPT-4o ou Claude claude-sonnet-4-6
├── Pas de clé API, open source → Ollama (local) ou Groq (rapide)
└── Multi-provider → Vercel AI SDK (abstraction parfaite)
```

---

## Scraping

```
Type de scraping ?
├── Sites statiques (HTML simple) → Cheerio + fetch natif
├── Sites avec JavaScript → Playwright (self-hosted) ou Oxylabs (managé)
├── À grande échelle / rotation IP → Oxylabs Web Scraper API
├── Scheduling automatique → Oxylabs Scheduler + Vercel Cron
└── Extraction structurée → FireCrawl ou Jina Reader
```

---

## Storage (fichiers)

```
Type de fichiers ?
├── Images utilisateurs → Cloudflare R2 (0.015$/GB, CDN mondial) ou Supabase Storage
├── PDFs / documents → Cloudflare R2 ou Vercel Blob
├── Vidéos → Cloudflare Stream ou Mux
└── Backup DB → Supabase auto-backup inclus
```

---

## Monitoring / Observabilité

```
Priorité ?
├── Erreurs frontend/backend → Sentry (gratuit jusqu'à 5k errors/mois)
├── Logs structurés → Axiom (1GB/jour gratuit) ou Logtail
├── Analytics produit → Posthog (self-host gratuit ou cloud) ou Plausible (privacy-first)
└── Uptime → Better Uptime ou Checkly
```

---

## Tableau de coûts estimés (MVP, plan gratuit/starter)

| Service | Plan gratuit | Premier plan payant |
|---------|-------------|---------------------|
| Vercel | Hobby (suffisant MVP) | Pro 20$/mois |
| Supabase | 500MB DB, 1GB storage | Pro 25$/mois |
| Clerk | 10k MAU | Pro 25$/mois |
| Resend | 3k emails/mois | 20$/mois |
| OpenAI | Pay-as-you-go | ~0.15$/1M tokens (gpt-4o-mini) |
| Cloudflare R2 | 10GB/mois | 0.015$/GB |
| Sentry | 5k errors/mois | 26$/mois |
| Oxylabs | Trial | Pay-as-you-go |
