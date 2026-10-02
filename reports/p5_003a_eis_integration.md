# P5-003A ЕИС adapter: authentication boundary

**Status:** integration-ready, credentials required for live ingestion.

## Implemented

- Isolated `getDocsIP` SOAP 1.1 request builder, HTTP transport interface, and response parser for registry-number delivery (`PRIZ`/`RGK`). The endpoint and SOAP action come from the [official WSDL](https://int.zakupki.gov.ru/eis-integration/services/getDocsIP?wsdl); request/response field names come from its [official XSD](https://int.zakupki.gov.ru/eis-integration/services/getDocsIP?xsd=getDocsIP-ws-api.xsd).
- The provider rejects missing credentials **before any network request**. It does not follow redirects or log the token. SOAP responses distinguish archive links, `noData`, service errors, and the observed missing-token error.
- An offline parser for a 44-ФЗ `contract` XML export preserves registry and procurement numbers, document date, customer/supplier INNs, raw supplier name, exact source OKPD2/KTRU fields when present, item values, source URL, retrieval time, and raw SHA-256. It does not derive comparable unit prices or write to a database.
- Saved official WSDL/XSD snapshots (retrieved 2026-10-02) and small schema-based SOAP fixtures. The reduced contract fixture is **illustrative**, derived from a [public contract export template](https://github.com/AmaliyaG/portal44_xml/blob/master/templates/contract.xml); it is not a live ЕИС record.

## Tested

- Offline ЕИС adapter/XML tests: **9 passed**. Combined ЕИС and shared unit tests: **230 passed**.
- The wider unit command had **357 passed, 33 failed, 14 errors** because this isolated worktree has no `DATABASE_URL`; those database-dependent tests were not treated as ЕИС regressions.
- No live archive was retrieved, no real procurement XML was ingested, and no 5–10 case pilot or organizer overlap comparison was performed. No organizer, ranking, HOLDOUT, or other application data was changed.

## Exact blocker and later activation

The official `getDocsIP` endpoint answered an unauthenticated request with `errorInfo/code=5`: **«Токены для сервисов отдачи отсутствуют в ЕИС»**. The user confirmed that neither an authorized СОИ token nor official XML/ZIP files are available. A local token can later be supplied as `EIS_SOI_TOKEN` (never committed) and passed to `EisProcurementProvider(HttpSoapTransport(), os.environ.get("EIS_SOI_TOKEN"))`. Then call `fetch_by_registry_number(number, "PRIZ")` or `"RGK"`. Its archive URL result still needs authorized download, archive validation, versioned document parsing, and separate evidence persistence before any live ingestion claim. The SOAP header format and end-to-end authorization should be verified with the actual token before enabling production use.

The WSDL also lists `getDocsByOrgRegion`, `getDocSignaturesByUrl`, `getPreparedPart`, and `getNsi`; this patch implements only registry-number retrieval. No HTML search scraping was used.
