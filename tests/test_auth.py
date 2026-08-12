"""Auth endpoint tests."""


def test_register_success(client):
    r = client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "secret123"}
    )
    assert r.status_code == 201
    assert r.json()["email"] == "a@b.com"


def test_register_duplicate_email(client):
    client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "secret123"}
    )
    r = client.post(
        "/api/auth/register", json={"email": "A@B.COM", "name": "Other", "password": "secret123"}
    )
    assert r.status_code == 409


def test_register_weak_password(client):
    r = client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "short"}
    )
    assert r.status_code == 422


def test_register_password_requires_letter_and_number(client):
    r = client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "abcdefgh"}
    )
    assert r.status_code == 422


def test_register_invalid_email(client):
    r = client.post(
        "/api/auth/register",
        json={"email": "not-an-email", "name": "Abrar", "password": "secret123"},
    )
    assert r.status_code == 422


def test_login_success(client):
    client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "secret123"}
    )
    r = client.post("/api/auth/login", data={"username": "a@b.com", "password": "secret123"})
    assert r.status_code == 200
    assert r.json()["token_type"] == "bearer"
    assert r.json()["access_token"]


def test_login_wrong_password(client):
    client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "secret123"}
    )
    r = client.post("/api/auth/login", data={"username": "a@b.com", "password": "wrongpass1"})
    assert r.status_code == 401


def test_login_unknown_user(client):
    r = client.post("/api/auth/login", data={"username": "nope@nope.com", "password": "secret123"})
    assert r.status_code == 401


def test_me_requires_token(client):
    assert client.get("/api/auth/me").status_code == 401


def test_me_with_token(client):
    client.post(
        "/api/auth/register", json={"email": "a@b.com", "name": "Abrar", "password": "secret123"}
    )
    tok = client.post(
        "/api/auth/login", data={"username": "a@b.com", "password": "secret123"}
    ).json()["access_token"]
    r = client.get("/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    assert r.json()["name"] == "Abrar"
