import logging
from contextlib import asynccontextmanager

import app.models  # noqa: F401

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.storage import ensure_bucket_exists
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Crée le compartiment de stockage au démarrage ; s'il est indisponible,
    # l'API démarre quand même et réessaiera au premier dépôt de CV.
    try:
        ensure_bucket_exists()
    except Exception:
        logger.warning("Stockage objet indisponible au demarrage", exc_info=True)
    yield


app = FastAPI(title="Jobalso API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def read_root():
    return {"status": "ok"}


@app.get("/health")
def health():
    """Sonde de santé : vérifie aussi la connexion à la base."""
    try:
        with SessionLocal() as db:
            db.execute(text("SELECT 1"))
    except Exception:
        return JSONResponse(status_code=503, content={"status": "degraded", "database": "indisponible"})
    return {"status": "ok", "database": "ok"}
