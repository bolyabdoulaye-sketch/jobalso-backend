"""
Sécurité applicative : hachage bcrypt des mots de passe (JA-003) et
émission/validation des JWT d'accès et de rafraîchissement (JA-005).
"""
from datetime import datetime, timedelta, timezone
from typing import Literal
from uuid import UUID

import bcrypt
import jwt

from app.core.config import settings

# ─────────────────────────── Mots de passe ───────────────────────────

def hash_password(mot_de_passe: str) -> str:
    """Retourne le hash bcrypt à stocker dans utilisateur.mot_de_passe_hash."""
    sel = bcrypt.gensalt()
    return bcrypt.hashpw(mot_de_passe.encode("utf-8"), sel).decode("utf-8")


def verify_password(mot_de_passe: str, mot_de_passe_hash: str) -> bool:
    """Compare un mot de passe en clair à son hash stocké."""
    return bcrypt.checkpw(mot_de_passe.encode("utf-8"), mot_de_passe_hash.encode("utf-8"))


# ─────────────────────────────── JWT ──────────────────────────────────

def _create_token(sub: UUID, expires_delta: timedelta, token_type: Literal["access", "refresh"]) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(sub),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(id_utilisateur: UUID) -> str:
    return _create_token(
        id_utilisateur,
        timedelta(minutes=settings.access_token_expire_minutes),
        "access",
    )


def create_refresh_token(id_utilisateur: UUID) -> str:
    return _create_token(
        id_utilisateur,
        timedelta(days=settings.refresh_token_expire_days),
        "refresh",
    )


def decode_token(token: str) -> dict:
    """
    Décode et valide un JWT. Lève jwt.PyJWTError (ExpiredSignatureError,
    InvalidTokenError, ...) si le token est invalide ou expiré — à capturer
    dans les dépendances FastAPI (voir app/deps.py).
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


# ─────────────────────── Hash de refresh token (session) ───────────────────
# bcrypt limite l'entrée à 72 octets : inadapté à un JWT complet. On utilise
# donc un simple sha256 pour stocker/retrouver le refresh token en base
# (session.refresh_token_hash), uniquement à des fins de révocation.
import hashlib


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()