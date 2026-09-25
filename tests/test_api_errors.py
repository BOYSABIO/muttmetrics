"""Unhandled errors should return JSON for the SPA (#87)."""

from fastapi.testclient import TestClient

from muttmetrics.api.app import create_app


def test_unhandled_exception_returns_json_detail() -> None:
    app = create_app()

    @app.get("/__test_boom__")
    def boom() -> None:
        raise RuntimeError("kaboom")

    # Default TestClient re-raises server exceptions; we want the HTTP response.
    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/__test_boom__")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")
    assert response.json() == {"detail": "Internal server error"}


def test_http_exception_still_returns_its_detail() -> None:
    """HTTPException must keep FastAPI's normal JSON (not our generic 500)."""
    from fastapi import HTTPException

    app = create_app()

    @app.get("/__test_not_found__")
    def missing() -> None:
        raise HTTPException(status_code=404, detail="nope")

    client = TestClient(app, raise_server_exceptions=False)
    response = client.get("/__test_not_found__")

    assert response.status_code == 404
    assert response.json() == {"detail": "nope"}
