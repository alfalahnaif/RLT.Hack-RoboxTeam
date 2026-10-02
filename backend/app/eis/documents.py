"""Narrow, source-preserving parser for 44-ФЗ contract XML export documents.

The paths follow the public 13.0 contract export template. Other ЕИС document
families need their own versioned parser after credentialed delivery is tested.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
import xml.etree.ElementTree as ET

from app.eis.soap import _safe_xml
from app.shared.normalize import normalize_inn


def _tag(node: ET.Element) -> str:
    return node.tag.rsplit("}", 1)[-1]


def _path(node: ET.Element, *names: str) -> ET.Element | None:
    for name in names:
        node = next((child for child in node if _tag(child) == name), None)
        if node is None:
            return None
    return node


def _text(node: ET.Element, *names: str) -> str | None:
    target = _path(node, *names)
    value = (target.text or "").strip() if target is not None else ""
    return value or None


def _inn(node: ET.Element, *names: str) -> str | None:
    normalized = normalize_inn(_text(node, *names))
    return normalized.inn if normalized.inn and not normalized.flags else None


@dataclass(frozen=True)
class EisSupplier:
    inn: str | None
    raw_legal_name: str | None


@dataclass(frozen=True)
class EisItem:
    source_item_id: str | None
    name: str | None
    okpd2_code: str | None
    okpd2_label: str | None
    ktru_code: str | None
    quantity: str | None
    unit_code: str | None
    source_price: str | None


@dataclass(frozen=True)
class EisContract:
    source_system: str
    source_document_type: str
    source_document_id: str | None
    registry_number: str
    procurement_number: str | None
    customer_inn: str | None
    suppliers: tuple[EisSupplier, ...]
    items: tuple[EisItem, ...]
    document_date: date
    retrieved_at: datetime
    source_url: str | None
    raw_sha256: str
    contract_value: str | None

    @property
    def supplier_inns(self) -> tuple[str, ...]:
        return tuple(supplier.inn for supplier in self.suppliers if supplier.inn)


def parse_contract(payload: bytes, *, source_url: str | None, retrieved_at: datetime) -> EisContract:
    if retrieved_at.tzinfo is None:
        raise ValueError("retrieved_at must have a timezone")
    root = _safe_xml(payload)
    contract = _path(root, "contract") if _tag(root) == "export" else root
    if contract is None or _tag(contract) != "contract":
        raise ValueError("Expected ЕИС contract export XML")
    registry_number = _text(contract, "regNum")
    published = _text(contract, "publishDate")
    if not registry_number or not published:
        raise ValueError("Contract registry number and publish date are required")
    try:
        document_date = date.fromisoformat(published[:10])
    except ValueError as error:
        raise ValueError("Invalid contract publish date") from error
    supplier_parent = _path(contract, "suppliers")
    suppliers = tuple(EisSupplier(
        inn=_inn(supplier, "legalEntityRF", "INN"),
        raw_legal_name=_text(supplier, "legalEntityRF", "fullName"),
    ) for supplier in supplier_parent if _tag(supplier) == "supplier") if supplier_parent is not None else ()
    item_parent = _path(contract, "products")
    items = tuple(EisItem(
        source_item_id=_text(product, "externalSid"),
        name=_text(product, "name"),
        okpd2_code=_text(product, "OKPD2", "code"),
        okpd2_label=_text(product, "OKPD2", "name"),
        ktru_code=_text(product, "KTRU", "code"),
        quantity=_text(product, "quantity"),
        unit_code=_text(product, "OKEI", "code"),
        source_price=_text(product, "price"),
    ) for product in item_parent if _tag(product) == "product") if item_parent is not None else ()
    return EisContract(
        source_system="EIS", source_document_type="contract",
        source_document_id=_text(contract, "id"),
        registry_number=registry_number,
        procurement_number=_text(contract, "foundation", "fcsOrder", "order", "notificationNumber"),
        customer_inn=_inn(contract, "customer", "inn"),
        suppliers=suppliers, items=items, document_date=document_date,
        retrieved_at=retrieved_at, source_url=source_url,
        raw_sha256=sha256(payload).hexdigest(),
        contract_value=_text(contract, "priceInfo", "price"),
    )
