from __future__ import annotations

from web.app_factory import create_app


def _test_client():
    app = create_app(
        {
            "TESTING": True,
            "SKIP_RUNTIME_INITIALIZATION": True,
        }
    )
    return app.test_client()


def test_health_reports_flask_runtime():
    response = _test_client().get("/health")

    assert response.status_code == 200
    assert response.get_json() == {
        "status": "healthy",
        "framework": "Flask",
        "execution_model": "synchronous",
    }


def test_route_inventory_contains_chat_and_gateway_contracts():
    response = _test_client().get("/api/docs")

    assert response.status_code == 200
    paths = {item["path"] for item in response.get_json()["routes"]}
    assert "/api/chat/stream" in paths
    assert "/api/v1/gateway/chat/message" in paths


def test_protected_route_requires_bearer_token():
    response = _test_client().get("/api/chat/sessions")

    assert response.status_code == 401
    assert response.get_json()["detail"] == "missing authentication token"


def test_pydantic_request_validation_is_preserved():
    response = _test_client().post("/api/auth/login", json={})

    assert response.status_code == 422
    locations = {tuple(item["loc"]) for item in response.get_json()["detail"]}
    assert ("username",) in locations
    assert ("password",) in locations


def test_endpoint_executes_on_the_request_thread():
    response = _test_client().get("/health")
    assert response.get_json()["execution_model"] == "synchronous"
