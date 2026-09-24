# Jobalso Backend

## Stack technique
- FastAPI + SQLAlchemy + Alembic
- PostgreSQL 16 avec extension pgvector
- MinIO (stockage S3-compatible pour les CV)
- pgAdmin (administration de la base)

Tout tourne en conteneurs Docker : API, base de données, pgAdmin et MinIO.

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

Dans ce cas, garder `db`, `pgadmin` et `minio` lancés via Docker (`docker-compose up -d db pgadmin minio`), mais adapter `DATABASE_URL` et `MINIO_ENDPOINT` dans `.env` pour utiliser `localhost` au lieu des noms de service Docker.