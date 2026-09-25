import hashlib
import hmac
import time
import uuid

from app.core.config import settings
from app.models.utilisateur import Utilisateur

DUREE_VALIDITE_SECONDES = 30 * 60  # 30 minutes


def _sign(payload: str, mot_de_passe_hash: str) -> str:
    # La cle de signature inclut le hash du mot de passe actuel : des que le
    # mot de passe change, tout jeton emis avant devient invalide de lui-meme.
    cle = f"{settings.SECRET_KEY}:{mot_de_passe_hash}".encode()
    return hmac.new(cle, f"reset:{payload}".encode(), hashlib.sha256).hexdigest()


def make_reset_token(utilisateur: Utilisateur) -> str:
    payload = f"{utilisateur.id_utilisateur}.{int(time.time())}"
    signature = _sign(payload, utilisateur.mot_de_passe)
    return f"{payload}.{signature}"


def read_reset_token(token: str, utilisateur: Utilisateur) -> bool:
    """Verifie le jeton pour cet utilisateur precis (id + expiration + signature)."""
    try:
        user_id_str, emis_str, signature = token.split(".", 2)
        if not hmac.compare_digest(user_id_str, str(utilisateur.id_utilisateur)):
            return False
        emis = int(emis_str)
        if time.time() - emis > DUREE_VALIDITE_SECONDES:
            return False
        payload = f"{user_id_str}.{emis_str}"
        return hmac.compare_digest(signature, _sign(payload, utilisateur.mot_de_passe))
    except (ValueError, AttributeError):
        return False


def extract_user_id(token: str) -> uuid.UUID | None:
    """Lit l'id utilisateur porte par le jeton, sans encore verifier la signature."""
    try:
        user_id_str = token.split(".", 1)[0]
        return uuid.UUID(user_id_str)
    except (ValueError, IndexError):
        return None
