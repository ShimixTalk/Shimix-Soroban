# Analyses mieux mesurées et sorties de risque prioritaires

Demande du 13 novembre : préparer une analyse plus réactive et plus rigoureuse, sans augmenter le risque ni promettre un taux de réussite. Cette évolution s’appuie sur la protection −5 %/−10 % déjà active (#16). Elle reste une PR de revue jusqu’à autorisation d’intégration.

## Réactivité

La cadence déclarée du workflow est déjà de quinze minutes. Les exécutions observées dans GitHub Actions sont parfois espacées d’environ 44 à 77 minutes : modifier uniquement le cron ne garantit pas une surveillance plus fréquente. Cette branche ne change aucune planification et n’ajoute aucun service.

Deux délais internes sont traités :

1. **Cotations :** cache maximal de quinze minutes au lieu d’une heure. Au cours d’une exécution, une cotation de plus de quinze minutes entraîne une nouvelle requête groupée au fournisseur existant. Un échec ne permet pas de négocier sur des cours expirés.
2. **Sorties de position :** stop-loss et take-profit fondés sur le prix sont exécutés et sauvegardés avant les téléchargements d’historique. La protection globale −10 % était déjà évaluée avant ces téléchargements ; elle reste prioritaire. Les téléchargements peuvent durer, mais ne retiennent plus une vente de protection déjà identifiable avec le prix et la référence d’entrée.

Un point de sauvegarde intermédiaire est créé seulement si une sortie par prix a réellement eu lieu. Ses signaux sont vides pour ne pas présenter les signaux du passage précédent comme de nouvelles décisions. La source conserve tout l’historique ; un second relevé au même instant de passage n’est pas une nouvelle vente. Les statistiques de ventes sont dédupliquées par identifiant d’opération.

Le deuxième enregistrement utilise obligatoirement le nouveau SHA du contenu retourné par GitHub. Un checkpoint non confirmé interrompt l’analyse ; une erreur ultérieure ne rétablit pas l’ancienne position déjà vendue. Aucun écrasement forcé ni réécriture d’historique. Les autres sorties sur signal continuent après l’analyse. L’actif vendu en début de passage ne peut pas être racheté dans le même passage ; il reste soumis au délai par actif habituel aux passages suivants.

Le budget reste au maximum une requête de marché groupée et deux téléchargements historiques par exécution. Le rafraîchissement plus fréquent du cache peut augmenter le nombre de requêtes de marché si les passages se rapprochent réellement de quinze minutes ; aucun nouvel abonnement, fournisseur ou appel payant n’est ajouté. Les erreurs de réseau/limite restent visibles, sans boucle de relance agressive.

Ce n’est pas une mesure de vitesse garantie en production : les tests établissent l’ordre des appels. Les attentes réelles dépendent de GitHub, du réseau et du fournisseur. Les indicateurs restent journaliers : les recalculer plus souvent ne transforme pas une stratégie quotidienne en stratégie intrajournalière. Une telle transformation nécessiterait une expérience distincte.

## Qualité des conclusions

Le rapport dérivé ajoute `observed.outcomeQuality` calculé sur toutes les ventes FIFO attribuables, avant la limitation d’affichage à cinquante explications. Il contient : nombre de ventes connues, gains/pertes/neutres, taux de ventes gagnantes observé, résultat net moyen connu par vente, facteur gains/pertes quand il est calculable, couverture des frais et opérations non attribuables.

Les coûts d’achat et de vente sont déjà inclus dans chaque résultat FIFO connu. Les positions ouvertes ne sont pas comptées comme des réussites. Des coûts de revient manquants ne sont jamais inventés. Un taux de réussite de 80 % peut correspondre à une perte globale si les rares pertes dépassent les petits gains : un test vérifie explicitement ce cas.

L’intervalle de Wilson à 95 % est fourni comme indicateur descriptif sous hypothèse de ventes indépendantes. Les ventes partielles ou corrélées, les données manquantes et la sélection des seuls résultats attribuables limitent cette interprétation. Il ne représente ni la probabilité du prochain gain ni une garantie statistique de rentabilité. Sans vente, aucun taux n’est affiché ; sans perte connue, le facteur de profit n’est pas inventé comme infini.

Le tableau de bord indique l’incertitude et l’absence d’autorisation de promotion automatique. Ces statistiques évaluent les résultats ; elles ne constituent pas un modèle autoapprenant et ne modifient aucun signal, paramètre, poids ou limite. Les hypothèses de stratégie restent à comparer sur de nouvelles données avec coûts, pertes et exposition.

## Validation locale

- 41 tests moteur, dont 9 nouveaux : sauvegarde avant le premier téléchargement historique, utilisation du nouveau SHA, panne de téléchargement après sortie, checkpoint non confirmé, cache frais/périmé, absence de checkpoint superflu, absence de rachat immédiat et confirmation de sauvegarde ;
- 50 tests learning, dont 9 nouveaux : données absentes, échantillon très court, gains/pertes/neutres, coûts inconnus, historique de plus de cinquante ventes, déduplication, absence de coût de revient et taux de réussite élevé malgré un résultat négatif ;
- 12 tests Chromium du tableau de bord, dont deux nouveaux sur l’incertitude et l’absence de faux taux en l’absence de vente ;
- total : 103 tests locaux ; reproduction exacte des trois études gelées, collecteur en lecture seule, données protégées identiques, compilation et diff contrôlés.

Le contrôle d’intégration accepte uniquement la transition du moteur protégé SHA-256 `e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a` vers le moteur testé `c459629e19a1554ea96b0bde65e73f59d18f910d0b1329f6e5d9ae7d26460968`. Les données et autres moteurs protégés restent identiques à la base `e2b6f3ad5a4a2d621ccc7f9928f1dc974b7eb041`.

La règle de pause −5 %, la liquidation −10 % et son verrou, la référence 1 600 EUR, les frais et les plafonds restent inchangés. Aucun benchmark de rentabilité améliorée n’est annoncé. Le contrôle du risque peut être mieux ordonné sans que les achats deviennent automatiquement plus pertinents.

Avant intégration conjointe, revalider les conflits éventuels avec les PR d’audit, d’affichage et d’expériences encore ouvertes. Cette branche n’active aucune réserve, filtre de stablecoins ou nouvelle stratégie d’entrée. Aucun workflow métier, fusion ou déploiement n’est déclenché par la préparation.


## Révision conjointe du 14 novembre 2026

Cette révision intègre la dernière application, y compris le bouton de suivi corrigé (#10), et le correctif de couverture des cours (#18). Les cotations complémentaires par identifiant sont récupérées avant la protection et les sorties anticipées. Leur échec conserve la valorisation inconnue et le blocage des nouveaux achats. Un test conjoint vérifie qu’une position hors classement peut être valorisée et qu’une autre position est vendue puis sauvegardée avant les téléchargements historiques. Le test simule le SHA renvoyé par GitHub après sauvegarde.

Validation de cette révision : 58 tests moteur et 50 tests learning réussis. Le contrôle d’intégration contre fa2887074f0cfe8aca6a8d521f32393858da4a26 conserve les données et vérifie le moteur combiné par empreinte exacte.

Limites : aucune amélioration de rendement démontrée ; aucune modification du signal d’achat agressif ni des seuils de risque. La durée du cache passe à 15 minutes, mais la fréquence du workflow reste inchangée : des exécutions horaires ne deviennent pas des contrôles toutes les 15 minutes. Les deux requêtes historiques maximales restent en place, avec une requête de cotations complémentaires groupée uniquement si des positions sont absentes du classement. Les limites gratuites et les échecs du fournisseur restent possibles.

Pour améliorer les entrées, la comparaison prospective stricte (#12) et l’exclusion expérimentale des stablecoins (#15) doivent fournir de nouvelles observations nettes de coûts. Les résultats de quatre ventes ne permettent pas de choisir une règle gagnante ni de prétendre à un apprentissage autonome. Aucun ajustement n’est choisi pour embellir les pertes déjà connues.
