# Gotchas et pièges connus par outil

## Next.js App Router

### ❌ "use client" inutile / mal placé
- Ne pas mettre `"use client"` sur un composant juste parce qu'il utilise des props
- Un composant serveur peut passer des données à un composant client
- Garder les Server Components aussi loin que possible dans l'arbre

### ❌ Route handlers qui font trop
- Les route handlers (`app/api/*/route.ts`) doivent rester minces (< 20 lignes)
- La logique métier va dans `lib/`, pas dans la route
- Pattern : `route.ts` → valide secret → appelle fonction de `lib/` → retourne JSON

### ❌ Importer un module server-only côté client
- Tout module avec `import "server-only"` lèvera une erreur si importé côté client
- Utiliser ce pattern sur TOUS les modules qui touchent des secrets

### ❌ Variables d'env manquantes au build
- `NEXT_PUBLIC_*` : disponible côté client ET serveur
- Variables sans préfixe : serveur SEULEMENT
- Un accès à `process.env.MA_VAR` côté client retourne `undefined` silencieusement

### ❌ generateStaticParams avec données dynamiques
- Ne pas utiliser `generateStaticParams` pour des routes dont les IDs viennent d'une DB live
- Utiliser le rendu dynamique à la place

### ✅ Middleware file
- Next.js 16+ : le fichier s'appelle `proxy.ts` (pas `middleware.ts`)
- Vérifier la version exacte dans `node_modules/next/dist/docs/`

---

## Supabase

### ❌ `.eq('foreignTable.column', value)` — CASSÉ
```typescript
// ❌ Ne génère PAS le SQL attendu
supabase.from('articles').select('*, sources(*)').eq('sources.active', true)

// ✅ Filtrer en JavaScript après la requête
const { data } = await supabase.from('articles').select('*, sources(*)')
const filtered = data?.filter(a => a.sources?.active === true)
```

### ❌ Détecter les articles "en attente" avec `analyzed_at IS NULL` seul
```typescript
// ❌ analyzed_at peut être set sans que la ligne article_analyses existe
.is('analyzed_at', null)

// ✅ LEFT JOIN sur la table d'analyse
.select('*, article_analyses(id)').is('article_analyses', null)
```

### ❌ Singleton client dans un contexte serverless
- Ne pas créer un client Supabase global partagé entre requêtes Next.js
- Créer un nouveau client par requête : `function getServiceClient() { return createClient(...) }`

### ❌ RLS non activé = toutes les données exposées via l'API REST
- Activer RLS sur TOUTES les tables : `alter table X enable row level security;`
- Ajouter des politiques SELECT pour les données publiques
- La clé service_role bypass RLS — ne l'utiliser que côté serveur

### ❌ Clé service_role exposée
- `SUPABASE_SERVICE_ROLE_KEY` ne doit JAMAIS avoir le préfixe `NEXT_PUBLIC_`
- Protéger avec `import "server-only"` dans tous les modules qui l'utilisent

### ❌ `.in()` avec trop d'éléments
- Limiter les tableaux dans `.in()` à 15 éléments max par requête
- Chunker les arrays en lots de 15 pour les grandes listes

---

## Clerk

### ❌ ClerkProvider autour de `<html>` au lieu de `<body>`
```tsx
// ❌
export default function RootLayout({ children }) {
  return <ClerkProvider><html><body>{children}</body></html></ClerkProvider>
}

// ✅ Provider DANS body
export default function RootLayout({ children }) {
  return <html><body><ClerkProvider>{children}</ClerkProvider></body></html>
}
```

### ❌ Utiliser `auth()` dans un composant client
- `await auth()` est server-only
- Côté client, utiliser `useAuth()` ou les composants `<SignedIn>` / `<SignedOut>`

### ❌ Nom du fichier middleware
- Next.js 16+ : `proxy.ts` à la racine (pas `middleware.ts`)

### ❌ Pas de fallback redirect URL
- Sans `NEXT_PUBLIC_CLERK_SIGN_IN_FALLBACK_REDIRECT_URL`, l'utilisateur atterrit dans le vide après login
- Toujours définir les 4 variables Clerk dans `.env.local`

---

## Vercel AI SDK

### ❌ `generateObject` sans Zod = output non garanti
```typescript
// ❌ Pas de validation = l'IA peut retourner n'importe quoi
const result = await generateText({ prompt: "retourne du JSON" })

// ✅ Zod garantit la structure
const { object } = await generateObject({
  schema: z.object({ title: z.string(), score: z.number() }),
  prompt: "analyse cet article"
})
```

### ❌ `bias_score` calculé par l'IA
- Toujours dériver `bias_score` côté serveur : `(rightPct - leftPct) / 100`
- Ne jamais faire confiance à l'IA pour calculer un score numérique dérivé

### ❌ Percentages AI qui ne somment pas à 100
- Toujours valider avec Zod `.refine()` : `d.left + d.center + d.right === 100`
- Normaliser avant sauvegarde si la somme est dans ±2 de tolérance

### ❌ Texte trop long envoyé à l'IA
- Tronquer `raw_text` à 8000-12000 chars max avant d'envoyer au modèle
- Au-delà : timeout, coût élevé, qualité dégradée

### ❌ Pas de retry sur output invalide
- Toujours implémenter 1 retry si Zod échoue
- Après 2 échecs : skip l'article sans sauvegarder, log l'erreur, continuer

---

## Oxylabs Scheduler

### ❌ 64-bit integer IDs corrompus par JSON.parse
- Les `schedule_id` et `job_id` dépassent `Number.MAX_SAFE_INTEGER`
- `JSON.parse` tronque silencieusement les derniers chiffres
- Solution : extraire les IDs de la réponse HTTP brute (text) avec une regex AVANT `JSON.parse`

```typescript
// ❌
const data = await response.json()
const scheduleId = data.schedule_id // CORROMPU si > 9007199254740991

// ✅
const text = await response.text()
const match = text.match(/"schedule_id"\s*:\s*(\d+)/)
const scheduleId = match?.[1] // string, précision préservée
```

### ❌ Utiliser GET /schedules/{id}/jobs pour le statut
- Cette endpoint ne retourne que des IDs sans statut
- Utiliser GET /schedules/{id}/runs pour obtenir `result_status` de chaque job

### ❌ Host Scheduler ≠ Host Realtime
- Scheduler/résultats : `https://data.oxylabs.io`
- Scraping realtime : `https://realtime.oxylabs.io`
- Mêmes credentials, hôtes différents

---

## TypeScript général

### ❌ `any` partout
- Chaque `any` est une bombe à retardement
- Préférer `unknown` + narrowing ou types explicites

### ❌ Fonctions trop longues avec logique mélangée
- Une fonction = une responsabilité
- Si une fonction dépasse 40 lignes → la découper

### ❌ Gestion d'erreurs silencieuse
```typescript
// ❌
try { await doSomething() } catch (_) {}

// ✅
try { await doSomething() } catch (err) {
  console.error("[module] context:", err instanceof Error ? err.message : err)
  throw err // ou gérer explicitement
}
```
