"""Vercel serverless entrypoint — mirrors the local FastAPI app."""

# vercel rewrites /* -> api/index.py; module-level `app` is picked up automatically.
