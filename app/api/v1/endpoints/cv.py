from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.core.rate_limit import check_rate_limit
from app.core.storage import delete_file, get_download_url
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.schemas.cv import CVCreate, CVUpdate, CVRead, generate_code_cv
from app.services.cv_upload import lire_fichier_borne, valider_et_stocker_cv
from app.services.matching import recalculer_resultats_cv

router = APIRouter(prefix="/cv", tags=["cv"])


def get_own_candidat(current_user: Utilisateur, db: Session) -> Candidat:
    candidat = db.query(Candidat).filter(Candidat.id_utilisateur == current_user.id_utilisateur).first()
    if not candidat:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")
    return candidat


def nouveau_code_cv(db: Session) -> str:
    code = generate_code_cv()
    while db.query(CV).filter(CV.code_cv == code).first():
        code = generate_code_cv()
    return code


@router.post("/", response_model=CVRead, status_code=status.HTTP_201_CREATED)
def create_cv(
    cv_in: CVCreate,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)

    existing = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if existing:
        raise HTTPException(status_code=400, detail="Un CV existe deja pour ce candidat. Utilisez la modification.")

    cv = CV(
        id_candidat=candidat.id_candidat,
        resume_cv=cv_in.resume_cv,
        experience=cv_in.experience,
        education=cv_in.education,
        langues=cv_in.langues,
        domaine_etude=cv_in.domaine_etude,
        competences=cv_in.competences,
        certifications=cv_in.certifications,
        localisation=cv_in.localisation,
        type_poste_recherche=cv_in.type_poste_recherche,
        statut_cv="actif",
        code_cv=nouveau_code_cv(db),
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


# Fonction synchrone : FastAPI l'exécute dans un thread, la lecture du PDF et
# l'envoi vers le stockage ne bloquent donc plus les autres requêtes.
@router.post("/upload", response_model=CVRead, status_code=status.HTTP_200_OK)
def upload_cv(
    background_tasks: BackgroundTasks,
    fichier: UploadFile = File(...),
    maj_competences: bool = Query(
        True,
        description="false : garde le résumé, les compétences et les langues déjà saisis",
    ),
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    """Depot de CV en PDF/DOCX avec extraction automatique (JA-030, JA-031)."""
    check_rate_limit(f"upload-cv:{current_user.id_utilisateur}", 10, 3600)
    candidat = get_own_candidat(current_user, db)

    contenu = lire_fichier_borne(fichier)
    donnees, object_name = valider_et_stocker_cv(contenu, fichier.filename or "")

    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if cv is None:
        cv = CV(id_candidat=candidat.id_candidat, code_cv=nouveau_code_cv(db))
        db.add(cv)

    for champ in ("resume_cv", "competences", "langues"):
        if maj_competences or not getattr(cv, champ):
            setattr(cv, champ, donnees[champ])

    ancien_fichier = cv.url_cv
    cv.url_cv = object_name
    cv.statut_cv = "actif"

    try:
        db.commit()
    except Exception:
        db.rollback()
        delete_file(object_name)
        raise
    db.refresh(cv)

    # L'ancien fichier n'est plus référencé : on l'efface (Loi 25).
    if ancien_fichier and ancien_fichier != object_name:
        background_tasks.add_task(delete_file, ancien_fichier)
    background_tasks.add_task(recalculer_resultats_cv, cv.id_cv)
    return cv


@router.get("/moi", response_model=CVRead)
def get_my_cv(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve pour ce candidat")
    return cv


@router.get("/moi/fichier")
def get_my_cv_file(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    """Lien temporaire (15 min) pour télécharger le fichier du CV."""
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv or not cv.url_cv:
        raise HTTPException(status_code=404, detail="Aucun fichier de CV")
    return {"url": get_download_url(cv.url_cv, expires_seconds=900)}


@router.put("/moi", response_model=CVRead)
def update_my_cv(
    cv_in: CVUpdate,
    background_tasks: BackgroundTasks,
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve. Creez-en un d'abord.")

    for field, value in cv_in.model_dump(exclude_unset=True).items():
        setattr(cv, field, value)

    db.commit()
    db.refresh(cv)

    # JA-044 : toute mise à jour du profil déclenche le recalcul asynchrone.
    background_tasks.add_task(recalculer_resultats_cv, cv.id_cv)
    return cv


@router.delete("/moi", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_cv(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    """Supprime le CV, son fichier et les candidatures qui l'utilisent (droit à l'effacement)."""
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve")

    fichier = cv.url_cv
    db.delete(cv)
    db.commit()
    delete_file(fichier)
