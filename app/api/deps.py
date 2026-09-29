import uuid
from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.utilisateur import Utilisateur, StatusUtilisateur, TypeUtilisateur
from app.models.membre_organisation import (
    MembreOrganisation,
    RoleOrganisation,
)
from app.models.organisation import Organisation
from app.models.recruteur import Recruteur


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> Utilisateur:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user_uuid = _uuid_ou_none(user_id)
    if user_uuid is None:
        raise credentials_exception

    user = db.get(Utilisateur, user_uuid)

    if user is None:
        raise credentials_exception

    # JA-007 : un jeton reste valable jusqu'a son expiration meme si le compte
    # est desactive/supprime entre-temps. On revalide le statut a chaque
    # requete protegee, pas seulement a la connexion.
    if user.status == StatusUtilisateur.SUPPRIME:
        raise HTTPException(status_code=403, detail="Compte supprime")

    if user.status == StatusUtilisateur.INACTIF:
        raise HTTPException(status_code=403, detail="Compte inactif")

    return user


def _uuid_ou_none(valeur: str) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(valeur))
    except ValueError:
        return None


def require_role(*allowed_roles):
    def role_checker(
        current_user: Utilisateur = Depends(get_current_user),
    ) -> Utilisateur:
        if current_user.type_utilisateur not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Acces refuse : role insuffisant",
            )

        return current_user

    return role_checker


def get_current_recruteur(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
) -> Recruteur:
    recruteur = db.scalar(
        select(Recruteur).where(Recruteur.id_utilisateur == current_user.id_utilisateur)
    )
    if recruteur is None:
        raise HTTPException(status_code=404, detail="Profil recruteur introuvable")
    return recruteur


def get_current_membership(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
) -> MembreOrganisation:
    # Regle produit : un recruteur appartient a une seule organisation.
    membre = db.scalar(
        select(MembreOrganisation)
        .where(MembreOrganisation.id_utilisateur == current_user.id_utilisateur)
        .order_by(MembreOrganisation.date_ajout.asc())
        .limit(1)
    )

    if membre is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur non membre d'une organisation",
        )

    return membre


def get_current_organisation(
    membership: MembreOrganisation = Depends(get_current_membership),
    db: Session = Depends(get_db),
) -> Organisation:
    organisation = db.get(Organisation, membership.id_organisation)

    if organisation is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Organisation introuvable",
        )

    return organisation


def require_organisation_role(*allowed_roles: RoleOrganisation):
    def organisation_role_checker(
        membership: MembreOrganisation = Depends(get_current_membership),
    ) -> MembreOrganisation:
        if membership.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permissions insuffisantes pour cette organisation",
            )

        return membership

    return organisation_role_checker
