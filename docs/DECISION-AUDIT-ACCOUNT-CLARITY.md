# Décisions traçables et comptes distincts

Évolution demandée le 12 novembre 2026 : expliquer les décisions et rendre les deux ensembles de simulations lisibles. Elle dépend du suivi de rigueur #11 et de la correction #8. Aucune fusion ni publication n’est réalisée.

## Métadonnées de décision

Le moteur ajoute aux nouvelles opérations seulement un objet `decision` capturé avant mutation des soldes/positions : horodatage du passage, règle déclenchée, cours indicatif, référence d’entrée pour les sorties, trésorerie et quantité avant opération, date du cache de cotation, mode, coûts et limites en vigueur.

Pour les signaux exploitables, `decisionContext` conserve les indicateurs sans leur arrondi d’affichage : RSI, SMA7, SMA21, SMA21 précédente, deux derniers cours clôturés disponibles et horodatage de collecte de l’historique. Aucune date de clôture inconnue n’est inventée. La règle distingue le signal strict du rebond agressif. Les nouvelles ventes conservent leur motif existant (stop-loss, take-profit ou signal) et leur référence d’entrée.

Les signaux précisent l’issue : achat ou vente exécutés, délai par actif, limite de positions, limite d’historique, montant/allocation insuffisant, arrêt global ou non-sélection. Les signaux non parcourus après le premier achat restent « non sélectionnés » : aucun motif de blocage précis n’est inventé pour eux. L’absence d’historique garde son message existant.

L’horodatage correspond au passage du moteur. Il ne prétend pas fournir une résolution temporelle plus fine que la source. Ces métadonnées servent à l’audit, jamais à choisir un ordre.

Le collecteur conserve une sélection bornée de champs dans les nouveaux événements. Les champs inconnus et nombres non finis sont exclus. Un contexte invalide est signalé sans supprimer l’opération. Le contexte ne participe pas à l’identifiant des opérations, pour éviter les doublons lorsque des métadonnées supplémentaires sont collectées. Les opérations et événements historiques ne sont pas enrichis rétroactivement. Les nouvelles opérations d’achat ont un motif stable dès leur création.

Le rapport de rigueur affiche les dix derniers motifs, avec les indicateurs disponibles. Pour une opération ancienne sans contexte, il affiche explicitement son absence ; il ne reconstruit pas l’explication depuis un signal observé après coup.

## Comptes et coûts

- La vue du robot rappelle sa référence indépendante de 1 600 EUR fictifs.
- La vue des profils distingue référence historique, flux nets, capital après transferts, valeur et variation hors transferts.
- Avec le registre audité, le capital après transferts est de 560/480/360 EUR, soit 1 400 EUR. Les −200 EUR sont des flux, jamais des pertes de trading.
- Un transfert absent du rapport est « non calculable », sans hypothèse implicite de zéro.
- La variation publiée des profils est avant liquidation des positions et avant impôts ; les frais futurs de sortie ne sont pas présentés comme déjà déduits.
- Les capitaux et résultats des deux ensembles ne s’additionnent pas dans la performance du robot.

## Preuves de comportement inchangé

Les ajouts du moteur sont des blocs d’instrumentation délimités. Leur suppression reproduit octet pour octet le moteur de base. Le contrôle d’intégration n’accepte que l’empreinte exacte du moteur audité (`a6c7702be7b95e5faabfde1719cf392db1452b2072145c5c060571594eb99bef`) et exige cette identité de logique après retrait des blocs ; des blocs arbitraires ou toute autre modification restent refusés.

Un test différentiel exécute l’ancien moteur et le moteur instrumenté avec horloge fixe et GitHub/marché interceptés, dans dix scénarios : achat strict, achat agressif, stop-loss, take-profit, arrêt global, cours détenu absent, marché invalide, cooldown, limite de positions et allocation nulle. Après exclusion des nouvelles métadonnées, les états complets sont identiques, y compris montants, frais, ordres, indicateurs, soldes, historiques, suspensions et risques.

Validation locale :
- 23 tests moteur (dont six nouveaux, comprenant le test différentiel sur dix scénarios) ;
- 67 tests learning (dont quatre nouveaux sur la conservation et la validation des contextes) ;
- 14 tests Chromium (dont deux nouveaux sur séparation des comptes, transferts inconnus et contexte historique absent) ;
- contrôle d’intégrité et collecteur en lecture seule, reproduction exacte des trois études gelées, syntaxe JS et diff sans erreur.

Les données et moteurs protégés, sauf le seul fichier moteur instrumenté explicitement audité, restent identiques. Aucun état de portefeuille, fichier de données ou journal vivant n’est modifié par cette branche. Les comparaisons et tests se font sur des copies et sans réseau métier.

Les modifications devront encore être validées ensemble avec les PR d’interface et de simulation complémentaires avant intégration. La stratégie, les seuils, les montants, le capital et les tâches planifiées ne sont pas changés. Une modification du code moteur pour ajouter des métadonnées ne constitue pas une autorisation de changer ses règles de trading.

## Compatibilité locale complémentaire

Intégration temporaire sans commit ni publication des évolutions #10 (`86509bcdb7e6551f3e6e39a0334d2c229650fae8`) et #12 (`f57db3ee1d973e680901e96c7a192361d2e0999c`) avec cette branche et sa base #11. Application des changements sans conflit, puis **138 tests locaux réussis** : 84 learning, 23 moteur, 14 tableau de bord Chromium et 17 sécurité/actualisation Chromium. Ces résultats concernent ces révisions exactes et ne constituent ni une fusion sur une branche cible, ni un déploiement, ni une validation de nouvelles révisions futures. Les essais WebKit n’ont pas été répétés pour cette évolution.
