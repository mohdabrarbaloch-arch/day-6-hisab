"""Client CRUD tests."""


def make_user_and_token(client):
    client.post(
        "/api/auth/register", json={"email": "c@d.com", "name": "Test", "password": "secret123"}
    )
    tok = client.post(
        "/api/auth/login", data={"username": "c@d.com", "password": "secret123"}
    ).json()["access_token"]
    return {"Authorization": f"Bearer {tok}"}


def test_list_clients_empty(client):
    h = make_user_and_token(client)
    assert client.get("/api/clients", headers=h).json() == []


def test_create_client(client):
    h = make_user_and_token(client)
    r = client.post(
        "/api/clients",
        headers=h,
        json={"name": "Studio Nine", "company": "Nine Ltd", "country": "UAE"},
    )
    assert r.status_code == 201
    assert r.json()["name"] == "Studio Nine"


def test_create_client_requires_auth(client):
    r = client.post("/api/clients", json={"name": "X"})
    assert r.status_code == 401


def test_client_name_too_short(client):
    h = make_user_and_token(client)
    r = client.post("/api/clients", headers=h, json={"name": "A"})
    assert r.status_code == 422


def test_get_client_owned(client):
    h = make_user_and_token(client)
    cid = client.post("/api/clients", headers=h, json={"name": "PixelWorks"}).json()["id"]
    r = client.get(f"/api/clients/{cid}", headers=h)
    assert r.status_code == 200
    assert r.json()["name"] == "PixelWorks"


def test_get_client_not_found(client):
    h = make_user_and_token(client)
    assert client.get("/api/clients/9999", headers=h).status_code == 404


def test_cannot_access_other_users_client(client):
    h1 = make_user_and_token(client)
    cid = client.post("/api/clients", headers=h1, json={"name": "Mine"}).json()["id"]
    client.post(
        "/api/auth/register",
        json={"email": "other@x.com", "name": "Other", "password": "secret123"},
    )
    h2 = {
        "Authorization": "Bearer "
        + client.post(
            "/api/auth/login", data={"username": "other@x.com", "password": "secret123"}
        ).json()["access_token"]
    }
    assert client.get(f"/api/clients/{cid}", headers=h2).status_code == 404


def test_update_client(client):
    h = make_user_and_token(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Old Name"}).json()["id"]
    r = client.put(f"/api/clients/{cid}", headers=h, json={"name": "New Name", "company": "Co"})
    assert r.status_code == 200
    assert r.json()["name"] == "New Name"


def test_delete_client(client):
    h = make_user_and_token(client)
    cid = client.post("/api/clients", headers=h, json={"name": "Gone Soon"}).json()["id"]
    assert client.delete(f"/api/clients/{cid}", headers=h).status_code == 204
    assert client.get(f"/api/clients/{cid}", headers=h).status_code == 404
