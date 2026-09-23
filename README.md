# KP Cars — gestion du stock

Application privée pour suivre le stock de véhicules. Les annonces externes et les API de sourcing sont en attente.

## Fonctions

- Ajouter, modifier et supprimer des véhicules.
- Suivre l'année, le kilométrage, le prix d'achat, les frais, le statut et les notes.
- Consulter les coûts engagés et la marge de revente estimée.
- Rechercher, filtrer par statut et trier le stock.
- Enregistrer les données partagées dans PostgreSQL.

## Configuration locale

1. Installer Node.js 20 ou plus récent.
2. Copier `.env.example` dans `.env` et y renseigner `DATABASE_URL`, `APP_USER` et `APP_PASSWORD`.
3. Ouvrir un terminal dans ce dossier et lancer `npm install`, puis `npm start`.
4. Ouvrir `http://localhost:3000` et saisir les identifiants définis dans `.env` sur l’écran de connexion.

Au premier démarrage, l'application crée automatiquement la table `vehicles`. La connexion web expire après 8 heures. Le fichier `.env` ne doit jamais être ajouté à GitHub.

## Déploiement Render

Le service web doit recevoir les variables secrètes `DATABASE_URL`, `APP_USER` et `APP_PASSWORD`. Pour un service Render situé dans la même région que PostgreSQL, utiliser l'URL de connexion **interne** de la base.

La base Render gratuite choisie pour ce MVP expire le **23 octobre 2026**. Elle n'inclut pas de sauvegardes. Exporter les données et passer à une base payante avant cette date pour conserver le stock.
