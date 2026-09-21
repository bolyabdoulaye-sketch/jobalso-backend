import os
import uuid
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.storage import upload_file, get_download_url
from app.models.user import User, UserRole
from app.models.candidate import CandidateProfile, CV, CandidateSkill, CVAnalysisStatus, SkillSource
from app.schemas.candidate import (
    CandidateProfileRead,
    CandidateProfileUpdate,
    CVRead,
    CandidateSkillCreate,
    CandidateSkillRead,
)

router = APIRouter(prefix="/profils-candidats", tags=["profils-candidats"])

MAX_FILE_SIZE_MB = 10
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


def get_own_profile(current_user: User, db: Session) -> CandidateProfile:
    profil = db.query(CandidateProfile).filter(
        CandidateProfile.utilisateur_id == current_user.id
    ).first()
    if not profil:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")
    return profil


@router.get("/moi", response_model=CandidateProfileRead)
def get_my_profile(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    return get_own_profile(current_user, db)


@router.put("/moi", response_model=CandidateProfileRead)
def update_my_profile(
    profile_in: CandidateProfileUpdate,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)

    if profile_in.localisation is not None:
        profil.localisation = profile_in.localisation
    if profile_in.type_poste_recherche is not None:
        profil.type_poste_recherche = profile_in.type_poste_recherche

    db.commit()
    db.refresh(profil)
    return profil


@router.post("/moi/cv", response_model=CVRead, status_code=status.HTTP_201_CREATED)
def upload_cv(
    fichier: UploadFile = File(...),
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)

    extension = os.path.splitext(fichier.filename)[1].lower()
    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail="Format non supporte. Utilisez PDF ou DOCX")

    contenu = fichier.file.read()
    taille_mo = len(contenu) / (1024 * 1024)
    if taille_mo > MAX_FILE_SIZE_MB:
        raise HTTPException(status_code=400, detail="Fichier trop volumineux (max 10 Mo)")

    fichier.file.seek(0)
    content_type = "application/pdf" if extension == ".pdf" else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    object_name = upload_file(fichier.file, extension, content_type)

    db.query(CV).filter(CV.profil_candidat_id == profil.id).update({"est_actuel": False})

    cv = CV(
        profil_candidat_id=profil.id,
        chemin_fichier=object_name,
        type_fichier=extension.replace(".", ""),
        statut_analyse=CVAnalysisStatus.EN_ATTENTE,
        est_actuel=True,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.get("/moi/cv", response_model=list[CVRead])
def list_my_cvs(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)
    return db.query(CV).filter(CV.profil_candidat_id == profil.id).all()


@router.get("/moi/cv/{cv_id}/telecharger")
def get_cv_download_link(
    cv_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)
    cv = db.query(CV).filter(CV.id == cv_id, CV.profil_candidat_id == profil.id).first()
    if not cv:
        raise HTTPException(status_code=404, detail="CV introuvable")

    url = get_download_url(cv.chemin_fichier)
    return {"url": url}


@router.post("/moi/competences", response_model=CandidateSkillRead, status_code=status.HTTP_201_CREATED)
def add_skill(
    skill_in: CandidateSkillCreate,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)

    skill = CandidateSkill(
        profil_candidat_id=profil.id,
        type_competence=skill_in.type_competence,
        valeur=skill_in.valeur,
        source=skill_in.source,
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)
    return skill


@router.get("/moi/competences", response_model=list[CandidateSkillRead])
def list_my_skills(
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)
    return db.query(CandidateSkill).filter(CandidateSkill.profil_candidat_id == profil.id).all()


@router.delete("/moi/competences/{skill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_skill(
    skill_id: uuid.UUID,
    current_user: User = Depends(require_role(UserRole.CANDIDAT)),
    db: Session = Depends(get_db),
):
    profil = get_own_profile(current_user, db)
    skill = db.query(CandidateSkill).filter(
        CandidateSkill.id == skill_id, CandidateSkill.profil_candidat_id == profil.id
    ).first()
    if not skill:
        raise HTTPException(status_code=404, detail="Competence introuvable")

    db.delete(skill)
    db.commit()