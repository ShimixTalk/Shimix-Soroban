# Transferts fictifs et âge des cours — audit du 11 novembre 2026

Le commit f1f3221108db602c23a8c489cd25efea4e142dce du 9 novembre à 18:39:53 UTC a retiré 80/80/40 EUR des profils et remplacé leurs historiques antérieurs par les valeurs de 560/480/360 EUR. Le commit 1952c33e1734bf73741c27818846c92bb899d31e a ensuite remis les références 640/560/400 EUR sans réinjecter de trésorerie. Le calcul valeur moins référence comptait donc ces 200 EUR comme pertes.

Les profils sont comparatifs : aucune conclusion sur la destination ou le solde actuel du robot n'est déduite du transfert historique. Le capital de référence reste 1 600 EUR. Aucun argent n'est ajouté.

La correction ajoute un registre cashFlows sourcé par le commit historique : résultat de trading = valeur − référence initiale − transferts nets signés. Au snapshot e39c2a0, les résultats passent de −80/−81,13/−42,88 EUR à 0/−1,13/−2,88 EUR, soit −4,01 EUR. Les pertes et frais réels de simulation restent inclus. Soldes, positions, coûts de revient, historiques, opérations, pics, suspensions et limites de risque restent identiques. Les historiques déjà réécrits ne sont pas reconstruits : le graphique comparatif exclut les points antérieurs au transfert et l'indique. Le composant comparatif est actuellement sans conteneur dans la page ; le test navigateur monte ce conteneur pour vérifier son rendu sans changer la navigation.

La PR complémentaire sur main corrige l'écrivain des états. La migration est idempotente et réservée à l'historique audité ; un historique inconnu est refusé. Les registres sont conservés à chaque exécution, sans plafonner ni supprimer les opérations et points historiques. Les plafonds d'ordre, allocations, seuils et calculs de suspension restent identiques.

Dans learning/journal.py :
- quoteAgeAtExecutionSeconds = updatedAt − marketCacheAt ; updatedAt est le relevé d'exécution publié, pas l'heure de chaque opération historique.
- collectionDelaySeconds = observedAt − updatedAt.
- Le seuil existant de 3 600 secondes reste identique ; cache absent, invalide ou futur toujours signalé.

Les événements et rapports d'apprentissage archivés ne sont pas réécrits. Les anciennes alertes restent des preuves du diagnostic alors utilisé ; les nouveaux événements portent les deux durées. Le prochain passage normal de collecte actualisera le rapport dérivé à partir du nouvel état. Aucun workflow n'est déclenché manuellement par cette correction.

Validation hors réseau métier : 48 tests learning, 17 tests moteur, 18 tests Node sur main, test Chromium avec réponses interceptées (−4,01 EUR et trois transferts affichés, aucune erreur JavaScript). Les tests comparent les données sensibles au snapshot audité, couvrent les vraies pertes, migration répétée, métadonnées invalides, délais de collecte, fuseaux, seuil exact et cours réellement périmés.

Deux PR sont nécessaires car l'application et son écrivain vivent sur des branches distinctes. Elles restent à revoir et fusionner explicitement ; aucune fusion, aucun déploiement, aucun appel payant ou ordre réel n'est effectué.
