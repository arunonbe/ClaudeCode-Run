# Business Analyst View — cs-api-singlewar_API

## Business Purpose
`cs-api-singlewar_API` is a packaging consolidation project that bundles both the V1-era account inquiry logic and the V3-era enhanced operations (search, update, reissue, handle escalation) into a single WAR artifact (`CardManagement.war`). Its business value is deployment simplification: instead of deploying separate WARs for V1 and V3 operations, a single WAR serves both API versions under different URL contexts (`/CardManagement/services/AccountManagement` for V1 and `/CardManagementV3/services/AccountManagement` for V3).

This is an intermediate architecture step, likely introduced when clients were migrating from V1 to V3 and needed both versions served simultaneously. It is a Gen-1/Gen-2 bridge artifact.

## Capabilities
| Operation | Version | Description |
|---|---|---|
| accountInquiry | V1 | Search prepaid account by card_number or PUID; returns balance, transactions, registration |
| accountInquiry | V3 | Same as V1 but adds PPD, mobile phone lookup, ship date, comment history, merchant name control |
| updateAccountProfile | V3 | Update cardholder registration data (address, name, phone, email) |
| reissueCard | V3 | Block current card and initiate reissue with block code (lost, stolen, etc.) |
| handleEscalation | V3 | Record a CS escalation event against a member account |

## Entities
- **AccountInquiry**: Aggregate return object — contains Balance, CardDetail, TransactionDetail[], Registration, Response
- **Balance**: Available, ledger, pending amounts + date
- **CardDetail**: Masked card number (first 8 digits masked as XXXXXXXX), PUID, program_id, created_date, last_plastic_date, expiration, account_status, ship_date
- **TransactionDetail**: transaction_date, amount, fee, type, details (merchant name or XXXX masked)
- **Registration**: address_1/2, city, state, ZIP, email, first/last/company/attention name, home/business/mobile phones
- **Response**: completion_code (int), completion_message (string)
- **CommentHistory**: CS note records (escalation ID, dates, problem description, type, employee, status)
- **PaymentDetail**: PPD label/value pairs from transaction addenda

## Business Rules
1. Application ID must map to a valid affiliate program in the CbaseApp database.
2. Either `card_number` or `puid` (V1) / or `ppd` / `mobile_phone` (V3 additionally) must be supplied.
3. `cs_api_enabled` affiliate metadata flag must be `Y` and the version-specific flag (`cs_api_v1` or `cs_api_v3`) must be `Y`.
4. Card number is masked in response: first 8 digits become XXXXXXXX, last 8 digits returned. (Note: V3 later refines this to `first 4 + XXXXXXXX + last 4` — this singlewar version uses the older V1 masking pattern.)
5. Transaction merchant names are masked as `XXXX` unless the affiliate's `cs_api_disp_merchant_name` metadata is set to `Y`.
6. Account status is normalised to one of: active, closed, frozen, lost — otherwise returns "Contact Ecount for Status".
7. End date is automatically incremented by 1 day to include the full requested end day.
8. SQL injection is mitigated via `SQLInjectionScrubber` (single-quote escaping and wildcard stripping) before passing string inputs to backend.

## Business Flows
1. **Account Inquiry (V1)**: client → SOAP → V1 action bean → affiliate lookup → C-Base ecount platform → return balance/card/journal/registration
2. **Account Inquiry (V3)**: same as V1 plus PPD/mobile lookup + comment service + ship date retrieval + PPD promotion details
3. **Update Account**: client → SOAP → V3 action → member search → extended inquiry → field validation → update registration in platform
4. **Reissue Card**: client → SOAP → V3 action → affiliate lookup → device manager → block + reissue operation
5. **Handle Escalation**: client → SOAP → V3 action → affiliate lookup → comment service → create escalation comment

## Compliance Concerns
- Card number is masked in responses — partial compliance with PCI DSS display requirement; however the implementation uses only 8-char masking (XXXXXXXX + last 8) vs. the more secure first 6/last 4 pattern required by PCI DSS.
- The `configPath` entry in `accountManagementContext.xml` hardcodes a Windows filesystem path (`d:\\c-base\\config\\ecount-config.xml`) — indicates deployment on a Windows server with a specific directory layout.
- Application IDs (API keys) are stored in the Spring XML context as key-value pairs — these function as shared secrets with no expiry or rotation mechanism.
- No evidence of transport-layer mutual TLS or message-level signing beyond the HTTPS transport.

## Risks
1. **Legacy Spring framework (2.0.8)**: Well beyond end-of-life; known CVEs exist in Spring 2.x.
2. **Apache Axis 1.x**: The SOAP framework (Axis 1.4) is end-of-life and has known security vulnerabilities.
3. **Single WAR serving two API versions**: Version-specific routing is configuration-level only; a misconfiguration could expose the wrong operation handler to a client.
4. **Static affiliate-to-program mapping in XML**: Adding new affiliates requires a code deployment rather than a data change.
5. **No authentication at SOAP level**: Any caller with a valid `application_id` can invoke operations; there is no session token, no IP allowlisting visible in the code.
