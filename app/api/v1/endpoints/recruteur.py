from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_db
from app.models.recruteur import Recruteur
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.schemas.recruteur import (
    PersonaRecruteurRead,
    PersonaRecruteurUpdate,
)

router = APIRouter(prefix="/recruteur", tags=["recruteur"])


def _get_recruteur(
    current_user: Utilisateur,
    db: Session,
) -> Recruteur:
    if current_user.type_utilisateur != TypeUtilisateur.RECRUTEUR:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acces reserve aux recruteurs.",
        )

    recruteur = (
        db.query(Recruteur)
        .filter(Recruteur.id_utilisateur == current_user.id_utilisateur)
        .first()
    )

    if recruteur is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil recruteur introuvable.",
        )

    return recruteur


@router.get(
    "/persona",
    response_model=PersonaRecruteurRead,
)
def get_persona(
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recruteur = _get_recruteur(current_user, db)
    return {"persona": recruteur.persona}


@router.put(
    "/persona",
    response_model=PersonaRecruteurRead,
)
def update_persona(
    data: PersonaRecruteurUpdate,
    current_user: Utilisateur = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recruteur = _get_recruteur(current_user, db)

    recruteur.persona = data.persona.value
    db.commit()
    db.refresh(recruteur)

    return {"persona": recruteur.persona}
