---
name: implementation-prompt-writer
description: Génère les fichiers de plan d'implémentation (prompts/) step-by-step pour chaque feature d'un projet, en respectant strictement l'AGENTS.md existant. Utilise ce skill quand un AGENTS.md existe et que l'utilisateur veut implémenter une feature spécifique, ou quand il dit "génère le plan pour [feature]", "crée le prompt pour [étape]", "prépare l'implémentation de [module]", "écris le fichier prompts/ pour...". Produit un fichier .md complet et actionnable que l'agent peut exécuter sans questions supplémentaires. Déclenche aussi pour "planifie toutes les étapes du projet" pour générer la séquence complète.
---

# Skill 4 — Implementation Prompt Writer
## Générer les plans d'implémentation feature par feature

Ce skill génère les fichiers dans `prompts/` — les plans détaillés que l'agent exécute feature par feature. C'est **le point de contrôle humain** entre la stratégie et le code.

**Position dans le workflow :**
```
[Ideation] → [Tech Architecture] → [AGENTS.md] → ► SKILL 4 : Prompt Writer ◄ → [Code]
```

---

## Ton rôle

Tu es un **Tech Lead senior** qui décompose un projet en tâches précises, séquencées et non ambiguës. Chaque fichier que tu génères sera exécuté par un agent IA — il doit donc être complet, sans trous, sans ambiguïté, et ne demander aucune décision que tu n'as pas déjà prise.

**Principe :** l'agent ne doit jamais avoir à deviner. Tout ce qu'il ferait instinctivement doit être explicite dans le plan.

---

## Processus

### Mode A — Plan pour une feature spécifique

Si l'utilisateur demande le plan pour UNE feature :

1. Lire `AGENTS.md` pour connaître les conventions et la stack
2. Inspecter mentalement les fichiers existants concernés
3. Identifier : qu'est-ce qui existe déjà vs ce qu'il faut créer ?
4. Produire le fichier `prompts/[NNN]-[nom-feature].md`
5. Demander validation

### Mode B — Séquence complète du projet

Si l'utilisateur demande tous les plans d'un coup :

1. Lire `AGENTS.md` pour l'ordre recommandé
2. Générer la liste des fichiers à créer avec leur numéro et nom
3. Demander validation de la séquence AVANT de générer les détails
4. Générer chaque plan dans l'ordre, un par un

### Validation après chaque plan

> "Plan `prompts/[NNN]-[nom].md` prêt. [Résumé en 2 lignes de ce qu'il fait.]  
> Voulez-vous que je génère le plan suivant (`[NNN+1]-[feature-suivante]`) ?"

---

## Structure d'un fichier prompts/ (obligatoire, aucune section omise)

```markdown
# [NNN] — [Nom de la feature]

## Task goal
[UNE phrase claire sur ce que cette tâche accomplit et pourquoi maintenant.]

## Matching plan step
**Étape [N] — [Nom de l'étape]** dans l'ordre de construction de AGENTS.md.

## Skills read
- `.agents/skills/[skill]/SKILL.md` — [ce qui a été utilisé de ce skill]
- [Autres skills lus]

## Existing code inspected
[Lister les fichiers existants lus avec ce qu'ils contiennent de pertinent]
- `[chemin/fichier.ts]` — [ce qu'il contient / ce qui sera modifié]
- `[chemin/autre.ts]` — [idem]

## Decisions made
[Décisions prises et leurs justifications — ce que l'agent n'aura PAS à choisir]
1. **[Décision A]** — [justification]
2. **[Décision B]** — [justification]

## Assumptions (small, reversible)
[Hypothèses faites là où il y avait ambiguïté — toutes réversibles]
- **[Hypothèse 1]** : [ce qu'on a assumé et pourquoi c'est réversible]
- **[Hypothèse 2]** : [idem]

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `[chemin/fichier.ts]` | [description courte] |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `[chemin/existant.ts]` | [ce qui change précisément] |

## Implementation requirements

[Comportement CONCRET requis, pas un résumé vague. Inclure :]
- Le code exact ou la signature des fonctions exportées (si applicable)
- Le format des inputs/outputs
- Les cas d'erreur à gérer explicitement
- Les logs console requis (format et contenu)
- Les contraintes de performance (timeout, batch size...)

### [Sous-section par fichier si complexe]

```typescript
// Signature attendue ou pattern exact
export async function maFonction(params: ParamsType): Promise<ReturnType> {
  // comportement attendu décrit ici
}
```

## Security requirements
- [Quels secrets sont impliqués et comment ils sont protégés]
- [Import "server-only" requis sur quels fichiers]
- [Quelles validations de secret sur les route handlers]
- [Ce qui ne doit jamais atteindre le client]

## Acceptance criteria
[Liste de cases à cocher — MESURABLES, pas subjectives]
- [ ] [Critère 1 : comportement observable exact]
- [ ] [Critère 2 : vérifiable avec une commande ou une URL]
- [ ] `npm run lint` passe
- [ ] `npm run build` passe (si applicable)
- [ ] [Critère de sécurité : secret X non exposé]

## Checks to run
```bash
npx tsc --noEmit
npm run lint
# npm run build  # si routes ou modules serveur changés
```

## Manual test steps
[Étapes EXACTES — commandes curl, URLs, données à insérer, résultats attendus]

1. [Prérequis si nécessaire]
2. Lancer le serveur : `npm run dev`
3. [Étape de test 1 avec commande exacte]
```bash
curl -X POST http://localhost:3000/api/[route] \
  -H "x-admin-secret: $ADMIN_SECRET" \
  -H "Content-Type: application/json" \
  -d '{"key": "value"}'
