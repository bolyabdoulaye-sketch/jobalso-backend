FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /code

# Utilisateur sans privilèges : l'API ne tourne jamais en root.
RUN useradd --system --uid 10001 --home-dir /code jobalso

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY --chown=jobalso:jobalso alembic.ini ./
COPY --chown=jobalso:jobalso alembic ./alembic
COPY --chown=jobalso:jobalso app ./app

USER jobalso

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"

# Production : pas de --reload. Les migrations tournent à part
# (service "migrate" de docker-compose, ou job de déploiement).
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
