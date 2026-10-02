"""Offline contract tests against a saved official getDocsIP WSDL/XSD snapshot."""
from datetime import datetime, timezone
from pathlib import Path
import xml.etree.ElementTree as ET

import pytest

from app.eis.provider import EisProcurementProvider
from app.eis.soap import CredentialsRequired, EisServiceError, build_registry_request, parse_delivery_response
from app.eis.documents import parse_contract


FIXTURES = Path(__file__).parent / "fixtures"


def test_official_schema_snapshot_exposes_used_operation():
    wsdl = ET.parse(FIXTURES / "getDocsIP.wsdl")
    xsd = ET.parse(FIXTURES / "getDocsIP-ws-api.xsd")
    assert wsdl.find(".//{http://schemas.xmlsoap.org/wsdl/}operation[@name='getDocsByReestrNumber']") is not None
    assert xsd.find(".//{http://www.w3.org/2001/XMLSchema}element[@name='getDocsByReestrNumberRequest']") is not None


def test_request_uses_schema_fields_and_token_header():
    xml = build_registry_request("0372200000923001155", "RGK", "secret", request_id="12345678-1234-1234-1234-123456789012",
                                 created_at=datetime(2026, 10, 2, tzinfo=timezone.utc))
    root = ET.fromstring(xml)
    assert root.find(".//individualPerson_token").text == "secret"
    assert root.find(".//reestrNumber").text == "0372200000923001155"
    assert root.find(".//subsystemType").text == "RGK"
    assert root.find(".//mode").text == "PROD"


@pytest.mark.parametrize("fixture, expected", [("delivery_error.xml", "credentials"), ("delivery_archive.xml", "archive")])
def test_soap_responses(fixture, expected):
    payload = (FIXTURES / fixture).read_bytes()
    if expected == "credentials":
        with pytest.raises(CredentialsRequired):
            parse_delivery_response(payload)
    else:
        assert parse_delivery_response(payload).archive_urls == ("https://int.zakupki.gov.ru/example.zip",)


def test_provider_refuses_network_without_token():
    class NoNetwork:
        def post(self, *args, **kwargs):
            raise AssertionError("network call must not occur")

    with pytest.raises(CredentialsRequired):
        EisProcurementProvider(NoNetwork(), token=None).fetch_by_registry_number("0372200000923001155")


def test_provider_surfaces_auth_error_without_downloading_archive():
    class FakeTransport:
        def post(self, url, body, headers):
            assert url.endswith("/getDocsIP")
            assert headers["SOAPAction"] == "http://zakupki.gov.ru/fz44/queue/ws/get-docs-ip"
            return (FIXTURES / "delivery_error.xml").read_bytes()

    with pytest.raises(CredentialsRequired):
        EisProcurementProvider(FakeTransport(), token="test-only").fetch_by_registry_number("0372200000923001155")


def test_contract_parser_preserves_source_identity_and_dates():
    payload = (FIXTURES / "contract_sample.xml").read_bytes()
    record = parse_contract(payload, source_url="https://int.zakupki.gov.ru/example.xml",
                            retrieved_at=datetime(2026, 10, 2, tzinfo=timezone.utc))
    assert record.registry_number == "2780804311155801217"
    assert record.procurement_number == "0372200000923001155"
    assert record.supplier_inns == ("7727809340",)
    assert record.customer_inn == "7813045709"
    assert [item.okpd2_code for item in record.items] == ["21.20.10.221", "21.20.10.222"]
    assert record.document_date.isoformat() == "2023-02-28"
    assert len(record.raw_sha256) == 64
    assert record.contract_value == "10000.00"


def test_contract_parser_rejects_malformed_and_wrong_document_type():
    with pytest.raises(ValueError):
        parse_contract(b"<broken", source_url=None, retrieved_at=datetime.now(timezone.utc))
    with pytest.raises(ValueError):
        parse_contract(b"<export><other/></export>", source_url=None, retrieved_at=datetime.now(timezone.utc))


def test_non_auth_service_error_is_explicit():
    payload = (FIXTURES / "delivery_error.xml").read_bytes().replace(b"<code>5</code>", b"<code>7</code>")
    with pytest.raises(EisServiceError) as error:
        parse_delivery_response(payload)
    assert error.value.code == 7
