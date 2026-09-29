from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str
    SECRET_KEY: str

    # Jetons de connexion : accès court, rafraîchissement long (rotation à chaque usage)
    ACCESS_TOKEN_MINUTES: int = 15
    REFRESH_TOKEN_DAYS: int = 14

    MINIO_ENDPOINT: str
    MINIO_ACCESS_KEY: str
    MINIO_SECRET_KEY: str
    MINIO_BUCKET: str
    MINIO_SECURE: bool = False  # True en production (https)

    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = "no-reply@jobalso.com"
    SMTP_TLS: bool = False

    API_PUBLIC_URL: str = "http://localhost:8000"
    FRONTEND_URL: str = "http://localhost:3000"
    # Origines autorisées par CORS, séparées par des virgules. Vide = FRONTEND_URL seul.
    CORS_ORIGINS: str = ""

    # Limitation du nombre de requêtes (mémoire du processus)
    RATE_LIMIT_ENABLED: bool = True

    @field_validator("SECRET_KEY")
    @classmethod
    def _secret_non_vide(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("SECRET_KEY ne doit pas etre vide")
        return value

    @property
    def cors_origins(self) -> list[str]:
        origines = [o.strip().rstrip("/") for o in self.CORS_ORIGINS.split(",") if o.strip()]
        return origines or [self.FRONTEND_URL.rstrip("/")]


settings = Settings()
