from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_recruteur, get_current_user
from app.models import Offre, Recruteur, Utilisateur
from app.schemas.offres_schemas import OffreCreate, OffreRead

router = APIRouter(prefix="/offres", tags=["Offres d'emploi"])


@router.post("/", response_model=OffreRead, status_code=status.HTTP_201_CREATED)
async def creer_une_offre(
    data: OffreCreate,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Seul un recruteur peut publier une offre.
    Elle est automatiquement liée à son entreprise.
    """
    nouvelle_offre = Offre(
        **data.model_dump(),
        id_recruteur=current_recruteur.id_recruteur
    )
    db.add(nouvelle_offre)
    await db.commit()
    await db.refresh(nouvelle_offre)
    return nouvelle_offre


@router.get("/entreprise", response_model=List[OffreRead])
async def mes_offres_entreprise(
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Récupère toutes les offres associées à l'entreprise du recruteur connecté.
    """
    query = (
        select(Offre)
        .join(Recruteur)
        .where(Recruteur.id_entreprise == current_recruteur.id_entreprise)
        .order_by(Offre.date_publication.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/", response_model=List[OffreRead])
async def lister_toutes_les_offres(
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    _: Utilisateur = Depends(get_current_user)  # Accessible à tout utilisateur connecté (ex: Candidat)
):
    """
    Liste globale des offres disponibles sur la plateforme.
    """
    query = select(Offre).order_by(Offre.date_publication.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    return result.scalars().all()
