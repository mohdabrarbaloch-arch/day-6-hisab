# API Reference

Base URL: `http://localhost:8000` · Interactive docs: `/api/docs` (OpenAPI)

Auth: `Authorization: Bearer <token>` for all endpoints except register/login/health.

---

## Auth

### POST /api/auth/register
Body: `{ "email": str, "name": str, "password": str (≥8, letters+numbers) }`
→ `201` with user · `409` duplicate email · `422` invalid

### POST /api/auth/login
OAuth2 form: `username`, `password` · rate-limited 10/min/IP
→ `200` `{ "access_token": str, "token_type": "bearer" }`

### GET /api/auth/me
→ `200` current user

## Clients

### GET /api/clients
→ list of `{id, name, company, email, country, owner_id, created_at}`

### POST /api/clients
Body: `{ "name": str (2–160), "company"?, "email"?, "country"? }` → `201`

### GET /api/clients/{id} · PUT /api/clients/{id} · DELETE /api/clients/{id}
Delete returns `409` if the client still has invoices.

## Invoices

### GET /api/invoices?status=sent
List with `client_name` + `total`. Status filter: draft/sent/paid/overdue.

### POST /api/invoices
```json
{
  "client_id": 1,
  "currency": "USD",
  "due_date": "2026-08-27T00:00:00Z",
  "notes": "Thanks!",
  "items": [
    { "description": "Landing page", "quantity": 1, "unit_price": 1200 }
  ]
}
```
→ `201` with computed `subtotal`, `tax` (5%), `total`, and `invoice_number`.

Errors: `400` unknown client · `422` bad currency / empty items / negative price

### GET /api/invoices/{id}
→ full invoice incl. client + items + totals (auto-refreshes overdue status)

### POST /api/invoices/{id}/send → mark `sent` (409 if paid)
### POST /api/invoices/{id}/pay → mark `paid`
### DELETE /api/invoices/{id} → `204`

## Stats

### GET /api/stats/summary
```json
{
  "total_invoiced": 600.0, "total_paid": 100.0,
  "total_overdue": 200.0, "total_pending": 300.0,
  "invoice_count": 3, "paid_count": 1, "overdue_count": 1,
  "outstanding_pkr": 140000.0, "usd_to_pkr": 280.0
}
```

### GET /api/stats/dashboard
`summary` + `paid_30d` + `overdue_count` + `recent_invoices` (last 5)

## Misc

### GET /api/health → `{ "status": "ok", "app": "Hisab", "version": "1.0.0" }`
