# Rotation équitable des analyses historiques

Deux historiques au maximum sont téléchargés à chaque passage. Jusqu’ici, les deux premiers actifs restaient prioritaires après chaque échec : une panne persistante pouvait empêcher les autres de recevoir leur historique. La file trie désormais les actifs dus par date de dernière tentative, sans changer leur classement d’investissement. À égalité, l’ordre existant est conservé.

`historyAttempted` enregistre la tentative avant téléchargement ; `historyUpdated` confirme uniquement un historique complet reçu. Une tentative échouée ne rend jamais un historique frais. Les historiques insuffisants, périmés et futurs restent en attente. La rotation couvre les actifs restant dans la présélection, sans garantir la disponibilité du fournisseur ni une fréquence d’exécution.

Six nouveaux tests vérifient la rotation malgré les échecs, la réutilisation d’un historique récent, les dates limites/futures, la séparation tentative/succès, la validation des métadonnées et leur sauvegarde par le moteur. Les 64 tests moteur et 50 tests learning passent ; le contrôle d’intégration vérifie les données inchangées.

Cette correction peut changer les actifs effectivement analysés puis achetés : elle doit donc être approuvée avant activation. Aucun changement des seuils d’entrée, des frais, du capital fictif de 1 600 €, des stops ou des protections globales. Aucun abonnement ou nouveau service.

## Sources et suite de la recherche

- CoinGecko, [erreurs 429](https://support.coingecko.com/articles/7750453634-why-am-i-getting-errors-with-a-status-code-429) : réduire la fréquence des appels lorsqu’une limite est atteinte. Ici, le budget de deux historiques est conservé ; cette rotation ne supprime pas les quotas.
- Bailey et al., [The Probability of Backtest Overfitting](https://www.davidhbailey.com/dhbpapers/backtest-prob.pdf) : multiplier les configurations testées sur un même historique peut sélectionner un résultat trompeur. Les variantes d’entrée doivent rester préfixées puis évaluées sur de nouvelles données nettes de coûts.

Aucune actualité ou recommandation web ne devient automatiquement un ordre. Les sources externes alimentent les hypothèses documentées, pas une promesse de rendement. Une offre payante ne sera envisagée qu’avec un besoin précis, un essai comparatif et une autorisation de coût.
