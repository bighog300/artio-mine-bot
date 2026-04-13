"""Vercel serverless entry point."""
import os
import sys

# Ensure repo root is on the path so `app` package is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

os.environ.setdefault("ENVIRONMENT", "production")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")

from mangum import Mangum  # noqa: E402
from app.api.main import app  # noqa: E402

handler = Mangum(app, lifespan="off")
