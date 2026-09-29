import hashlib
import hmac
import uuid

from app.core.config import settings


def _sign(payload: str) -> str:
    return hmac.new(
        settings.SECRET_KEY.encode(),
        f"desabonnement:{payload}".encode(),
        hashlib.sha256,
    ).hexdigest()


def make_unsubscribe_token(user_id: uuid.UUID) -> str:
    payload = str(user_id)
    return f"{payload}.{_sign(payload)}"


def read_unsubscribe_token(token: str) -> uuid.UUID | None:
    """Renvoie l'id utilisateur si le jeton est valide, sinon None."""
    try:
        payload, signature = token.rsplit(".", 1)
        if not hmac.compare_digest(signature, _sign(payload)):
            return None
        return uuid.UUID(payload)
    except ValueError:
        return None
