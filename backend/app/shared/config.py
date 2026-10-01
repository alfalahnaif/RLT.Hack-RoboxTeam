"""Runtime configuration from environment variables (no credentials in code)."""
from __future__ import annotations

import os
from pathlib import Path


def database_url() -> str:
    url = os.environ.get("DATABASE_URL")
    if not url:
        raise RuntimeError("DATABASE_URL is not set (see .env.example / docker-compose.yml)")
    return url


def sqlalchemy_url(url: str | None = None) -> str:
    """postgresql://… -> postgresql+psycopg://… for SQLAlchemy/Alembic (psycopg 3 driver)."""
    url = url or database_url()
    return "postgresql+psycopg://" + url.split("://", 1)[1] if url.startswith("postgresql://") else url


def repo_root() -> Path:
    """Repository root (/srv in the backend container; the checkout root on the host)."""
    env = os.environ.get("REPO_ROOT")
    return Path(env) if env else Path(__file__).resolve().parents[3]
