# Checklist sécurité par feature (à inclure dans les plans)

## Toujours (tout plan)

```markdown
## Security requirements
- Aucun secret ne touche le bundle client
- Variables sans NEXT_PUBLIC_ = server-only uniquement
- Pas de logique métier dans les composants UI
```

---

## Si le plan touche une route API (action : POST, DELETE...)

```markdown
## Security requirements
- Header `x-[projet]-admin-secret` vérifié en premier, avant tout traitement
- Rejet 401 immédiat si manquant ou invalide
- Aucune logique exécutée avant la vérification du secret
- Pattern exact :
  ```ts
  const secret = req.headers.get("x-admin-secret")
  if (!secret || secret !== process.env.ADMIN_SECRET) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 })
  }
  ```
```

---

## Si le plan touche Supabase (écriture ou lecture sensible)

```markdown
## Security requirements
- `SUPABASE_SERVICE_ROLE_KEY` uniquement dans des modules avec `import "server-only"`
- Ne jamais préfixer `SERVICE_ROLE_KEY` avec `NEXT_PUBLIC_`
- Le client service role est créé par fonction (pas de singleton global) :
  `function getServiceClient() { return createClient(url, serviceKey, ...) }`
- RLS activé sur toutes les tables concernées
- `grant select on [tables] to anon, authenticated` pour les tables publiques
- Aucun grant sur les tables internes (logs, schedules, runs)
```

---

## Si le plan touche l'Auth (Clerk, NextAuth...)

```markdown
## Security requirements
- Provider auth DANS `<body>`, pas autour de `<html>`
- Secret key (`CLERK_SECRET_KEY`) server-only uniquement
- Seule la publishable key (`NEXT_PUBLIC_CLERK_*`) est exposée côté client
- Fichier middleware = `proxy.ts` (Next.js 16+)
- Routes protégées définies via `createRouteMatcher`, pas hardcodées
- Pages sign-in/sign-up restent publiques (ne jamais les protéger)
```

---

## Si le plan touche l'IA (OpenAI, Anthropic...)

```markdown
## Security requirements
- `OPENAI_API_KEY` uniquement dans des modules avec `import "server-only"`
- Ne jamais passer la clé AI à un composant client ou une route accessible publiquement
- L'output AI est toujours validé avec Zod avant sauvegarde en DB
- Le texte brut des articles n'est PAS loggé (données potentiellement privées)
- Pas de prompt injection possible : le texte utilisateur est isolé du system prompt
```

---

## Si le plan touche un service externe (scraping, email, paiement...)

```markdown
## Security requirements
- Credentials `[SERVICE]_USERNAME` et `[SERVICE]_PASSWORD` uniquement côté serveur
- Ne jamais logger les credentials, même partiellement
- Les erreurs retournées à l'API ne contiennent pas de secrets :
  ```ts
  catch (err) {
    const message = err instanceof Error ? err.message : "Scrape failed"
    // ✅ message public safe
    return NextResponse.json({ error: message }, { status: 500 })
  }
  ```
```

---

## Si le plan touche le Cron Vercel

```markdown
## Security requirements
- `CRON_SECRET` injecté par Vercel — NE PAS l'ajouter dans `.env.local`
- Vérification `Authorization: Bearer <CRON_SECRET>` en production uniquement
- En développement (`NODE_ENV !== 'production'`) : skip la vérification pour tests manuels
- La route cron ne partage PAS le même secret que les routes admin (secrets différents)
- Exporter `maxDuration = 300` pour éviter les timeouts Vercel
```

---

## Si le plan touche pgvector / embeddings

```markdown
## Security requirements
- La fonction RPC pgvector utilise `security invoker` (s'exécute avec le rôle du caller)
- Requêtes embedding via service role uniquement (jamais anon key)
- Les vecteurs embedding ne sont pas exposés via l'API publique
- L'embedding d'un article n'est sauvegardé qu'après que l'analyse soit réussie
```
