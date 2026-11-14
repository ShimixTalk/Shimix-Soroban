# Analyse des entrées et sorties — confirmed-entry-v1

Cette version resserre les nouvelles entrées en simulation. Le signal historique RSI/moyennes mobiles reste un préalable, mais un achat exige désormais : SMA7 strictement au-dessus de SMA21 ; dernière clôture en hausse ; cours actuel au moins égal à cette clôture ; prix fournisseur horodaté, âgé d’au plus 15 minutes (tolérance d’horloge future de 60 secondes) ; actif absent de la liste gelée d’identifiants de stablecoins connus ; scénario net au seuil de gain positif et rapport gain/perte théorique d’au moins 1,5. Cette liste n’est pas un registre exhaustif de tous les stablecoins.

Les seuils de sortie existants (−4 % / +8 %) et leurs frais déterminent les scénarios, sans prédiction de gain ni pourcentage de confiance. Le code journalise les motifs de refus/acceptation, les indicateurs et les scénarios. Chaque nouvel achat conserve cette analyse. Les ventes conservent coût d’entrée connu, produit net et résultat net ; une base inconnue reste inconnue, jamais un gain inventé. Ces annotations ne changent ni le calcul des quantités ni le montant des frais.

Les positions déjà ouvertes, dont USD1, ne sont pas forcées à la vente par le filtre des nouvelles entrées. Leurs sorties et les protections globales restent actives. Aucune hausse de risque, aucun changement du capital de référence de 1 600 EUR, aucune réinitialisation des soldes ou historiques. Le challenge conserve ses comptes et limites ; les nouveaux signaux filtrés lui parviennent par le collecteur existant, avec décalage de disponibilité préservé.

La rotation des téléchargements d’historiques de la PR #19 est intégrée : les échecs des deux premiers actifs ne monopolisent plus les passages. Budget inchangé : deux historiques par exécution. Le suivi ne devient pas temps réel.

Le journal distingue maintenant l’âge du cache des cours **à l’exécution observée** du retard de collecte. Une collecte tardive n’est pas interprétée comme un cours périmé lors de la décision. Un cache réellement ancien/futur/inconnu à l’exécution reste signalé. Les archives existantes ne sont pas réécrites et leurs anciens avertissements sont conservés. Les prix fournisseur des nouvelles entrées font en plus l’objet du contrôle de fraîcheur décrit plus haut.

## Preuve et limites

Le fichier research/entry-review-diagnostic-2026-11-14.json présente les sept achats enregistrés avec leurs commits source. Deux n’ont pas une preuve historique suffisante. Les cinq autres seraient refusés, y compris PEARL qui a ensuite gagné : on ne prétend donc pas que tous les refus évitent des pertes. Aucun rendement contrefactuel n’est inventé. Cette relecture du passé n’est pas une validation indépendante ni une comparaison prospective. Les paramètres ont été fixés avant cette relecture et ne sont pas réoptimisés pour faire disparaître les pertes passées.

Cette version est une expérience prudente : moins d’entrées peut aussi signifier davantage d’occasions manquées. Évaluer les prochains résultats nets, les pertes maximales et l’exposition, pas seulement le taux de réussite. Aucune rentabilité supérieure démontrée et aucun apprentissage autonome.

La [documentation RSI de Fidelity](https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/rsi) rappelle qu’un RSI peut rester bas pendant une tendance forte. Elle motive la vérification de tendance ; elle ne valide pas ces paramètres sur les cryptos.

## Validation et intégrité

Tests de signaux synthétiques confirmés ou invalidés, stablecoins par identifiant exact, cours anciens/futurs/inconnus, coûts défavorables, journal des décisions, attribution des ventes et base inconnue, rotation d’historique, garde de liquidation, absence de rachat immédiat et import du validateur GitHub via runpy. Les données de marché synthétiques positives ont été rendues cohérentes : leur dernière clôture correspond au cours courant de la fixture, au lieu d’être 30 % au-dessus.

Le moteur de référence avant modification, SHA-256 c459629e19a1554ea96b0bde65e73f59d18f910d0b1329f6e5d9ae7d26460968, est conservé en fixture texte locale, jamais exécutée. Le contrôle d’intégration vérifie la transition exacte du moteur et l’empreinte du nouveau module d’analyse ; les autres fichiers financiers restent identiques à la base.

Une panne de marché efface les anciennes intentions d’achat, marque les données de marché indisponibles et laisse la valeur des positions inconnue au lieu de republier un ancien prix comme actuel. Le journal transmet cet état et le challenge bloque ses opérations sur ce relevé. Les protections ne réutilisent pas un ancien signal d’entrée. Les tests couvrent ce cas sans suppression des positions, des soldes ou des opérations antérieures.

Validation locale finale : 78 tests moteur, 73 tests learning, 14 tests du tableau de bord, 19 tests sécurité/actualisation et 3 tests de protection navigateur : 187 tests réussis. Reproduction des trois études gelées, vérification des empreintes et du collecteur en lecture seule, import du validateur sans exécution, compilation JavaScript et diff vérifiés. Les contrôles GitHub de la dernière révision restent nécessaires avant activation.
