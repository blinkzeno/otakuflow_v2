# Sections supplémentaires pour les plans de pages UI

À ajouter dans `prompts/[NNN]-[page].md` quand la tâche est une page ou un composant visuel.

---

## Section à ajouter : Visual interpretation (top → bottom)

```markdown
## Visual interpretation (top → bottom)
[Décrire la page visuellement de haut en bas, comme si tu la décrivais à quelqu'un qui ne peut pas la voir]

1. **[Élément 1]** — [couleur de fond, hauteur, contenu, comportement]
2. **[Élément 2]** — [idem]
3. **[Section principale]** — [layout, contenu, interaction]
4. **[Footer/fin]** — [idem]
```

---

## Section à ajouter : Layout et espacement

```markdown
## Layout et espacement
- Container max-width : [1280px / 960px / fluid]
- Padding horizontal : [24px / px-6]
- Grille : [1 col mobile / 2 col sm / 3 col lg] avec gap [24px / gap-6]
- Padding vertical sections : [32px / py-8]
- Padding interne cartes : [16px / p-4]
- Gap entre éléments internes : [8-12px]
```

---

## Section à ajouter : Typographie

```markdown
## Typographie (tokens du design system)
- Titre de page H1/H2 : `text-h2` (24px, font-bold)
- Titre de carte : `text-body-lg` (16px, font-semibold)
- Méta / catégorie : `text-body-sm` (13px, text-secondary)
- Labels : `text-caption` (11px, font-medium)
- Corps de texte : `text-body-md` (14px, Regular)
```

---

## Section à ajouter : Couleurs (tokens)

```markdown
## Couleurs (tokens du design system)
- Background page : `bg-bg-primary` (#FFFFFF)
- Background cartes : `bg-bg-primary`
- Background surfaces : `bg-surface` (#F6F6F6)
- Bordures : `border-border` (#E5E7EB)
- Texte principal : `text-text-primary` (#0D0D0F)
- Texte secondaire : `text-text-secondary` (#6B7280)
- Dark elements (header, footer) : `bg-text-primary` avec texte blanc
[Ajouter les couleurs spécifiques à ce projet]
```

---

## Section à ajouter : Responsive behavior

```markdown
## Responsive behavior
- Mobile (< 640px) : [comportement : stack, hide, scroll...]
- Tablet (640-1024px) : [comportement]
- Desktop (> 1024px) : [comportement]
- Header mobile : [nav cachée sous `md:`, hamburger visible, Subscribe/Login visible]
- Grille cartes : 1 col (mobile) → 2 (sm) → 3 (lg)
- Footer : 1 col (mobile) → 2 (sm) → 4 (lg)
- Overflow horizontal : aucun à 320px (category bar : overflow-x-auto)
```

---

## Section à ajouter : Composants à créer

```markdown
## Composants à créer / modifier

| Composant | Fichier | Props | Type |
|-----------|---------|-------|------|
| [NomComposant] | `components/[feature]/[nom].tsx` | `{ prop: Type }` | RSC / Client |
| [NomComposant2] | ... | ... | RSC |

**Règles composants :**
- RSC par défaut (pas de `"use client"` sauf si interactivité JS requise)
- Hand-rolled Tailwind (pas de shadcn sauf si déjà utilisé dans le projet)
- Inline SVG pour les icônes (pas de lib d'icônes sauf si déjà installée)
- Images via `next/image` avec domaines configurés dans `next.config.ts`
- Liens semantiques `<Link href="/[route]/[id]">` même si la route n'existe pas encore
```

---

## Section à ajouter : Mock data (si data layer pas encore connecté)

```markdown
## Mock data (temporaire)
- Source : `lib/mock-[resource].ts` — import statique, pas de fetch
- Contenu : [N] items représentatifs des vraies données
- Format : correspondre exactement au type `[TypeName]` dans `lib/types.ts`
- Lien avec données réelles : sera remplacé à l'étape [N] (Data Layer)
- Ne pas appeler Supabase, Oxylabs, ou l'IA depuis cette page
```

---

## Checklist review plan UI

Avant de finaliser un plan UI, vérifier :

- [ ] Chaque couleur est un token du design system (pas un hex hardcodé)
- [ ] Chaque taille de texte est un token typographique
- [ ] Le comportement responsive est décrit pour les 3 breakpoints
- [ ] Les composants à créer sont listés avec leurs props
- [ ] Il n'y a pas d'appel à la DB ou à un service externe dans le plan
- [ ] Les liens vers des routes futures sont mentionnés comme "pending"
- [ ] Les images placeholder sont identifiées (picsum, etc.)
- [ ] Le plan indique si c'est RSC ou Client Component
