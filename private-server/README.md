# Compte privé SHIMIX — implémentation à tester avant activation

Ce code n'est pas déployé. Il ne crée aucun service Render et ne modifie pas les comptes ni les données de l'application existante. Aucun ordre réel, banque, exchange ou fournisseur d'IA n'est intégré.

## Ce qui est construit

- Serveur Node 24, authentification WebAuthn avec `@simplewebauthn/server` épinglé, présence et vérification utilisateur obligatoires. Inscription unique du propriétaire avec un secret de démarrage ; secret inutilisable pour contourner une passkey après inscription.
- Passkeys supplémentaires après authentification récente. Sessions aléatoires, tokens et CSRF stockés sous forme d'empreintes, cookies HttpOnly/Secure/SameSite=Strict en HTTPS, expiration après 30 minutes d'inactivité et 12 heures absolues.
- Déconnexion, révocation des autres sessions et retrait individuel de passkey avec protection de la dernière clé. Origine exacte, protection CSRF, limitation de tentatives, corps limités, réponses sans cache et anti-iframe. Le proxy n'est pas autorisé à fournir une adresse IP arbitraire ; derrière un proxy partagé la limite peut affecter tous les appareils du propriétaire.
- Coffre de sauvegardes chiffrées par le navigateur : AES-256-GCM et PBKDF2-SHA256 600 000 itérations. Import des sauvegardes 250 000 itérations existantes ; restauration des nouvelles sauvegardes dans l'application grâce à la compatibilité ajoutée. Le serveur ne reçoit pas le mot de passe ni les données en clair.
- Révisions optimistes, clés d'idempotence et transaction SQL ; pas de règle « dernier appareil gagnant ». Historique conservé, quota provisoire de 50 Mio bloquant les nouvelles sauvegardes lorsqu'il est atteint, sans effacement automatique.
- Synchronisation explicite depuis le portail ouvert et déverrouillé ; option automatique, avec détection des changements entre onglets/appareils. En cas de deux modifications concurrentes, arrêt et choix utilisateur. Pas de synchronisation garantie si Safari suspend l'onglet ou si le téléphone est verrouillé.
- L'application de simulation existante est servie par le serveur privé après connexion, sans réécriture de son moteur. Le lien l'ouvre dans un onglet séparé pour laisser le portail de synchronisation ouvert. Le service worker n'est pas servi par le backend privé : aucune promesse de mode privé hors ligne.

## Démarrage local

Depuis `private-server/`, `npm ci --ignore-scripts`, puis définir `SHIMIX_ORIGIN=http://localhost:3000`, `SHIMIX_SQLITE_FILE` vers un fichier local hors Git et un `SHIMIX_BOOTSTRAP_TOKEN` aléatoire. Lancer `npm start`, ouvrir `http://localhost:3000/private/index.html`, saisir le code d'installation et créer une passkey. Ne pas utiliser les secrets des fixtures de test.

SQLite est limité au développement. Le démarrage en production refuse SQLite et exige PostgreSQL durable. Pour la base de production, l'URL doit demander `sslmode=verify-full`, avec une CA de confiance. Ne jamais désactiver la vérification TLS.

## Mise en service : décisions et conditions

1. Valider un hébergement Node et PostgreSQL durable, leur région, budget, rétention, sauvegardes et surveillance. Ne pas choisir une base gratuite expirante pour les seules copies d'un compte privé. Aucun service n'a été provisionné par ce travail.
2. Choisir l'origine HTTPS définitive avant la première inscription. Les passkeys créées sur localhost sont des passkeys de test. Celles de `shimix-hub.onrender.com` ne peuvent pas être transférées implicitement vers un autre domaine.
3. L'actuel hébergement Render est statique et ne peut pas exécuter ce backend. Prévoir un service adapté ou un proxy sur un domaine stable ; ne pas modifier automatiquement l'application actuelle. Les deux origines ne partagent pas localStorage : exporter/importer les sauvegardes chiffrées explicitement lors de la migration.
4. Saisir les secrets dans le gestionnaire de secrets du service, jamais dans Git ni dans le chat. Vérifier les droits SQL minimaux, les en-têtes à travers le proxy et les délais de session. Une seule instance au départ ; la limitation de débit en mémoire doit devenir partagée avant multiplication des instances.
5. Définir et tester les sauvegardes PostgreSQL hors service, leurs clés, leur restauration et les alertes. L'historique du coffre n'est pas une sauvegarde indépendante de la base. Le serveur ne peut pas récupérer un mot de passe de chiffrement oublié.
6. Créer une passkey de secours, conserver une copie chiffrée externe, puis tester perte d'appareil et révocation. Il n'existe pas de récupération par email, ni de réinitialisation secrète contournant les passkeys. La page permet de retirer une passkey après une connexion récente, en conservant au moins une autre clé ; le retrait déconnecte les autres sessions. Tester ce parcours et la possession de la clé de secours sur les vrais appareils.
7. Tester sur Safari iOS/macOS réels Face ID/Touch ID/code, passkeys iCloud, nouvelle session, conflits, arrière-plan et retour d'une coupure réseau. Les tests livrés utilisent Chromium et des authentificateurs virtuels, pas de vrais appareils Apple.
8. Faire une revue de sécurité avant migration de données privées. La simulation historique conserve des scripts inline et sa CSP transitoire ; elle n'est pas refactorisée intégralement par ce changement. Le compte est unique, pas multitenant. Aucune RLS multiutilisateur n'est revendiquée.

## Conservation et limites

L'application publique et ses données ne sont jamais supprimées lors de l'import. Une restauration remplace uniquement les rubriques correspondantes après confirmation. localStorage n'offre pas de transaction durable en cas de panne ou quota pendant un rollback : conserver les sauvegardes originales. Les données déchiffrées de simulation restent en clair dans le navigateur après déconnexion, comme dans l'application actuelle ; se déconnecter retire l'accès serveur, pas les données de l'appareil. Ne pas utiliser un appareil partagé pour des données privées. La clé de chiffrement en mémoire reste accessible au code de la page : une XSS compromettrait cette protection. La nouvelle page utilise une CSP sans scripts inline ; l'application historique demande une revue supplémentaire avant des données sensibles.

Le coffre protège la confidentialité du contenu côté serveur, pas les métadonnées (dates, tailles, versions) ni une restauration malveillante d'un ancien snapshot par un administrateur de base. L'intégrité GCM est vérifiée par le client ; le serveur valide l'enveloppe sans pouvoir certifier le contenu chiffré. Les pages ne proposent aucune route d'ordre réel.

## Vérification

- `npm test` : contrôles HTTP, CSRF/origine, expiration, challenge unique, inscription propriétaire atomique, conflits et idempotence. SQLite local ; le test PostgreSQL est ignoré si son URL de test dédiée manque.
- `SHIMIX_TEST_DATABASE_URL=... node --test tests/postgres.test.mjs` : uniquement base jetable `shimix_private_test` sur localhost. Vérifie concurrence et persistance PostgreSQL. La CI fournit cette base en service éphémère.
- Depuis la racine : `SHIMIX_CHROMIUM=/usr/bin/chromium python3 tests/private_browser.py` : cérémonies cryptographiques WebAuthn réelles avec authentificateurs virtuels, deux contextes isolés, synchronisation, refus de signature altérée et de replay, mauvais mot de passe et restauration dans l'application.
- Les régressions existantes Python et navigateur restent applicables. `npm audit --omit=dev` vérifie les avis connus des dépendances ; ce n'est pas une preuve de sécurité complète.
