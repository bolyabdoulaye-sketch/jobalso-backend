# Dockerfile pour le backend FastAPI JobAlso
# Utilise une image officielle Python légère
FROM python:3.11-slim
# Variables d'environnement
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Définir le répertoire de travail
WORKDIR /app

# Copier les fichiers de dépendances
COPY requirements.txt .

# Installer les dépendances système nécessaires pour psycopg et asyncpg
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Installer les dépendances Python
RUN pip install --no-cache-dir -r requirements.txt

# Copier le code source
COPY . .

# Créer un utilisateur non-root pour la sécurité
RUN adduser --disabled-password --gecos '' appuser && \
    chown -R appuser:appuser /app
USER appuser

# Exposer le port de l'application
EXPOSE 8000



# Commande de démarrage
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
