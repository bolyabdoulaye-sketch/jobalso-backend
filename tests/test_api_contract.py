from uuid import uuid4

from fastapi.testclient import TestClient

from app.core.security import create_access_token
from app.main import app


def test_openapi_exposes_pagination_parameters() -> None:
    specification = TestClient(app).get("/openapi.json").json()
    parameters = specification["paths"]["/offres/"]["get"]["parameters"]
    assert {parameter["name"] for parameter in parameters} >= {"limit", "offset"}


def test_health_endpoint() -> None:
    response = TestClient(app).get("/")
    assert response.status_code == 200


def test_refresh_contract_requires_a_refresh_token() -> None:
    specification = TestClient(app).get("/openapi.json").json()
    schema = specification["components"]["schemas"]["TokenResponse"]
    assert "refresh_token" in schema["required"]


def test_refresh_rejects_an_access_token() -> None:
    token = create_access_token(uuid4())
    response = TestClient(app).post("/auth/refresh", json={"refresh_token": token})
    assert response.status_code == 401
