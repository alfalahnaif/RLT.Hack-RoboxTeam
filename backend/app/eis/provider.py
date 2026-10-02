"""Transport boundary for official ЕИС document delivery. No ingestion side effects."""
from __future__ import annotations

from typing import Protocol

import httpx

from app.eis.soap import (ENDPOINT, SOAP_ACTION, CredentialsRequired, DeliveryResult,
                          build_registry_request, parse_delivery_response)


class SoapTransport(Protocol):
    def post(self, url: str, body: bytes, headers: dict[str, str]) -> bytes: ...


class HttpSoapTransport:
    def __init__(self, timeout_seconds: float = 20):
        self.timeout_seconds = timeout_seconds

    def post(self, url: str, body: bytes, headers: dict[str, str]) -> bytes:
        with httpx.Client(timeout=self.timeout_seconds, follow_redirects=False) as client:
            response = client.post(url, content=body, headers=headers)
            response.raise_for_status()
            return response.content


class EisProcurementProvider:
    def __init__(self, transport: SoapTransport, token: str | None):
        self.transport = transport
        self.token = token

    def fetch_by_registry_number(self, registry_number: str, subsystem: str = "PRIZ") -> DeliveryResult:
        if not self.token or not self.token.strip():
            raise CredentialsRequired("Set EIS_SOI_TOKEN locally with an authorized СОИ token")
        body = build_registry_request(registry_number, subsystem, self.token)
        response = self.transport.post(ENDPOINT, body, {
            "Content-Type": "text/xml; charset=utf-8", "SOAPAction": SOAP_ACTION,
        })
        return parse_delivery_response(response)
