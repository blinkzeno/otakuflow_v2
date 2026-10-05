# Signaux de sur-construction (Scope Red Flags)

Quand l'utilisateur mentionne ces éléments dans son idée de MVP, les challenger systématiquement.

## 🚩 Red flags immédiats (presque toujours hors scope MVP)

| Mention | Question à poser | Alternative MVP |
|---------|-----------------|-----------------|
| "système de recommandation" | "Est-ce le cœur du produit ou un nice-to-have ?" | Affichage chronologique d'abord |
| "notifications en temps réel" | "L'utilisateur ne peut vraiment pas attendre un email ?" | Email/webhook pour commencer |
| "messagerie interne" | "Pourquoi pas WhatsApp / email entre utilisateurs ?" | Lien email mailto: pour le MVP |
| "multi-langue / i18n" | "Quel est ton marché de lancement ?" | 1 langue pour le MVP |
| "app mobile" | "L'usage est vraiment mobile ou desktop aussi ?" | PWA ou web responsive d'abord |
| "mode hors-ligne" | "À quelle fréquence l'utilisateur sera sans connexion ?" | Online-only pour le MVP |
| "analytics / dashboard admin" | "Tu as besoin de ça avant d'avoir tes premiers users ?" | Supabase dashboard direct |
| "import CSV / Excel massif" | "Combien de données pour le lancement ?" | Formulaire manuel pour le MVP |
| "API publique" | "Tu as des développeurs tiers qui en ont besoin maintenant ?" | API interne d'abord |
| "système de billing custom" | "Stripe Billing ne couvre pas le besoin ?" | Stripe Billing/Checkout |
| "vérification d'identité KYC" | "C'est légalement obligatoire pour le MVP ?" | Email seul pour commencer |
| "social features" | "C'est un réseau social ou un outil ?" | Outil d'abord, social après |

## 🟡 Yellow flags (à discuter selon le type de projet)

| Mention | Contexte où c'est OK | Contexte où c'est trop tôt |
|---------|---------------------|---------------------------|
| "rôles et permissions" | Marketplace avec vendeurs/acheteurs | SaaS B2B avec 1 type d'utilisateur |
| "historique / audit trail" | Finance, santé, compliance | Outil interne simple |
| "version premium / freemium" | Si c'est le modèle business cœur | Si c'est une "idée sympa" |
| "search" | Si c'est la feature principale | Si le contenu tient en une page |
| "dark mode" | Design system dès le début | Si pas dans la charte graphique |

## Comment challenger poliment

> "Je vois que tu mentionnes [feature X]. Pour le MVP, est-ce que ça blocquerait vraiment tes premiers utilisateurs si on l'ajoutait en v2 ? L'objectif est de lancer vite et de valider que le cœur du produit fonctionne."

## La règle des 3 questions avant d'accepter une feature

1. Est-ce que l'utilisateur principal peut accomplir sa mission principale SANS cette feature ?
2. Est-ce que cette feature double le temps de développement ?
3. Est-ce qu'on peut la simuler manuellement (par email, spreadsheet, etc.) pendant la v1 ?

Si OUI à 1 ou 3 → Out of scope MVP.
Si OUI à 2 → Challenger fortement.
