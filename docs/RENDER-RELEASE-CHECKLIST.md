# Réglages Render et livraison — proposition sans application en production

Service vérifié : `shimix-hub`, site statique, branche `shimix-hub`, publication `hub`.
Dashboard : https://dashboard.render.com/static/srv-dbmko2utlv9c73ba67cg

## Avant la fusion

- Examiner et valider les deux branches d'audit (application et automatisations `main`).
- Protéger `shimix-hub` et `main` : PR obligatoire, checks requis, interdire force-push et suppression. Prévoir le mécanisme autorisé d'écriture des états de simulation avant d'imposer cette protection : les robots écrivent aujourd'hui via l'API Contents. Préférer ensuite des données privées hors branche de code.
- Changer Render Auto-Deploy de « On Commit » vers « Off » pour conserver une validation manuelle, ou « After CI Checks Pass » après validation du processus. Aucun de ces réglages n'a été changé pendant l'audit.
- Ne pas activer les previews de PR sans accord : il s'agit de ressources supplémentaires potentielles.

## En-têtes HTTP natifs Render à configurer après recette

`hub/_headers` n'a pas produit les en-têtes attendus lors de la lecture HTTP. Configurer les headers dans les réglages du site statique Render, chemin `/trading/*` :

| Nom | Valeur |
| --- | --- |
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| Referrer-Policy | strict-origin-when-cross-origin |
| Permissions-Policy | camera=(), geolocation=(), payment=(), usb=() |
| Content-Security-Policy | default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; connect-src 'self' https://api.coingecko.com https://raw.githubusercontent.com; img-src 'self' data:; object-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'; upgrade-insecure-requests |

La CSP proposée reste transitoire : le code inline et ses gestionnaires nécessitent encore `unsafe-inline`. La CSP dans le HTML de la branche d'audit réduit les destinations de connexion, mais ne remplace pas `frame-ancestors`, qui exige un en-tête HTTP. Externaliser ensuite scripts et gestionnaires puis retirer `unsafe-inline` avec une recette complète. HSTS est déjà présent dans la réponse publique observée.

## Publication autorisée ultérieurement

1. Export chiffré des données locales de chaque appareil et conservation des fichiers d'état GitHub. Les changements de cette PR ne modifient aucun fichier d'état JSON.
2. Tests CI et locaux réussis sur les deux branches et validation utilisateur.
3. Fusion explicite ; livraison du commit choisi, suivi jusqu'à `live`.
4. Relever le commit déployé et vérifier page, ressources JS, sauvegarde/restauration dans un profil de test, cache/service worker et en-têtes HTTP.
5. Conserver l'ancien commit et vérifier qu'un rollback de code ne touche pas les données. Aucun rollback de base n'est fourni par un rollback Render.

Le passage à un unique écrivain de `robot-state.json` nécessite la PR d'automatisation ciblant `main`. Une fusion de la seule PR application ne règle pas cette concurrence. Ne pas modifier la limite enregistrée de 50 % sans décision explicite sur le risque souhaité.
