# SHIMIX TRADING — sécurité et état réel

## Mode actuel
- Simulation uniquement : aucune transaction réelle autorisée par l'interface.
- Site statique Render public : il n'existe PAS encore de contrôle d'accès côté serveur.
- Données de la démo et du robot navigateur : localStorage, non chiffrées et non synchronisées.
- Robot autonome distant : GitHub Actions et fichier robot-state.json. Ce fichier ne doit jamais contenir de secrets ni de données personnelles.
- Sauvegarde JSON locale manuelle : non chiffrée. Conserver dans un espace privé; ne pas partager publiquement.
- Aucun service bancaire / exchange ne doit être branché sur le frontend.

## Conditions bloquantes avant argent réel
1. Backend privé authentifié, sessions HTTP-only Secure SameSite, MFA/passkeys, anti-bruteforce, limitation de débit.
2. Base de données avec chiffrement, séparation des comptes, sauvegardes automatiques testées et restauration vérifiée.
3. Clés d'échange uniquement côté serveur dans un coffre de secrets, permissions de lecture/trading limitées, retraits interdits.
4. Ordres réels interdits par défaut avec autorisation explicite et distincte; garde-fous serveur (limites par ordre, perte quotidienne, exposition, arrêt d'urgence).
5. Journal d'audit, alertes, rotation des secrets, surveillance et tests d'intrusion / revue de code.
6. IA sans permissions d'exécuter des transactions ou modifier la production sans approbation et tests.

## Points à traiter
- Les scripts JavaScript sont intégrés dans index.html; CSP stricte nécessite leur externalisation.
- Un service worker ne protège pas les données locales.
- L'application ne peut pas garantir une récupération après effacement du stockage avant mise en place de la synchronisation.
- Ne jamais publier une clé API ou un mot de passe dans GitHub ou dans du JavaScript client.
- Ne pas présenter cette application comme prête au trading réel.
