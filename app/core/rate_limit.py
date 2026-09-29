"""Limitation simple du nombre de requêtes, en mémoire du processus.

Suffisant pour une instance unique. Avec plusieurs instances, il faudra un
stockage partagé (Redis) : l'interface `limiter(...)` restera la même.
"""
import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, Request, status

from app.core.config import settings

_lock = threading.Lock()
_hits: dict[str, deque[float]] = defaultdict(deque)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "inconnu"


def check_rate_limit(cle: str, max_requetes: int, fenetre_secondes: int, enregistrer: bool = True) -> None:
    """Lève 429 si la limite est atteinte ; sinon compte cette requête (si `enregistrer`)."""
    if not settings.RATE_LIMIT_ENABLED:
        return
    maintenant = time.monotonic()
    with _lock:
        hits = _hits[cle]
        while hits and hits[0] <= maintenant - fenetre_secondes:
            hits.popleft()
        if len(hits) >= max_requetes:
            attente = int(fenetre_secondes - (maintenant - hits[0])) + 1
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Trop de tentatives, reessayez plus tard",
                headers={"Retry-After": str(attente)},
            )
        if enregistrer:
            hits.append(maintenant)


def record_hit(cle: str) -> None:
    """Compte une tentative sans vérifier la limite (ex. : échec de connexion)."""
    if settings.RATE_LIMIT_ENABLED:
        with _lock:
            _hits[cle].append(time.monotonic())


def limiter(nom: str, max_requetes: int, fenetre_secondes: int):
    """Dépendance FastAPI : limite par adresse IP pour une route donnée."""

    def dependance(request: Request) -> None:
        check_rate_limit(f"{nom}:{_client_ip(request)}", max_requetes, fenetre_secondes)

    return dependance


def reset_rate_limits() -> None:
    with _lock:
        _hits.clear()
