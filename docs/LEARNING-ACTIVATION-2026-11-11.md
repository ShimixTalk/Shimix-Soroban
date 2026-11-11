# Activation autorisée du 11 novembre 2026

Les deux en-têtes natifs ont été appliqués au seul service statique Render existant `srv-dbmko2utlv9c73ba67cg`. Le plan Blueprint a uniquement repris ce service et ajouté `X-Frame-Options: DENY` et `Referrer-Policy: strict-origin-when-cross-origin` sur `/trading/*`. Aucun service, stockage ou abonnement supplémentaire. Blueprint `exs-dbq07mrl550s7395iifg`, autoSync désactivé ; une planification après application ne propose aucun changement. Les 7 contrôles HTTP de production réussissent.

La PR #4 a été fusionnée avec accord au commit `fb301625942a5632df520efdb73241fc6c194583`. Son arbre est identique à l’intégration temporaire vérifiée (`abdd7243f677b90cb68b861b2ce701f3f87c48f5`) et conserve les données courantes de son premier parent `eb95113bd52d1bff48a8aeef687d9f8638692ff9`. Render a publié ce commit : déploiement `dep-dbq08mgae00c73fk2lvg`, live. HTML, module du tableau de bord et rapport sont identiques aux fichiers du commit publié. Les 77 tests précédents et le contrôle de préservation/restauration de la dernière base ont réussi.

Le workflow de collecte sur main démarre aussi lors d’une modification de son propre fichier sur main. Cette première collecte autorisée pourra donc être vérifiée immédiatement après la fusion ; les déclenchements récurrents restent aux minutes 19 et 49 UTC, avec les retards possibles de GitHub Actions. Les copies sur shimix-hub et dans ops ne sont pas actives pour la planification : main fait autorité. Le verrou, les permissions, le contrôle de branche, les tests et la restauration avant écriture restent identiques.

À confirmer après fusion de #5 : résultat de la première collecte, journaux, curseurs et rapport, absence de modifications hors learning-data et comportement du marqueur skip Render. Un essai sur appareils Apple physiques reste à faire ; WebKit utilise des profils de taille iPhone et Mac et ne certifie pas le matériel.

Aucune modification des risques ou du capital fictif de référence de 1 600 EUR. OpenAI reste désactivé avec budget zéro ; aucun ordre réel ni connexion à un exchange.
