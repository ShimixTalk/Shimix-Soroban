# Compte privé et synchronisation — livraison de développement

Branche : `feature/private-passkeys-sync-20261110`, issue de `shimix-hub` au commit `1b3340fc6debf48fab4e993eafd0b5b21735c668`.

La connexion par passkey, le serveur de sessions, le coffre chiffré, l'import de sauvegarde et la synchronisation avec conflits sont implémentés. La conception précédente envisageait OIDC ; cette variante utilise WebAuthn directement pour un propriétaire unique, sans fournisseur d'identité tiers. Un serveur et une base PostgreSQL durables restent nécessaires.

**Aucun service créé, aucune fusion ni activation, aucune donnée de production modifiée.** La nouvelle page ne peut pas fonctionner sur l'actuel site statique sans backend configuré. L'application en ligne actuelle reste conservée.

Validation locale : tests de serveur, tests navigateur avec authentificateurs virtuels, régressions Python et sauvegardes navigateur. La CI ajoute PostgreSQL éphémère afin de tester le stockage cible. Les résultats précis et le statut distant figurent dans la pull request ; ne pas confondre des tests locaux SQLite avec une preuve d'exploitation PostgreSQL.

Avant toute activation : budget et hébergement, origine définitive, secrets, sauvegardes PostgreSQL restaurables, passkey de secours, validation de révocation individuelle et recette iPhone/Mac. Les risques détaillés et commandes sont dans `private-server/README.md`. Ni Face ID seul ni une passkey ne récupère un mot de passe de chiffrement perdu. La synchronisation est active seulement tant que le portail est ouvert et déverrouillé ; aucune promesse d'exécution en arrière-plan sur iOS.
