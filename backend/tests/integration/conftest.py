"""Integration fixtures: a throwaway database `<db>_test` on the same PostgreSQL server (never the main database),
migrated with Alembic, plus a CSV slice in the exact organizer format built from contracts/fixtures/source_rows.json."""
import csv
import json
import os
from pathlib import Path

import psycopg
import pytest

from app.ingestion.mapping import SOURCE_COLUMNS
from app.ingestion.organizer import DATASETS
from app.shared.config import repo_root, sqlalchemy_url


def _admin_url():
    url = os.environ.get("DATABASE_URL")
    if not url:
        pytest.skip("DATABASE_URL not set — run integration tests via `docker compose run --rm backend pytest`")
    return url


@pytest.fixture(scope="session")
def test_db_url():
    url = _admin_url()
    base, _, dbname = url.rpartition("/")
    test_name = f"{dbname}_test"
    try:
        admin = psycopg.connect(url, autocommit=True)
    except psycopg.OperationalError as e:
        pytest.skip(f"PostgreSQL not reachable: {e}")
    with admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{test_name}" WITH (FORCE)')
        admin.execute(f'CREATE DATABASE "{test_name}"')
    test_url = f"{base}/{test_name}"
    from alembic import command
    from alembic.config import Config
    cfg = Config(str(Path(__file__).resolve().parents[2] / "alembic.ini"))
    cfg.set_main_option("script_location", str(Path(__file__).resolve().parents[2] / "migrations"))
    cfg.set_main_option("sqlalchemy.url", sqlalchemy_url(test_url))
    command.upgrade(cfg, "head")
    yield test_url
    with psycopg.connect(url, autocommit=True) as admin:
        admin.execute(f'DROP DATABASE IF EXISTS "{test_name}" WITH (FORCE)')


@pytest.fixture(scope="session")
def slice_dir(tmp_path_factory):
    """Organizer-format CSVs (';', '"', no BOM) from the contract fixtures (masked identifiers)."""
    src = json.loads((repo_root() / "contracts" / "fixtures" / "source_rows.json").read_text(encoding="utf-8"))
    d = tmp_path_factory.mktemp("raw")
    for ds, name in DATASETS.items():
        cols = SOURCE_COLUMNS[ds]
        with open(d / name, "w", encoding="utf-8", newline="") as f:
            w = csv.writer(f, delimiter=";", quotechar='"', quoting=csv.QUOTE_MINIMAL, lineterminator="\n")
            w.writerow(cols)
            for r in sorted(src[ds], key=lambda r: r["row_number"]):
                w.writerow([r[c] for c in cols])
    return d
