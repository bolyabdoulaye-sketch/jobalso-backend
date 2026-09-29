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