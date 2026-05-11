# Business Analyst Report: stand-in-processing-api

## Business Purpose

The Stand-In Processing API (SASI) is a critical Gen-3 fallback system designed to ensure uninterrupted financial transaction processing when primary applications experience downtime. When the primary card management and transaction systems are unavailable, SASI serves as the active stand-in processor for cardholder debit operations and account management inquiries, targeting 99.999% uptime. It integrates exclusively with Fiserv as the external payment processor.

SASI is built specification-first: REST endpoints are generated from an OpenAPI JSON specification (`openapi.json`) and Fiserv YAML; SOAP endpoints are generated from WSDL files (CsApi_v1.wsdl, CsApi_v3.wsdl). Both REST and SOAP routes share the same business logic and repository layer, mediated by MapStruct mappers.

## Capabilities

- **Account Management**: Account inquiries, updates, maintenance, balance queries via REST (`/api/`) and SOAP (`/ws/`)
- **Debit Operations**: Payment processing, transaction authorisation, card debit operations forwarded to Fiserv via mutual TLS
- **Stand-In Mode**: Designed for active operation during primary system outages; reads from local replicas of legacy databases (cbaseapp, ecountcore, jobsvc, ordersvc) rather than depending on live primary systems
- **Sweep Request Processing**: `SasiSweepRequest` entity suggests processing of fund sweep/consolidation requests during stand-in windows
- **Set PIN**: `SetPinRequest` model in `stip-generated` indicates PIN management capability
- **Azure Service Bus Failover**: `sasi-failover` queue for asynchronous message processing during high-load scenarios

## Client and Cardholder Impact

SASI serves as the last line of defence for cardholder transaction continuity. During primary system outages, cardholders attempting to use their prepaid cards for purchases or withdrawals are routed to SASI. Failures in SASI directly result in transaction declines and inability to access funds — a Reg E breach. Given the 99.999% uptime requirement, SASI is designated as the most availability-critical system in the platform.

## Business Rules in Code

- IP-based access control: only authorised caller IP addresses can invoke SOAP or REST endpoints (`RestSecurityValidator`, `SoapSecurityValidator`)
- REST authentication: `External-Auth-Response` header must be present, parseable as JSON, and contain a valid `validationResult.isValid() == true`
- Circuit breaker protection on Fiserv integration via Resilience4j
- SOAP endpoints use X.509 certificate validation combined with IP verification
- `sasi.dev.disable-security-filter` property allows bypassing all security in local/dev mode
- EhCache used for security validation results (IP lookups, certificate validation) to reduce repeated database queries
- Flyway manages the primary SASI database schema migrations

## Regulatory Obligations

- **PCI DSS**: SASI processes debit card transactions and connects to Fiserv; it is firmly within the Cardholder Data Environment. Requirements 1 (network), 3 (stored data), 4 (encryption in transit), 6 (secure systems), 7 (access restriction), 8 (identity/auth), and 10 (audit) all apply directly. Mutual TLS with Fiserv satisfies Req 4 for that integration
- **Reg E (Electronic Fund Transfer Act)**: As a stand-in processor for debit transactions, SASI must process authorisations within required timeframes; errors or delays in SASI constitute Reg E exposure
- **NACHA**: If ACH transactions are processed during stand-in, NACHA settlement window compliance obligations apply
- **OFAC**: Sanctions screening obligations apply to any cardholder or payee records processed during stand-in; if SASI bypasses real-time OFAC screening during failover, this is a compliance gap
- **GLBA / CCPA / GDPR**: Account management operations handle cardholder PII; data minimisation, access logging, and right-to-deletion obligations apply
- **SOX**: SASI's availability and transaction integrity directly affect the financial reporting accuracy of card programme ledgers

## Key Business Risks

1. **Security bypass via property flag**: `sasi.dev.disable-security-filter=false` is the default, but a misconfiguration setting this to `true` in any non-local environment would disable all authentication and access control across all SASI endpoints
2. **SOAP authentication failure returns 200**: The `SecurityConfig.java` comments and code explicitly acknowledge that SOAP authentication failures return HTTP 200 with no body ("We always return 200 and let the caller figure it out. Yuck.") — this is non-standard and risks silent authentication bypass
3. **Azure App Config connection string committed to `.env`**: The file `stand-in-processing-api/.env` (line 2) contains a full Azure App Configuration connection string including an access key (`Id=zvgN;Secret=[REDACTED — rotate immediately]`) committed to the repository
4. **Primary-system dependency during stand-in**: If SASI itself depends on legacy databases (ecountcore, cbaseapp) that are also part of the failing primary system, a catastrophic failure affecting those databases removes SASI's stand-in capability simultaneously
