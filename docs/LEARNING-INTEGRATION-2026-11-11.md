# Préparation d’activation de l’apprentissage — 11 novembre 2026

## État de livraison

PR #4 (`shimix-hub`) et PR #5 (`main`) restent en brouillon, sans fusion ni déploiement. L’accord final du propriétaire est attendu après les vérifications. Aucun nouveau service, abonnement, appel OpenAI ou opération réelle n’a été activé.

## Compatibilité avec l’application actuelle

Les différences récentes de production portent uniquement sur `robot-state.json`, `scanner-state.json` et `three-portfolios.json`, mis à jour par les automatisations existantes. Aucun conflit de code avec la PR #4 n’a été trouvé.

Une intégration locale isolée a été construite à partir de la PR #4 et de la base `52a2a9d961e008597f6a0ac0c0cfbf36a2c11efe`, sans déplacer `shimix-hub` ni `main`. Les quatre fichiers de données existants, les deux moteurs Python, le validateur de sécurité, le manifeste et l’icône sont vérifiés octet par octet contre la base. Le capital de 1 600 €, les trois profils et les drapeaux « simulation uniquement » sont vérifiés.

La CI de la PR #4 prépare désormais elle-même une intégration éphémère avec la dernière version de `shimix-hub`, puis vérifie ces invariants. Elle ne publie jamais cette intégration et ne pousse aucun fichier de données. Les automatisations de production continuent de modifier leurs données indépendamment : les empreintes sont donc rattachées à la référence exacte vérifiée, pas présentées comme un gel de la production.

## Vérifications et corrections supplémentaires

- 40 tests unitaires : 32 contrôles d’apprentissage existants, 6 contrôles de sauvegarde/restauration et 2 contrôles transactionnels Git.
- 17 tests existants du robot ; 11 tests de sauvegarde chiffrée ; 5 tests du tableau de bord.
- 4 tests WebKit aux profils iPhone et Mac : affichage, dimensions du panneau, navigation existante, actualisation, export et absence de modification du stockage local.
- Total : **77 tests**, plus vérification des fichiers protégés, prévisualisation du collecteur sans réseau, reproduction exacte des résultats historiques et restauration d’un instantané complet.

Les tests WebKit utilisent le moteur de navigateur et une origine HTTPS de test servie depuis les fichiers locaux. Ils ne constituent pas un essai matériel sur un vrai iPhone ou Mac. Une recette sur les appareils du propriétaire restera souhaitable après le déploiement autorisé.

La protection des écritures concurrentes du collecteur a été renforcée : l’empreinte des fichiers de journal est contrôlée dans l’arbre exact du commit parent avant construction de la transaction Git. Ainsi, une mise à jour survenue après le premier contrôle ne peut pas être écrasée silencieusement. Les modifications d’autres fichiers du robot sont conservées dans l’arbre de base ; aucune force-push n’est utilisée.

## Sauvegardes réellement vérifiées

La tâche existante `42963253476` du 11 novembre a réussi. Son archive `shimix-robot-backup-42963253476` (artefact `13829579420`, 37 531 octets) a été téléchargée, décodée et vérifiée en lecture seule. Empreinte du fichier robot restauré :

`fad6387c784fedc3dc7117eda00edd065a364ca337220c3a4e02a81a69177b5b`

Le capital vaut 1 600 €, le trading réel et la connexion exchange sont désactivés. Aucun fichier de production n’a été remplacé.

Un utilitaire `learning/backup.py` crée et restaure une copie des quatre fichiers d’état et de tous les fichiers d’apprentissage. Le manifeste contient les tailles et SHA-256 ; les liens symboliques, chemins sortants, contenus inattendus et dossiers de restauration existants sont refusés. Le contrôle local a restauré 14 fichiers, environ 555 Ko, à l’identique.

Cette répétition de restauration est ajoutée **avant chaque collecte**, uniquement dans les dossiers temporaires du runner. Elle n’ajoute aucun téléversement d’artefact ni stockage cloud facturable. Les journaux restent versionnés dans Git ; une sauvegarde distante indépendante et complète de l’apprentissage n’est pas créée par ce mécanisme. La sauvegarde GitHub existante couvre toujours le robot, avec sa rétention actuelle. Les sauvegardes locales chiffrées existantes restent inchangées.

## Planification, permissions et absence de frais nouveaux

