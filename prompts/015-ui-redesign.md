# 015 — Refonte UI SaaS sombre + sidebar (sans toucher au backend)

## Task goal
Reconstruire toute l interface en SaaS sombre pro (sidebar étapes,
design tokens, composants, responsive) avec comportement strictement
identique : mêmes routes, mêmes appels API, aucune logique métier
déplacée.

## Matching plan step
Hors séquence (refonte transverse après 014). Aucun changement backend,
aucun contrat API modifié, aucun champ DB touché.

## Skills read
- `.agents/skills/implementation-prompt-writer/SKILL.md` — structure du plan, exigences concrètes
- `.agents/skills/implementation-prompt-writer/references/ui-plan-extras.md` — sections visuel, layout, typo, couleurs, responsive, composants
- `.agents/skills/tech-architecture/SKILL.md` — stack front (React + Vite + Tailwind v4, servie par FastAPI)

## Existing code inspected
- `frontend/src/index.css` — 1 ligne (`@import "tailwindcss"`), aucun token
- `frontend/src/App.tsx` — routes `/` et `/p/:id` (conservées telles quelles)
- `frontend/src/pages/ProjectsPage.tsx` — liste + upload, styles gris inline
- `frontend/src/pages/WorkspacePage.tsx` — onglets haut, polling jobs, panneau par étape
- `frontend/src/features/*` — 6 panneaux fonctionnels à restyler sur place (aucune logique à changer)
- `frontend/src/components/` — `JobProgress`, `QuotaBadge` (à restyler + compléter par un kit UI)
- `frontend/src/services/api.ts`, `types/` — contrats stables, aucune retouche

## Decisions made
1. **Thème sombre par tokens Tailwind v4** (`@theme` dans `index.css`) :
   fond `#0B0D10`, surfaces `#14181D`, bordures `#262C34`, texte
   `#EDEFF2` / secondaire `#9AA3AF`, accent indigo `#6366F1`, succès
   émeraude, alerte ambre, danger rouge. Aucun hex hors tokens.
2. **Coquille applicative** : sidebar 260 px (logo, retour projets,
   6 étapes avec pastille de statut, QuotaBadge en bas) + barre haute
   (titre projet, job en cours, progression). Contenu `max-w-7xl`.
   Sous `lg` : sidebar → barre haute avec étapes en scroll horizontal.
3. **Statuts d étapes calculés dans `WorkspacePage`** (seul endroit qui
   possède déjà projet + pages + jobs) + `listSegments` et
   `getLatestRender` chargés ici : import (chapitre + pages),
   analysis (≥ 1 page `done`), script (segments + 0 `draft` = done),
   voice (tout `voiced`), export (render `done`). Pastilles seules,
   navigation toujours libre (les verrous restent serveur).
4. **Kit UI minimal** (`components/ui/`) : `Button` (primary/ghost/danger),
   `Card`, `Badge`, `ProgressBar`, `EmptyState`, `Skeleton`, `Field`,
   `Icon` (SVG inline : upload, image, chart, script, mic, film, check,
   x, plus, trash, play, download). Police système (pas de webfont,
   localhost souvent hors-ligne).
5. **États partout** : chaque vue async = chargement (squelette) + vide
   (avec action) + erreur (message serveur + réessayer). Le polling et
   les endpoints restent byte-identiques.
6. **Images sur fond sombre** : vignettes et lecteurs avec anneau
   `border` + fond surface (jamais d image collée au fond page).

## Assumptions (small, reversible)
- **Anglais conservé** pour tous les libellés (contrat produit, réversible : dictionnaire plus tard).
- **Pas de drag & drop ni d animations** : transitions CSS simples uniquement (réversible : motion ajoutée sans toucher la structure).
- **Contrastes dark validés par tokens** (texte ≥ 4.5 sur fond) plutôt que mesurés un par un (réversible : ajuster les tokens).

## Files to create / modify

### Créer
| Fichier | But |
|---------|-----|
| `frontend/src/components/ui/Button.tsx` | `props {variant, size, disabled, onClick, children}` |
| `frontend/src/components/ui/Card.tsx` | `props {children, className?}` surface + bordure + radius |
| `frontend/src/components/ui/Badge.tsx` | `props {tone: info/success/warn/danger/neutral, children}` |
| `frontend/src/components/ui/ProgressBar.tsx` | `props {value: 0-100, tone?}` |
| `frontend/src/components/ui/EmptyState.tsx` | `props {icon, title, hint, action?}` |
| `frontend/src/components/ui/Skeleton.tsx` | `props {lines?}` blocs pulsés |
| `frontend/src/components/ui/Field.tsx` | Label + input/textarea/select stylés |
| `frontend/src/components/ui/Icon.tsx` | SVG inline nommées |
| `frontend/src/components/layout/AppShell.tsx` | Sidebar + topbar + `<Outlet>`-like `children` |
| `frontend/src/components/layout/StepNav.tsx` | `props {steps: {id, label, status, icon}[], active, onGo}` |

