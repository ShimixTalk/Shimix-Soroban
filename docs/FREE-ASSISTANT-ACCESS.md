# Accès manuels à ChatGPT et Codex

Dans Apprentissage du robot, préparer un message pour ChatGPT ou Codex, le relire, le copier (ou le télécharger), puis ouvrir le service choisi et le coller. Aucune analyse ne se lance automatiquement. Les réponses restent dans le service utilisé et ne sont jamais appliquées automatiquement au robot.

Aucun appel API, clé, nouvel abonnement ou hébergement. Les offres et quotas des comptes ChatGPT/Codex restent applicables ; ces liens ne donnent pas un accès illimité ou supplémentaire. Le compte peut devoir être connecté, et Codex peut nécessiter une connexion GitHub autorisée par le propriétaire.

Le message sélectionne uniquement des indicateurs numériques du rapport public : capital, frais, résultats des profils et des essais historiques, nombre d’observations et de jours nouveaux. Les données locales, trades détaillés, clés, textes libres et champs inconnus sont exclus. Les URL des services ne contiennent ni message ni données. L’utilisateur choisit lui-même ce qu’il partage. Copier utilise le presse-papiers, sans en lire le contenu ; une zone sélectionnable et le téléchargement servent de repli sur iPhone/Mac.

Les moteurs, historiques, capitaux, risques et secrets restent inchangés. Toute modification future de code nécessite une branche séparée, des tests et une validation avant fusion ou publication. La fréquence de collecte sur main n’est pas modifiée par cette interface.

## Environnement des tests GitHub

Les runners ont échoué sur la résolution DNS des dépôts Ubuntu pendant l’installation des dépendances navigateur, jusqu’au timeout. Les deux jobs navigateur utilisent désormais l’image officielle Microsoft Playwright Python 1.62.0 Noble, vérifiée dans le registre MCR et épinglée par empreinte SHA-256. Elle correspond à la version du paquet des tests et inclut les navigateurs et dépendances système. Tous les tests et permissions en lecture sont conservés ; seule l’installation système à chaque passage est évitée. Aucun service ni runner payant n’est ajouté.
