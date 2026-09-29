import re
import uuid
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from app.core import rate_limit
from app.core.config import settings

RACINE = Path(__file__).resolve().parents[3]


@pytest.fixture(scope="session")
def moteur():
    """Base vide, puis toutes les migrations Alembic : elles sont testées au passage."""
    engine = create_engine(settings.DATABASE_URL)
    with engine.begin() as conn:
        conn.execute(text("DROP SCHEMA public CASCADE"))
        conn.execute(text("CREATE SCHEMA public"))
    config = Config(str(RACINE / "alembic.ini"))
    config.set_main_option("script_location", str(RACINE / "alembic"))
    command.upgrade(config, "head")
    yield engine
    engine.dispose()


@pytest.fixture(autouse=True)
def base_propre(moteur):
    with moteur.begin() as conn:
        tables = conn.execute(
            text("SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename <> 'alembic_version'")
        ).scalars().all()
        conn.execute(text(f"TRUNCATE {', '.join(tables)} RESTART IDENTITY CASCADE"))
    rate_limit.reset_rate_limits()
    settings.RATE_LIMIT_ENABLED = False
    yield
    settings.RATE_LIMIT_ENABLED = False


class Stockage:
    """Remplace le stockage objet : garde les fichiers en mémoire."""

    def __init__(self):
        self.fichiers: dict[str, bytes] = {}
        self.supprimes: list[str] = []

    def upload_file(self, file_obj, extension, content_type):
        nom = f"{uuid.uuid4()}{extension}"
        self.fichiers[nom] = file_obj.read()
        return nom

    def delete_file(self, nom):
        self.supprimes.append(nom)
        self.fichiers.pop(nom, None)
        return True


class BoiteMail:
    def __init__(self):
        self.messages: list[dict] = []

    def send_email(self, to, subject, body_text, body_html=None, headers=None):
        self.messages.append({"to": to, "subject": subject, "text": body_text, "html": body_html})
        return True

    def pour(self, email):
        return [m for m in self.messages if m["to"] == email]

    def jeton(self, email, chemin):
        """Extrait le jeton du dernier lien <chemin>?token=... envoyé à cet email."""
        for message in reversed(self.pour(email)):
            trouve = re.search(rf"/{chemin}\?token=([^\s\"<]+)", message["text"])
            if trouve:
                from urllib.parse import unquote

                return unquote(trouve.group(1))
        raise AssertionError(f"Aucun lien {chemin} envoye a {email}")


@pytest.fixture
def stockage(monkeypatch):
    faux = Stockage()
    import app.api.v1.endpoints.cv as cv_endpoints
    import app.api.v1.endpoints.public as public_endpoints
    import app.main as main
    import app.services.cv_upload as cv_upload

    monkeypatch.setattr(cv_upload, "upload_file", faux.upload_file)
    monkeypatch.setattr(cv_endpoints, "delete_file", faux.delete_file)
    monkeypatch.setattr(public_endpoints, "delete_file", faux.delete_file)
    monkeypatch.setattr(cv_endpoints, "get_download_url", lambda nom, expires_seconds=3600: f"http://stockage.test/{nom}")
    monkeypatch.setattr(main, "ensure_bucket_exists", lambda: None)
    return faux


@pytest.fixture
def boite_mail(monkeypatch):
    boite = BoiteMail()
    import app.services.email_candidature as e1
    import app.services.email_compte as e2
    import app.services.email_password_reset as e3

    for module in (e1, e2, e3):
        monkeypatch.setattr(module, "send_email", boite.send_email)
    return boite


@pytest.fixture
def client(stockage, boite_mail):
    from app.main import app

    with TestClient(app) as c:
        yield c
