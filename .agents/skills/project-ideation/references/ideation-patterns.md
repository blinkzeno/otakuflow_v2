# Patterns d'idéation par type de projet

## SaaS B2B (outil professionnel)
**Questions clés :**
- Qui paie ? (acheteur ≠ utilisateur final dans B2B)
- Quel est le workflow actuel sans cet outil ? (Excel ? email ? rien ?)
- Combien d'utilisateurs par compte client ?
- Y a-t-il un rôle admin vs utilisateur standard ?

**Out of scope typique :**
- Facturation / gestion abonnement (utiliser Stripe Billing en SaaS)
- Mobile app (desktop d'abord)
- Import/export massif de données (v2)
- API publique pour intégrations tierces (v2)

---

## Marketplace (acheteurs + vendeurs)
**Questions clés :**
- Qui arrive en premier : acheteurs ou vendeurs ? (problème de chicken-and-egg)
- Modèle de commission ou abonnement ?
- Le paiement passe par la plateforme ou hors plateforme ?
- Vérification d'identité requise ?

**Out of scope typique :**
- Messagerie interne entre users (utiliser email d'abord)
- Système d'avis et notation (v2)
- Gestion des litiges (v2)
- App mobile (web d'abord)

---

## Outil interne (usage entreprise unique)
**Questions clés :**
- Combien d'utilisateurs simultanés max ?
- Accès internet ou intranet seulement ?
- Données sensibles ? (PII, financières, médicales)
- SSO entreprise nécessaire ? (LDAP, Azure AD, Okta)

**Out of scope typique :**
- Multi-tenant (un seul client = l'entreprise)
- Scalabilité massive (audience connue et bornée)
- Internationalisation i18n (une seule langue en général)

---

## App mobile (iOS/Android)
**Questions clés :**
- iOS seulement, Android seulement, ou cross-platform ?
- Offline first nécessaire ? (données disponibles sans connexion)
- Notifications push requises ?
- App Store review acceptable (2-3 semaines) ou déploiement direct ?

**Out of scope typique :**
- Web version (mobile d'abord, web peut attendre)
- Admin dashboard (separate product)
- Analytics intégrées (utiliser Mixpanel/Amplitude externe)

---

## API / Outil développeur
**Questions clés :**
- REST ou GraphQL ou tRPC ?
- Authentication : API keys, OAuth, JWT ?
- Rate limiting nécessaire dès le MVP ?
- Documentation interactive (Swagger/OpenAPI) requise ?

**Out of scope typique :**
- Dashboard UI (doc d'abord)
- SDK multi-langage (1 langage d'abord)
- Webhooks (v2)

---

## Site éditorial / News / Blog
**Questions clés :**
- Qui écrit le contenu ? (équipe interne, contributeurs, AI, scraping)
- Fréquence de publication ?
- Monétisation : pubs, paywall, abonnement ?
- SEO critique ? (contenu indexable par Google)

**Out of scope typique :**
- Commentaires utilisateurs
- Système de newsletter intégré (utiliser Mailchimp/Resend externe)
- Version mobile app
