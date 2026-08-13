"""Vercel serverless entrypoint for Hisab.

Vercel's Python runtime looks for a top-level ``app`` (or ``application`` /
``handler``) in this file. The real FastAPI instance is assembled in
``app.main``; we simply re-export it here under the name the runtime expects.
"""

from app.main import app  # noqa: F401  (re-exported for Vercel's runtime)
