# Comparaison prospective, séparée du robot

Le propriétaire a approuvé un test séparé, sans hausse du risque ni modification du robot courant. Le protocole `learning/shadow-plan-v1.json` est gelé le 11 novembre 2026 à 20:00:52 UTC (21:00:52 à Paris), avant les observations retenues. Aucun réglage n’est sélectionné sur les résultats de l’expérience. Changer le protocole exige une nouvelle version et une nouvelle revue.

## Trois témoins, aux différences explicites

1. **Robot courant observé** : sa valeur après liquidation simulée est recalculée à chaque relevé valide. Il conserve ses positions et son passé ; il n’est pas réinitialisé à la date du gel. Il ne s’agit pas d’une reproduction historique exacte de ses décisions.
2. **Variante stricte isolée** : repart avec 1 600 EUR fictifs dans la mémoire du comparateur. Parmi les signaux Achat effectivement enregistrés et déjà collectés, ne retient que RSI < 35 et SMA7 > SMA21. Le signal vient d’un relevé précédent, disponible avant le cours utilisé pour la transaction fictive. Ne prétend pas reproduire une décision non journalisée. Sorties : seuils de position 4 %/8 % ou signal Vente précédent, avec les coûts du moteur. Une acquisition au plus par relevé, délai de 24 heures par actif.
3. **Achat-conservation BTC/ETH à budget limité** : achats de 120 EUR de BTC puis de 120 EUR d’ETH, au maximum un achat par relevé admissible. Solde conservé en euros fictifs. Les coûts et plafonds sont identiques ; l’univers et l’exposition restent différents et sont explicitement indiqués. Ce n’est pas un portefeuille entièrement investi ni une comparaison à exposition identique.

Tous utilisent la référence de 1 600 EUR et les taux commission/spread/glissement de 0,1 % chacun. La variante conserve les plafonds 120 EUR par achat, 20 % du capital par actif à l’acquisition, 8 positions et arrêt global à 50 % de perte. Aucun de ces plafonds n’est augmenté. Le seuil de 50 % est une configuration existante, pas une recommandation : son éventuelle revue relève d’un accord séparé.

Le robot observé a un inventaire initial différent. Les gains en euros ne suffisent donc pas à démontrer une supériorité : les courbes d’exposition, leur moyenne et leur maximum doivent être lus avec rendement et baisse maximale. Aucun gagnant n’est choisi par le programme.

## Données et garde-fous

- Lecture exclusive des événements postérieurs au gel ; ancien historique exclu des résultats.
- Vérification du chaînage et des empreintes du journal avant calcul ; chemins de segments bornés.
- Signaux utilisés seulement si `observedAt <= at` du relevé suivant. Un signal arrivé tardivement n’est pas disponible rétroactivement. Deux commits au même instant source ne créent pas deux occasions de transaction.
- Pas de transaction sur un signal vieux de plus de deux heures. Ce seuil fait partie du protocole et les trous sont signalés.
- Arrêt de l’évaluation si la configuration source change, si une cotation détenue manque, si les cours à l’exécution sont périmés ou si les coûts sont invalides. Les résultats éventuels sont étiquetés partiels/bloqués.
- Frais d’achat déduits des quantités ; coûts de vente déduits des produits. Toutes les valeurs finales déduisent aussi la liquidation des positions encore ouvertes. Les frais déjà payés ne sont pas déduits deux fois.
- Empreintes du plan, du code évaluateur et des données d’entrée incluses pour la reproduction.
- Aucune connexion réseau, clé, requête au courtier, écriture de portefeuille, mutation des événements ou programmation de tâche. Le programme imprime un rapport JSON ; les comptes de test sont reconstruits uniquement en mémoire.

## Utilisation

Depuis la branche contenant le comparateur :

```sh
python learning/shadow_compare.py --root /chemin/vers/une/copie/du/dernier/depot
```

La copie d’entrée doit contenir `hub/trading/learning-data/index.json` et ses segments. Conserver le même plan et le même code pour chaque point. Le programme peut être relancé sur les archives les plus récentes ; il ne collecte pas lui-même de nouveaux cours et ne s’exécute pas pendant l’absence de l’assistant.

Premier essai sur la copie des archives disponibles : **0 observation admissible après gel**, statut `waiting_for_new_observations`, aucune performance de variante annoncée. Empreinte du plan : `beed173cd9cc690bfd3bd19faaf76f66efcb9a271f8ead1304ae1fa995dfc3d7`.

## Tests et limites

80 tests learning passent, dont 17 nouveaux tests du comparateur : exclusion du passé, signal précédent seulement, retard de collecte, doublons, coûts, cooldown, exposition, ventes, arrêt global, métadonnées modifiées, cotations absentes/périmées et journal altéré. Les sorties sont déterministes et les entrées restent identiques après évaluation. CLI hors ligne et compilation Python vérifiées.

Les remplissages sont indicatifs, les gaps peuvent masquer des événements intrapériode, la liquidité et le carnet ne sont pas reconstitués. Un arrêt de position n’assure pas une perte plafonnée. Les observations disponibles après la collecte ne représentent pas tous les cours du marché. Les frais réels, impôts et délais réels ne sont pas modélisés. Le gain net d’une courte période ne prouve aucun avantage durable.

Cette évolution dépend du contrôle de rigueur #11, lui-même complémentaire de #8. Aucun test ne vaut autorisation de fusion, de déploiement ou de changement de stratégie. #10 reste une évolution séparée de l’interface.
