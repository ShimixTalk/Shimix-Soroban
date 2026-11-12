# Filtre d’entrée des stablecoins — test isolé

Demande du propriétaire : vérifier la pertinence des achats, notamment USD1, et préparer un filtre sans toucher aux positions du robot publié.

## Constat sur l’achat existant

Au commit `e6da821ffb09ce4290d8e4ceba9800c3c9710633`, achat fictif de 120 EUR de USD1 le 12 novembre 2026 à 07:51:12 UTC : signal Achat, RSI 44,780414, SMA7 0,8924027591, SMA21 0,8922796272, dernier cours journalier 0,8939969558 contre 0,8889653704 auparavant. Le mode agressif admettait RSI <45, dernier cours en hausse et SMA7 >=97 % de SMA21. Le filtre strict RSI <35 n’était pas satisfait.

Cette cohérence mécanique ne démontre pas une opportunité rentable. Le moteur actuel n’a pas de classification spécifique des stablecoins. Une variation EUR d’un jeton visant le dollar peut notamment refléter le change ; l’achat a des coûts d’entrée et de sortie. Le présent test n’interprète pas son mouvement comme une forte hausse attendue du jeton en dollars.

## Comparaison définie à l’avance

Le plan `learning/stablecoin-plan-v1.json` est gelé le 12 novembre 2026 à 13:48:35 UTC, soit 14:48:35 à Paris. Trois comptes de recherche, chacun avec sa propre référence de 1 600 EUR fictifs :

1. Signaux Achat enregistrés du relevé précédent, sans exclusion.
2. Même règle de recherche, avec exclusion des symboles de stablecoins listés dans le plan.
3. Même exclusion et filtre strict additionnel (RSI <35 et SMA7 >SMA21).

Le premier témoin n’est pas une reproduction historique complète du robot : il suit les signaux effectivement enregistrés à partir d’un nouveau capital en trésorerie. Le robot publié conserve ses positions antérieures et ses valeurs sont affichées séparément. Les trois comptes de test ne s’additionnent pas à son capital.

La liste du plan couvre 20 symboles connus, dont USD1, USDT, USDC et DAI. Elle n’est **ni une classification exhaustive ni une identification par contrat**. Un nouveau stablecoin peut manquer et un symbole peut être ambigu ; ces limites sont explicitement reportées. Ajouter une classe ou un symbole exige une nouvelle revue du protocole. L’exclusion n’est pas un jugement de sûreté des autres actifs.

## Portée exacte du filtre

Le filtre s’applique aux **nouveaux achats uniquement**. Il ne force aucune vente d’un actif déjà détenu. Les sorties stop-loss, take-profit ou signal Vente restent disponibles indépendamment de l’exclusion. Les achats et ventes du robot actuel restent entièrement inchangés, car ce code ne s’exécute que dans l’évaluateur hors ligne.

Le rapport consigne les signaux exclus, leur date de disponibilité et le relevé envisagé pour le remplissage. Un signal exclu n’est pas nécessairement une opération évitée : d’autres conditions (cooldown, positions, cash) auraient aussi pu empêcher son exécution.

Même modèle de coûts et limites de recherche : commission/spread/glissement 0,1 % chacun ; 120 EUR par achat, un achat au plus par relevé, allocation à l’acquisition limitée à 320 EUR par actif, 8 positions au plus, délai de 24 h par actif et arrêt global existant à 50 %. Aucun relèvement du risque. Un cours en hausse peut dépasser ensuite la limite à l’acquisition ; ce n’est pas une garantie permanente d’exposition.

Les signaux doivent avoir été collectés avant le relevé suivant. Les anciens événements sont exclus du calcul de performance ; les trous de plus de deux heures n’autorisent pas de transaction sur l’ancien signal. Cotation détenue absente, taux invalide ou configuration modifiée bloquent les résultats avec un statut partiel explicite. Les positions encore ouvertes sont valorisées après liquidation simulée, avant impôts.

## Validation

- 97 tests learning passent, dont 17 nouveaux cas : exclusion de USD1, maintien de BTC/ETH/ASTER sous la règle de base, filtre strict, signaux incomplets, compte conservé, vente d’un stablecoin déjà détenu, sélection du candidat suivant, frais, limites, temporalité, données manquantes et reproductibilité.
- Compilation Python, CLI en lecture seule et `git diff --check` passent.
- Premier passage sur copie actualisée du journal au commit `9e12671abe3ffe681126e48947a2caed5855d9ba` : **0 observation admissible après le gel**, statut `waiting_for_new_observations`. Aucune performance gagnante n’est annoncée.

Utilisation depuis la branche du comparateur :

```sh
python learning/stablecoin_compare.py --root /chemin/vers/une/copie/du/depot
```

Le programme vérifie les empreintes du journal puis imprime un JSON. Il n’utilise aucun réseau, clé, API payante, service, tâche planifiée ou écriture de portefeuille. Les empreintes du plan, du code, des modules dépendants et des données d’entrée sont incluses.

Comparer ensuite résultat net après liquidation, pertes et exposition, sans sélectionner une stratégie sur quelques relevés. Un filtre qui réduit les achats n’est pas automatiquement une amélioration rentable. Tout déploiement de la règle dans le robot courant demande encore une revue et un accord explicite ; cette PR n’en est pas l’activation.
