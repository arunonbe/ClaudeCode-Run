# Business Analyst View — cs-api-v3_API

## Business Purpose
`cs-api-v3_API` is the third and current generation of the CS (Customer Service) API. It is the production platform for B2C cardholder inquiry and account management. V3 replaces both V1 (read-only) and V2 (basic read/write) with a significantly expanded capability set, dynamic affiliate permission management, and a modern Spring Boot 3 / Azure-native deployment model.

V3 is the first CS API generation to include: card reissue, escalation handling, PPD promotion data, comment history, mobile phone search, international address support, DDA-only account lookup, and a full payout sub-service for cardholder self-service portal operations.

## Capabilities

### Core CS Operations
| Operation | Description |
|---|---|
| searchAccount | Returns account balance, transactions, card details, registration; supports search by card number, PUID, PPD, or mobile phone |
| updateAccount | Updates cardholder registration (name, address, phone, email); writes audit comment; supports international addresses |
| reissueCard | Initiates card reissue; writes audit comment; checks affiliate reissue permission flag |
| handleEscalation | Creates or updates a CS escalation comment entry in the cardholder record |

### Payout Sub-Service Operations
| Operation | Description |
|---|---|
| payoutAccountInquiry | Account inquiry with DDA number; returns payout-specific balance and registration including DDA details |
| authenticationReq | Authenticate cardholder for self-service portal access |
| forgotUserNameReq | Retrieve username for portal login recovery |
| registrationReq | Register cardholder for self-service portal |
| updatePasswordReq | Update cardholder portal password |
| updateRegistrationReq | Update cardholder registration from self-service portal |

## Entities
- **AccountInquiry**: Balance, CardDetail (with ship date), TransactionDetail[] (with PPD), PaymentDetail[], CommentHistory[], Registration, Response
- **AccountProfile**: puid, application_id or program_id, address fields, name fields, home/mobile/business phones, home_email, postal, state, country (supports international)
- **Response**: code (int), message (String) — integer codes throughout (not String as in V2)
- **PaymentDetail**: PPD-based partner payment promotion data per transaction
- **CommentHistory**: Historical CS comment entries per cardholder
- **CardDetail additions in V3**: ship_date, card masking changed to first-4 + XXXXXXXX + last-4

## Business Rules

### Application Authentication
1. `application_id` must resolve to an affiliate via `AffiliateService.getAffiliateForValue("cs_api_v3_app_id", application_id)` — dynamic lookup, not a static XML map.
2. Resolved affiliate must have `cs_api_enabled = Y` and `cs_api_v3 = Y` flags.
3. Access can be revoked immediately by setting either flag to `N` — no redeployment required.

### Search Account
1. At least one of: card_number, puid, ppd, mobilePhone must be provided; otherwise returns 34002.
2. Card masking: first 4 digits + XXXXXXXX + last 4 digits (16-character total preserved).
3. Merchant name in transaction detail: shown if affiliate has `cs_api_disp_merchant_name = Y`; otherwise masked as XXXX.
4. Auth sync: if program is in `authSyncPrograms`, a Samsung API balance refresh is triggered before returning balance.
5. DDA-only accounts (no prepaid card) are supported; identified by `isDDAOnly` flag.
6. FiservDR resilient inquiry path for programs in `fiservDRPrograms` list.
7. Comment history: always retrieved for last 12 months (depth=12, offset=0).
8. PPD promotion details: returned per transaction if PPDPromotionXref data is available.

### Update Account
1. PUID is required.
2. Email must match pattern `[^@]+@[^@]+[.][^@]+`.
3. Email suffix must not be in restricted domain list (`.cu,.ir,.kp,.sy,.ua` — OFAC-related).
4. KYC required flag (`kyc_required`) changes authorisation path: if `kyc_required=N`, only application_id-based updates are permitted; program_id direct updates are blocked.
5. If address fields change, an audit comment is auto-written via `ICommentService`.
6. International country support: state field extended to 3 chars, postal to 12 chars.
7. International programs validated via Redis HTTP lookup: `programSetup/{affiliateID}/intlProgram`.

### Card Reissue
1. Affiliate must have reissue permission; operation writes an audit comment.
2. Returns `Response` with integer completion code.

### Payout Authentication
1. Cardholder authentication is gated by XSecurity service.
2. DDA number transmitted encrypted (JWE); decrypted via JweHelper using `jwe.secretKey`.

## Business Flows

### Search Account
```
Client → SOAP searchAccount(application_id, card_number/puid/ppd/mobilePhone, ...)
→ AffiliateService.getAffiliateForValue("cs_api_v3_app_id", application_id)
→ check cs_api_enabled + cs_api_v3 flags
→ MemberService.searchMemberByPuid / inquiry / inquiryDdaOnly
→ DeviceService.inquiryEcard (or inquiryEcardResilient for FiservDR programs)
→ Comment history, PPD promotions, balance, registration assembly
→ Return AccountInquiry (masked)
```

### Update Account
```
Client → SOAP updateAccount(AccountProfile)
→ Translate application_id via AffiliateService
→ Check cs_api_enabled + cs_api_v3 + kyc_required flags
→ prepareInputData (trim, length check)
→ validateRequest (email format, restricted suffix, phone digits, name chars)
→ Redis lookup for international program
→ performUpdate → MemberService.update
→ If address changed: ICommentService.addComment
→ Return Response (int code)
```

## Compliance Concerns
- **JWE keys committed to source**: `applicationContext-CSWS.properties` contains `jwe.secretKey` and `jwe.secretToken` in plaintext — these are production encryption keys; immediate rotation and secrets management migration required.
- **OFAC restricted email domains**: `.cu,.ir,.kp,.sy,.ua` — enforcement present, but list is managed in a properties file, not a centralised OFAC screening system.
- **Comment audit trail**: Address changes write an audit comment (V2/V1 did not). This covers UDAAP/audit requirements for profile changes.
- **DDA encryption**: DDA numbers are JWE-encrypted in transit; however, the encryption keys are committed to the repository (see above).
- **PUID in logs**: `puid` value logged at debug level — production log level configuration must suppress debug to prevent PUID exposure in production logs.

## Risks
1. **JWE secret committed**: Encryption key and token for DDA number encryption are in a committed properties file.
2. **Redis single point**: International program lookup goes to a Redis HTTP endpoint; no fallback documented.
3. **Comment service failure not fatal**: If `ICommentService.addComment` throws, the update still succeeds (exception logged only). Audit gap possible if comment service is degraded.
4. **authSync balance refresh**: Samsung API programs trigger an extra platform call per inquiry — additional latency and dependency.
