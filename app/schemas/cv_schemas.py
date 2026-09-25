from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID
from pydantic import BaseModel, ConfigDict, Field


# 1. Champs de base du CV
class CVBase(BaseModel):
    resume_cv: Optional[str] = None
    experience: Optional[Any] = None              # Format JSON
    education: Optional[Any] = None               # Format JSON
    langues: Optional[Any] = None                 # Format JSONB
    domaine_etude: Optional[Any] = None           # Format JSONB
    competences: Optional[Any] = None             # Format JSONB
    certifications: Optional[Any] = None          # Format JSONB
    entretien: Optional[str] = None
    statut_cv: Optional[str] = None
    url_cv: Optional[str] = None                  # Lien vers le fichier stocké sur MinIO
    cv: Optional[Any] = None                      # Structure JSON globale du CV
    interview: bool = False                       # Champ NOT NULL dans le diagramme
    code_cv: Optional[str] = None
    commentaires_recruteurs: Optional[Any] = None # Format JSONB


# 2. Schéma pour la création d'un CV (POST /cv)
class CVCreate(CVBase):
    pass


# 3. Schéma pour la mise à jour partielle (PATCH /cv/{id_cv})
class CVUpdate(BaseModel):
    resume_cv: Optional[str] = None
    experience: Optional[Any] = None
    education: Optional[Any] = None
    langues: Optional[Any] = None
    domaine_etude: Optional[Any] = None
    competences: Optional[Any] = None
    certifications: Optional[Any] = None
    entretien: Optional[str] = None
    statut_cv: Optional[str] = None
    url_cv: Optional[str] = None
    cv: Optional[Any] = None
    interview: Optional[bool] = None
    code_cv: Optional[str] = None
    commentaires_recruteurs: Optional[Any] = None


# 4. Schéma complet renvoyé par l'API (GET /cv)
class CVRead(CVBase):
    id_cv: UUID
    id_candidat: UUID
    cv_hash: Optional[str] = None
    cv_vector: Optional[List[float]] = None       # Vector 768 dimensions pour pgvector
    date_creation: datetime
    date_modification: Optional[datetime] = None
    url_presignee: Optional[str] = None
    model_config = ConfigDict(from_attributes=True)
