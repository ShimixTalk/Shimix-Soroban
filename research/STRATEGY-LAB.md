# Essai comparatif fictif v1 — proposé, non activé

Gel des règles : 17 novembre 2026, 22:22:44 Europe/Paris. Source des données :
commit 645785b94fe77ad4ddcdf3e39baedaf47e35ac8c, fichiers locaux de prix en EUR.
Le rapport contient les empreintes SHA-256 des trois sources et du modèle.
Aucun appel réseau, moteur de production, écriture du journal ou service nouveau.

## Modèle figé

Univers commun BTC/ETH/SOL, capital neuf de 1600 EUR par variante et par fenêtre,
départ sans position. Les résultats sont indépendants et ne s'additionnent pas.
Coûts de chaque côté : frais 0,1 %, spread 0,1 %, glissement 0,1 %, sans double
retrait des frais d'achat inclus dans les quantités. La valeur finale inclut les
coûts de sortie des positions restantes. Un signal utilise seulement les prix
antérieurs ; l'exécution simulée prend le prix de l'observation quotidienne suivante.

- Référence quotidienne simplifiée : conditions RSI/SMA du mode agressif courant,
  suivies de tendance SMA7>SMA21 et clôture en hausse. Ce n'est pas un rejeu exact :
  scanner, cadence intrajournalière, qualité fournisseur et plafonds réels de
  requêtes ne sont pas reconstruits. Elle ne porte pas le résultat du robot réel.
- Rebond plus précoce : RSI<45, clôture en hausse, SMA3>SMA7, SMA7>=97 % de SMA21 ;
  cette variante change explicitement la condition de tendance du contrôle d'entrée.
  Ordres réduits à 60 EUR au lieu de 120 EUR.
- Suivi de tendance : SMA7>SMA21, dernière clôture au-dessus des vingt précédentes,
  RSI<70 ; ordre plafonné à 120 EUR.

Pour les trois stratégies : une entrée maximum par jour, allocation maximum
320 EUR par actif, sorties au stop 4 %, objectif 8 % ou signal baissier, sans
rachat le jour de la sortie. Référence et objectifs utilisent le coût moyen
incluant les frais d'entrée. Le contrôle actuel des scénarios nets est satisfait
aux coûts fixés : objectif net/risque net théorique supérieur à 1,5. Il ne s'agit
pas d'une probabilité de gain. Les achats exigent aussi un prix d'exécution au
moins égal à la dernière clôture. Pause à 1520 EUR liquidables, liquidation
verrouillée à 1440 EUR. Les gaps et l'échantillonnage quotidien peuvent dépasser
ces pertes : aucune borne absolue n'est promise. Univers de trois actifs, donc
jamais plus de trois positions (limite courante de huit non dépassée).

Repères contextuels : rester en EUR ; achat-conservation équipondéré des trois
actifs avec tout le capital. Ce dernier a une exposition de 100 % et n'applique
pas les protections ; il ne représente donc pas un risque comparable.

## Résultats rétrospectifs, pas une validation prospective

371 dates communes, du 11 novembre 2025 au 16 novembre 2026. Les 1113 points ont
été observés après leur date historique. A : 20 juillet–17 septembre 2026 ;
B : 18 septembre–16 novembre 2026, 60 séances chacune. Les deux fenêtres sont
rétrospectives. Aucune optimisation ni sélection de seuil après lecture des résultats.

| Modèle | PnL net A | PnL net B | Exposition moyenne A/B |
|---|---:|---:|---:|
| Référence quotidienne simplifiée | 0,00 EUR | 0,00 EUR | 0 % / 0 % |
| Rebond précoce | +19,26 EUR | -6,50 EUR | 2,61 % / 0,31 % |
| Suivi de tendance | -7,11 EUR | -17,53 EUR | 2,47 % / 5,92 % |
| EUR | 0,00 EUR | 0,00 EUR | 0 % / 0 % |
| Achat-conservation, repère distinct | +386,33 EUR | -319,24 EUR | 100 % / 100 % |

Le rapport donne aussi perte maximale, frais, positions, valeur liquidable et
registre des opérations. Les faibles nombres d'opérations et les expositions
inégales empêchent de déclarer une variante supérieure. En particulier, le rebond
précoce perd face à EUR sur B. Aucun revenu mensuel extrapolé, aucune promotion.

## Prochaine preuve attendue

Conserver ce modèle et ses seuils sans réglage pendant au moins 20 nouvelles
séances quotidiennes communes après la date de gel, puis analyser les résultats
prospectifs séparément, avec les mêmes coûts et mesures d'exposition. Vingt séances
restent un minimum d'observation, pas une preuve de rentabilité. Aucune collecte
supplémentaire ou tâche automatique n'est ajoutée ici. Le modèle courant refuse
les observations reçues après le gel ; sa sortie prospective reste explicitement
nulle. La partie prospective nécessitera une nouvelle entrée figée et une revue,
sans remplacer les résultats historiques ni changer les expériences #12/#14/#15.

## Reproduction locale

    python research/strategy_lab.py --history-dir hub/trading/learning-data/history
    python -m unittest discover -s research -v

Sur la copie vérifiée : 8 tests du modèle, 99 tests trading incluant ces 8 tests,
77 tests apprentissage réussis. Tests de comptabilité, frais terminaux, absence de
lecture future, données invalides, absence de mutation et verrouillage après gap.
Le robot, les états publiés, les risques et les horaires restent inchangés.
