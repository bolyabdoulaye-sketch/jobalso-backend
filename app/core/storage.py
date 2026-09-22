import uuid
from minio import Minio
from minio.error import S3Error

from app.core.config import settings

_client = Minio(
    settings.MINIO_ENDPOINT,
    access_key=settings.MINIO_ACCESS_KEY,
    secret_key=settings.MINIO_SECRET_KEY,
    secure=False,  # False en local (http), True en production (https)
)


def ensure_bucket_exists():
    if not _client.bucket_exists(settings.MINIO_BUCKET):
        _client.make_bucket(settings.MINIO_BUCKET)


def upload_file(file_obj, extension: str, content_type: str) -> str:
    """Upload un fichier vers MinIO et retourne sa cle (object name)."""
    ensure_bucket_exists()
    object_name = f"{uuid.uuid4()}{extension}"

    file_obj.seek(0, 2)  # se placer a la fin pour obtenir la taille
    size = file_obj.tell()
    file_obj.seek(0)  # revenir au debut pour l'upload

    _client.put_object(
        settings.MINIO_BUCKET,
        object_name,
        file_obj,
        length=size,
        content_type=content_type,
    )
    return object_name


def get_download_url(object_name: str, expires_seconds: int = 3600) -> str:
    """Genere une URL temporaire pour telecharger le fichier."""
    from datetime import timedelta
    return _client.presigned_get_object(
        settings.MINIO_BUCKET, object_name, expires=timedelta(seconds=expires_seconds)
    )
