import uuid

from pydantic import BaseModel, ConfigDict


class PublicOffreRead(BaseModel):
    id_offre: uuid.UUID
    titre_offre: str
    type_contrat: str | None = None
    resume_offre: str | None = None

    model_config = ConfigDict(from_attributes=True)


class PostulerResponse(BaseModel):
    message: str
