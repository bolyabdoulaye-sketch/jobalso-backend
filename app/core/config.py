"""
Configuration centralisée de l'application.

Toutes les valeurs proviennent du fichier .env (voir .env.example à la racine).
Ne jamais coder une valeur de config en dur ailleurs dans le code : on passe
toujours par `settings`.
"""
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=Path(__file__).resolve().parents[2] / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ── Environnement ────────────────────────────────────────────
    app_env: str = "development"
    app_debug: bool = True
    cors_origins: list[str] = []

    # ── Base de données ──────────────────────────────────────────
    database_url: str

    @property
    def async_database_url(self) -> str:
        """URL PostgreSQL compatible avec SQLAlchemy async."""
        if self.database_url.startswith("postgresql+asyncpg://"):
            return self.database_url
        if self.database_url.startswith("postgresql+psycopg://"):
            return self.database_url.replace("postgresql+psycopg://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        raise ValueError("DATABASE_URL doit utiliser PostgreSQL.")

    # ── MinIO ────────────────────────────────────────────────────
    minio_endpoint: str
    minio_root_user: str
    minio_root_password: str
    minio_bucket_cv: str
    minio_secure: bool = False

    # ── JWT ──────────────────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7


@lru_cache
def get_settings() -> Settings:
    """
    Mise en cache : la config n'est lue qu'une seule fois, pas à chaque
    injection de dépendance FastAPI.
    """
    return Settings()


settings = get_settings()
