# Transferts fictifs et âge des cours — audit du 11 novembre 2026

Le commit f1f3221108db602c23a8c489cd25efea4e142dce du 9 novembre à 18:39:53 UTC a retiré 80/80/40 EUR des profils et remplacé leurs historiques antérieurs par les valeurs de 560/480/360 EUR. Le commit 1952c33e1734bf73741c27818846c92bb899d31e a ensuite remis les références 640/560/400 EUR sans réinjecter de trésorerie. Le calcul valeur moins référence comptait donc ces 200 EUR comme pertes.

Les profils sont comparatifs : aucune conclusion sur la destination ou le solde actuel du robot n'est déduite du transfert historique. Le capital de référence reste 1 600 EUR. Aucun argent n'est ajouté.

La correction complète utilise un registre cashFlows sourcé par le commit historique, migré par l’écrivain de #9 : résultat de trading = valeur − référence initiale − transferts nets signés. Au snapshot e39c2a0, les résultats passent de −80/−81,13/−42,88 EUR à 0/−1,13/−2,88 EUR, soit −4,01 EUR. Les pertes et frais réels de simulation restent inclus. Soldes, positions, coûts de revient, historiques, opérations, pics, suspensions et limites de risque restent identiques. Les historiques déjà réécrits ne sont pas reconstruits : le graphique comparatif exclut les points antérieurs au transfert et l'indique. Le composant comparatif est actuellement sans conteneur dans la page ; le test navigateur monte ce conteneur pour vérifier son rendu sans changer la navigation.

La PR complémentaire sur main corrige l'écrivain des états. La migration est idempotente et réservée à l'historique audité ; un historique inconnu est refusé. Les registres sont conservés à chaque exécution, sans plafonner ni supprimer les opérations et points historiques. Les plafonds d'ordre, allocations, seuils et calculs de suspension restent identiques.

Dans learning/journal.py :
- quoteAgeAtExecutionSeconds = updatedAt − marketCacheAt ; updatedAt est le relevé d'exécution publié, pas l'heure de chaque opération historique.
- collectionDelaySeconds = observedAt − updatedAt.
- Le seuil existant de 3 600 secondes reste identique ; cache absent, invalide ou futur toujours signalé.

Les événements et rapports d'apprentissage archivés ne sont pas réécrits. Les anciennes alertes restent des preuves du diagnostic alors utilisé ; les nouveaux événements portent les deux durées. Le prochain passage normal de collecte actualisera le rapport dérivé à partir du nouvel état. Aucun workflow n'est déclenché manuellement par cette correction.

Validation initiale hors réseau métier : 48 tests learning, 17 tests moteur, 18 tests Node sur main, test Chromium avec réponses interceptées (−4,01 EUR et trois transferts affichés, aucune erreur JavaScript). Les tests comparent les données sensibles au snapshot audité, couvrent les vraies pertes, migration répétée, métadonnées invalides, délais de collecte, fuseaux, seuil exact et cours réellement périmés.

Deux PR sont nécessaires car l'application et son écrivain vivent sur des branches distinctes. Elles restent à revoir et fusionner explicitement ; aucune fusion, aucun déploiement, aucun appel payant ou ordre réel n'est effectué.

## Reprise et compatibilité des PR #8, #9 et #10

Le conflit de #8 provenait du snapshot versionné des trois profils, modifié aussi par l’automate. La branche est actualisée depuis la cible courante et conserve ce fichier, les états robot/scanner et les journaux d’apprentissage exactement tels que publiés sur la cible. #8 ne livre plus de changement du fichier vivant : seule #9 migre le registre lors d’une exécution normale de l’écrivain. Les fixtures de régression historiques sont explicites et les contrôles supplémentaires utilisent le relevé courant sans le modifier.

Ordre de mise en service après validation du propriétaire : intégrer #9 sur main, laisser son exécution normale produire le registre des transferts et vérifier les soldes/historiques et résultats ; intégrer ensuite #8 sur shimix-hub. Si l’écrivain ne peut pas passer (fournisseur indisponible ou historique non reconnu), différer l’activation de #8 plutôt que modifier les données à la main. #10 conserve une PR indépendante ; son intégration avec #8 est testée dans un checkout temporaire, sans fusion des branches cibles.

Les contrôles d’intégration ne confondent pas la référence de recherche avec le capital réellement affecté après transfert. Aucun solde n’est crédité et aucune limite de risque n’est changée. Les archives originales restent intactes ; les anciens points déjà réécrits dans la source historique ne sont pas inventés.

Le test `tests/combined_pr_compatibility.py --automation-ref b3b77a713a3246bc3d89aff0b682e9d8f81240ae` exécute le véritable écrivain #9 sur une copie du relevé courant, avec fetch entièrement intercepté et aucun ordre simulé nouveau (variations de cours de fixture à zéro). Il vérifie la migration répétée, les soldes/positions/opérations/risques conservés, l’historique existant conservé et prolongé d’un relevé normal, puis transmet la sortie aux lecteurs Python et au tableau de bord. L’option `--require-refresh-feedback` vérifie aussi le bouton de #10 dans le checkout d’intégration temporaire. La version de #9 est épinglée et doit être revue si sa tête change.

Références de la reprise : cible applicative `0754a51f4d3054820f4da0dcdf0d2f6055301009`, #9 `b3b77a713a3246bc3d89aff0b682e9d8f81240ae`, #10 `86509bcdb7e6551f3e6e39a0334d2c229650fae8`. Sur ce relevé, le scénario sans nouvel ordre donne −0,24 / −1,19 / −1,51 EUR hors transferts, sans figer ces montants dans les tests de l’état courant. Le cas historique reste testé séparément à −4,01 EUR.