Le workflow proposé sur `main` conserve `cron: '19,49 * * * *'`, soit deux déclenchements par heure en UTC. GitHub peut les retarder ; il s’exécute sans navigateur ouvert. Le job est bloqué sur les branches de développement. Les permissions sont en lecture au niveau du workflow, en écriture de contenu uniquement pour l’observateur, sans secrets persistés au checkout. Aucune action de fusion, modification de secrets ou API d’exchange n’est implémentée. Le droit GitHub `contents: write` reste large : la restriction aux fichiers d’apprentissage est un contrôle du code, pas une ACL de fichiers imposée par GitHub. Les règles de protection des branches n’ont pas été modifiées.

Le programme de collecte n’autorise des écritures que sous `hub/trading/learning-data/`. Les tests, la vérification d’intégrité et la répétition de restauration précèdent toute écriture. Les appels OpenAI restent absents du programme et le budget vaut 0 USD.

Aucun service Render supplémentaire n’est créé. Les seuls coûts potentiels restent les quotas/conditions des services existants : aucun nouvel abonnement ni stockage cloud supplémentaire n’est engagé par ces préparatifs.

## Render et production observée

Le service existant `shimix-hub` est un site statique, publication `hub`, branche `shimix-hub`, auto-déploiement sur commit, previews désactivées. Le déploiement `dep-dbpvjncs728c738t0po0`, commit `0feffd1b1d2b368c40249e3af3b151d2ea24c1b0`, était `live` lors du contrôle et la page publique répondait HTTP 200.

Ce déploiement vient du scanner déjà planifié, pas de nos changements. La rubrique d’apprentissage n’est pas encore présente sur le site en ligne. Aucun déploiement n’a été déclenché par cette préparation. Le marqueur `[skip render]` des futurs commits d’observation est documenté par Render pour éviter les redéploiements de données ; son effet réel sera vérifié à la première collecte autorisée.

## Réserve de sécurité préexistante à lever avant activation complète

Le contrôle HTTP de production déjà présent dans `main` a été exécuté en lecture seule : 5 contrôles passent et 2 échouent (`Frame protection`, `Referrer policy`). Il n’existe pas encore d’exécution GitHub enregistrée pour ces workflows de contrôle dans les métadonnées consultées ; ce résultat est celui de leur code exécuté localement contre la vraie page publiée. Les tests de la PR ne doivent pas être confondus avec ce contrôle de production.

Les en-têtes `X-Frame-Options` et `Referrer-Policy` ne sont pas fournis par le site actuel. HTTPS/HSTS et anti-sniffing sont présents. Ce défaut précède l’apprentissage et n’est pas corrigé par un simple fichier `_headers` dans ce dépôt.

La proposition `ops/render-security-headers.json` décrit deux réglages natifs à appliquer au **service Render existant**, sans création de service : chemin `/trading/*`, `X-Frame-Options: DENY`, `Referrer-Policy: strict-origin-when-cross-origin`. Il s’agit d’une spécification de revue, pas d’un programme d’application automatique. Ces valeurs sont également utilisées dans les essais WebKit locaux pour vérifier qu’elles ne cassent pas le tableau de bord.

Aucun réglage Render n’a été modifié. Après accord, configurer ces deux en-têtes dans les réglages du site statique et réexécuter le contrôle HTTP : il devra passer avant la mise en production de l’apprentissage. Le site restera public ; ces en-têtes ne créent pas de compte privé.

## Ordre d’activation après accord explicite

1. Appliquer les deux réglages HTTP Render proposés après accord et exiger un contrôle de production entièrement réussi. Relever les deux commits approuvés et confirmer leurs tests GitHub réussis ; contrôler l’absence de nouveau conflit et de modification du moteur ou des risques.
2. Fusionner la PR #4 dans `shimix-hub`, en conservant les données courantes de la branche cible. Surveiller Render jusqu’au statut `live` puis vérifier la page publiée et ses nouvelles ressources.
3. Vérifier sur iPhone et Mac réels l’accès à l’onglet et l’export, sans import ou réinitialisation de données personnelles. Le test peut utiliser un profil de navigateur séparé.
4. Fusionner ensuite la PR #5 dans `main`. Déclencher une première collecte explicitement autorisée, puis vérifier le succès de la tâche, les permissions, les curseurs, les lignes de journal, les rapports et l’absence de modification des fichiers de trading.
5. Vérifier l’absence de déploiement Render pour le seul commit de données, puis observer une exécution planifiée sans application ouverte. Aucun candidat n’est promu : les hypothèses historiques restent non confirmées et les données futures sont encore attendues.

**Code d’apprentissage prêt et tests de PR réussis ; activation complète encore suspendue** aux deux réglages HTTP préexistants et à l’accord du propriétaire. Le système n’est pas déjà opérationnel en production. La collecte réelle, son premier journal et la recette du déploiement final ne peuvent pas être déclarés réussis tant que les PR n’ont pas été approuvées puis intégrées.
