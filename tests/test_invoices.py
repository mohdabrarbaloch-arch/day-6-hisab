"""Invoice engine + endpoint tests."""

from datetime import UTC, datetime, timedelta


def make_user_and_token(client, email="inv@x.com"):
    client.post(
        "/api/auth/register", json={"email": email, "name": "Test", "password": "secret123"}
    )
    tok = client.post("/api/auth/login", data={"username": email, "password": "secret123"}).json()[
        "access_token"
    ]
    return {"Authorization": f"Bearer {tok}"}


def make_client(client, h, name="Client A"):
    return client.post("/api/clients", headers=h, json={"name": name}).json()["id"]


def make_invoice_payload(cid, due_days=14):
    due = (datetime.now(UTC) + timedelta(days=due_days)).isoformat()
    return {
        "client_id": cid,
        "currency": "USD",
        "due_date": due,
        "notes": "Thanks!",
        "items": [
            {"description": "Design work", "quantity": 1, "unit_price": 1000},
            {"description": "Revisions", "quantity": 2, "unit_price": 100},
        ],
    }


def test_create_invoice(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    r = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid))
    assert r.status_code == 201
    body = r.json()
    assert body["invoice_number"].startswith("INV-")
    assert body["subtotal"] == 1200.0
    assert body["tax"] == 60.0
    assert body["total"] == 1260.0
    assert body["status"] == "draft"


def test_invoice_number_sequence(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    a = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    b = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    assert int(a["invoice_number"].split("-")[1]) + 1 == int(b["invoice_number"].split("-")[1])


def test_create_invoice_unknown_client(client):
    h = make_user_and_token(client)
    r = client.post("/api/invoices", headers=h, json=make_invoice_payload(9999))
    assert r.status_code == 400
    assert "client not found" in r.json()["detail"]


def test_create_invoice_invalid_currency(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    payload = make_invoice_payload(cid)
    payload["currency"] = "XYZ"
    assert client.post("/api/invoices", headers=h, json=payload).status_code == 422


def test_create_invoice_requires_item(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    payload = make_invoice_payload(cid)
    payload["items"] = []
    assert client.post("/api/invoices", headers=h, json=payload).status_code == 422


def test_create_invoice_negative_price_rejected(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    payload = make_invoice_payload(cid)
    payload["items"] = [{"description": "Bad", "quantity": 1, "unit_price": -5}]
    assert client.post("/api/invoices", headers=h, json=payload).status_code == 422


def test_invoice_owner_isolation(client):
    h1 = make_user_and_token(client, "u1@x.com")
    h2 = make_user_and_token(client, "u2@x.com")
    cid = make_client(client, h1)
    inv = client.post("/api/invoices", headers=h1, json=make_invoice_payload(cid)).json()
    assert client.get(f"/api/invoices/{inv['id']}", headers=h2).status_code == 404


def test_mark_sent_and_paid(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    inv = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    iid = inv["id"]
    assert client.post(f"/api/invoices/{iid}/send", headers=h).json()["status"] == "sent"
    assert client.post(f"/api/invoices/{iid}/pay", headers=h).json()["status"] == "paid"


def test_paid_invoice_cannot_resend(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    inv = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    iid = inv["id"]
    client.post(f"/api/invoices/{iid}/send", headers=h)
    client.post(f"/api/invoices/{iid}/pay", headers=h)
    assert client.post(f"/api/invoices/{iid}/send", headers=h).status_code == 409


def test_delete_invoice(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    inv = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    iid = inv["id"]
    assert client.delete(f"/api/invoices/{iid}", headers=h).status_code == 204
    assert client.get(f"/api/invoices/{iid}", headers=h).status_code == 404


def test_list_invoices_filter_by_status(client):
    h = make_user_and_token(client)
    cid = make_client(client, h)
    inv = client.post("/api/invoices", headers=h, json=make_invoice_payload(cid)).json()
    client.post(f"/api/invoices/{inv['id']}/pay", headers=h)
    r = client.get("/api/invoices?status=paid", headers=h)
    assert len(r.json()) == 1
    assert r.json()[0]["status"] == "paid"
    assert client.get("/api/invoices?status=overdue", headers=h).json() == []
