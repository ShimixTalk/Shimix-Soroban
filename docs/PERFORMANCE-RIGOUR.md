# Contrôle de performance en lecture seule

Cette évolution complète #8. Elle n’ajoute aucun ordre, réglage de stratégie, service, appel payant ou tâche planifiée. Elle ne modifie aucun état de simulation ou événement archivé. Le collecteur ajoute uniquement un bloc `rigour` au prochain rapport dérivé ; les anciens rapports restent lisibles avec une indication de contrôle indisponible.

## Calculs

- Valeur marquée = trésorerie + somme des quantités × derniers cours observés.
- Valeur après liquidation = trésorerie + valeur investie × (1 − spreadRate − slippageRate) × (1 − feeRate). C’est la convention de sortie du moteur courant, pas une estimation des tarifs réels d’un courtier.
- Les coûts d’achat sont déjà déduits des soldes et des quantités. Les commissions historiques connues sont affichées pour information, jamais soustraites une seconde fois.
- Variation après liquidation = valeur après liquidation − référence enregistrée. Elle est libellée comme une variation par rapport à la référence, car des flux non journalisés ne peuvent pas être exclus par ce contrôle.
- Les opérations sont dédupliquées par l’identifiant du journal, achats et ventes comptés séparément. Les commissions absentes sont signalées, sans inventer leur valeur.
- Exposition = valeur investie / valeur marquée. Les paramètres de risque sont affichés, jamais modifiés.
- Baisse maximale : calcul sur les seules valeurs positives observées dans le journal. Un point unique donne « non calculable ». Ce calcul ne prétend pas retrouver les mouvements entre relevés, ni une baisse corrigée de flux non journalisés.

## Qualité et interprétation

Cours manquants, cours périmés à l’exécution, incohérence de valeur, coûts de sortie absents ou invalides : aucune estimation de liquidation chiffrée. Aucun taux implicite par défaut.

Un rapport tardif distingue l’âge des cours à l’exécution de l’âge du relevé à la génération du rapport. L’estimation conserve la date du relevé et signale un relevé vieux de plus d’une heure ; ce n’est pas une valeur de marché actuelle. Les alertes archivées ne sont pas supprimées.

Les achats sans motif enregistré sont signalés. Des signaux collectés après exécution ne doivent pas être transformés en explications certaines de la décision.

Le statut de preuve reste « insuffisant » : ce module ne décerne jamais automatiquement une certification de rentabilité. Il ne calcule pas de rendement mensuel extrapolé, de probabilité de succès ou de seuil arbitraire de maturité. Des tests techniques qui passent ne prouvent pas la qualité économique de la stratégie.

## Vérification sur une copie

Relevé `8191fa3`, robot du 11 novembre 2026 à 19:38 UTC : valeur recalculée 1 604,906873 EUR ; frais d’achat connus 0,36 EUR ; coûts de sortie estimés 1,093991 EUR ; liquidation estimée 1 603,812882 EUR ; variation +3,812882 EUR (+0,238305 %). Trois achats, aucune vente. Les trois motifs d’achat ne sont pas enregistrés dans les opérations et le contrôle le signale. Ces chiffres datés ne sont pas une promesse de gain.

## Validation

- `python -m unittest discover -s learning/tests -q` : 63 tests, dont 14 nouveaux cas de qualité/comptabilité.
- `python -m unittest discover -s hub/trading -q` : 17 tests existants.
- `SHIMIX_CHROMIUM=/usr/bin/chromium python tests/learning_browser.py` : 12 tests Chromium, dont deux nouveaux sur le rendu du contrôle et les estimations absentes. Réseau métier intercepté, stockage local préservé.
- Contrôle d’intégrité sur la base exacte `0754a51f4d3054820f4da0dcdf0d2f6055301009` : données et moteurs protégés identiques, collecteur en lecture seule.
- Reproduction exacte des trois études historiques gelées ; syntaxe JS et `git diff --check`.

## Étapes qui restent à faire valider

1. Confirmer la migration de #9 sur un véritable passage planifié ; intégrer #8 et #10 seulement après accord explicite.
2. Revoir séparément le seuil d’arrêt de 50 % actuellement enregistré : aucun changement n’est proposé automatiquement par ce contrôle.
3. Définir avant comparaison un portefeuille de référence, une période et une exposition comparables. Une comparaison rétrospective choisie après lecture du résultat doit être signalée comme exploratoire.
4. Recueillir suffisamment de ventes et de nouvelles observations ; tester les hypothèses sur des périodes distinctes avant toute proposition de modification du robot.

Aucune fusion ni publication n’est autorisée par ces tests. La référence de 1 600 EUR et les limites de risque restent inchangées.
