import asyncio
import io

import pytest
from fastapi import HTTPException, UploadFile

from app.api.v1.endpoints.cv import (
    MAX_CV_SIZE_BYTES,
    normalize_optional_text,
    read_cv_upload,
    validate_cv_content,
)


def test_accepts_valid_pdf_signature() -> None:
    validate_cv_content("cv.pdf", "application/pdf", b"%PDF-1.7\n")


def test_rejects_mismatched_extension_and_content_type() -> None:
    with pytest.raises(HTTPException) as exc_info:
        validate_cv_content("cv.pdf", "application/msword", b"%PDF-1.7\n")
    assert exc_info.value.status_code == 400


def test_rejects_upload_larger_than_five_megabytes() -> None:
    upload = UploadFile(
        filename="cv.pdf",
        file=io.BytesIO(b"x" * (MAX_CV_SIZE_BYTES + 1)),
    )
    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(read_cv_upload(upload))
    assert exc_info.value.status_code == 413


def test_normalizes_empty_cv_code_to_null() -> None:
    assert normalize_optional_text("   ") is None
    assert normalize_optional_text(" CV-001 ") == "CV-001"
