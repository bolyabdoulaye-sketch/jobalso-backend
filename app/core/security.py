import hashlib
import hmac
import secrets
import time
import uuid
from datetime import timedelta

import bcrypt
import jwt

from app.core.config import settings
from app.core.dates import utcnow

ALGORITHME = "HS256"
BCRYPT_MAX_OCTETS = 72


# ------------------------------------------------------------------
# Mots de passe
# ------------------------------------------------------------------

def hash_password(password: str) -> str:
    # bcrypt ignore tout au-delà de 72 octets : les schémas refusent déjà
    # ces mots de passe, ceci n'est qu'une garde supplémentaire.
    data = password.encode()
    if len(data) > BCRYPT_MAX_OCTETS:
        raise ValueError("Mot de passe trop long")
    return bcrypt.hashpw(data, bcrypt.gensalt()).decode()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    # Compatible avec les empreintes $2b$ produites auparavant par passlib.
    try:
        return bcrypt.checkpw(plain_password.encode(), hashed_password.encode())
    except ValueError:
        return False


# ------------------------------------------------------------------
# Jeton d'accès (JWT court)
# ------------------------------------------------------------------

def create_access_token(subject: str, expires_minutes: int | None = None) -> str:
    minutes = expires_minutes or settings.ACCESS_TOKEN_MINUTES
    maintenant = utcnow()
    payload = {
        "sub": subject,
        "type": "access",
        "iat": maintenant,
        "exp": maintenant + timedelta(minutes=minutes),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHME)


def decode_access_token(token: str) -> dict | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHME])
    except jwt.PyJWTError:
        return None
    # Les anciens jetons (sans "type") restent acceptés jusqu'à leur expiration.
    if payload.get("type", "access") != "access":
        return None
    return payload


# ------------------------------------------------------------------
# Jeton de rafraîchissement (opaque, stocké haché en base)
# ------------------------------------------------------------------

def generate_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# ------------------------------------------------------------------
# Jetons signés à usage unique (réinitialisation, vérification d'email)
# ------------------------------------------------------------------

def _signer(usage: str, payload: str, lien: str) -> str:
    # "lien" rattache le jeton à un état du compte : pour la réinitialisation,
    # c'est l'empreinte du mot de passe, donc le jeton meurt dès qu'il a servi.
    cle = f"{settings.SECRET_KEY}:{lien}".encode()
    return hmac.new(cle, f"{usage}:{payload}".encode(), hashlib.sha256).hexdigest()


def make_signed_token(usage: str, user_id: uuid.UUID, lien: str, duree_secondes: int) -> str:
    expire = int(time.time()) + duree_secondes
    payload = f"{user_id}.{expire}"
    return f"{payload}.{_signer(usage, payload, lien)}"


def read_signed_token_user_id(token: str) -> uuid.UUID | None:
    """Lit l'id porté par le jeton, sans vérifier la signature."""
    try:
        return uuid.UUID(token.split(".", 1)[0])
    except (ValueError, IndexError, AttributeError):
        return None


def verify_signed_token(usage: str, token: str, user_id: uuid.UUID, lien: str) -> bool:
    try:
        user_id_str, expire_str, signature = token.split(".", 2)
        if not hmac.compare_digest(user_id_str, str(user_id)):
            return False
        if int(expire_str) < time.time():
            return False
        attendu = _signer(usage, f"{user_id_str}.{expire_str}", lien)
        return hmac.compare_digest(signature, attendu)
    except (ValueError, AttributeError):
        return False
