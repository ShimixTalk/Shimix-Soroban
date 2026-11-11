# Apprentissage du robot — livraison en observation

État : branche de développement, aucune fusion, activation planifiée ni publication autorisée. Aucun fichier de données existant ni moteur de trading n'est modifié ; capital de référence 1 600 € conservé. Aucun service payant, exchange, compte bancaire, secret ou appel OpenAI créé.

## Fonctionnement livré

Le collecteur lit les versions Git de `robot-state.json` et `three-portfolios.json`, puis écrit exclusivement sous `hub/trading/learning-data/`. Il conserve prix, signaux, raisons fournies par les moteurs, frais, opérations, résultats et paramètres de risque observés. Les événements des deux sources sont distingués, y compris si elles changent dans le même commit. Les curseurs permettent de récupérer les mises à jour manquées entre collectes.

Au premier lancement, il capture la dernière version de chaque source, dont les opérations encore présentes. Il ne prétend pas retrouver des décisions déjà supprimées ou non journalisées avant son installation. Le fichier source complet est référencé par son commit Git. Les empreintes des opérations évitent de compter plusieurs fois une même opération à travers des snapshots ; des empreintes identiques dans une même source sont signalées comme ambiguës.

Le journal est append-only, chaîné par empreintes et découpé en segments d'environ 512 Ko. Les anciens segments et historiques ne sont jamais purgés. Une observation unique trop volumineuse ou un curseur perdu bloque la collecte plutôt que de supprimer des lignes. Les fichiers d'état, la politique, les secrets et les workflows sont hors du périmètre d'écriture autorisé du collecteur. Les commits sont atomiques ; en cas de concurrence Git, le collecteur réessaie une avance simple et refuse d'écraser un autre journal modifié. Ce n'est pas un registre inviolable face à un administrateur Git.

Le tableau de bord « Apprentissage du robot » se trouve dans un nouvel onglet du robot. Il présente les observations, comparaisons, coûts connus, erreurs, périodes distinctes et propositions en observation. Le résultat réalisé est calculé uniquement sur les coûts d'acquisition FIFO connus ; les quantités, frais ou coûts inconnus restent non attribuables. La variation de valeur est séparée entre effet des cours sur les positions précédentes et effet résiduel des exécutions/frais/flux fictifs. Ce résidu n'est pas présenté comme une preuve de causalité ou de profit réalisé.

## Stratégies et méthode

Les profils de recherche reprennent des capitaux indépendants de 640/560/400 € (total 1 600 €), univers fixes et risques constants. Ils ne s'ajoutent pas au capital du robot principal et ne modifient pas les trois portefeuilles actuels.

La référence de recherche utilise momentum 14 jours et moyennes 7/21. Neuf filtres candidats combinent fenêtres 7/14/21 et seuils 0/1/2 %. Il ne s'agit pas d'une reproduction exacte des moteurs actuellement exécutés : l'historique retenu ne fournit pas les données d'exécution, volumes et signaux intrajournaliers nécessaires à cette affirmation.

- Minimum 120 points journaliers alignés pour tous les actifs du profil, en EUR ; jours courants, prix non finis, trous et doublons contradictoires refusés.
- Décisions sur les points strictement antérieurs au prix d'exécution fictif. Fenêtre d'indicateurs de 21 points avant la première évaluation.
- Découpe chronologique 60/20/20, avec un jour d'écart à chaque frontière. Capital remis à son niveau de recherche au début de chaque période, uniquement dans le backtest, sans écriture dans les portefeuilles.
- Paramètres sélectionnés sur l'apprentissage uniquement, selon rendement net moins une pénalité de drawdown, avec au moins trois opérations. Validation et test final peuvent rejeter le candidat ; ils ne choisissent ni ne retouchent ses paramètres.
- Frais, spread, glissement et coûts de liquidation finale fictive inclus. Pas de marge, vente à découvert ou impôt personnalisé. La pause au seuil de perte ne garantit pas un plafond de perte ni un prix de liquidation.
- Expérience gelée et liée à l'empreinte du code, des données et des risques de recherche. Une nouvelle génération nécessite un nouvel identifiant et une revue humaine ; pas de réoptimisation répétée du test final.
- Suivi ultérieur sur au moins 20 points nouveaux **horodatés après le gel**, et découverts après celui-ci. Les points déjà disponibles au début du jour du gel ne comptent pas comme données futures. Les anciennes données peuvent uniquement servir à réchauffer les indicateurs.
- Une meilleure sélection peut être proposée en observation seulement si validation, test final et données nouvelles soutiennent le candidat et son drawdown. Aucune proposition n'est appliquée au robot, au risque ou au code automatiquement.

Les données publiques CoinGecko sont conservées avec dates de première observation. Deux historiques au maximum sont demandés par collecte, en rotation incluant les erreurs. Si le fournisseur révise un prix archivé, l'ancienne valeur est conservée et une erreur est signalée. Les sources peuvent être indisponibles ou limitées : aucune valeur ni performance n'est inventée en remplacement.

## Résultat historique réel initial, sans promotion