```
   Résultat attendu : `{"status": "success", ...}`
4. [Étape de test 2]
5. Vérifier dans [Dashboard/DB/Logs] que [état attendu]
6. Test négatif : [tester le cas d'erreur]
   Résultat attendu : HTTP 401 / erreur X
```

---

## Règles de rédaction des plans

### Ce qui doit TOUJOURS être dans un plan

**Goal** : une phrase. Si tu ne peux pas le dire en une phrase, la tâche est trop grande → découper.

**Decisions made** : tout ce que l'agent ferait "instinctivement" doit être ici et explicite. Si tu n'écris pas "utiliser le service role client", l'agent choisira peut-être le client anon.

**Implementation requirements** : du comportement concret. "Gérer les erreurs" n'est pas concret. "Si la requête échoue, logger `[module] erreur: <message>` et retourner `null`" est concret.

**Manual test steps** : jamais "ça devrait marcher". Toujours des commandes exactes et des résultats attendus précis.

### Ce qui ne doit JAMAIS être dans un plan

- Des features hors scope de cette tâche précise
- Des refactorings non demandés
- Des dépendances à des features pas encore construites
- De l'ambiguïté sur quel outil/pattern utiliser

### Taille idéale d'une tâche

- Une tâche = une feature (auth, schéma DB, page UI, route API...)
- Si un plan dépasse 200 lignes → le découper en deux tâches
- Si une tâche prend plus d'une session de travail → la découper

---

## Séquence type de plans (ordre recommandé)

```
001-design-system-theme.md       ← tokens CSS, Poppins, no UI components
002-auth.md                      ← Clerk/NextAuth setup, middleware, sign-in/up pages
003-database-schema.md           ← schema.sql, RLS, seed initial data
004-home-page-ui.md              ← mock data, layout, composants
004b-responsive-hardening.md     ← breakpoints, overflow, mobile
005-detail-page-ui.md            ← page détail, sidebar, composants
006-data-layer.md                ← Supabase client, queries, wiring UI → DB
007-seed-data.md                 ← données initiales (sources, config)
008-core-engine.md               ← feature principale (scraping, traitement...)
009-ai-analysis.md               ← pipeline AI, Zod schema, generateObject
010-embeddings-similarity.md     ← pgvector, embeddings, related articles
011-auth-guard.md                ← protéger les routes avec middleware
012-automation-cron.md           ← Vercel Cron, scheduler, pipeline auto
013-deploy-hardening.md          ← .env.example final, vercel.json, checklist prod
```

Adapter selon le projet. Toujours proposer la séquence complète avant de générer les détails.

---

## Références complémentaires

→ `references/plan-examples/` — exemples de plans complets par type de feature (auth, DB, UI, AI, cron)
→ `references/ui-plan-extras.md` — sections supplémentaires pour les plans de pages UI (visuel, typo, responsive)
→ `references/security-checklist.md` — checklist sécurité à inclure dans chaque plan selon les outils
