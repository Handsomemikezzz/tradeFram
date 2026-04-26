from fastapi.testclient import TestClient

from backend.app.main import app


def test_local_vite_fallback_port_is_allowed_by_cors():
    client = TestClient(app)

    response = client.options(
        "/api/v1/system/status",
        headers={
            "Origin": "http://localhost:3002",
            "Access-Control-Request-Method": "GET",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "http://localhost:3002"