Source : CoinGecko, prix journaliers EUR de BTC, ETH, SOL, LINK, AVAX et DOGE, 364 points du 11 novembre 2025 au 9 novembre 2026. Les fichiers sont archivés sous `learning-data/history/` ; aucune donnée de test synthétique n'est publiée comme performance réelle.

Périodes d'évaluation : apprentissage du 2 décembre 2025 au 16 juin 2026 après préchauffage ; validation du 18 juin au 28 août ; test final du 30 août au 9 novembre. Les rendements ci-dessous concernent uniquement ces simulations de recherche, pas les résultats réels du robot publié.

| Profil | Référence nette, test final | Candidat net, test final | Conclusion |
| --- | ---: | ---: | --- |
| Prudent | −0,037532 % | −0,910498 % | Candidat rejeté |
| Équilibré | −1,199607 % | −2,078623 % | Candidat rejeté |
| Dynamique | −0,810928 % | −11,626545 % | Candidat rejeté |

**Aucune amélioration validée à appliquer.** L'amélioration du prudent observée en validation ne tient pas sur le test final. Aucun point véritablement nouveau n'est encore disponible après le gel : le suivi futur est en attente. Le système conserve donc la référence en observation et ne change aucun signal réellement exécuté.

Reproduction hors ligne : `python3 learning/reproduce.py`. Elle doit retrouver exactement les expériences gelées à partir des archives. Les frais sont hypothétiques, les univers fixes sélectionnés parmi des cryptos aujourd'hui connues laissent un biais de survivance, et neuf essais peuvent surajuster malgré les séparations. Aucun rendement futur n'est garanti.

## OpenAI et revues Codex : aucune dépense

`learning/policy.json` fixe `openai.enabled=false`, budget mensuel `0` USD et plafond par requête `0` USD. `ai_review.py` prépare un dossier structuré, sans client HTTP ni invocation d'API. Il reste incapable d'appeler OpenAI même si un drapeau est modifié : une future activation exige une implémentation distincte, une clé serveur, tarifs/modèle validés, réservation budgétaire durable, plafond de tokens et validation explicite. Aucun outil d'ordre, d'écriture de code, de secret ou de fusion n'est offert à une IA.

Le tableau de bord permet de télécharger ce dossier hors ligne. `learning-data/codex-review.md` et le modèle de PR préparent la revue de code. Ils ne lancent pas automatiquement un agent, ne publient pas de commentaire et n'autorisent ni fusion ni déploiement. Une analyse manuelle copiée dans ChatGPT/Codex dépend de l'abonnement personnel existant, pas d'un appel API effectué par ce projet.

## GitHub Actions et ordre d'activation proposé

1. Examiner les PR de l'application et du planificateur et les résultats des tests ; aucune fusion automatique.
2. Après validation, intégrer l'application sur `shimix-hub`, puis la copie identique de `.github/workflows/shimix-robot-learning.yml` sur la branche par défaut `main`. Le workflow de développement est bloqué hors de `main` et ne collecte pas en production lors des tests de PR.
3. Une fois ces deux livraisons explicitement approuvées, lancer la collecte et vérifier journal/rapports. La planification proposée est deux fois par heure ; elle n'est pas activée par cette livraison. GitHub peut retarder ou suspendre les tâches planifiées.
4. Les rapports futurs sont lus par le tableau de bord via GitHub brut, avec repli local. Les commits de données portent `[skip render]` pour éviter un redéploiement du code sur chaque collecte, selon le comportement Render à confirmer lors de la recette.
5. Surveiller échecs, quotas API, taille Git, couverture et retards. Le journal est actuellement relu pour ses agrégats : à grande échelle, prévoir des checkpoints vérifiés sans supprimer les archives. Ce projet ne fournit pas de capacité infinie ni une garantie de gratuité de tout plan GitHub futur. Aucun hébergement supplémentaire n'est nécessaire dans cette proposition.

Ne pas fusionner la PR de planification avant que le code testé soit présent sur `shimix-hub` : elle échouerait en précontrôle, sans écriture de données. Les autres robots et leurs planifications restent inchangés.

## Vérifications livrées

32 tests unitaires d'apprentissage : politique zéro coût, modes réels et changements de capital refusés, non-mutation des sources, attribution FIFO, cours manquants, absence d'anticipation, séparation des périodes, gel/rejeu, données véritablement postérieures, historique défectueux, journal modifié, segmentation et refus d'écriture hors du répertoire d'apprentissage. 5 tests navigateur du tableau de bord : lecture, erreurs en texte, historique manquant, absence de mutation locale et dossier IA sans réseau OpenAI. Les 17 tests existants du robot et 11 tests de sauvegarde sont également relancés : **65 tests au total**. La CI distante doit confirmer l'état exact du commit proposé ; ses liens figurent dans les PR.

Aucun fichier de capital, de portefeuille ou d'état existant n'est modifié. Le moteur actuel `autonomous_simulation.py` et les scripts Node de `main` restent inchangés. Les limites de risque actuelles (dont le seuil principal de 50 %) sont seulement observées. Aucun secret n'est inspecté ni écrit pour ce module.
