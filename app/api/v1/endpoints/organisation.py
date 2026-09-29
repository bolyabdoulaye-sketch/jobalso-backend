from datetime import datetime, timedelta, timezone
from uuid import UUID

import secrets

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_user,
    get_current_organisation,
    get_current_membership,
    require_organisation_role,
)
from app.models.utilisateur import Utilisateur, TypeUtilisateur
from app.models.organisation import Organisation
from app.models.membre_organisation import (
    MembreOrganisation,
    RoleOrganisation,
)
from app.models.invitation_organisation import (
    InvitationOrganisation,
    RoleInvitationOrganisation,
)
from app.schemas.organisation import (
    OrganisationRead,
    MembreOrganisationRead,
    InvitationOrganisationCreate,
    InvitationOrganisationRead,
    InvitationAccept,
    OrganisationMemberDetail,
)


router = APIRouter(
    prefix="/organisation",
    tags=["organisation"],
)


INVITATION_DURATION_DAYS = 7


def generate_invitation_token(db: Session) -> str:
    token = secrets.token_urlsafe(32)

    while db.scalar(
        select(InvitationOrganisation).where(
            InvitationOrganisation.token == token
        )
    ):
        token = secrets.token_urlsafe(32)

    return token


@router.get(
    "",
    response_model=OrganisationRead,
)
def get_my_organisation(
    organisation: Organisation = Depends(get_current_organisation),
):
    """
    Retourne l'organisation de l'utilisateur connecte.
    """
    return organisation


