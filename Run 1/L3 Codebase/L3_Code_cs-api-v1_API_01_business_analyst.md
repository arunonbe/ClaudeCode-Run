# Business Analyst View — cs-api-v1_API

## Business Purpose
`cs-api-v1_API` is the modernised, Spring Boot-packaged version of the CS API Version 1 service. It exposes a single SOAP operation (`accountInquiry`) that allows authorised client applications to retrieve prepaid card account information on behalf of cardholders. This is a read-only service: it supports no write operations (no updates, no card reissue — those are V3 capabilities).

The repository contains three modules: the core web service (`card-management-ws`), the WAR packaging module (`card-management-war`), and the Spring Boot packaging module (`card-management-boot`). The Spring Boot module represents the Gen-2 cloud-ready refactoring of this service, replacing the legacy JNDI-configured WAR deployment.

## Capabilities
| Operation | Description |
|---|---|
| accountInquiry | Returns account balance, transaction history, card details, and registration data for a prepaid card identified by card_number or PUID |

This is intentionally narrow compared to V2/V3. V1 was designed as a minimal inquiry API.

## Entities
- **AccountInquiry**: Top-level response aggregate
- **Balance**: Available balance (cents), ledger balance (cents), pending balance, balance date
- **CardDetail**: Masked card number (XXXXXXXX + last 8), PUID, program_id, created_date, last_plastic_date, expiration, account_status
- **TransactionDetail**: date, amount, fee, type (activity+phase mapped to description), details (XXXX masked, or PPID if journal_detail=2)
- **Registration**: first/last/company/attention names, address, city, state, ZIP, home/business/mobile phone, email
- **Response**: completion_code (int), completion_message (string)

## Business Rules
1. Caller must supply a valid `application_id` that maps to an affiliate in the CbaseApp database via the `cs_api_v1_app_id` attribute type.
2. `cs_api_enabled` AND `cs_api_v1` affiliate metadata flags must both be `Y`; otherwise returns code 33035 "You are not allowed to access this service."
3. Either `card_number` or `puid` must be supplied; otherwise returns code 33031 "Missing Account Identifier."
4. PUID lookup must resolve to a valid member ID; null member ID returns code 33032 "Invalid Partner User ID."
5. Card number must resolve to a valid device in the platform; failure returns code 33033 "Invalid Card."
6. Card number in response is masked: first 8 digits → XXXXXXXX; last 8 digits returned. (Note: differs from V3 which masks the middle 8.)
7. Transaction merchant name is always masked as XXXX unless affiliate metadata `cs_api_disp_merchant_name = Y`.
8. If `journal_detail = 2`, the PPID (Partner Payment ID) from transaction addenda replaces the merchant description in `transaction_details`.
9. End date is automatically incremented by 1 day for inclusive range queries.
10. Account status normalised to: active, closed, frozen, lost, or "Contact Ecount for Status."

## Business Flows
```
1. Client Application → SOAP accountInquiry request
2. Validate application_id via AffiliateService (cs_api_v1_app_id lookup)
3. Check cs_api_enabled + cs_api_v1 affiliate flags
4. [Optional] PUID search → resolve to member ID
5. Device create/lookup by card number or member ID
6. Device processInquiry → retrieve balance, journal, definition
7. [Optional] Extended member inquiry → registration data
8. Build masked response → return to client
```

## Compliance Concerns
- **PCI DSS**: Card masking implemented (XXXXXXXX + last 8). Meets basic display masking but not strictly PCI first-6/last-4 (V3 corrects this).
- **Reg E**: Transaction history returned — operator must ensure the correct date range and maximum item count to meet Reg E disclosure requirements.
- **GDPR/CCPA**: Registration data (name, address, email, phone) returned only when `registration_detail > 0`. Callers are responsible for handling returned PII in compliance with applicable privacy regulations.
- **No audit trail for data access**: Individual card lookups are logged at INFO level with timing but not as structured security audit events.

## Risks
1. **Affiliate permission model is binary (Y/N)**: No granular scope or role — a client either has full V1 access or none.
2. **PUID exposure**: The PUID is returned in the `card` object — if the PUID is a sensitive identifier, this represents potential over-disclosure.
3. **No pagination for transaction history**: `max_items` is client-controlled with no server-side cap enforced — large requests could cause performance issues.
4. **Parallel thread safety**: The `AccountManagementImpl` class uses instance-level fields (`output`, `balance`, `card`, `journal`, `reg`, `response`) that are initialised in `initializeInputs()` — these could be re-used across requests if the bean is not prototype-scoped. The v1 Spring Boot config must ensure this bean is request-scoped or re-created per call.
