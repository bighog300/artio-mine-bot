"""Vercel serverless entrypoint for FastAPI."""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Configure app for serverless constraints.
os.environ.setdefault("ENVIRONMENT", "vercel")
os.environ.setdefault("PLAYWRIGHT_ENABLED", "false")

from app.api.main import app
