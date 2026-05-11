# accept-prechecks_API — Business Analyst View

## Business Purpose

The Accept Prechecks API is a SOAP web service that validates and accepts pre-authorised paper checks (prechecks) on behalf of a presenting vendor or merchant. It acts as a gating service: a caller submits check details before physically accepting a precheck from a consumer, and the API verifies whether that check is legitimate, authorised, and has not already been processed or stopped. On successful validation, the service marks the check as "accepted" in the ecount Core payment platform.

The service is historically used in the Certegy check-guarantee ecosystem (the `facility` property is hardcoded to `"certegy"` in `application.yml`). It is consumed by downstream systems or partner integrators who need real-time precheck acceptance decisions.

## Business Capabilities

| Capability | Implementation Evidence |
|---|---|
| Precheck validation and acceptance | `AcceptPrecheckService.acceptPrecheck()` — `AcceptPrecheckServiceImpl.java` |
| Format validation (check number, serial number) | Regex patterns `\\d{8}|\\d{14}` (check), `\\d{3}|\\d{10}` (serial) — `AcceptPrecheckServiceImpl.java` lines 36–37 |
| Amount verification against authorised amount | `definition.authorized_amount.intValue() != requestAmount` — line 169 |
| Serial number match against core record | `definition.serial_number` comparison — line 177 |
| Last-name identity verification | `validateLastName()` against ecount Core addenda field `cz-lastname` — line 197 |
| Check lifecycle status enforcement | States: `authorized`, `verified`, `stopped`, `accepted` — lines 31–34 |
| Citibank check special-case handling | Check number `38791282` triggers left-zero-padded serial number — lines 82–86, 114–116 |
| Test mode (dry-run) support | `testMode` boolean suppresses the `preCheckMerchantVerify` call — line 109 |
| Health check endpoint | `GET /hc` returns "OK" — `HealthCheck.java` |

## Business Entities

| Entity | Fields | Source |
|---|---|---|
| **AcceptPrecheckRequest** | `checkNumber`, `serialNumber`, `amount` (BigDecimal), `lastName`, `vendorId`, `testMode` (Boolean) | `AcceptPrecheckRequest.java` |
| **AcceptPrecheckResponse** | `validateCheckReturnFailureCodeResult` (byte), `errorMessage`, `failedAt` | `AcceptPrecheckResponse.java` |
| **PreCheckDefinition** | `authorized_amount`, `serial_number`, `status`, `addenda` (map with `cz-lastname`) | Referenced from `com.cbase.business.core.value.PreCheckDefinition` (xplatform dependency) |

## Business Rules & Validations

1. **Check Number Format**: Must be exactly 8 or 14 digits (`\\d{8}|\\d{14}`). Validation is applied before the null check, creating a null-pointer risk (see Business Risks).
2. **Serial Number Format**: Must be exactly 3 or 10 digits (`\\d{3}|\\d{10}`). Same ordering risk.
3. **Amount Match**: Request amount (converted to integer cents) must exactly match `PreCheckDefinition.authorized_amount`. Code: `(int)(amount.floatValue() * 100)` — floating-point conversion is a precision risk.
4. **Serial Number Match**: If the core record has a non-null serial number, it must match the request serial.
5. **Last Name Match**: If the check addenda contains `cz-lastname`, it must case-insensitively equal the request `lastName`. An absent `cz-lastname` in addenda causes the validation to return `true` (pass-through) — `validateLastName()` line 202.
6. **Check Status Gate**: Check must be in `authorized` status. `stopped` → code 20, `verified` → code 30, any other non-`authorized` → code 10 (already processed).
7. **Citibank Override (Check Number 38791282)**: The routing number `38791282` is treated as the Citibank routing number; in this case the actual check identifier is the serial number, which is left-padded to 10 digits. This hardcoded logic appears in three distinct places (`process()`, `validateAgainstDefinition()`, and the padding method).
8. **Empty Last Name**: An empty last name always returns `INVALID_CREDENTIALS` (code 50), before attempting further lookup.

