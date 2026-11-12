# Expérience prospective de réserve de bénéfices

Le propriétaire a approuvé le test séparé proposé : 800 EUR récolte / 800 EUR croissance, 400 EUR récolte / 1 200 EUR croissance, en conservant le robot courant et sans hausse du risque. Cette branche prépare uniquement un évaluateur hors ligne ; elle n’active pas la réserve dans le robot.

## Comparaisons fixées avant les résultats

Protocole `learning/reserve-plan-v1.json`, gelé le 12 novembre 2026 à 08:41:23 UTC (09:41:23 à Paris), empreinte `b85dccb6d272ccec671d335fbc3258ec41aaa47387eb5b78f72712892b3ee73d`.

Trois comptes de recherche indépendants commencent chacun avec 1 600 EUR fictifs :
- `0/1600` : aucune poche récolte, témoin de recherche sans réserve ;
- `800/800` : récolte / croissance à parts égales ;
- `400/1200` : récolte plus petite, croissance plus grande.

Ces trois comptes ne s’additionnent pas au capital du robot. Le robot courant figure comme témoin observé avec ses positions antérieures. Son point de départ diffère ; le compte `0/1600` permet d’isoler la comparaison entre variantes de recherche, mais ne prétend pas reproduire le robot courant.

Le filtre d’entrée des comptes de recherche est le filtre strict défini précédemment : signal Achat déjà collecté, RSI < 35 et SMA7 > SMA21. Le remplissage utilise une cotation d’un relevé distinct suivant. Aucune donnée antérieure au gel n’est réutilisée pour obtenir une performance de cette expérience.

## Règles de sortie et de réserve

Les poches conservent les sorties de recherche : position −4 %, +8 % par rapport au coût d’entrée, ou signal Vente précédent. La poche récolte ajoute une sortie si la position procure au moins 5 EUR **nets de tous les coûts d’achat et de vente modélisés**, et si ce gain permet de couvrir les pertes réalisées antérieures et les montants déjà transférés. Il s’agit d’une clôture de position, pas du retrait de 5 EUR laissant fictivement toute la position ouverte.

Après les clôtures, le transfert est le plus grand multiple entier de 5 EUR limité simultanément par :
1. le résultat réalisé cumulé de la poche récolte moins ses transferts cumulés ;
2. sa trésorerie effectivement disponible ;
3. la valeur liquidable des deux poches de trading moins 1 600 EUR.

Si l’une de ces limites est insuffisante, le transfert attend. Cette règle supplémentaire est prudente : une perte latente de croissance peut différer le transfert d’une opération gagnante de récolte. Les pertes réalisées sont prises en compte sans remise à zéro périodique. Les bénéfices de la poche croissance ne sont pas transférés.

La réserve ne produit pas de rendement et reste exclue des achats. Aucun transfert inverse n’est autorisé pour reconstituer la base. Préserver au moins 1 600 EUR liquidables **au moment du transfert** ne garantit pas ce montant ensuite. Les positions restantes peuvent perdre.

Les mouvements possèdent un identifiant déterministe, une origine/destination et deux variations de trésorerie signées opposées. Ils ne modifient ni le résultat réalisé ni le total réserve + capital liquidable. Relancer l’évaluateur reconstruit ses comptes en mémoire ; cela ne rejoue aucun mouvement sur les comptes publiés.

## Coûts, limites et réinvestissement

Commission 0,1 %, spread 0,1 % et glissement 0,1 %, selon la convention du moteur courant. Les frais d’achat sont inclus dans le coût de revient. Le produit de vente et les positions encore ouvertes déduisent les coûts de sortie. Tous les résultats sont avant impôts et n’utilisent pas les tarifs vérifiés d’un courtier.

Un achat au maximum par relevé pour les deux poches ensemble, montant maximal 120 EUR. Délai de 24 h par actif partagé entre poches, au maximum 8 actifs détenus et allocation à l’acquisition limitée à 20 % du capital global **et** à 20 % du capital propre à chaque poche. Les montants de capital ne sont pas augmentés. Une position dont le cours monte peut dépasser ensuite son pourcentage à l’acquisition : il ne s’agit pas d’une garantie permanente d’exposition.

La poche la moins déployée proportionnellement à son capital initial est prioritaire ; en cas d’égalité, récolte d’abord. Aucun argent ne passe d’une poche à l’autre pour financer un achat. Un actif vendu ne peut pas être racheté au même relevé. Il faut un signal antérieur admissible et un nouveau relevé pour réinvestir.

L’arrêt global existant à 50 % est conservé sur la seule valeur marquée des poches de trading ; la réserve ne vient pas compenser leur perte pour retarder l’arrêt. Ce niveau reste une configuration de comparaison, pas une recommandation. Les règles sont déterministes ; aucun « ressenti » sur le prochain cours n’est inventé.

## Critères du bilan

Le rapport montre séparément : réserve, capital de trading liquidable, somme des deux, résultat global par rapport aux 1 600 EUR, gains/pertes réalisés, solde latent après coûts de sortie, commissions déjà payées, baisses et expositions observées, opérations et transferts.

Le premier critère à examiner est **réserve + valeur liquidable restante**, puis les baisses et l’exposition. Une réserve croissante accompagnée d’une baisse plus importante du capital de trading ne constitue pas une amélioration. Les fréquences de transactions et expositions diffèrent entre répartitions ; aucune variante n’est promue automatiquement.

## Exécution et validation

```sh
python learning/reserve_compare.py --root /chemin/vers/une/copie/du/depot
```

Le programme lit les seuls événements postérieurs au gel dans un journal à empreintes vérifiées et imprime un JSON. Aucune requête réseau, clé, tâche planifiée ou écriture de portefeuille. Le plan, le code, les modules dépendants et les données d’entrée sont identifiés par empreinte. Un changement de configuration source ou une cotation détenue absente/périmée bloque les résultats avec un statut explicite ; un gap de plus de deux heures n’autorise aucun remplissage sur l’ancien signal.

Premier essai sur copie actualisée du journal au commit `15578cd37ca9938ac7d7fb22a5cd3dcbfc2c9a55` : **0 observation admissible après gel**, `waiting_for_new_observations`. Aucun rendement ni réserve accumulée n’est annoncé à partir de données anciennes.

106 tests learning passent, dont 26 nouveaux : seuil exact et juste inférieur à 5 EUR, pertes avant/après transfert, absence de cash, gain latent non transférable, perte de croissance, conservation de richesse sur gains/pertes successifs, frais inclus, mouvements signés équilibrés, absence de renflouement/réinvestissement de la réserve, sortie récolte et absence de rachat instantané, limites partagées, temporalité, configuration modifiée et intégrité des résultats. Compilation Python, CLI hors ligne et `git diff --check` vérifiés.

Les tests artificiels établissent la comptabilité et les règles, pas la rentabilité. Les nouvelles données restent nécessaires pour comparer les résultats ; ni 5 EUR par jour ni un revenu mensuel ne sont promis.

Cette PR dépend du comparateur #12, lui-même complémentaire de #11/#8. Aucune donnée, stratégie, limite, branche cible, publication ou automatisation en fonctionnement n’est modifiée. Toute intégration et tout changement du robot attendent l’accord explicite du propriétaire.
