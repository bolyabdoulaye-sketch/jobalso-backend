import io
import zipfile
from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from app.deps import get_current_candidat, get_db
from app.models import CV, Candidat
from app.schemas.cv_schemas import CVRead
# Importation de votre module MinIO
from app.services.minio_service import delete_cv, get_presigned_url, upload_cv

router = APIRouter(prefix="/cv", tags=["CVs Candidat"])

TYPES_AUTORISES = [
    "application/pdf",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
]
MAX_CV_SIZE_BYTES = 5 * 1024 * 1024


async def read_cv_upload(fichier: UploadFile) -> bytes:
    """Lit un fichier sans accepter plus de 5 Mio en mémoire."""
    chunks: list[bytes] = []
    size = 0
    while chunk := await fichier.read(1024 * 1024):
        size += len(chunk)
        if size > MAX_CV_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="La taille maximale d'un CV est de 5 Mo.",
            )
        chunks.append(chunk)
    return b"".join(chunks)


def validate_cv_content(filename: str | None, content_type: str | None, contenu: bytes) -> None:
    """Contrôle extension, MIME annoncé et signature du document."""
    extension = filename.rsplit(".", 1)[-1].lower() if filename and "." in filename else ""
    expected_types = {
        "pdf": "application/pdf",
        "doc": "application/msword",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    if expected_types.get(extension) != content_type:
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


def normalize_optional_text(value: str | None) -> str | None:
    """Évite qu'une chaîne vide soit considérée comme une valeur unique."""
    return value.strip() or None if value else None


@router.post("/upload_cv", response_model=CVRead, status_code=status.HTTP_201_CREATED)
async def uploader_cv(
    fichier: UploadFile = File(...),
    code_cv: Optional[str] = Form(None),
    interview: bool = Form(False),
    statut_cv: Optional[str] = Form("EN_ATTENTE"),
    resume_cv: Optional[str] = Form(None),
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db),
):
    """
    Uploade le CV dans MinIO et enregistre la clé d'objet en BDD.
    """
    if fichier.content_type not in TYPES_AUTORISES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Seuls les fichiers PDF et Word sont acceptés.",
        )

    contenu = await read_cv_upload(fichier)
    if not contenu:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Le fichier envoyé est vide.",
        )

    # 1. Déposer dans MinIO (exécuté dans un threadpool)
    validate_cv_content(fichier.filename, fichier.content_type, contenu)

    object_key = await run_in_threadpool(
        upload_cv,
        id_candidat=current_candidat.id_candidat,
        filename=fichier.filename,
        contenu=contenu,
        content_type=fichier.content_type,
    )

    # 2. Créer l'entrée en Base de Données
    nouveau_cv = CV(
        id_candidat=current_candidat.id_candidat,
        url_cv=object_key,  # Clé objet MinIO
        code_cv=normalize_optional_text(code_cv),
        interview=interview,
        statut_cv=statut_cv,
        resume_cv=resume_cv,
    )
    db.add(nouveau_cv)
    try:
        await db.commit()
        await db.refresh(nouveau_cv)
    except IntegrityError as exc:
        await db.rollback()
        await run_in_threadpool(delete_cv, object_key=object_key)
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ce code CV est déjà utilisé.",
        ) from exc
    except SQLAlchemyError:
        await db.rollback()
        await run_in_threadpool(delete_cv, object_key=object_key)
        raise

    # 3. Générer l'URL pré-signée pour la réponse HTTP
    presigned_url = await run_in_threadpool(get_presigned_url, object_key)

    # Reconstitution du modèle de réponse
    response_data = CVRead.model_validate(nouveau_cv)
    response_data.url_presignee = presigned_url

    return response_data


@router.get("/mes-cvs", response_model=List[CVRead])
async def lister_mes_cvs(
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    """
    Liste les CVs du candidat connecté avec une URL pré-signée fraîche pour chacun.
    """
    query = (
        select(CV)
        .where(CV.id_candidat == current_candidat.id_candidat)
        .order_by(CV.date_creation.desc())
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(query)
    cvs = result.scalars().all()

    resultats = []
    for cv in cvs:
        cv_dto = CVRead.model_validate(cv)
        if cv.url_cv:
            # Génère une URL pré-signée temporaire pour la lecture
            cv_dto.url_presignee = await run_in_threadpool(get_presigned_url, cv.url_cv)
        resultats.append(cv_dto)

    return resultats


@router.delete("/{id_cv}", status_code=status.HTTP_204_NO_CONTENT)
async def supprimer_mon_cv(
    id_cv: UUID,
    current_candidat: Candidat = Depends(get_current_candidat),
    db: AsyncSession = Depends(get_db),
):
    """
    Supprime le CV de MinIO et de la base de données (conformité RGPD / Effacement).
    """
    query = select(CV).where(
        CV.id_cv == id_cv,
        CV.id_candidat == current_candidat.id_candidat
    )
    result = await db.execute(query)
    cv = result.scalar_one_or_none()

    if not cv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="CV introuvable.",
        )

    # 1. Supprimer le fichier physique sur MinIO
    if cv.url_cv:
        await run_in_threadpool(delete_cv, object_key=cv.url_cv)

    # 2. Supprimer la ligne en BDD
    await db.delete(cv)
    await db.commit()
