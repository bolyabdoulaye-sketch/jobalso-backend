import logging
import uuid
from datetime import timedelta

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)

_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=settings.MINIO_SECURE,
)


def ensure_bucket_exists() -> None:
    if not _client.bucket_exists(settings.MINIO_BUCKET):
        _client.make_bucket(settings.MINIO_BUCKET)


def upload_file(file_obj, extension: str, content_type: str) -> str:
    """Envoie un fichier vers le stockage objet et retourne sa clé."""
    ensure_bucket_exists()
    object_name = f"{uuid.uuid4()}{extension}"

    file_obj.seek(0, 2)
    size = file_obj.tell()
    file_obj.seek(0)

    _client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        file_obj,
        length=size,
        content_type=content_type,
    )
    return object_name


def delete_file(object_name: str | None) -> bool:
    """Supprime un fichier (droit à l'effacement, Loi 25). Ne lève jamais d'exception."""
    if not object_name:
        return True
    try:
        _client.remove_object(settings.MINIO_BUCKET, object_name)
        return True
    except (S3Error, OSError):
        logger.exception("Suppression impossible du fichier %s", object_name)
        return False


def get_download_url(object_name: str, expires_seconds: int = 3600) -> str:
    """Génère une URL temporaire pour télécharger le fichier."""
    return _client.presigned_get_object(
        settings.MINIO_BUCKET, object_name, expires=timedelta(seconds=expires_seconds)
    )
