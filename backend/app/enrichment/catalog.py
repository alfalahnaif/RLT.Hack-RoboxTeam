"""Small, read-only catalog of validated curated evidence seeds."""
from __future__ import annotations

from pathlib import Path

from app.enrichment.models import EvidenceSeed
from app.enrichment.verification import load_evidence_seed
from app.shared.config import repo_root


class EvidenceCatalogError(Exception):
    """The curated catalog is unavailable or invalid."""


class CuratedEvidenceCatalog:
    def __init__(self, directory: Path | None = None) -> None:
        self.directory = directory or repo_root() / "data" / "seed"

    def get(self, target_okpd2: str) -> EvidenceSeed | None:
        if not self.directory.is_dir():
            raise EvidenceCatalogError("Curated evidence catalog directory is unavailable")
        indexed: dict[str, EvidenceSeed] = {}
        for path in sorted(self.directory.glob("*_evidence_seed.json")):
            try:
                seed = load_evidence_seed(path)
            except ValueError as error:
                raise EvidenceCatalogError(f"Invalid curated evidence seed {path.name}: {error}") from error
            if seed.target_okpd2 in indexed:
                raise EvidenceCatalogError(f"Duplicate curated category {seed.target_okpd2}")
            indexed[seed.target_okpd2] = seed
        return indexed.get(target_okpd2)
