"""Logique de compte partagée : organisation par défaut, sessions, jetons signés."""
import uuid
from datetime import timedelta
from urllib.parse import quote

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.dates import utcnow
from app.core.security import (
    create_access_token,
    generate_refresh_token,
    hash_token,
    make_signed_token,
    read_signed_token_user_id,
    verify_signed_token,
)
from app.models.membre_organisation import MembreOrganisation, RoleOrganisation
from app.models.organisation import Organisation
from app.models.session_utilisateur import SessionUtilisateur
from app.models.utilisateur import Utilisateur

DUREE_RESET_SECONDES = 30 * 60
DUREE_ACTIVATION_SECONDES = 7 * 24 * 3600
DUREE_VERIFICATION_SECONDES = 7 * 24 * 3600


# ------------------------------------------------------------------
# Organisation
# ------------------------------------------------------------------

def creer_organisation(db: Session, utilisateur: Utilisateur, nom: str | None) -> Organisation:
    """Crée une organisation dont l'utilisateur est ADMIN (JA-008)."""
    nom_final = (nom or "").strip() or f"Organisation de {utilisateur.nom_prenom}"
    organisation = Organisation(nom=nom_final[:255])
    db.add(organisation)
    db.flush()
    db.add(
        MembreOrganisation(
            id_organisation=organisation.id_organisation,
            id_utilisateur=utilisateur.id_utilisateur,
            role=RoleOrganisation.ADMIN,
        )
    )
    return organisation


def adhesion(db: Session, utilisateur: Utilisateur) -> MembreOrganisation | None:
    return db.scalar(
        select(MembreOrganisation)
        .where(MembreOrganisation.id_utilisateur == utilisateur.id_utilisateur)
        .order_by(MembreOrganisation.date_ajout.asc())
        .limit(1)
    )


# ------------------------------------------------------------------
# Sessions (jetons de rafraîchissement)
# ------------------------------------------------------------------

def ouvrir_session(db: Session, utilisateur: Utilisateur) -> tuple[str, str]:
    """Crée une session et retourne (access_token, refresh_token). Ne commit pas."""
    refresh_token = generate_refresh_token()
    db.add(
        SessionUtilisateur(
            id_utilisateur=utilisateur.id_utilisateur,
            token_hash=hash_token(refresh_token),
            date_expiration=utcnow() + timedelta(days=settings.REFRESH_TOKEN_DAYS),
        )
    )
    access_token = create_access_token(subject=str(utilisateur.id_utilisateur))
    return access_token, refresh_token


def trouver_session(db: Session, refresh_token: str) -> SessionUtilisateur | None:
    return db.scalar(
        select(SessionUtilisateur).where(SessionUtilisateur.token_hash == hash_token(refresh_token))
    )


def revoquer_sessions(db: Session, id_utilisateur: uuid.UUID) -> None:
    db.execute(
        update(SessionUtilisateur)
        .where(
            SessionUtilisateur.id_utilisateur == id_utilisateur,
            SessionUtilisateur.date_revocation.is_(None),
        )
        .values(date_revocation=utcnow())
    )


# ------------------------------------------------------------------
# Jetons signés
# ------------------------------------------------------------------

def jeton_reset(utilisateur: Utilisateur, duree_secondes: int = DUREE_RESET_SECONDES) -> str:
    # Lié à l'empreinte du mot de passe : inutilisable une fois le mot de passe changé.
    return make_signed_token("reset", utilisateur.id_utilisateur, utilisateur.mot_de_passe, duree_secondes)


def utilisateur_du_jeton_reset(db: Session, token: str) -> Utilisateur | None:
    user_id = read_signed_token_user_id(token)
    utilisateur = db.get(Utilisateur, user_id) if user_id else None
    if utilisateur and verify_signed_token("reset", token, utilisateur.id_utilisateur, utilisateur.mot_de_passe):
        return utilisateur
    return None


def _lien_verification(utilisateur: Utilisateur) -> str:
    status = getattr(utilisateur.status, "value", utilisateur.status)
    return f"{utilisateur.email}:{status}"


def jeton_verification(utilisateur: Utilisateur) -> str:
    # Lié à l'email et au statut : inutilisable une fois le compte activé.
    return make_signed_token(
        "verification", utilisateur.id_utilisateur, _lien_verification(utilisateur), DUREE_VERIFICATION_SECONDES
    )


def utilisateur_du_jeton_verification(db: Session, token: str) -> Utilisateur | None:
    user_id = read_signed_token_user_id(token)
    utilisateur = db.get(Utilisateur, user_id) if user_id else None
    if utilisateur and verify_signed_token(
        "verification", token, utilisateur.id_utilisateur, _lien_verification(utilisateur)
    ):
        return utilisateur
    return None


def url_front(chemin: str, token: str) -> str:
    return f"{settings.FRONTEND_URL.rstrip('/')}/{chemin}?token={quote(token)}"
