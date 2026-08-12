# Hisab — Architecture

> Day 6 of the 30-day autonomous build challenge. FastAPI + SQLAlchemy 2.0 + vanilla JS SPA.

## System diagram

```
┌─────────────────────────────┐
│  Browser (SPA, hash router) │
│  index.html · styles.css    │
│  app.js  ──fetch──┐         │
└───────────────────┼─────────┘
                    ▼
┌──────────────────────────────────────┐
│  FastAPI app (app/main.py)           │
│  • CORS allowlist        • SlowAPI   │
│  • Security headers      • routers   │
│  /api/auth · /api/clients            │
│  /api/invoices · /api/stats          │
│  /api/health · / (static SPA)        │
└───────────────┬──────────────────────┘
                │ SQLAlchemy 2.0 ORM
                ▼
┌──────────────────────────────────────┐
│  Database                            │
│  dev:  SQLite WAL (zero setup)       │
│  prod: PostgreSQL 16 (docker-compose)│
│  users · clients · invoices · items  │
└──────────────────────────────────────┘
```

## Tech stack

| Layer | Choice | Why |
|---|---|---|
| API | FastAPI 0.115 | async-ready, typed, auto OpenAPI docs |
| ORM | SQLAlchemy 2.0 (typed `Mapped[]`) | one codebase for SQLite + Postgres |
| Validation | Pydantic v2 | strict input contracts, automatic 422s |
| Auth | JWT (HS256) + bcrypt | stateless, industry-standard |
| Rate limiting | slowapi | 10 logins/min per IP |
| Frontend | Vanilla JS SPA | no build step, deploys anywhere |
| Deploy | Docker + Vercel (serverless) | dev/prod parity |

## Data flow

1. **Auth** — `POST /api/auth/register` hashes the password with bcrypt and stores the user.
   `POST /api/auth/login` (OAuth2 form) verifies and returns a signed JWT (24h expiry).
   Every protected route resolves the user from the `Authorization: Bearer` header.
2. **Clients** — simple per-user CRUD. Deletion is blocked while the client still has invoices
   (409) to protect financial history.
3. **Invoices** — creation validates the client belongs to the caller, generates the next
   sequential number (`INV-0004`), computes subtotal + 5% tax + total, and stores items.
   Statuses: `draft → sent → paid`, with `overdue` derived when `due_date` passes.
4. **Stats** — a read-only sweep marks overdue invoices, then summarizes invoiced / paid /
   pending / overdue amounts, plus an approximate PKR figure (USD × configurable rate) for
   tax-season planning.

## Security

- bcrypt password hashing (passlib, bcrypt backend)
- JWT signed with `SECRET_KEY` from env — no hardcoded secrets
- SlowAPI rate limiting on login (10/min/IP)
- CORS origins from `CORS_ORIGINS` env (default `*` for dev)
- Security headers: `X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`
- Owner-scoped queries everywhere — a user can never read another user's clients/invoices
- Pydantic validation rejects negative prices, empty item lists, unknown currencies

## Scaling notes

- **Stateless API** — horizontal scale is trivial; JWT carries the session.
- **DB** — SQLite (WAL) is fine for a single user; switch `DATABASE_URL` to Postgres for
  production. Indexes exist on `users.email`, `invoices.owner_id`, `invoices.client_id`.
- **Rate limits** — move from per-IP to per-user once auth is everywhere; slowapi supports
  custom key functions.
- **Income reports** — the PKR conversion is a fixed rate today; plug a currency API later
  without touching the schema.
- **Deployment** — `api/index.py` exposes the same app for Vercel; `vercel.json` rewrites
  all routes to it. The static SPA needs no build step.
