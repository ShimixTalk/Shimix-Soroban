# Protection globale en deux étapes — simulation uniquement

Le propriétaire a approuvé le 13 novembre 2026 : pause des nouveaux achats à −5 %, poursuite de la gestion des positions, liquidation fictive à −10 % puis attente d’un accord pour reprendre. Cette branche prépare ce changement ; elle ne fusionne ni ne publie le code.

## Mesure et seuils

La référence est le capital initial déjà enregistré, sans remise à zéro. Pour les 1 600 EUR du robot :

- valeur liquidable estimée ≤1 520 EUR : nouveaux achats bloqués ; stops de position, prises de bénéfices et signaux de vente restent traités ;
- valeur liquidable estimée ≤1 440 EUR : déclenchement durable de la liquidation des positions fictives aux cotations disponibles ; état désactivé et reprise soumise à accord explicite.

La valeur liquidable inclut les coûts de sortie du moteur : cash + positions × (1 − spread − glissement) × (1 − commission). Les coûts d’achat sont déjà inclus dans cash/quantités et ne sont pas déduits une deuxième fois. Ces seuils sont donc un peu plus prudents que des seuils appliqués à la seule valeur marquée. Ils se réfèrent à la mise initiale, pas au dernier sommet du portefeuille.

Au niveau −5 %, le robot reste actif pour surveiller les positions et exécuter leurs sorties. La pause peut se lever si la valeur remonte au-dessus de ce niveau lors d’un passage ultérieur. Un nouvel achat est également refusé si ses coûts feraient immédiatement franchir la limite de −5 %.

Au niveau −10 %, `globalProtection.liquidationLatched` reste vrai après la liquidation et même après un rebond. Remettre seulement `enabled=true` ne relance pas les achats. Une reprise demandera une intervention distincte, explicitement approuvée, sur l’état d’arrêt ; aucun bouton de reprise automatique n’est ajouté.

Le champ `maxLossPercent` publié par un futur passage du nouveau moteur devient 10 et `buyPauseLossPercent` vaut 5. La configuration `globalProtection` consigne la référence, le seuil, l’état de pause, le verrou de liquidation, la date de déclenchement et les actifs restant à liquider. Aucun fichier d’état actuel n’est modifié par cette PR ; ces champs n’apparaîtront en production qu’après une intégration approuvée et un passage du nouveau moteur.

## Cours absents et continuité

Une cotation absente, nulle, non finie ou invalide n’est jamais remplacée par zéro ni réutilisée depuis un ancien prix. Sans valorisation complète, aucun nouvel achat n’est autorisé et aucun franchissement global n’est inventé.

Si une liquidation est déjà déclenchée, les actifs ayant une cotation valide sont vendus fictivement et les autres restent listés dans `pendingAssets`. Les passages suivants peuvent terminer ces ventes même si `enabled=false`. Le cache de marché incomplet est rafraîchi plutôt que réutilisé pour attendre une heure de plus. Un actif déjà vendu ne l’est pas une seconde fois. Un échec réseau conserve les positions restantes et le verrou de protection.

Une valorisation incomplète est publiée comme non calculable (`value=null`, erreurs explicites). L’interface affiche le problème et conserve le dernier affichage connu avec sa date, sans afficher un faux retour à 1 600 EUR. Lorsque tous les cours sont disponibles, la valeur après vente correspond à la trésorerie nette réelle du compte fictif.

La surveillance dépend des passages planifiés, des délais et de la disponibilité des cotations. Il n’existe ni exécution continue ni prix garanti : une chute ou un gap peut dépasser la perte de 10 %. Les coûts restent des hypothèses de simulation, avant impôts, pas des tarifs réels de courtier.

## Périmètre et préservation

Les règles d’entrée RSI/moyennes, le mode de signal existant, les stops/pris de bénéfices de position et le choix des actifs ne changent pas ici. Les limites d’ordre, d’allocation et de nombre de positions restent identiques. Les expériences de réserve et de stablecoins ne sont pas activées par cette protection.

Aucun solde n’est crédité, aucun transfert historique corrigé ne devient une perte et le capital initial reste 1 600 EUR. Les opérations et points historiques existants ne sont ni effacés ni réécrits ; les troncatures au fil des nouvelles sauvegardes sont retirées pour préserver l’historique. Les nouvelles ventes de sécurité portent le motif `global-loss-liquidation` et les frais d’exécution. Les garde-fous de simulation restent obligatoires.

## Validation locale

- 32 tests moteur, dont 15 nouveaux sur les seuils exacts, les coûts, les sorties maintenues à −5 %, les ventes à −10 %, les cours absents/invalides, les reprises partielles sans doublons et le verrou d’arrêt ;
- 41 tests learning, dont le contrôle de transition exacte du moteur ;
- 3 nouveaux tests Chromium d’affichage de protection, de valorisation incomplète et d’absence de fausse activation sur un ancien état ;
- 11 régressions Chromium sécurité/sauvegardes et 10 du tableau de bord ;
- total : **97 tests locaux réussis** ; reproduction exacte des trois études historiques gelées ; contrôle d’intégrité du collecteur, compilation et diff sans erreur.

Le contrôle d’intégration continue d’exiger des données protégées identiques octet pour octet. L’unique exception est la transition du moteur original SHA-256 `7dee49c3618ea2cb9a15c9e13517216cbbd066bcebb79f8d8d1f06fd906e33ea` vers le moteur testé `e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a`. Une autre modification du moteur ou des états reste refusée. La base exacte contrôlée est `419423677e965c92d0bf12488d2daf7559b4d220`.

Les tests utilisent des états artificiels, appels GitHub/marché remplacés et navigateur sans réseau métier. Ils prouvent le fonctionnement de la protection, pas sa supériorité économique ni une limite de perte garantie.

## Intégration à revoir

Cette PR cible directement `shimix-hub` pour isoler la protection prioritaire des expériences encore ouvertes. Les PR #8/#10/#13 touchent aussi le moteur ou l’interface/les contrôles ; leur intégration conjointe doit être revalidée, notamment le contexte de décision pour les nouvelles ventes de sécurité. Aucun contrôle antérieur de compatibilité n’est présenté comme validant cette nouvelle version.

Les plans de recherche #12/#14/#15 sont gelés sur l’ancienne configuration de risque. Après activation de cette protection, ils doivent signaler une configuration source modifiée et suspendre leurs comparaisons plutôt que mélanger silencieusement les régimes. Une nouvelle version de protocole sera nécessaire pour comparer proprement la protection à l’ancien témoin, sans retoucher les anciens résultats.

Aucun workflow métier, nouvelle dépense ou service n’est lancé. Fusion, déploiement et reprise après arrêt nécessitent les accords explicites prévus par le propriétaire.
