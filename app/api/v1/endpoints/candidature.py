from datetime import datetime
import io
import zipfile
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, get_current_candidat, get_current_user
from app.models import Candidature, Candidat, Offre, CV
from app.schemas.offres_schemas import CandidatureCreate, CandidatureRead, CandidatureUpdate, CandidatureExterneCreate
from app.core.config import settings
from app.services.minio_service import upload_external_cv, delete_cv
from app.core.storage import get_presigned_url

router = APIRouter(prefix="/candidatures", tags=["Candidatures"])


@router.post("/postuler", response_model=CandidatureRead, status_code=status.HTTP_201_CREATED)
async def candidater_a_offre(
    data: CandidatureCreate,
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db)
):
    """
    Permet à un candidat de postuler à une offre.
    La source_candidature est par défaut 'lien_public'.
    """
    # Vérifier que l'offre existe et est active
    query_offre = select(Offre).where(
        Offre.id_offre == data.id_offre,
        Offre.status == True
    )
    result_offre = await db.execute(query_offre)
    offre = result_offre.scalar_one_or_none()
    
    if not offre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable ou non disponible."
        )
    
    # Vérifier que le CV appartient au candidat si un CV est fourni
    if data.id_cv:
        query_cv = select(CV).where(
            CV.id_cv == data.id_cv,
            CV.id_candidat == current_candidat.id_candidat
        )
        result_cv = await db.execute(query_cv)
        cv = result_cv.scalar_one_or_none()
        
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV introuvable ou ne vous appartient pas."
            )
    
    # Créer la candidature
    nouvelle_candidature = Candidature(
        **data.model_dump(),
        id_candidat=current_candidat.id_candidat
    )
    db.add(nouvelle_candidature)
    await db.commit()
    await db.refresh(nouvelle_candidature)
    return nouvelle_candidature


