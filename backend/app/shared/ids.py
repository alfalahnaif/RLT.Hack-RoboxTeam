"""Deterministic canonical identifiers (contracts v0.2.0, DATA_MAPPING §3)."""
from __future__ import annotations

import hashlib
import uuid

# = uuid5(NAMESPACE_URL, "urn:supplier-radar:canonical")
NAMESPACE = uuid.UUID("9a58f195-b16e-554c-b016-5a636976af05")


def lot_uuid(lot_id: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"lot:{lot_id}")


def item_uuid(lot_id: str, line_no: int) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"item:{lot_id}:{line_no}")


def history_uuid(lot_id: str, supplier_inn: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"history:{lot_id}:{supplier_inn}")


def supplier_uuid(inn: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"supplier:inn:{inn}")


def delivery_uuid(notices_sha: str, suppliers_sha: str, items_sha: str, normalization_version: str) -> uuid.UUID:
    return uuid.uuid5(NAMESPACE, f"delivery:{notices_sha}:{suppliers_sha}:{items_sha}:{normalization_version}")


def item_content_hash(lot_id: str, product_name_raw: str, okpd2_code_raw: str) -> str:
    return hashlib.sha256(f"{lot_id}\x1f{product_name_raw}\x1f{okpd2_code_raw}".encode("utf-8")).hexdigest()
