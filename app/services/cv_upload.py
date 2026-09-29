import io
import zipfile

from fastapi import HTTPException, UploadFile

from app.core.storage import upload_file
from app.services.extraction import CVIllisibleError, extraire_donnees_cv

EXTENSIONS_AUTORISEES = {".pdf", ".docx"}
TAILLE_MAX_OCTETS = 10 * 1024 * 1024  # 10 Mo (JA-030)
# Un .docx est une archive zip : on borne la taille décompressée (bombe zip).
TAILLE_MAX_DECOMPRESSEE = 50 * 1024 * 1024
SIGNATURES_VALIDES = {
    ".pdf": [b"%PDF-"],
    ".docx": [b"PK\x03\x04"],
}
CONTENT_TYPES = {
    ".pdf": "application/pdf",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


def lire_fichier_borne(fichier: UploadFile) -> bytes:
    """Lit le fichier envoyé sans jamais charger plus de TAILLE_MAX_OCTETS + 1 octets."""
    contenu = fichier.file.read(TAILLE_MAX_OCTETS + 1)
    if len(contenu) > TAILLE_MAX_OCTETS:
        raise HTTPException(status_code=400, detail="Le fichier depasse la taille maximale de 10 Mo")
    return contenu


def _valider_docx(contenu: bytes) -> None:
    try:
        with zipfile.ZipFile(io.BytesIO(contenu)) as archive:
            noms = set(archive.namelist())
            if "[Content_Types].xml" not in noms or "word/document.xml" not in noms:
                raise ValueError("pas un document Word")
            if sum(info.file_size for info in archive.infolist()) > TAILLE_MAX_DECOMPRESSEE:
                raise ValueError("archive trop volumineuse une fois decompressee")
    except (zipfile.BadZipFile, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Le fichier n'est pas un document Word valide ({exc})",
        ) from exc


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
    if extension == ".docx":
        _valider_docx(contenu)

    try:
        donnees = extraire_donnees_cv(contenu, extension)
    except CVIllisibleError as exc:
        raise HTTPException(status_code=422, detail=f"CV illisible : {exc}") from exc

    object_name = upload_file(io.BytesIO(contenu), extension, CONTENT_TYPES[extension])
    return donnees, object_name
