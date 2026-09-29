from typing import Generator

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.core.security import decode_access_token
from app.models.utilisateur import Utilisateur, StatusUtilisateur
from app.models.membre_organisation import (
    MembreOrganisation,
    RoleOrganisation,
)
from app.models.organisation import Organisation


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

    user = (
        db.query(Utilisateur)
        .filter(Utilisateur.id_utilisateur == user_id)
        .first()
    )

    if user is None:
        raise credentials_exception

    # JA-007 : un jeton reste valable jusqu'a son expiration (30 min) meme si
    # le compte est desactive/supprime entre-temps. On revalide le statut a
    # chaque requete protegee, pas seulement a la connexion.
    if user.status == StatusUtilisateur.SUPPRIME:
        raise HTTPException(status_code=403, detail="Compte supprime")

    if user.status == StatusUtilisateur.INACTIF:
        raise HTTPException(status_code=403, detail="Compte inactif")

    return user


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


def get_current_membership(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> MembreOrganisation:
    membre = db.scalar(
        select(MembreOrganisation).where(
            MembreOrganisation.id_utilisateur == current_user.id_utilisateur
        )
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
    organisation = db.scalar(
        select(Organisation).where(
            Organisation.id_organisation == membership.id_organisation
        )
    )

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