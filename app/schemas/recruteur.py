from enum import Enum

from pydantic import BaseModel


class PersonaRecruteur(str, Enum):
    PME = "pme"
    ENTREPRENEUR = "entrepreneur"
    RH = "rh"
    RECRUTEUR = "recruteur"
    GESTIONNAIRE = "gestionnaire"


class PersonaRecruteurUpdate(BaseModel):
    persona: PersonaRecruteur


class PersonaRecruteurRead(BaseModel):
    persona: PersonaRecruteur | None