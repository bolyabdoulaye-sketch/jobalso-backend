import io

from fastapi import HTTPException, UploadFile

from app.core.storage import upload_file
from app.services.extraction import CVIllisibleError, extraire_donnees_cv

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
TAILLE_MAX_OCTETS = 10 * 1024 * 1024
SIGNATURES_VALIDES = {
    ".pdf": [b"%PDF"],
    ".docx": [b"PK\x03\x04"],
}


def valider_et_stocker_cv(contenu: bytes, nom_fichier: str):
    extension = "." + nom_fichier.rsplit(".", 1)[-1].lower() if "." in nom_fichier else ""

    if extension not in EXTENSIONS_AUTORISEES:
        raise HTTPException(status_code=400, detail="Seuls les fichiers PDF et DOCX sont acceptes")
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=400, detail="Le fichier depasse la taille maximale de 10 Mo")
    if len(contenu) == 0:
        raise HTTPException(status_code=400, detail="Le fichier est vide")

    if not any(contenu.startswith(sig) for sig in SIGNATURES_VALIDES[extension]):
        raise HTTPException(
            status_code=400,
            detail="Le contenu du fichier ne correspond pas a son extension (fichier corrompu ou deguise)",
        )

    try:
        donnees = extraire_donnees_cv(contenu, extension)
    except CVIllisibleError as exc:
        raise HTTPException(status_code=422, detail=f"CV illisible : {exc}")

    content_type = (
        "application/pdf"
        if extension == ".pdf"
        else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
    object_name = upload_file(io.BytesIO(contenu), extension, content_type)
    return donnees, object_name
