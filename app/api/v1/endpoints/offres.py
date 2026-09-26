from datetime import datetime
import secrets
from typing import List
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_recruteur, get_current_user
from app.models import Offre, Recruteur, Utilisateur
from app.schemas.offres_schemas import OffreCreate, OffreRead, OffreUpdate


def generate_public_token(length: int = 32) -> str:
    """Génère un token public unique pour les liens de candidature."""
    return secrets.token_urlsafe(length)

router = APIRouter(prefix="/offres", tags=["Offres d'emploi"])


@router.post("/", response_model=OffreRead, status_code=status.HTTP_201_CREATED)
async def creer_une_offre(
    data: OffreCreate,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Seul un recruteur peut créer une offre.
    Elle est automatiquement liée à son entreprise avec un token public pour candidature externe.
    """
    nouvelle_offre = Offre(
        **data.model_dump(),
        id_recruteur=current_recruteur.id_recruteur,
        public_token=generate_public_token()
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


@router.patch("/{id_offre}", response_model=OffreRead)
async def modifier_offre(
    id_offre: UUID,
    data: OffreUpdate,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Modifier une offre existante (uniquement par le recruteur propriétaire).
    """
    query = select(Offre).where(
        Offre.id_offre == id_offre,
        Offre.id_recruteur == current_recruteur.id_recruteur
    )
    result = await db.execute(query)
    offre = result.scalar_one_or_none()

    if not offre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable ou vous n'êtes pas autorisé à la modifier."
        )

    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(offre, key, value)

    await db.commit()
    await db.refresh(offre)
    return offre


@router.delete("/{id_offre}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_offre(
    id_offre: UUID,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprimer une offre (soft delete : marque comme inactive avec date_suppression).
    """
    query = select(Offre).where(
        Offre.id_offre == id_offre,
        Offre.id_recruteur == current_recruteur.id_recruteur
    )
    result = await db.execute(query)
    offre = result.scalar_one_or_none()

    if not offre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable ou vous n'êtes pas autorisé à la supprimer."
        )

    offre.status = False
    offre.date_suppression = datetime.utcnow()

    await db.commit()


@router.post("/{id_offre}/publier", response_model=OffreRead)
async def publier_offre(
    id_offre: UUID,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Publier une offre (mettre status à True).
    Seul le recruteur propriétaire peut publier son offre.
    Génère un token public si ce n'est pas déjà fait.
    """
    query = select(Offre).where(
        Offre.id_offre == id_offre,
        Offre.id_recruteur == current_recruteur.id_recruteur
    )
    result = await db.execute(query)
    offre = result.scalar_one_or_none()

    if not offre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable ou vous n'êtes pas autorisé à la publier."
        )

    offre.status = True
    offre.date_publication = datetime.utcnow()
    
    # Générer un token public si ce n'est pas déjà fait
    if not offre.public_token:
        offre.public_token = generate_public_token()

    await db.commit()
    await db.refresh(offre)
    return offre
