# Business Analyst View — cs-api-v2_API

## Business Purpose
`cs-api-v2_API` is the second generation of the CS (Customer Service) API. It extends V1's read-only account inquiry with a write operation: `updateAccountProfile`. This allows authorised client applications to update a cardholder's registration data (address, name, phone, email) without direct access to the C-Base platform.

V2 is the first CS API version to include mutation capability. It is a WAR-only deployment with no Spring Boot module, making it a pure Gen-1 artifact. It is the last version using a static application_id-to-program-id mapping in XML configuration (V3 moved to dynamic AffiliateService lookup for application IDs).

Key distinguishing characteristics from V1:
- Adds `updateAccountProfile` operation
- Adds `AccountProfile` request object with full cardholder address/contact fields
- Adds `ZipValidation` class for postal code validation
- Application IDs still mapped statically in XML
- Context path: `/CardManagementV2`

## Capabilities
| Operation | Description |
|---|---|
| accountInquiry | Returns account balance, transactions, card details, registration (same as V1) |
| updateAccountProfile | Updates cardholder registration data: name, address, phone, email |

V2 does not include: card reissue, escalation handling, PPD details, mobile phone search, comment history, ship date — all of which were added in V3.

## Entities
- **AccountInquiry** (same structure as V1): Balance, CardDetail, TransactionDetail[], Registration, Response
- **AccountProfile** (V2 addition): puid, program_id, address fields, name fields, home/mobile/business phones, home_email, postal, state, country, suffix_name
- **ResultCode** (V2 addition): code (String), description (String) — update operation response
- **ZipValidation**: US ZIP and Canadian postal code validation patterns

## Business Rules
### Account Inquiry
1. `application_id` must map to an affiliate in the static configMap in `accountManagementContext.xml`.
2. `card_number` or `puid` required; otherwise returns 34002.
3. Card number masked as XXXXXXXX + last 8.
4. Merchant name always masked as XXXX (V2 has no `cs_api_disp_merchant_name` flag check — always masks).

### Update Account Profile
1. `program_id` must map to a valid affiliate via static configMap lookup.
2. `puid` is required; PUID must resolve to a member ID.
3. Email must match pattern `[^@]+@[^@]+[.][^@]+`.
4. Phones must contain at least 10 digit characters.
5. Name fields must not contain characters from `|"_+%$#/=()?,`.
6. Address fields are trimmed and length-checked (address: 26, city: 18, state: 2, postal: 10).
7. Country must be US or CA.
8. Postal code must match: 5-digit US ZIP, 9-digit US ZIP+4, or Canadian A#A #A# format.
9. State must be a 2-char alphabetic state code.
10. If postal code or state differs from the existing record, the new value is validated before update.

## Business Flows
### Account Inquiry
Same flow as V1: validate app_id → PUID/card lookup → device inquiry → return masked response.

### Update Account Profile
```
1. Client → SOAP updateAccountProfile(AccountProfile)
2. Translate program_id via static configMap
3. prepareInputData: trim + length-check all fields
4. validateRequest: email format, phone digit count, name character set
5. performUpdate:
   a. PUID member search → resolve member ID
   b. processInquiryExtended → retrieve current registration
   c. checkAgainstExistingProfile → validate postal/state against existing record
   d. updateRegistrationInfo → set registration fields, call processUpdate
6. Return ResultCode (code "0" = success)
```

## Compliance Concerns
- **No affiliate-level permission flag check**: V2's `accountInquiry` uses static configMap lookup — if an application_id is in the map, it has access. There is no `cs_api_enabled` or `cs_api_v2` flag check as V3 implements. Revoking access requires removing the application_id from XML and redeploying.
- **Update operation without audit log**: The `updateAccountProfile` operation does not write a comment/audit entry (V3's `updateAccount` adds the `addCommentForAddress` call). Address changes by CS API have no traceable audit trail in V2.
- **PUID exposure**: `profile.getPuid()` is logged at INFO level — PUID values may appear in logs.
- **Country validation limited to US/CA**: V2 explicitly only supports US and Canadian addresses; no internationalisation support.

## Risks
1. **Static configMap for application IDs**: Compromised or deprecated API keys cannot be revoked without a code deployment.
2. **Null pointer in `generateErrorCode`**: `rc.setCode("7")` where `rc` is declared as `ResultCode rc=null` — this is a confirmed NPE bug in the code path triggered when `updateRegistrationInfo` returns a non-zero error code.
3. **`isValidState` method**: Uses `matchesPattern(s, "AA")` which only checks that the string is exactly 2 alpha characters — it does not validate against the US state list. Any 2-letter string would pass.
4. **Java 1.5 source/target**: Extremely outdated; no modern language features; end-of-life since 2009.
5. **Spring 2.5.4**: End-of-life; known CVEs.