@router.get(
    "/membres",
    response_model=list[OrganisationMemberDetail],
)
def list_organisation_members(
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    """
    Retourne tous les membres de l'organisation.
    """

    rows = (
        db.query(
            MembreOrganisation.id_utilisateur,
            Utilisateur.email,
            Utilisateur.nom_prenom,
            MembreOrganisation.role,
            MembreOrganisation.date_ajout,
        )
        .join(
            Utilisateur,
            Utilisateur.id_utilisateur
            == MembreOrganisation.id_utilisateur,
        )
        .filter(
            MembreOrganisation.id_organisation
            == organisation.id_organisation
        )
        .order_by(MembreOrganisation.date_ajout.asc())
        .all()
    )

    return [
        OrganisationMemberDetail(
            id_utilisateur=row.id_utilisateur,
            email=row.email,
            nom_prenom=row.nom_prenom,
            role=row.role,
            date_ajout=row.date_ajout,
        )
        for row in rows
    ]


@router.post(
    "/invitations",
    response_model=InvitationOrganisationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation_invitation(
    invitation_in: InvitationOrganisationCreate,
    organisation: Organisation = Depends(get_current_organisation),
    membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """
    Cree une invitation pour rejoindre l'organisation.

    Seul un ADMIN peut inviter un nouveau membre.
    """

    email = invitation_in.email.strip().lower()

    existing_user = db.scalar(
        select(Utilisateur).where(
            Utilisateur.email == email
        )
    )

    if existing_user:
        existing_membership = db.scalar(
            select(MembreOrganisation).where(
                MembreOrganisation.id_organisation
                == organisation.id_organisation,
                MembreOrganisation.id_utilisateur
                == existing_user.id_utilisateur,
            )
        )

        if existing_membership:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Cet utilisateur est deja membre de l'organisation",
            )

    existing_invitation = db.scalar(
        select(InvitationOrganisation).where(
            InvitationOrganisation.id_organisation
            == organisation.id_organisation,
            InvitationOrganisation.email == email,
            InvitationOrganisation.date_utilisation.is_(None),
        )
    )

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une invitation active existe deja pour cet email",
        )

    token = generate_invitation_token(db)

    now = datetime.now(timezone.utc).replace(tzinfo=None)
    expiration = now + timedelta(days=INVITATION_DURATION_DAYS)

    invitation = InvitationOrganisation(
        id_organisation=organisation.id_organisation,
        email=email,
        role=invitation_in.role,
        token=token,
        date_creation=now,
        date_expiration=expiration,
        date_utilisation=None,
    )

    db.add(invitation)
    db.commit()
    db.refresh(invitation)

    return invitation


@router.get(
    "/invitations",
    response_model=list[InvitationOrganisationRead],
)
def list_organisation_invitations(
    organisation: Organisation = Depends(get_current_organisation),
    db: Session = Depends(get_db),
):
    """
    Retourne les invitations de l'organisation.
    """

    return (
        db.query(InvitationOrganisation)
        .filter(
            InvitationOrganisation.id_organisation
            == organisation.id_organisation
        )
        .order_by(
            InvitationOrganisation.date_creation.desc()
        )
        .all()
    )


@router.delete(
    "/invitations/{invitation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def cancel_organisation_invitation(
    invitation_id: UUID,
    organisation: Organisation = Depends(get_current_organisation),
    membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """
    Annule une invitation qui n'a pas encore ete utilisee.
    """

    invitation = (
        db.query(InvitationOrganisation)
        .filter(
            InvitationOrganisation.id_invitation == invitation_id,
            InvitationOrganisation.id_organisation
            == organisation.id_organisation,
        )
        .first()
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation introuvable",
        )

    if invitation.date_utilisation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette invitation a deja ete utilisee",
        )

    db.delete(invitation)
    db.commit()


@router.post(
    "/invitations/accept",
    response_model=MembreOrganisationRead,
)
def accept_organisation_invitation(
    invitation_in: InvitationAccept,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Accepte une invitation avec le token recu.

    Le compte connecte doit correspondre a l'adresse email invitee.
    """

    invitation = db.scalar(
        select(InvitationOrganisation).where(
            InvitationOrganisation.token == invitation_in.token
        )
    )

    if not invitation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation introuvable ou invalide",
        )

    if invitation.date_utilisation is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cette invitation a deja ete utilisee",
        )

    now = datetime.now(timezone.utc).replace(tzinfo=None)

    if invitation.date_expiration <= now:
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="Cette invitation a expire",
        )

    if current_user.email.strip().lower() != invitation.email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cette invitation ne correspond pas au compte connecte",
        )

    existing_membership = db.scalar(
        select(MembreOrganisation).where(
            MembreOrganisation.id_organisation
            == invitation.id_organisation,
            MembreOrganisation.id_utilisateur
            == current_user.id_utilisateur,
        )
    )

    if existing_membership:
        invitation.date_utilisation = now
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vous etes deja membre de cette organisation",
        )

    membership = MembreOrganisation(
        id_organisation=invitation.id_organisation,
        id_utilisateur=current_user.id_utilisateur,
        role=RoleOrganisation(invitation.role.value),
        date_ajout=now,
    )

    db.add(membership)

    invitation.date_utilisation = now

    db.commit()
    db.refresh(membership)

    return membership


@router.patch(
    "/membres/{user_id}/role",
    response_model=MembreOrganisationRead,
)
def change_member_role(
    user_id: UUID,
    role: RoleOrganisation,
    organisation: Organisation = Depends(get_current_organisation),
    current_membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """
    Modifie le role d'un membre.

    Seul un ADMIN peut modifier les roles.
    """

    membership = db.scalar(
        select(MembreOrganisation).where(
            MembreOrganisation.id_organisation
            == organisation.id_organisation,
            MembreOrganisation.id_utilisateur == user_id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membre introuvable",
        )

    if membership.id_utilisateur == current_membership.id_utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un administrateur ne peut pas modifier son propre role",
        )

    membership.role = role

    db.commit()
    db.refresh(membership)

    return membership


@router.delete(
    "/membres/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def remove_organisation_member(
    user_id: UUID,
    organisation: Organisation = Depends(get_current_organisation),
    current_membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """
    Retire un membre de l'organisation.

    Seul un ADMIN peut retirer un membre.
    """

    membership = db.scalar(
        select(MembreOrganisation).where(
            MembreOrganisation.id_organisation
            == organisation.id_organisation,
            MembreOrganisation.id_utilisateur == user_id,
        )
    )

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Membre introuvable",
        )

    if membership.id_utilisateur == current_membership.id_utilisateur:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Un administrateur ne peut pas se retirer lui-meme",
        )

    db.delete(membership)
    db.commit()