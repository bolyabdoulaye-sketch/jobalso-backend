"""Configuration commune des tests.

Les tests d'intégration utilisent une vraie base PostgreSQL (avec pgvector),
indiquée par TEST_DATABASE_URL. Sans elle, ils sont ignorés et seuls les
tests unitaires tournent.
"""
import os

if os.environ.get("TEST_DATABASE_URL"):
    os.environ["DATABASE_URL"] = os.environ["TEST_DATABASE_URL"]

os.environ.setdefault("DATABASE_URL", "postgresql://test:test@localhost:5432/jobalso_test")
os.environ.setdefault("SECRET_KEY", "cle-de-test-uniquement")
os.environ.setdefault("MINIO_ENDPOINT", "localhost:9000")
os.environ.setdefault("MINIO_ACCESS_KEY", "test")
os.environ.setdefault("MINIO_SECRET_KEY", "test")
os.environ.setdefault("MINIO_BUCKET", "cv-test")
os.environ.setdefault("FRONTEND_URL", "http://front.test")

# Sans base de test, on n'essaie même pas de collecter les tests d'intégration.
collect_ignore_glob = [] if os.environ.get("TEST_DATABASE_URL") else ["integration/*"]