## Business Flows

### Normal Acceptance Flow
1. Caller submits SOAP `acceptPrecheck` request with `checkNumber`, `serialNumber`, `amount`, `lastName`, `vendorId`.
2. Citibank routing number check → pad serial if needed.
3. Format validation: check number regex → serial number regex.
4. Core lookup: `IEManageManager.preCheckDefinitionInquiry(checkNumber, 1)` returns `PreCheckDefinition`.
5. Status validation: must be `authorized`.
6. Amount validation: authorised amount must match.
7. Serial validation: core serial (if present) must match.
8. Last-name validation: addenda `cz-lastname` (if present) must match.
9. If `testMode` is false: `preCheckMerchantVerify(checkNumber, "accepted", "certegy", callerInfo)` updates the check status.
10. Return `NO_PROBLEMS` (code 0).

### Error Paths (Response Codes)
- `00` NO_PROBLEMS — successful acceptance
- `10` ALREADY_PROCESSED — check not in `authorized` or any other unrecognised status
- `20` ALREADY_VOIDED — check is `stopped`
- `30` CHECK_VERIFIED — check already `verified`
- `40` INVALID_CHECK_NUMBER — format mismatch, core not found, or serial mismatch
- `50` INVALID_CREDENTIALS — empty or mismatched last name
- `60` INVALID_AMOUNT — amount mismatch
- `70` INVALID_SERIAL_NUMBER — format mismatch
- `90` SYSTEM_DOWN — any unhandled Throwable

## Compliance & Regulatory Concerns

- **Reg E / Payment Authorisation**: The service gates whether a consumer-issued precheck can be accepted. Incorrect acceptances (e.g., due to the last-name pass-through when `cz-lastname` is absent) could constitute unauthorised debit against a consumer's bank account — a Reg E exposure.
- **NACHA / Check Processing Rules**: The check lifecycle states (`authorized → accepted`) map to ACH/check clearing states. Premature or duplicate acceptances violate check-guarantee rules.
- **PCI DSS**: The request contains `checkNumber` (bank routing/account number) and `lastName`. These are sensitive financial identifiers. The `toString()` method on `AcceptPrecheckRequest` logs `checkNumber` at INFO level (`log.info("processing request " + request.toString())` — `AcceptPrecheckServiceImpl.java` line 58). This constitutes logging of payment-sensitive data and may breach PCI DSS Requirement 3.3/10.3.
- **Data Minimisation (CCPA/GDPR)**: `lastName` is a personal data element. It is logged indirectly through the request `toString()`, which includes it in the output.
- **Vendor Identity**: The `vendorId` field is accepted in the request but never validated or used in any business logic — it is present in the request object but unused in `AcceptPrecheckServiceImpl`.

## Business Risks

1. **Last-name bypass**: When `cz-lastname` is absent from check addenda, the last-name validation unconditionally returns `true` (`LastNameValidatorECountCore` is present but not wired into `AcceptPrecheckServiceImpl` — the service only checks addenda, not the card-holder record). Any caller who submits any last name for a check without addenda will pass validation.
2. **Hardcoded facility**: `facility=certegy` is hardcoded in `application.yml`. If the service is used for non-Certegy checks, all verify calls will use the wrong facility.
3. **Floating-point amount comparison**: `(int)(request.getAmount().floatValue() * 100)` can introduce rounding errors for amounts like $1.10 or $9.99.
4. **Null-before-regex check**: In `process()`, `matcher.matches()` is called before the null guard (`if ((checkNumber == null)`), so a null `checkNumber` will throw `NullPointerException` — `AcceptPrecheckServiceImpl.java` lines 88–93. Same for `serialNumber`.
5. **vendorId not validated**: The `vendorId` field is received, serialised, and logged but never validated against any authorised vendor list.
