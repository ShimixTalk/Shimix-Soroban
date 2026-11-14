# Cotations des actifs détenus hors classement de découverte

## Incident

Le relevé du 13 novembre 2026 à 06:31 UTC indique `value=null`, `buyPaused=true` et « Prix indisponible [...] PEARL ». Les prix étaient extraits de la seule liste des 100 premiers actifs. PEARL était absent de cette réponse alors que le compte détenait encore `pearl-2`. Une requête publique ciblée a confirmé que le fournisseur exposait un prix pour cet identifiant.

L’incident est intermittent : le relevé de 12:43 UTC a retrouvé une valorisation sans erreur lorsque l’actif est revenu dans le flux de découverte. Ce retour spontané ne corrige pas la dépendance erronée entre classement de marché et suivi des positions.

L’absence de prix bloque les nouveaux achats et empêche d’évaluer correctement la protection globale. Elle peut également retarder les sorties ordinaires des autres positions tant que la valorisation est incomplète. La correction est prioritaire sur les optimisations de la PR #17.

## Correction préparée

Après les cotations de découverte et avant la protection/les décisions, le moteur recherche les actifs détenus en quantité positive dont le prix manque. Il utilise exclusivement leurs identifiants `assetIds` déjà enregistrés. Les identifiants manquants sont regroupés en **une seule requête supplémentaire** `/coins/markets` au même fournisseur existant, avec prix en euros.

Chaque prix complémentaire exige :
- un unique résultat pour l’identifiant exact demandé ;
- un symbole correspondant à celui du compte (sinon revue manuelle, pas de substitution) ;
- un prix numérique fini strictement positif ;
- une date fournisseur avec fuseau, âgée au plus d’une heure, sans avance de plus de 60 secondes.

Un résultat d’un autre actif portant le même symbole n’est jamais utilisé. L’identifiant n’est jamais deviné depuis le ticker. Un résultat ambigu, invalide, ancien ou absent laisse le prix inconnu et les achats bloqués ; aucun ancien prix n’est repris et aucune position n’est valorisée à zéro.

Les résultats complètent uniquement les cotations des positions. Ils ne sont pas ajoutés au classement de découverte ni aux candidats d’achat. Ils ne rafraîchissent pas artificiellement `marketCacheAt` pour les autres cours. `holdingQuoteCoverage` expose la date du contrôle, les actifs requis, les identifiants demandés, la date fournisseur des cours complémentaires et les actifs encore sans prix.

Le mécanisme conserve le fonctionnement défensif en cas de vraie panne du fournisseur : erreurs visibles, valorisation non calculable et pas de nouvelle opération fondée sur un prix inventé. En cas de liquidation déjà déclenchée, les prix complémentaires valides peuvent permettre de terminer les ventes des actifs sortis du classement.

## Préservation et budget

Aucun solde, capital, position ou historique n’est changé par la fonction de récupération ; seules les cotations et leurs métadonnées sont complétées sur les prochains passages de la version intégrée. Les éventuelles sorties ensuite exécutées restent les règles existantes du moteur. La protection −5 %/−10 %, les coûts, les plafonds, le mode et la stratégie d’entrée ne sont pas retouchés.

Aucun nouveau fournisseur, abonnement ou service. Au maximum une requête groupée supplémentaire par passage, seulement si une position n’est pas déjà cotée : jusqu’à quatre requêtes par passage complet au lieu de trois (marché, complément des positions, deux historiques). Pas de boucle de relance en cas de panne ou de limite HTTP.

## Validation

- 49 tests moteur passent, dont 17 nouveaux : actif hors liste, identifiant exact, collision de symbole, ambiguïté, prix invalides, dates absentes/périmées/futures, fuseau, limite d’âge, identifiant inconnu, requête groupée, panne et préservation des finances/cache ;
- scénarios de bout en bout : PEARL reste valorisé hors classement ; la cotation de PEARL débloque une sortie stop-loss d’ETH ; une vraie absence de réponse maintient l’arrêt des achats sans effacer les positions ;
- 41 tests learning passent ;
- contrôle d’intégrité sur base exacte `0b4a220434b34e342bf6666d406c85025aa81ffb`, collecteur en lecture seule, compilation et diff vérifiés.

Total : **90 tests locaux réussis**. Les tests sont hors réseau métier ; les réponses du fournisseur et les écritures GitHub y sont interceptées. Le contrôle d’intégration conserve les données protégées octet pour octet et autorise uniquement la transition exacte du moteur `e3479e3fa7b7718276b04d50cb3694120627631df8fb03ef7894a9daab21bd0a` vers `8a5d1d3f8d6a6d31862434da75a357b132d8a88828b83cf43e3e57664fafe695`.

Les données publiées sont préservées dans cette branche ; aucune opération n’a été exécutée en production pour fabriquer une preuve. Si PEARL figure déjà dans les 100 premiers à l’activation, le complément est simplement inutile pour ce passage ; les tests démontrent le cas hors liste sans modifier les données vivantes.

## Intégration

PR indépendante ciblant `shimix-hub`, sans intégrer la PR #17 ni les autres expériences. Rebaser et retester #17 après cette correction, en conservant cette couverture des positions et en actualisant les empreintes attendues ; son ancien budget de requêtes doit aussi intégrer le complément potentiel. Une compatibilité ancienne ne vaut pas validation de l’intégration conjointe.

Aucune fusion ni publication effectuée lors de la préparation. L’accord du propriétaire reste nécessaire pour activer cette seule correction.
