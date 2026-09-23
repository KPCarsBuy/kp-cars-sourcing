# KP Cars — gestion du stock (MVP)

Première version centrée sur la gestion manuelle des véhicules. Les annonces externes et les API sont volontairement mises en attente.

## Fonctionnalités

- Ajouter, modifier et supprimer des véhicules.
- Suivre année, kilométrage, prix d'achat, autres frais, revente prévue, statut et notes.
- Voir les coûts engagés et les marges prévisionnelles du stock.
- Rechercher, filtrer par statut et trier les véhicules.

## Lancer sur PC

1. Installer Node.js 20 ou plus récent.
2. Ouvrir un terminal dans ce dossier et lancer `npm install`.
3. Lancer `npm start`.
4. Ouvrir `http://localhost:3000` dans le navigateur.

Les données sont enregistrées dans le stockage local du navigateur : elles restent sur ce navigateur et cet appareil. Elles ne sont pas encore synchronisées ni sauvegardées sur un serveur. Une base de données et des comptes utilisateur seront nécessaires avant un usage multi-appareils ou partagé.
