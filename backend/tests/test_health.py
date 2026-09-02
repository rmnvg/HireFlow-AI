from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.main import app


def test_health_returns_healthy_when_database_is_available(monkeypatch) -> None:
    monkeypatch.setattr("app.main.check_database_connection", lambda: None)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def test_health_returns_safe_error_when_database_is_unavailable(monkeypatch) -> None:
    def unavailable() -> None:
        raise SQLAlchemyError("sensitive connection details")

    monkeypatch.setattr("app.main.check_database_connection", unavailable)

    with TestClient(app) as client:
        response = client.get("/health")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
    assert "sensitive" not in response.text
