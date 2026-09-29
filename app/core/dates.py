from datetime import datetime, timezone


def utcnow() -> datetime:
    """Heure UTC sans fuseau, cohérente avec les colonnes DateTime existantes.

    Remplace datetime.utcnow(), dépréciée depuis Python 3.12.
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
