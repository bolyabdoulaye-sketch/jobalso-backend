import io

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.api.deps import get_db, require_role
from app.models.utilisateur import TypeUtilisateur, Utilisateur
from app.models.candidat import Candidat
from app.models.cv import CV
from app.schemas.cv import CVCreate, CVUpdate, CVRead, generate_code_cv
from app.services.extraction import extraire_donnees_cv, CVIllisibleError
from app.core.storage import upload_file

router = APIRouter(prefix="/cv", tags=["cv"])

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
TAILLE_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo (JA-030)

# Signatures de fichier reelles (verification basique, pas un antivirus complet)
SIGNATURES_VALIDES = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04"],  # .docx est une archive zip
}


def get_own_candidat(current_user: Utilisateur, db: Session) -> Candidat:
    candidat = db.query(Candidat).filter(Candidat.id_utilisateur == current_user.id_utilisateur).first()
    if not candidat:
        raise HTTPException(status_code=404, detail="Profil candidat introuvable")
    return candidat


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

    # Genere un code_cv unique
    code = generate_code_cv()
    while db.query(CV).filter(CV.code_cv == code).first():
        code = generate_code_cv()

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
        code_cv=code,
    )
    db.add(cv)
    db.commit()
    db.refresh(cv)
    return cv


@router.post("/upload", response_model=CVRead, status_code=status.HTTP_200_OK)
async def upload_cv(
    fichier: UploadFile = File(...),
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    """Depot de CV en PDF/DOCX avec extraction automatique (JA-030, JA-031)."""
    nom_fichier = fichier.filename or ""
    extension = "." + nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""

    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF et DOCX sont acceptes")

    contenu = await fichier.read()

    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=400, detail="Le fichier depasse la taille maximale de 10 Mo")
    if len(contenu) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    # Controle de signature reelle du fichier (pas un antivirus complet, mais bloque
    # les fichiers renommes/deguises avec une mauvaise extension)
    signatures = SIGNATURES_VALIDES.get(extension, [])
    if not any(contenu.startswith(sig) for sig in signatures):
        raise HTTPException(
            status_code=400,
            detail="Le contenu du fichier ne correspond pas a son extension (fichier corrompu ou deguise)",
        )

    try:
        donnees = extraire_donnees_cv(contenu, extension)
    except CVIllisibleError as exc:
        raise HTTPException(status_code=422, detail=f"CV illisible : {exc}")

    content_type = "application/pdf" if extension == ".pdf" else (
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    object_name = upload_file(io.BytesIO(contenu), extension, content_type)

    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()

    if cv is None:
        code = generate_code_cv()
        while db.query(CV).filter(CV.code_cv == code).first():
            code = generate_code_cv()
        cv = CV(id_candidat=candidat.id_candidat, code_cv=code)
        db.add(cv)

    cv.resume_cv = donnees["resume_cv"]
    cv.competences = donnees["competences"]
    cv.langues = donnees["langues"]
    cv.url_cv = object_name
    cv.statut_cv = "actif"

    db.commit()
    db.refresh(cv)
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


@router.put("/moi", response_model=CVRead)
def update_my_cv(
    cv_in: CVUpdate,
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
    return cv


@router.delete("/moi", status_code=status.HTTP_204_NO_CONTENT)
def delete_my_cv(
    current_user: Utilisateur = Depends(require_role(TypeUtilisateur.CANDIDAT)),
    db: Session = Depends(get_db),
):
    candidat = get_own_candidat(current_user, db)
    cv = db.query(CV).filter(CV.id_candidat == candidat.id_candidat).first()
    if not cv:
        raise HTTPException(status_code=404, detail="Aucun CV trouve")

    db.delete(cv)
    db.commit()
