# SHIMIX TRADING PRESTIGE — Sécurité et passage éventuel au réel

État au 10 novembre 2026 : **SIMULATION UNIQUEMENT — NON PRÊT POUR L'ARGENT RÉEL**.

## Architecture actuelle vérifiée
- Interface statique hébergée sur Render ; le code exécuté côté navigateur est public.
- État local dans localStorage ; export complet chiffré manuel disponible ; ancien export de la démo non chiffré distinct.
- État de simulation autonome dans GitHub ; ne pas le confondre avec le stockage local.
- Aucune base PostgreSQL Render détectée lors de l'audit.
- Aucun système d'authentification serveur ni de restauration automatique validé.

## Critères impératifs avant toute transaction réelle
1. Backend dédié avec authentification serveur et sessions sécurisées (cookies HttpOnly, Secure, SameSite ; CSRF selon architecture).
2. Authentification forte via passkeys/WebAuthn, récupération de compte vérifiée, protection contre le brute force et limitation de débit.
3. Base privée et chiffrement au repos, accès minimaux, migrations contrôlées ; sauvegardes chiffrées avec tests de restauration.
4. Secrets exclusivement dans un coffre/variables serveur ; jamais dans GitHub, HTML, JavaScript client ou fichiers exportés.
5. Clés API d'exchange limitées au trading, sans droit de retrait ni transfert, idéalement IP allowlist et sous-compte dédié.
6. Moteur d'ordres serveur isolé du coach IA ; aucune commande de trading via une réponse libre du modèle.
7. Contrôles de risque exécutés côté serveur : budget par ordre, budget quotidien, exposition maximale, limites de pertes, anti-doublons, validation de solde, frais, slippage et état des marchés.
8. Arrêt d'urgence indépendant de l'IA ; état « trading réel désactivé » par défaut, nécessitant consentement explicite et vérification.
9. Journal d'audit horodaté et immuable des décisions, confirmations, erreurs et ordres ; alertes sur actions sensibles.
10. Audit de dépendances, en-têtes HTTP/CSP compatibles avec code refactorisé (pas de scripts inline), tests d'intrusion et vérification de déploiement.
11. Protection des données personnelles, durée de conservation, droit d'export et de suppression.
12. Simulation de reprise après incident : perte d'iPhone, perte de session, restauration base et réconciliation des ordres.

## Étapes de livraison
A. Sauvegarder/exporter et tester la restauration de toutes les données locales ; sauvegarder séparément l'état autonome.
B. Choisir et valider le budget d'un backend + base privée et de leurs sauvegardes.
C. Implémenter le compte privé, la synchronisation iPhone/Mac et l'authentification forte.
D. Ajouter un assistant IA via API serveur à permissions strictement pédagogiques, avec quotas.
E. Auditer puis faire une recette de sécurité documentée avant d'envisager le trading réel.

**Interdiction de considérer la PWA, l'icône installée, le fichier de sauvegarde JSON ou un badge de sécurité comme une authentification.**
