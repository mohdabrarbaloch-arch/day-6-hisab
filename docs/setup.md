# Setup Guide

## Requirements
- Python 3.11+
- (Optional) Docker + Docker Compose for the PostgreSQL stack

## Local (SQLite, zero setup)

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env             # defaults work out of the box
python seed.py                   # optional demo data
uvicorn app.main:app --reload
```

## Docker (PostgreSQL 16)

```bash
cp .env.example .env             # set SECRET_KEY to a long random string
docker compose up --build
```

The compose file wires `DATABASE_URL=postgresql+psycopg2://hisab:hisab@db:5432/hisab`
automatically. The DB volume persists across restarts.

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `APP_NAME` | `Hisab` | App display name |
| `APP_ENV` | `development` | Runtime environment label |
| `SECRET_KEY` | dev value | **Required in prod** — long random string for JWT signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `1440` | JWT lifetime (24h) |
| `DATABASE_URL` | `sqlite:///./hisab.db` | SQLite for dev, Postgres for prod |
| `CORS_ORIGINS` | `*` | Comma-separated allowed origins |
| `DEFAULT_USD_TO_PKR` | `280.0` | Rate used for PKR income estimates |

> Never commit a real `.env`. The repo ships `.env.example` only.
