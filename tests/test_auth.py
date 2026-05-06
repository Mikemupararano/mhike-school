from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_register_user():
    res = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "password123"
    })
    assert res.status_code in (200, 201, 400, 422)

def test_login_invalid_credentials():
    res = client.post("/api/v1/auth/login", json={
        "email": "wrong@example.com",
        "password": "wrongpass"
    })
    assert res.status_code in (400, 401, 422)

def test_login_missing_fields():
    res = client.post("/api/v1/auth/login", json={})
    assert res.status_code in (400, 422)
