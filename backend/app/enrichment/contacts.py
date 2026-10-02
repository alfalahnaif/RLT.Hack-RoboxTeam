"""P4-005C source-backed contact enrichment (adjacent to the curated evidence seed; never used for verification).

File: data/seed/*_contact_enrichment.json (deliberately not matching the evidence-seed glob `*_evidence_seed.json`).
Each populated field carries value + source_url + source_authority + checked_at; absent fields are null. `content_currency`
describes the source page itself, so an outdated page is STALE even when it was checked today.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

from app.shared.config import repo_root

FIELDS = ("website", "email", "phone", "address")
AUTHORITIES = {"FIRST_PARTY", "FNS_EGRUL_DERIVED_REGISTRY", "REGULATORY_REGISTRY"}
ADDRESS_TYPES = {"PUBLISHED_COMPANY_ADDRESS", "REGISTERED_LEGAL_ADDRESS"}
CURRENCY = {"CURRENT", "UNDATED", "OUTDATED"}
FRESH_DAYS = 180
_INN = re.compile(r"^(\d{10}|\d{12})$")
_URL = re.compile(r"^https?://[^\s/]+\.[^\s]+$")
_EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


class ContactEnrichmentError(ValueError):
    pass


@dataclass(frozen=True)
class ContactField:
    value: str
    source_url: str
    source_authority: str
    checked_at: datetime
    address_type: str | None = None


@dataclass(frozen=True)
class ContactRecord:
    supplier_inn: str
    company_name: str
    identity_basis: str
    identity_source_url: str
    content_currency: str
    content_currency_note: str
    fields: dict  # field name -> ContactField | None

    def freshness(self, today: date) -> tuple[datetime | None, str | None, str]:
        """(last_checked_at, primary source url, FRESH / STALE / UNKNOWN) of the contact information."""
        present = [f for f in self.fields.values() if f]
        if not present:
            return None, None, "UNKNOWN"
        last = max(f.checked_at for f in present)
        primary = next((self.fields[k].source_url for k in ("phone", "email", "address", "website") if self.fields.get(k)), None)
        if self.content_currency == "OUTDATED":
            return last, primary, "STALE"
        if self.content_currency == "UNDATED":
            return last, primary, "UNKNOWN"
        return last, primary, "FRESH" if (today - last.date()).days <= FRESH_DAYS else "STALE"


def _field(name: str, raw, inn: str) -> ContactField | None:
    if raw is None:
        return None
    missing = {"value", "source_url", "source_authority", "checked_at"} - set(raw)
    if missing or not str(raw["value"]).strip():
        raise ContactEnrichmentError(f"{inn}.{name}: incomplete provenance {sorted(missing)}")
    if raw["source_authority"] not in AUTHORITIES:
        raise ContactEnrichmentError(f"{inn}.{name}: unknown source_authority {raw['source_authority']}")
    if not _URL.match(raw["source_url"]):
        raise ContactEnrichmentError(f"{inn}.{name}: invalid source_url")
    if name == "website" and not _URL.match(raw["value"]):
        raise ContactEnrichmentError(f"{inn}.website: invalid URL")
    if name == "email" and not _EMAIL.match(raw["value"]):
        raise ContactEnrichmentError(f"{inn}.email: invalid e-mail")
    if name == "address" and raw.get("address_type") not in ADDRESS_TYPES:
        raise ContactEnrichmentError(f"{inn}.address: address_type required")
    try:
        checked = datetime.fromisoformat(raw["checked_at"])
    except ValueError as e:
        raise ContactEnrichmentError(f"{inn}.{name}: invalid checked_at") from e
    if checked.tzinfo is None:
        raise ContactEnrichmentError(f"{inn}.{name}: checked_at needs a timezone")
    return ContactField(raw["value"], raw["source_url"], raw["source_authority"], checked, raw.get("address_type"))


def parse(doc: dict) -> dict[str, ContactRecord]:
    out: dict[str, ContactRecord] = {}
    for c in doc.get("contacts", []):
        inn = c.get("supplier_inn", "")
        if not _INN.match(inn):
            raise ContactEnrichmentError(f"invalid INN {inn!r}")
        if inn in out:
            raise ContactEnrichmentError(f"duplicate INN {inn}")
        if set(c.get("fields", {})) - set(FIELDS):
            raise ContactEnrichmentError(f"{inn}: unsupported contact fields {sorted(set(c['fields']) - set(FIELDS))}")
        if c.get("content_currency") not in CURRENCY:
            raise ContactEnrichmentError(f"{inn}: content_currency must be one of {sorted(CURRENCY)}")
        out[inn] = ContactRecord(inn, c["company_name"], c["identity_basis"], c["identity_source_url"], c["content_currency"],
                                 c.get("content_currency_note", ""),
                                 {f: _field(f, c.get("fields", {}).get(f), inn) for f in FIELDS})
    return out


def load(directory: Path | None = None) -> dict[str, ContactRecord]:
    """INN -> contact record from every *_contact_enrichment.json (empty when none; invalid files raise)."""
    d = directory or repo_root() / "data" / "seed"
    out: dict[str, ContactRecord] = {}
    for path in sorted(d.glob("*_contact_enrichment.json")) if d.is_dir() else []:
        for inn, rec in parse(json.loads(path.read_text(encoding="utf-8"))).items():
            if inn in out:
                raise ContactEnrichmentError(f"duplicate INN {inn} across contact files")
            out[inn] = rec
    return out
