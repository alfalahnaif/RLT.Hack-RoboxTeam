"""getDocsIP SOAP 1.1 envelope and response, based on the saved official WSDL/XSD."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from uuid import uuid4
import xml.etree.ElementTree as ET


SOAP_NS = "http://schemas.xmlsoap.org/soap/envelope/"
EIS_NS = "http://zakupki.gov.ru/fz44/get-docs-ip/ws"
SOAP_ACTION = "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip"
ENDPOINT = "https://int.zakupki.gov.ru/eis-integration/services/getDocsIP"


class CredentialsRequired(RuntimeError):
    """Official ЕИС document delivery is unavailable without an authorized СОИ token."""


class EisServiceError(RuntimeError):
    def __init__(self, code: int | None, message: str):
        self.code = code
        super().__init__(f"ЕИС service error {code}: {message}")


@dataclass(frozen=True)
class DeliveryResult:
    archive_urls: tuple[str, ...] = ()
    no_data: bool = False


def _safe_xml(payload: bytes) -> ET.Element:
    if len(payload) > 10_000_000 or b"<!DOCTYPE" in payload.upper() or b"<!ENTITY" in payload.upper():
        raise ValueError("XML size or document type is unsupported")
    try:
        return ET.fromstring(payload)
    except ET.ParseError as error:
        raise ValueError("Malformed ЕИС XML") from error


def _child(parent: ET.Element, name: str) -> ET.Element | None:
    return next((node for node in parent if node.tag.rsplit("}", 1)[-1] == name), None)


def _required_text(parent: ET.Element, name: str) -> str:
    node = _child(parent, name)
    value = (node.text or "").strip() if node is not None else ""
    if not value:
        raise ValueError(f"Missing ЕИС field: {name}")
    return value


def build_registry_request(registry_number: str, subsystem: str, token: str,
                           *, request_id: str | None = None,
                           created_at: datetime | None = None) -> bytes:
    if not token or not token.strip():
        raise CredentialsRequired("Authorized СОИ token is required")
    if not registry_number.isdigit() or not registry_number:
        raise ValueError("registry_number must contain digits only")
    if subsystem not in {"PRIZ", "RGK"}:
        raise ValueError("Only PRIZ and RGK are enabled by this adapter")
    created_at = created_at or datetime.now(timezone.utc)
    if created_at.tzinfo is None:
        raise ValueError("created_at must have a timezone")
    ET.register_namespace("soapenv", SOAP_NS)
    ET.register_namespace("ip", EIS_NS)
    envelope = ET.Element(f"{{{SOAP_NS}}}Envelope")
    header = ET.SubElement(envelope, f"{{{SOAP_NS}}}Header")
    ET.SubElement(header, "individualPerson_token").text = token.strip()
    body = ET.SubElement(envelope, f"{{{SOAP_NS}}}Body")
    request = ET.SubElement(body, f"{{{EIS_NS}}}getDocsByReestrNumberRequest")
    index = ET.SubElement(request, "index")
    ET.SubElement(index, "id").text = request_id or str(uuid4())
    ET.SubElement(index, "createDateTime").text = created_at.isoformat()
    ET.SubElement(index, "mode").text = "PROD"
    selection = ET.SubElement(request, "selectionParams")
    ET.SubElement(selection, "subsystemType").text = subsystem
    ET.SubElement(selection, "reestrNumber").text = registry_number
    return ET.tostring(envelope, encoding="utf-8", xml_declaration=True)


def parse_delivery_response(payload: bytes) -> DeliveryResult:
    envelope = _safe_xml(payload)
    if envelope.tag != f"{{{SOAP_NS}}}Envelope":
        raise ValueError("Expected SOAP 1.1 Envelope")
    body = _child(envelope, "Body")
    if body is None:
        raise ValueError("Missing SOAP Body")
    fault = _child(body, "Fault")
    if fault is not None:
        raise EisServiceError(None, _required_text(fault, "faultstring"))
    response = _child(body, "getDocsByReestrNumberResponse")
    if response is None:
        raise ValueError("Unexpected getDocsIP response")
    data = _child(response, "dataInfo")
    if data is None:
        raise ValueError("Missing ЕИС dataInfo")
    error = _child(data, "errorInfo")
    if error is not None:
        code = int(_required_text(error, "code"))
        message = _required_text(error, "message")
        if code == 5 and "Токены" in message:
            raise CredentialsRequired("ЕИС returned code 5: authorized СОИ token absent")
        raise EisServiceError(code, message)
    no_data = _child(data, "noData")
    if no_data is not None:
        if (no_data.text or "").strip().lower() != "true":
            raise ValueError("Invalid noData response")
        return DeliveryResult(no_data=True)
    urls = tuple((node.text or "").strip() for node in data if node.tag.rsplit("}", 1)[-1] == "archiveUrl")
    if not urls or any(not url.startswith("https://") for url in urls):
        raise ValueError("Missing or unsupported archive URL")
    return DeliveryResult(archive_urls=urls)