@router.get("/list_candidatures", response_model=List[CandidatureRead])
async def lister_mes_candidatures(
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Liste toutes les candidatures du candidat connecté.
    """
    query = (
        select(Candidature)
        .where(Candidature.id_candidat == current_candidat.id_candidat)
        .order_by(Candidature.date_candidature.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{id_candidature}/details", response_model=CandidatureRead)
async def get_candidature(
    id_candidature: UUID,
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db)
):
    """
    Récupère une candidature spécifique du candidat connecté.
    """
    query = select(Candidature).where(
        Candidature.id_candidature == id_candidature,
        Candidature.id_candidat == current_candidat.id_candidat
    )
    result = await db.execute(query)
    candidature = result.scalar_one_or_none()
    
    if not candidature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature introuvable ou ne vous appartient pas."
        )
    
    return candidature


@router.patch("/modifier/{id_candidature}", response_model=CandidatureRead)
async def modifier_candidature(
    id_candidature: UUID,
    data: CandidatureUpdate,
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db)
):
    """
    Modifier une candidature (uniquement par le candidat propriétaire).
    """
    query = select(Candidature).where(
        Candidature.id_candidature == id_candidature,
        Candidature.id_candidat == current_candidat.id_candidat
    )
    result = await db.execute(query)
    candidature = result.scalar_one_or_none()
    
    if not candidature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature introuvable ou ne vous appartient pas."
        )
    
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(candidature, key, value)
    
    await db.commit()
    await db.refresh(candidature)
    return candidature


@router.delete("/supprimer/{id_candidature}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_candidature(
    id_candidature: UUID,
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db)
):
    """
    Supprimer une candidature.
    """
    query = select(Candidature).where(
        Candidature.id_candidature == id_candidature,
        Candidature.id_candidat == current_candidat.id_candidat
    )
    result = await db.execute(query)
    candidature = result.scalar_one_or_none()
    
    if not candidature:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Candidature introuvable ou ne vous appartient pas."
        )
    
    await db.delete(candidature)
    await db.commit()


@router.post("/externes/{public_token}", response_model=CandidatureRead, status_code=status.HTTP_201_CREATED)
async def candidater_via_lien_externe(
    public_token: str,
    nom_prenom: Optional[str] = Form(None),
    email: Optional[str] = Form(None),
    telephone: Optional[str] = Form(None),
    message: Optional[str] = Form(None),
    cv_file: Optional[UploadFile] = File(None),
    db: AsyncSession = Depends(get_db)
):
    """
    Permet à un candidat EXTERNE (non connecté) de postuler à une offre via un lien public.
    
    - Le public_token est généré lors de la publication de l'offre
    - La source_candidature est automatiquement définie à 'lien_public'
    - Le candidat peut uploader son CV (PDF ou Word, max 5Mo)
    - Les informations du candidat (nom, email, téléphone) sont stockées directement
    """
    # Trouver l'offre via son public_token
    query_offre = select(Offre).where(
        Offre.public_token == public_token,
        Offre.status == True
    )
    result_offre = await db.execute(query_offre)
    offre = result_offre.scalar_one_or_none()
    
    if not offre:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Offre introuvable ou lien de candidature invalide."
        )
    
    url_cv = None
    
    # Si un CV est uploadé, le traiter
    if cv_file:
        # Validation du type de fichier
        TYPES_AUTORISES = [
            "application/pdf",
            "application/msword",
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        ]
        
        if cv_file.content_type not in TYPES_AUTORISES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Seuls les fichiers PDF et Word sont acceptés.",
            )
        
        # Lire le contenu avec validation de taille
        MAX_CV_SIZE_BYTES = 5 * 1024 * 1024
        chunks: list[bytes] = []
        size = 0
        while chunk := await cv_file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_CV_SIZE_BYTES:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="La taille maximale d'un CV est de 5 Mo.",
                )
            chunks.append(chunk)
        contenu = b"".join(chunks)
        
        if not contenu:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Le fichier envoyé est vide.",
            )
        
        # Validation du contenu
        extension = cv_file.filename.rsplit(".", 1)[-1].lower() if cv_file.filename and "." in cv_file.filename else ""
        expected_types = {
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        if expected_types.get(extension) != cv_file.content_type:
            raise HTTPException(status_code=400, detail="Le type MIME et l'extension ne correspondent pas.")
        
        is_valid = (
            (extension == "pdf" and contenu.startswith(b"%PDF-"))
            or (extension == "doc" and contenu.startswith(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"))
        )
        if extension == "docx" and contenu.startswith(b"PK\x03\x04"):
            try:
                with zipfile.ZipFile(io.BytesIO(contenu)) as document:
                    is_valid = {"[Content_Types].xml", "word/document.xml"}.issubset(document.namelist())
            except zipfile.BadZipFile:
                is_valid = False
        if not is_valid:
            raise HTTPException(status_code=400, detail="Le contenu du CV n'est pas un PDF ou Word valide.")
        
        # Upload vers MinIO pour les candidats externes
        # Utiliser un préfixe spécial pour les CVs externes
        try:
            object_key = await run_in_threadpool(
                upload_external_cv,
                filename=cv_file.filename,
                contenu=contenu,
                content_type=cv_file.content_type,
            )
            url_cv = object_key
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Erreur lors de l'upload du CV: {str(e)}"
            )
    
    # Créer la candidature avec les informations du candidat externe
    nouvelle_candidature = Candidature(
        id_offre=offre.id_offre,
        id_candidat=None,  # Pas de candidat connecté
        id_cv=None,  # Pas de CV dans la table CV (le CV est stocké directement dans MinIO)
        source_candidature='lien_public',
        etape_courante='candidature',
        url_cv=url_cv,
        nom_prenom=nom_prenom,
        email=email,
        telephone=telephone,
        message=message
    )
    db.add(nouvelle_candidature)
    await db.commit()
    await db.refresh(nouvelle_candidature)
    return nouvelle_candidature