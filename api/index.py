"""Vercel serverless entry point.

Vercel routes all /api/* requests here via vercel.json.
Mangum adapts the ASGI app to the Lambda-compatible interface Vercel uses
for Python serverless functions.

The callable must be named `handler` at module level.
"""
import os

# Set before app modules are imported so Settings() picks them up.
os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")

from mangum import Mangum  # noqa: E402
from app.api.main import app  # noqa: E402

# lifespan="off" skips startup/shutdown events (init_db).
# Run: alembic upgrade head  against your Neon DB before first deploy.
handler = Mangum(app, lifespan="off")
