import sys
import types

try:
    import pgvector.sqlalchemy  # noqa: F401  (vrai module : les tests d'intégration en ont besoin)
except ImportError:
    pgvector = types.ModuleType("pgvector")
    pgvector_sqlalchemy = types.ModuleType("pgvector.sqlalchemy")
    from sqlalchemy import JSON
    pgvector_sqlalchemy.Vector = lambda *args, **kwargs: JSON()
    pgvector.sqlalchemy = pgvector_sqlalchemy
    sys.modules["pgvector"] = pgvector
    sys.modules["pgvector.sqlalchemy"] = pgvector_sqlalchemy


try:
    import minio  # noqa: F401
except ImportError:
    minio = types.ModuleType("minio")
    class _Minio:
        def __init__(self, *args, **kwargs): pass
    minio.Minio = _Minio
    minio_error = types.ModuleType("minio.error")
    class S3Error(Exception): pass
    minio_error.S3Error = S3Error
    minio.error = minio_error
    sys.modules["minio"] = minio
    sys.modules["minio.error"] = minio_error

import pytest
from fastapi import HTTPException

from app.services import cv_upload


def test_ja027_pdf_valide_est_extrait_et_stocke(monkeypatch):
    monkeypatch.setattr(cv_upload, "extraire_donnees_cv", lambda contenu, extension: {
        "resume_cv": "CV test",
        "competences": ["Python"],
        "langues": ["Français"],
    })
    monkeypatch.setattr(cv_upload, "upload_file", lambda *args, **kwargs: "cv/test.pdf")

    donnees, object_name = cv_upload.valider_et_stocker_cv(b"%PDF-1.7 contenu", "candidat.pdf")

    assert donnees["competences"] == ["Python"]
    assert object_name == "cv/test.pdf"


def test_ja027_refuse_extension_non_autorisee():
    with pytest.raises(HTTPException) as exc:
        cv_upload.valider_et_stocker_cv(b"contenu", "candidat.exe")

    assert exc.value.status_code == 400


def test_ja027_refuse_fichier_deguise():
    with pytest.raises(HTTPException) as exc:
        cv_upload.valider_et_stocker_cv(b"PK\x03\x04fake", "candidat.pdf")

    assert exc.value.status_code == 400


def test_ja027_refuse_fichier_superieur_a_10mo(monkeypatch):
    monkeypatch.setattr(cv_upload, "TAILLE_MAX_OCTETS", 10)

    with pytest.raises(HTTPException) as exc:
        cv_upload.valider_et_stocker_cv(b"%PDF-" + b"x" * 20, "candidat.pdf")

    assert exc.value.status_code == 400
