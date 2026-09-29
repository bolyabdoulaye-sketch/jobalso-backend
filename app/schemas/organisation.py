from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.membre_organisation import RoleOrganisation
from app.models.invitation_organisation import RoleInvitationOrganisation


class OrganisationCreate(BaseModel):
    nom: str = Field(min_length=2, max_length=255)


class OrganisationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_organisation: UUID
    nom: str
    date_creation: datetime
    date_modification: datetime | None = None


class MembreOrganisationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_organisation: UUID
    id_utilisateur: UUID
    role: RoleOrganisation
    date_ajout: datetime


class InvitationOrganisationCreate(BaseModel):
    email: EmailStr
    role: RoleInvitationOrganisation = RoleInvitationOrganisation.MEMBRE


class InvitationOrganisationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id_invitation: UUID
    id_organisation: UUID
    email: EmailStr
    role: RoleInvitationOrganisation
    date_creation: datetime
    date_expiration: datetime
    date_utilisation: datetime | None = None


class InvitationAccept(BaseModel):
    token: str = Field(min_length=10, max_length=255)


class OrganisationMemberDetail(BaseModel):
    id_utilisateur: UUID
    email: EmailStr
    nom_prenom: str
    role: RoleOrganisation
    date_ajout: datetime
