"""
Client MinIO — dépôt, lecture et suppression des CV (JA-030, JA-091).

Le chemin stocké en base (cv.chemin_fichier) est la CLÉ OBJET dans le bucket,
pas une URL complète : on génère une URL pré-signée à la demande, jamais
un lien public permanent.
"""
import io
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client = Minio(
    settings.minio_endpoint,
    access_key=settings.minio_root_user,
    secret_key=settings.minio_root_password,
    secure=settings.minio_secure,
)

BUCKET = settings.minio_bucket_cv


def upload_cv(id_candidat: uuid.UUID, filename: str, contenu: bytes, content_type: str) -> str:
    """
    Dépose un CV dans le bucket et retourne la clé objet à stocker dans
    cv.chemin_fichier. La clé inclut l'id candidat pour éviter toute
    collision et faciliter un nettoyage ciblé (droit à l'effacement).
    """
    extension = filename.rsplit(".", 1)[-1].lower()
    object_key = f"{id_candidat}/{uuid.uuid4()}.{extension}"

    _client.put_object(
        BUCKET,
        object_key,
        data=io.BytesIO(contenu),
        length=len(contenu),
        content_type=content_type,
    )
    return object_key


def get_presigned_url(object_key: str, expires_minutes: int = 15) -> str:
    """URL temporaire pour que le candidat ou le recruteur consulte le CV."""
    return _client.presigned_get_object(
        BUCKET, object_key, expires=timedelta(minutes=expires_minutes)
    )


def delete_cv(object_key: str) -> None:
    """Supprime un CV du stockage (purge de rétention, JA-091, ou effacement, JA-038)."""
    try:
        _client.remove_object(BUCKET, object_key)
    except S3Error as exc:
        if exc.code != "NoSuchKey":
            raise