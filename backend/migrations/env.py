"""Alembic environment — online migrations only; URL from DATABASE_URL (or an explicit sqlalchemy.url override)."""
from alembic import context
from sqlalchemy import create_engine

from app.shared.config import sqlalchemy_url

config = context.config


def run_migrations_online() -> None:
    url = config.get_main_option("sqlalchemy.url") or sqlalchemy_url()
    engine = create_engine(url)
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=None, transaction_per_migration=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    raise SystemExit("offline migrations are not supported; run `alembic upgrade head` against a database")
run_migrations_online()
