# Jobalso Backend

## Stack technique
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL 16 avec extension pgvector
- MinIO (stockage S3-compatible pour les CV)
- pgAdmin (administration de la base)
- Mailpit (serveur SMTP de développement, capture les emails sans les envoyer)

Tout tourne en conteneurs Docker : API, base de données, pgAdmin, MinIO et Mailpit.

## Prérequis
- Docker Desktop installé et lancé
- Git

## Installation

1. Cloner le repo et se placer dans le dossier
```bash
   git clone <url-du-repo>
   cd jobalso-backend
```

2. Créer le fichier `.env` à partir du template
```bash
   cp .env.example .env
```
   Puis remplir les valeurs (demander les vraies valeurs à l'équipe via un canal privé, jamais sur GitHub).

3. Lancer toute la stack
```bash
   docker-compose up -d --build
```
   ⚠️ Au tout premier démarrage, attendre quelques secondes que PostgreSQL finisse son initialisation avant de lancer les migrations (l'extension `pgvector` est activée automatiquement via `init/001_extensions.sql`).

4. Appliquer les migrations
```bash
   docker exec -it jobalso_api alembic upgrade head
```
   Si ça échoue avec une erreur de connexion au tout premier lancement, réessayer après quelques secondes.

C'est prêt. L'API est accessible avec le rechargement automatique activé (`--reload`) : toute modification du code dans `app/` est prise en compte immédiatement, sans relancer le conteneur.

## Accès aux services

| Service | URL | Identifiants |
|---|---|---|
| API FastAPI | http://localhost:8000 | - |
| Documentation Swagger | http://localhost:8000/docs | - |
| pgAdmin | http://localhost:5050 | Voir `PGADMIN_EMAIL` / `PGADMIN_PASSWORD` dans `.env` |
| MinIO Console | http://localhost:9001 | Voir `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` dans `.env` |
| Mailpit (emails de dev) | http://localhost:8025 | - |

Mailpit remplace un vrai fournisseur d'emails en développement : tout email envoyé par l'API (bienvenue, accusé de réception, changement de statut, réinitialisation de mot de passe) apparaît dans cette boîte, sans jamais partir sur Internet. Quand un fournisseur définitif sera choisi, seules les variables `SMTP_*` dans `.env` changeront ; le code applicatif n'a pas à bouger.

## Variables d'environnement notables

En plus des identifiants Postgres/pgAdmin/MinIO habituels :

| Variable | Rôle | Valeur par défaut |
|---|---|---|
| `SMTP_HOST` / `SMTP_PORT` | Serveur SMTP utilisé pour l'envoi d'emails | `mailpit` / `1025` (Docker) |
| `SMTP_FROM` | Adresse d'expéditeur affichée | `no-reply@jobalso.com` |
| `API_PUBLIC_URL` | Base des liens générés par l'API (désabonnement) | `http://localhost:8000` |
| `FRONTEND_URL` | Base des liens vers le frontend (réinitialisation de mot de passe) | `http://localhost:3000` |

## Aperçu des endpoints

- `POST /api/v1/auth/register`, `POST /api/v1/auth/login`, `GET /api/v1/auth/me`
- `POST /api/v1/auth/forgot-password`, `POST /api/v1/auth/reset-password` — mot de passe oublié (JA-004), lien à usage unique valable 30 minutes
- `GET/POST /api/v1/auth/desabonnement` — désabonnement des notifications par email (JA-083, CASL)
- `GET/POST/PUT/DELETE /api/v1/cv/...` — CV du candidat connecté
- `GET/POST/PUT/DELETE /api/v1/offres/...` — offres du recruteur connecté
- `POST /api/v1/offres/matching` — évaluation d'un CV par code, par le recruteur
- `PATCH /api/v1/offres/resultats/{id}/statut` — changement de statut d'une candidature (JA-056), notifie le candidat par email (JA-057)
- `GET /api/v1/candidatures/mes-candidatures` — suivi des candidatures du candidat connecté (JA-059)
- `GET /api/v1/public/offres/{id}`, `POST /api/v1/public/offres/{id}/postuler` — candidature publique sans compte (JA-027), avec accusé de réception (JA-081)

La documentation Swagger (http://localhost:8000/docs) reste la référence à jour pour les schémas de requête/réponse.

## Connecter pgAdmin à la base

1. Ouvrir http://localhost:5050 et se connecter
2. Clic droit sur **Servers** → **Register** → **Server...**
3. Onglet **General** : nom au choix (ex: `jobalso_db`)
4. Onglet **Connection** :
   - Host : `db` (nom du service Docker, pas `localhost`)
   - Port : `5432`
   - Maintenance database : valeur de `POSTGRES_DB`
   - Username : valeur de `POSTGRES_USER`
   - Password : valeur de `POSTGRES_PASSWORD`

## Commandes utiles

Voir les logs de l'API en direct
```bash
docker logs jobalso_api -f
```

Exécuter une commande dans le conteneur API (alembic, tests, shell...)
```bash
docker exec -it jobalso_api bash
```

Créer une nouvelle migration après modification des modèles
```bash
docker exec -it jobalso_api alembic revision --autogenerate -m "description"
docker exec -it jobalso_api alembic upgrade head
```

Arrêter la stack (garde les données)
```bash
docker-compose down
```

Reset complet de l'environnement (supprime toutes les données)
```bash
docker-compose down -v
docker-compose up -d --build
docker exec -it jobalso_api alembic upgrade head
```

## Développement sans Docker pour l'API (optionnel)

Si besoin de lancer l'API en dehors de Docker (autocomplétion IDE, debug local...), un environnement virtuel Python reste utilisable en parallèle :

```bash
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows
pip install -r requirements.txt
```

Dans ce cas, garder `db`, `pgadmin`, `minio` et `mailpit` lancés via Docker (`docker-compose up -d db pgadmin minio mailpit`), mais adapter `DATABASE_URL`, `MINIO_ENDPOINT` et `SMTP_HOST`/`SMTP_PORT` dans `.env` pour utiliser `localhost` au lieu des noms de service Docker.
