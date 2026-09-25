from datetime import date, datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# 1. Champs de base renseignés lors de la saisie par l'utilisateur / recruteur
class OffreBase(BaseModel):
    titre_offre: str = Field(..., min_length=3, max_length=255)
    description: Optional[Dict[str, Any]]
    type_contrat: Optional[str] = None
    revenu: Optional[float] = None
    entretien: Optional[bool] = False
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    status: Optional[bool] = True
    resume_offre: Optional[str] = None


# 2. Schéma pour la création d'une offre (POST /offres)
class OffreCreate(OffreBase):
    # Les champs générés automatiquement par le serveur (id_recruteur via le JWT, 
    # date_publication, offre_vector via l'IA) ne sont pas demandés au client.
    pass


# 3. Schéma pour la mise à jour partielle (PATCH /offres/{id_offre})
class OffreUpdate(BaseModel):
    titre_offre: Optional[str] = Field(default=None, min_length=3, max_length=255)
    description: Optional[Dict[str, Any]] = None
    type_contrat: Optional[str] = None
    revenu: Optional[float] = None
    entretien: Optional[bool] = None
    date_debut: Optional[date] = None
    date_fin: Optional[date] = None
    status: Optional[bool] = None
    resume_offre: Optional[str] = None


# 4. Schéma complet renvoyé par l'API (GET /offres)
class OffreRead(OffreBase):
    id_offre: UUID
    id_recruteur: UUID
    date_publication: datetime
    date_modification: Optional[datetime] = None
    
    # Champ vectoriel (768 dimensions pour embeddings pgvector)
    offre_vector: Optional[List[float]] = None

    model_config = ConfigDict(from_attributes=True)