from fastapi.testclient import TestClient

from app.main import app


def test_health_ok():
    client = TestClient(app)
    res = client.get("/api/health")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "ok"
    assert body["service"] == "ai-procurement-agent"
    assert "llm_provider" in body
    assert "finops_mode" in body
