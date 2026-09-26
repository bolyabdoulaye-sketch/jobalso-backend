"""
Endpoints pour la banque de profils (accessible uniquement aux recruteurs).
Seuls les candidats ayant donné leur consentement apparaissent dans cette banque.
"""
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_current_recruteur, get_db
from app.models import CV, Candidat, Utilisateur, Recruteur, Offre, Resultat, MiniStatusUtilisateurEnum
from app.schemas.cv_schemas import CandidatBanqueProfil
from app.services.minio_service import get_presigned_url

router = APIRouter(prefix="/recruteur", tags=["Banque de Profils"])


@router.get("/banque-profils", response_model=List[CandidatBanqueProfil])
async def lister_banque_profils(
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    competences: Optional[str] = Query(default=None),
):
    """
    Liste les candidats qui ont donné leur consentement pour apparaître dans la banque de profils.
    Accessible uniquement aux recruteurs.
    
    Args:
        competences: Filtre par compétence (recherche exacte dans la liste des compétences)
    """
    # Requête de base : candidats avec consentement actif
    query = (
        select(Candidat, CV, Utilisateur)
        .join(Utilisateur, Candidat.id_utilisateur == Utilisateur.id_utilisateur)
        .outerjoin(CV, Candidat.id_candidat == CV.id_candidat)
        .where(
            Candidat.consentement_banque_profils == True,
            Utilisateur.status == MiniStatusUtilisateurEnum.actif
        )
        .order_by(CV.date_creation.desc() if CV.date_creation else Candidat.id_candidat)
        .limit(limit)
        .offset(offset)
    )

    # Filtre par compétences si fourni
    if competences:
        query = query.where(CV.competences.contains([competences]))

    result = await db.execute(query)
    rows = result.all()

    resultats = []
    for candidat, cv, utilisateur in rows:
        cv_url = None
        if cv and cv.url_cv:
            cv_url = await run_in_threadpool(get_presigned_url, cv.url_cv)

        resultat = CandidatBanqueProfil(
            id_candidat=candidat.id_candidat,
            nom_prenom=utilisateur.nom_prenom,
            email=utilisateur.email,
            resume_cv=cv.resume_cv if cv else None,
            competences=cv.competences if cv else None,
            experience=cv.experience if cv else None,
            education=cv.education if cv else None,
            langues=cv.langues if cv else None,
            domaine_etude=cv.domaine_etude if cv else None,
            cv_id=cv.id_cv if cv else None,
            cv_url_presignee=cv_url,
            date_creation=cv.date_creation if cv else None
        )
        resultats.append(resultat)

    return resultats


@router.get("/banque-profils/{id_cv}", response_model=CandidatBanqueProfil)
async def details_profil_banque(
    id_cv: UUID,
    current_recruteur: Recruteur = Depends(get_current_recruteur),
    db: AsyncSession = Depends(get_db)
):
    """
    Détails d'un profil candidat de la banque de profils.
    Accessible uniquement aux recruteurs.
    """
    # Vérifier que le CV existe et que le candidat a donné son consentement
    query = (
        select(CV, Candidat, Utilisateur)
        .join(Candidat, CV.id_candidat == Candidat.id_candidat)
        .join(Utilisateur, Candidat.id_utilisateur == Utilisateur.id_utilisateur)
        .where(
            CV.id_cv == id_cv,
            Candidat.consentement_banque_profils == True,
            Utilisateur.status == MiniStatusUtilisateurEnum.actif
        )
    )

    result = await db.execute(query)
    row = result.one_or_none()

    if not row:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profil introuvable ou non disponible dans la banque de profils."
        )

    cv, candidat, utilisateur = row

    # Générer URL pré-signée si disponible
    cv_url = None
    if cv.url_cv:
        cv_url = await run_in_threadpool(get_presigned_url, cv.url_cv)

    return CandidatBanqueProfil(
        id_candidat=candidat.id_candidat,
        nom_prenom=utilisateur.nom_prenom,
        email=utilisateur.email,
        resume_cv=cv.resume_cv,
        competences=cv.competences,
        experience=cv.experience,
        education=cv.education,
        langues=cv.langues,
        domaine_etude=cv.domaine_etude,
        cv_id=cv.id_cv,
        cv_url_presignee=cv_url,
        date_creation=cv.date_creation
    )
