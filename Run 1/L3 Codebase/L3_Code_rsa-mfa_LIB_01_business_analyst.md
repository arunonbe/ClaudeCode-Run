# Business Analyst Analysis: rsa-mfa_LIB

## Business Purpose
rsa-mfa_LIB is a security-critical Java library that provides Multi-Factor Authentication (MFA) capabilities for the Onbe prepaid card platform by integrating with RSA Adaptive Authentication (RSA CSD). It enables the platform's consumer-facing applications (One Platform, Client Zone) to challenge cardholders and internal users with additional authentication factors beyond their primary password.

The library was originally developed under the CitiPrepaid brand and supports the full MFA lifecycle: risk analysis, knowledge-based authentication (KBA) questions, OTP delivery (SMS and phone call via TeleSign), and authentication result management.

## Capabilities
1. **Risk Analysis (Analyze)**: Submit a user's device fingerprint and session context to RSA for adaptive risk scoring. RSA returns an action recommendation: ALLOW, CHALLENGE, or DENY.
2. **KBA Question Management**: Retrieve available challenge questions, set user Q&A, retrieve user's assigned questions, and validate user answers.
3. **OTP Delivery (SMS/Phone)**: Deliver a one-time passcode to the user's registered phone number via TeleSign SMS or TeleSign voice call.
4. **OTP Validation**: Authenticate an OTP submission against RSA; update user status to VERIFIED if first-time OTP user.
5. **User Status Management**: Update user status (VERIFIED/UNVERIFIED) in RSA via updateUser API call.
6. **Notify**: Post authentication level outcomes back to RSA for audit/event tracking.
7. **Application-Specific Settings**: Load org/tenant configuration per application (CZ = appId 10, OP = appId 6).
8. **Event Type Routing**: Return appropriate RSA event type based on caller context (OP, GE, OP Custom).
9. **Retry Logic**: Configurable retry count and interval for RSA SOAP faults and remote exceptions.

## Key Business Entities
| Entity | Description |
|---|---|
| `AuthenticationService` | Primary interface: all MFA operations |
| `AuthenticationServiceImpl` | Implementation wrapping RSA Adaptive Authentication SOAP WS |
| `MFAConfigurationOptions` | Configuration: challengeQuestionCount, event types (op, ge, opCustom), fiPortfolio |
| `ApplicationSettings` | Per-application org/tenant settings |
| `MFACommonConstants` | All constant keys for device map parameters, session/transaction IDs, delivery methods |
| RSA WS Types | SOAP-generated Java classes: `AnalyzeRequest/Response`, `AuthenticateRequest/Response`, `ChallengeRequest/Response`, `QueryRequest/Response`, `UpdateUserRequest/Response`, `NotifyRequest` |
| TeleSign WS Types | `TelesignSmsAcspChallengeRequest`, `TelesignCallAcspChallengeRequest`, etc. |
| KBA Types | `KBAAuthenticationRequest/Response`, `KBAChallengeRequest/Response` |
| OOB Types | `OOBSMSAuthenticationRequest`, `OOBGenChallengeRequest`, `OOBBioAuthAuthenticationRequest` |
| `SSNInfo` | Contains SSN for KBA identity verification |
| `PersonInfo` | Name + birthday + address for KBA identity verification |

## Business Rules
- Application ID 10 = Client Zone (CZ); Application ID 6 = One Platform (OP). Only these two values are valid; all others throw `MFA_SYSTEM_CONFIGURATION_ERROR`.
- Username submitted to RSA is **SHA-256 hashed** before transmission (`AuthenticationServiceImpl:185-192`) — RSA never receives the plaintext username.
- Delivery method `"0"` = SMS (TeleSign); `"1"` = Phone call (TeleSign).
- On successful OTP validation, if user status is `UNVERIFIED`, an `updateUserOTP` call is made to set status to `VERIFIED`.
- When setting up KBA questions (setUserQA), TelesignSMS is also activated for the user to prevent RSA lockout if question-based auth is blocked.
- Session ID from a challenge response must be propagated into the subsequent authenticate request.
- Retry count and retry interval are configurable (used for SOAP faults and remote exceptions).
- Auto-create user flag is set to `TRUE` in Analyze calls — RSA will auto-create users on first encounter.

## Business Flows
### Login MFA Flow
1. User completes primary authentication.
2. Application calls `analyzeUserScore()` with userId and device fingerprint map.
3. RSA returns action code: ALLOW (no further challenge), CHALLENGE (require MFA), or DENY.
4. If CHALLENGE: application calls `deliverOTP()` or `getUserQA()` depending on configured method.
5. User submits OTP or KBA answer.
6. Application calls `validateOTP()` or `authenicateQusetion()`.
7. On success, `notifyRequest()` posts the authentication level back to RSA.

### First-Time KBA Enrollment Flow
1. Application calls `getQuestions()` to get available KBA questions.
2. User selects and answers questions.
3. Application calls `setUserQA()` to save answers and enroll user in TeleSign SMS.
4. User status set to VERIFIED.

## Compliance Relevance
- **PCI DSS Req 8**: Multi-factor authentication for all non-console administrative access and remote network access. This library implements MFA for consumer-facing and potentially admin portals.
- **FFIEC Authentication Guidance**: RSA Adaptive Authentication with device fingerprinting satisfies layered security requirements.
- **GLBA**: SSN and birthday used in KBA identity verification (via `SSNInfo`, `BirthdayInfo`, `PersonInfo` in RSA WS types) — handling these requires strict access controls.
- Username hashing before RSA transmission is a privacy-protective measure.

## Risks (Business Perspective)
- **RSA Adaptive Authentication is a legacy product**: RSA was acquired by Symphony Technology Group; the RSA Adaptive Authentication SOAP API used here is an older version-specific integration.
- **KBA SSN exposure**: The RSA WS API includes `SSNInfo` type for identity verification challenges; if used, this transmits SSN to RSA via SOAP — requires audit.
- **TeleSign integration**: Phone numbers are transmitted to TeleSign (third-party SMS/call provider); data sharing agreement and CCPA/GDPR must cover this.
- **No KBA bypass protection**: No account lockout visible within this library after repeated failed KBA attempts; depends on RSA configuration.
