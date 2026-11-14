# Challenge pédagogique parallèle

Un second compte de simulation démarre prospectivement avec une référence indépendante de 1 600 EUR. Il ne reçoit aucun transfert du robot, ne copie pas ses positions déjà ouvertes et ne rejoue pas ses gains passés. Le compte principal, ses historiques et ses protections restent inchangés.

Le collecteur existant utilise les observations du journal : aucun fournisseur, clé, abonnement, service ou téléchargement supplémentaire. Un signal est placé en attente puis exécuté au prix du relevé suivant, uniquement si le signal a au plus une heure et si les cours de ce relevé sont confirmés récents. Le démarrage enregistre seulement le dernier signal disponible, sans opération immédiate. Deux commits ayant le même horodatage ne produisent pas deux décisions.

## Règles gelées de la version pédagogique v1

- Objectif net après coûts de sortie : +8 %, avec au moins cinq dates distinctes comportant des opérations.
- Perte maximale journalière : 3 % des 1 600 EUR, mesurée depuis la dernière valorisation nette observée du jour précédent (Europe/Paris).
- Perte totale maximale : 6 % des 1 600 EUR de départ.
- Au plus quatre positions distinctes, 120 EUR par achat ; aucun renforcement d’une position déjà détenue ; délai d’un jour entre achats du même actif.
- Commission 0,1 %, spread 0,1 %, glissement 0,1 % à chaque côté, avec coût de sortie dans la valeur nette.
- Stop de prix −4 % et prise de bénéfice +8 %, signal de vente provenant de la précédente observation ; aucun rachat dans le passage d’une sortie.
- Franchissement d’une limite : liquidation fictive aux prix observés, état d’échec verrouillé. Aucun redémarrage automatique. Atteinte de l’objectif : clôture fictive et arrêt pédagogique.

Ces règles ne sont celles d’aucune prop firm commerciale. Ce résultat n’ouvre aucun compte et ne donne droit à aucun paiement. Il ne s’agit pas d’un capital supplémentaire dans le total du robot.

## Limites explicites

La valeur journalière de référence est une approximation au dernier relevé connu, pas un prix exactement à minuit. Les dépassements entre relevés ne peuvent pas être exclus. Un cours détenu manquant ou ancien interdit les opérations et laisse la valeur inconnue ; un changement de jour après une clôture inconnue exige une revue. Les signaux trop anciens sont abandonnés. Les deux comptes partagent les mêmes analyses et ne constituent pas deux expériences indépendantes. La fréquence dépend du collecteur existant et de GitHub Actions. Les stratégies peuvent diverger du compte principal du fait des limites, du démarrage prospectif et de l’exécution au relevé suivant.

## Données et affichage

`learning/challenge.py` n’effectue aucun accès réseau ni écriture directe. `learning/collect.py` publie l’état dans `hub/trading/learning-data/parallel-challenge.json` et le rapport existant, par transaction atomique contrôlée. Les opérations du challenge sont conservées sans troncature dans son propre état. La sauvegarde existante inclut tous les fichiers learning-data. L’état et les règles figurent dans l’onglet Apprentissage, avec les anomalies et la date du dernier relevé. Aucun changement du stockage du navigateur.

Les tests vérifient le démarrage sans historique inventé, les frais, la séparation des comptes, les signaux décalés, la répétition idempotente, les cours manquants/anciens, les limites et verrouillages, le calendrier, les règles immuables, les données corrompues, la transaction du collecteur et l’affichage sans HTML injecté. Le contrôle d’intégration confirme les empreintes du moteur autonome et des fichiers financiers inchangées.

## Collecteur planifié et clonage superficiel

Le collecteur échouait avant toute collecte depuis l’intégration #17 : son test de garde demandait via `git show` un commit absent d’un checkout superficiel. Une fixture locale du moteur antérieur, issue du commit 568f9f6694b57f24e038e89cc5bcaadf1dce687d et vérifiée par SHA-256 e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a, remplace cette dépendance à l’historique Git. La garde continue de vérifier la transition exacte et de refuser une modification du seuil ; aucun contrôle n’est supprimé. Ce fichier texte n’est jamais exécuté par le robot.

## Disponibilité effective du signal

`pendingAvailableAt` est l’heure de collecte rendant l’intention disponible au challenge. Un achat exige un relevé strictement postérieur à cette heure, en plus d’un signal source vieux d’au plus une heure. Une collecte de plusieurs événements anciens ne crée donc aucune opération antérieure à la connaissance effective du signal. Les deux heures sont conservées dans l’achat fictif. La migration depuis le premier état ne change ni soldes ni positions ni opérations : elle vide uniquement les intentions sans disponibilité enregistrée et ajoute les métadonnées d’activation.
