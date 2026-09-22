# Jobalso Backend

## Setup local

### Prérequis
- Docker Desktop installé et lancé
- Python 3.x + venv
- Git

### Installation

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

3. Créer l'environnement virtuel Python
```bash
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   pip install -r requirements.txt
```

4. Lancer les services Docker (PostgreSQL + pgAdmin + MinIO)
```bash
   docker-compose up -d
```
   ⚠️ Au tout premier démarrage, attendre quelques secondes que PostgreSQL finisse son initialisation avant de lancer les migrations (l'extension `pgvector` est activée automatiquement via `init/001_extensions.sql`).

5. Appliquer les migrations
```bash
   alembic upgrade head
```
   Si ça échoue avec une erreur de connexion au tout premier lancement, réessayer après quelques secondes.

6. Lancer le serveur
```bash
   uvicorn app.main:app --reload
```

### Accès aux services

| Service | URL | Identifiants |
|---|---|---|
| API FastAPI | http://localhost:8000 | - |
| pgAdmin | http://localhost:5050 | Voir `PGADMIN_EMAIL` / `PGADMIN_PASSWORD` dans `.env` |
| MinIO Console | http://localhost:9001 | Voir `MINIO_ROOT_USER` / `MINIO_ROOT_PASSWORD` dans `.env` |

### Connecter pgAdmin à la base

1. Ouvrir http://localhost:5050 et se connecter
2. Clic droit sur **Servers** → **Register** → **Server...**
3. Onglet **General** : nom au choix (ex: `jobalso_db`)
4. Onglet **Connection** :
   - Host : `db` (nom du service Docker, pas `localhost`)
   - Port : `5432`
   - Maintenance database : valeur de `POSTGRES_DB`
   - Username : valeur de `POSTGRES_USER`
   - Password : valeur de `POSTGRES_PASSWORD`

### Reset complet de l'environnement

```bash
docker-compose down -v
docker-compose up -d
alembic upgrade head
```