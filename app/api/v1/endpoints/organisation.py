from datetime import timedelta
from uuid import UUID

import secrets

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import (
    get_db,
    get_current_membership,
    get_current_organisation,
    require_organisation_role,
    require_role,
)
from app.core.dates import utcnow
from app.core.rate_limit import check_rate_limit
from app.models.offre import Offre
from app.models.utilisateur import Utilisateur, TypeUtilisateur
from app.models.organisation import Organisation
from app.models.membre_organisation import (
    MembreOrganisation,
    RoleOrganisation,
)
from app.models.invitation_organisation import (
    InvitationOrganisation,
)
from app.schemas.organisation import (
    OrganisationCreate,
    OrganisationRead,
    MembreOrganisationRead,
    InvitationOrganisationCreate,
    InvitationOrganisationRead,
    InvitationAccept,
    OrganisationMemberDetail,
)
from app.services import comptes
from app.services.email_compte import send_invitation_email


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


@router.post(
    "",
    response_model=OrganisationRead,
    status_code=status.HTTP_201_CREATED,
)
def create_organisation(
    data: OrganisationCreate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    """
    Cree une organisation pour un recruteur qui n'en a pas
    (par exemple apres avoir ete retire d'une equipe).
    """
    if comptes.adhesion(db, current_user) is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Vous etes deja membre d'une organisation",
        )
    organisation = comptes.creer_organisation(db, current_user, data.nom)
    db.commit()
    db.refresh(organisation)
    return organisation


@router.patch(
    "",
    response_model=OrganisationRead,
)
def rename_organisation(
    data: OrganisationCreate,
    organisation: Organisation = Depends(get_current_organisation),
    membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    organisation.nom = data.nom.strip()
    db.commit()
    db.refresh(organisation)
    return organisation


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
    background_tasks: BackgroundTasks,
    organisation: Organisation = Depends(get_current_organisation),
    membership: MembreOrganisation = Depends(
        require_organisation_role(RoleOrganisation.ADMIN)
    ),
    db: Session = Depends(get_db),
):
    """
    Cree une invitation pour rejoindre l'organisation.

    Seul un ADMIN peut inviter un nouveau membre. Le lien part par email :
    le jeton n'est jamais renvoye par l'API.
    """

    check_rate_limit(f"invitation:{organisation.id_organisation}", 30, 3600)
    email = invitation_in.email.strip().lower()

    existing_user = db.scalar(
        select(Utilisateur).where(
            func.lower(Utilisateur.email) == email
        )
    )

    if existing_user and existing_user.type_utilisateur != TypeUtilisateur.RECRUTEUR:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seul un compte recruteur peut rejoindre une organisation",
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

    now = utcnow()

    existing_invitation = db.scalar(
        select(InvitationOrganisation).where(
            InvitationOrganisation.id_organisation
            == organisation.id_organisation,
            InvitationOrganisation.email == email,
            InvitationOrganisation.date_utilisation.is_(None),
            InvitationOrganisation.date_expiration > now,
        )
    )

    if existing_invitation:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Une invitation active existe deja pour cet email",
        )

    token = generate_invitation_token(db)

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

    background_tasks.add_task(
        send_invitation_email,
        email,
        organisation.nom,
        comptes.url_front("invitation", token),
    )

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
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.RECRUTEUR)),
    db: Session = Depends(get_db),
):
    """
    Accepte une invitation avec le token recu.

    Le compte connecte doit correspondre a l'adresse email invitee.
    Un recruteur n'appartient qu'a une organisation : l'organisation creee
    a son inscription est remplacee si elle est encore vide (lui seul, aucune
    offre) ; sinon il doit d'abord la quitter.
    """
    check_rate_limit(f"accept-invitation:{current_user.id_utilisateur}", 10, 900)

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

    now = utcnow()

    if invitation.date_expiration is None or invitation.date_expiration <= now:
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

    actuelle = comptes.adhesion(db, current_user)
    if actuelle is not None:
        nb_membres = db.scalar(
            select(func.count()).select_from(MembreOrganisation).where(
                MembreOrganisation.id_organisation == actuelle.id_organisation
            )
        )
        nb_offres = db.scalar(
            select(func.count()).select_from(Offre).where(
                Offre.id_organisation == actuelle.id_organisation
            )
        )
        if nb_membres > 1 or nb_offres > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "Vous appartenez deja a une organisation active. "
                    "Quittez-la (POST /organisation/quitter) avant de rejoindre une autre equipe."
                ),
            )
        ancienne = db.get(Organisation, actuelle.id_organisation)
        db.delete(ancienne)
        db.flush()

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


@router.post(
    "/quitter",
    status_code=status.HTTP_204_NO_CONTENT,
)
def leave_organisation(
    membership: MembreOrganisation = Depends(get_current_membership),
    db: Session = Depends(get_db),
):
    """
    Quitte l'organisation. Refuse si cela la laisserait sans administrateur
    ou sans aucun membre (ses offres deviendraient inaccessibles).
    """
    autres = db.scalars(
        select(MembreOrganisation).where(
            MembreOrganisation.id_organisation == membership.id_organisation,
            MembreOrganisation.id_utilisateur != membership.id_utilisateur,
        )
    ).all()

    if not autres:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Vous etes le seul membre : l'organisation ne peut pas rester vide",
        )

    if membership.role == RoleOrganisation.ADMIN and not any(
        m.role == RoleOrganisation.ADMIN for m in autres
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nommez d'abord un autre administrateur",
        )

    db.delete(membership)
    db.commit()


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
