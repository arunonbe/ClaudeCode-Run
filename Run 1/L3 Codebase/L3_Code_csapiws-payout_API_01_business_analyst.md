# Business Analyst View — csapiws-payout_API

## Business Purpose
`csapiws-payout_API` is the standalone WAR deployment of the CS API Payout sub-service. It provides the server-side SOAP operations that power the B2C cardholder self-service payout portal. This service allows payout portal clients (web or mobile) to perform account inquiry and registration updates on behalf of the cardholder without direct platform access.

It is a specialised extension of the CS API family, focused entirely on the payout use case. The artifact name is `CardManagementPayoutV3`, context path `/CardManagementPayoutV3`. It originated in the northlane GitLab group and is deployed to Windows Tomcat (servers-8.5.5.7 naming convention).

Note: The payout SOAP sub-service is also included within `cs-api-v3_API` as the `csapi-v3-payout-ws` and `csapi-v3-payout-war` modules. This standalone repository (`csapiws-payout_API`) appears to be the original deployment vehicle that pre-dates the V3 Spring Boot consolidation.

## Capabilities

### Active Operations (as of JIRA 476 changes)
| Operation | Description |
|---|---|
| payoutAccountInquiry | Returns payout-specific account inquiry including balance, transactions, PayoutApp metadata (terms URL, fees URL, ATM type, CS phone, logo URL), and PayoutAppRegistration |

### Commented-Out Operations (JIRA 476 — suspended, not deleted)
The following operations are fully implemented in source but commented out in `AccountManagement.java` and in the Spring XML context:
- `accountInquiry` (general card inquiry)
- `updateAccountProfile` (profile update)
- `reissueCard` (card reissue)

### Active but Separate from Interface
`updateRegistrationAction` bean is wired in `accountManagementContext.xml` and the `UpdateRegistrationAction` class is present — this operation may be exposed through a different binding or was prepared for reactivation.

## Entities
- **PayoutAccountInquiry** (extends AccountInquiry): Balance, CardDetail, TransactionDetail[], PaymentDetail[], CommentHistory[], Registration, Response, **PayoutApp**, **PayoutAppRegistration**
- **PayoutApp**: termsURL, feesURL, ATMType, CSPhone, CustomLogoURL — payout portal content URLs retrieved from CMS
- **PayoutAppRegistration**: cardholder registration as seen by the payout portal
- **UpdateRegistrationDetails**: puid, application_id, address, name, phone, email, ddaNumber — payout registration update input
- **AccountInquiry** (base): Balance, CardDetail, TransactionDetail[], Registration, Response

## Business Rules

### Application Authentication
1. `application_id` must resolve to an affiliate via `AffiliateService.getAffiliateForValue("cs_api_payout_app_id", application_id)` — note the attribute type is `cs_api_payout_app_id`, not `cs_api_v3_app_id`.
2. Access can be revoked without redeployment by removing the AffiliateService mapping.

### Payout Account Inquiry
1. At least one of: card_number, puid, ppd, or ddaNumber must be provided; otherwise returns error.
2. Card masking applied on return.
3. PayoutApp metadata (terms URL, fees URL, etc.) retrieved from CMS ContentManagementServiceClient.
4. PPD promotion data assembled per transaction.
5. Comment history retrieved.
6. Merchant name display controlled by `displayMerchantName` affiliate flag.

### Update Registration (UpdateRegistrationAction)
1. Supports US, CA, and MX state/province validation (three state sets: USStatesSet, CAStatesSet, MXStatesSet).
2. MX (Mexico) state list included — extends beyond the US/CA-only support in V2 and standalone V3 updateAccount.
3. DDA number lookup via `CoreDeviceDDAInquiry` — SQL-based DDA account lookup.
4. Address change writes an audit comment via `ICommentService` (csUserId = "cs-api-Payout").
5. PUID is required for all update operations.

### Geography
This service is notable for being the only CS API component with explicit Mexican state validation (32 MX state/territory codes in `MXStatesSet`). V1, V2, and the main V3 updateAccount support US and Canada only.

## Business Flows

### Payout Account Inquiry
```
Payout Portal Client → SOAP payoutAccountInquiry(application_id, card_number/puid/ppd/ddaNumber, ...)
→ AffiliateService.getAffiliateForValue("cs_api_payout_app_id", application_id)
→ MemberManager / EMember / EDevice (xPlatform RPC)
→ PPD data, comment history, balance, registration
→ CMS ContentManagementServiceClient → PayoutApp metadata (URLs, ATM type, CS phone)
→ Return PayoutAccountInquiry (masked)
```

## Compliance Concerns
- **No `cs_api_enabled` flag check**: Unlike V3's searchAccount, `PayoutSearchAccount` only checks `cs_api_payout_app_id` mapping — there is no explicit `cs_api_enabled` permission flag validation documented in the source. Revocation depends entirely on removing the AffiliateService mapping.
- **PUID in logs**: INFO-level logging may expose PUID values.
- **Comments audit**: UpdateRegistrationAction writes audit comments with csUserId "cs-api-Payout" — addresses V2's no-audit-trail gap for this operation.
- **Legacy platform dependency**: xPlatform RPC (not ecount-core-rest-api) — same generation as V2.

## Risks
1. **JIRA 476 commented operations**: Three operations (accountInquiry, updateAccountProfile, reissueCard) are suspended by comment rather than removed. If these are ever uncommented without proper testing and security review, partially validated code paths would be re-exposed.
2. **Standalone vs. embedded**: The same payout logic exists in both this repository and in `cs-api-v3_API/csapi-v3-payout-ws`. If bugs are fixed in one, they must be manually propagated to the other. There is no shared library relationship.
3. **Windows Tomcat deployment**: GitLab CI targets named Windows servers (`d-na-app02`, `q-na-app01`, `q-na-app02`) — not containerised; manual or Tomcat manager deployment.
4. **Version misalignment**: `csapiws-payout_API` uses xPlatform 2019.1.1 and xPlatformLibrary 2014.3.1; `cs-api-v3_API` uses xPlatform 6.5.8. The payout standalone repo is on an older internal library version.
