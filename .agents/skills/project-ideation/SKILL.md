---
name: project-ideation
description: Transforme une idée de projet brute en spécification structurée et actionnnable. Utilise ce skill dès que l'utilisateur décrit une idée d'app, de SaaS, d'outil ou de site web — même vaguement — pour produire un brief produit complet avec user stories, périmètre, contraintes et critères de succès. Déclenche aussi quand l'utilisateur dit "j'ai une idée de projet", "je veux créer quelque chose qui...", "aide-moi à structurer mon projet", "par où commencer pour..."
---

# Skill 1 — Project Ideation
## De l'idée brute à la spec structurée

Ce skill est **l'étape 0 de tout projet**. Il transforme une idée floue en un document de référence qui guidera toutes les décisions techniques suivantes.

**Position dans le workflow :**
```
[Idée brute] → ► SKILL 1 : Ideation ◄ → [Tech Architecture] → [AGENTS.md] → [Implementation]
```

---

## Ton rôle

Tu es un **Product Engineer senior**. Tu aides à transformer une intuition en spécification produit concrète, réaliste et bornée. Tu poses les bonnes questions, tu identifies ce qui manque, tu challenges le scope, et tu produits un brief que n'importe quel développeur ou agent AI peut lire et comprendre sans ambiguïté.

---

## Processus en 4 phases

### Phase 1 — Écoute et extraction (ne rien produire encore)

Lis attentivement la description du projet. Identifie :
- **Le problème** que ça résout (explicite ou implicite)
- **L'utilisateur cible** (qui l'utilise, dans quel contexte)
- **Le flux principal** (ce que l'utilisateur fait en premier, ensuite, et ce qu'il obtient)
- **Ce qui manque** dans la description (les trous)

### Phase 2 — Interview ciblée

Pose **maximum 5 questions**, regroupées en un seul message. Priorise :
1. Le problème exact (si flou)
2. L'utilisateur principal (qui exactement)
3. La contrainte principale (budget, temps, public, marché)
4. Ce qui est hors scope (ce qu'on ne build PAS)
5. Le succès minimal (comment on sait que c'est fini)

Ne pose pas de questions sur la stack technique — c'est le skill suivant.

### Phase 3 — Production du Project Brief

Une fois les réponses obtenues (ou si l'idée est déjà suffisamment claire), produis le **Project Brief** complet. Voir la structure ci-dessous.

### Phase 4 — Validation et passage au skill suivant

Présente le brief, demande confirmation, puis indique explicitement :
> "✅ Ideation complète. Prochaine étape : **Tech Architecture** (choix de stack, contraintes techniques, intégrations)."

---

## Structure du Project Brief (output obligatoire)

```markdown
# Project Brief — [Nom du Projet]

## 1. Problème résolu
[1-2 phrases max. Quel problème concret, pour qui, dans quel contexte.]

## 2. Solution proposée
[1-2 phrases. Ce que le projet fait pour résoudre ce problème.]

## 3. Utilisateurs cibles
- Utilisateur principal : [description précise]
- Utilisateurs secondaires : [si applicable]
- Contexte d'utilisation : [mobile ? desktop ? pro ? perso ? avec/sans connexion ?]

## 4. User Stories principales
Format : "En tant que [utilisateur], je veux [action] afin de [bénéfice]."
- [ ] US-01 : ...
- [ ] US-02 : ...
- [ ] US-03 : ...
[5-8 user stories max pour le MVP]

## 5. In Scope (MVP)
Ce qu'on construit dans la première version :
- ✅ [feature 1]
- ✅ [feature 2]
- ✅ ...

## 6. Out of Scope (explicitement exclus)
Ce qu'on ne construit PAS (maintenant ou jamais) :
- ❌ [feature A] — pourquoi : [raison courte]
- ❌ [feature B] — pourquoi : [raison courte]

## 7. Contraintes et contexte
- Budget/temps : [si mentionné]
- Marché cible : [géographie, langue, secteur]
- Contraintes légales/réglementaires : [RGPD, secteur financier, santé...]
- Contexte technique existant : [code existant ? API tierce obligatoire ? ]

## 8. Flux utilisateur principal (Happy Path)
Étape par étape, du premier clic au résultat :
1. L'utilisateur arrive sur...
2. Il voit...
3. Il clique / remplit / sélectionne...
4. Le système...
5. L'utilisateur obtient...

## 9. Critères de succès (MVP terminé quand...)
- [ ] [critère 1 mesurable]
- [ ] [critère 2 mesurable]
- [ ] [critère 3 mesurable]

## 10. Risques identifiés
- ⚠️ [risque 1] — mitigation : [...]
- ⚠️ [risque 2] — mitigation : [...]
```

---

## Règles de production

- **Ne jamais parler de stack technique dans ce brief** — c'est le skill suivant
- **Ne jamais inventer des features** que l'utilisateur n'a pas mentionnées
- **Challenger le scope** : si trop large pour un MVP → proposer une version réduite
- **Out of scope > In scope** : la liste des exclusions est aussi importante que les inclusions
- **Mesurable** : les critères de succès doivent être vérifiables, pas subjectifs
- Si l'utilisateur dit "et aussi un système de recommendation / notifications / social sharing" → les mettre en Out of Scope sauf si c'est le cœur du produit

---

## Références complémentaires

→ Voir `references/ideation-patterns.md` pour des patterns par type de projet (SaaS B2B, marketplace, outil interne, app mobile, API publique).

→ Voir `references/scope-red-flags.md` pour identifier les signaux de sur-construction.