### Modifier
| Fichier | Changement |
|---------|-----------|
| `frontend/src/index.css` | Tokens `@theme` + base (fond, sélection, scrollbar) |
| `frontend/src/pages/ProjectsPage.tsx` | Dashboard : carte nouvel import + grille cartes projets |
| `frontend/src/pages/WorkspacePage.tsx` | Coquille AppShell, statuts d étapes, rendus par onglet inchangés dans le contenu |
| `frontend/src/features/*` (7 fichiers) | Restyle seul : tokens, cartes, badges, états (logique et appels intacts) |
| `frontend/src/components/JobProgress.tsx`, `QuotaBadge.tsx` | Restyle tokens + `ProgressBar`/`Badge` partagés |

## Implementation requirements
- `index.css` :
```css
@import "tailwindcss";
@theme {
  --color-base: #0B0D10; --color-surface: #14181D; --color-raised: #1B2128;
  --color-line: #262C34; --color-ink: #EDEFF2; --color-muted: #9AA3AF;
  --color-accent: #6366F1; --color-ok: #10B981; --color-warn: #F59E0B; --color-bad: #EF4444;
  --font-sans: ui-sans-serif, system-ui, "Segoe UI", Roboto, Arial, sans-serif;
}
body { @apply bg-base text-ink font-sans antialiased; }
```
- Interprétation visuelle (haut → bas, workspace) : topbar fine (titre +
  job + quota) ; sidebar sombre avec étapes numérotées et pastilles ;
  contenu en cartes espacées ; tableaux à en-tête discrète ; lecteurs
  audio/vidéo pleine largeur de carte ; boutons primaires indigo à
  droite des barres d action.
- Layout : sidebar `w-[260px] hidden lg:flex`, mobile `lg:hidden`
  avec nav horizontale `overflow-x-auto` ; grilles `1 → 2(sm) → 4(lg)` ;
  page détail `flex-col md:flex-row` ; timeline `overflow-x-auto`.
- Typo : H1 `text-2xl font-bold`, H2/cartes `text-base font-semibold`,
  méta `text-xs text-muted`, corps `text-sm`.
- Chaque appel API existant est conservé à la signature près ; si un
  composant a besoin d une donnée nouvelle (ex. segments pour statuts),
  elle est chargée dans `WorkspacePage`, jamais dans l UI profonde.
- Accessibilité : `focus-visible:ring-2 ring-accent` sur interactifs,
  `aria-current` sur l étape active, `alt` conservés sur images.

## Security requirements
- Aucun secret, aucun nouvel appel, aucune URL codée (inchangé)
- Upload toujours `FormData` + allowlist serveur (inchangé, juste restylé)

## Acceptance criteria
- [ ] Les 2 routes existantes fonctionnent, chaque bouton fait exactement comme avant (import, analyze, generate, review, voice, regen, render, retry, cancel, delete, export)
- [ ] Les 6 étapes affichent le bon statut (pastille) après import partiel, analyse partielle, script draft/reviewed, voix partielle, render done
- [ ] Chaque vue a ses 3 états (chargement, vide avec action, erreur avec réessai)
- [ ] Aucun scroll horizontal à 360 px ; sidebar repliée sous `lg`
- [ ] 0 hex hors tokens (`grep -r "#[0-9a-fA-F]" frontend/src` ne rend que `index.css`)
- [ ] `pytest`, `tsc`, `lint`, `build` passent

## Checks to run
```bash
pytest backend/tests -q
npx tsc --noEmit
npm run lint
npm run build
```

## Manual test steps
1. `cd frontend; npm run dev`, ouvrir `http://localhost:5173`.
2. Créer un projet (CBZ test), vérifier la carte projet + redirection.
3. Parcourir les 6 étapes : statuts corrects, squelettes au premier chargement, états vides avec actions.
4. DevTools 360 px : pas de scroll horizontal, nav étapes scrollable.
5. Tabulation clavier : focus visible sur tous les boutons/liens.
6. Build + servie par backend (`npm run build`, `http://127.0.0.1:8000`) : identique au dev.
