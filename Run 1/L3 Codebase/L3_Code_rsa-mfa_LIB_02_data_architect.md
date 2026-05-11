# Data Architect Analysis: rsa-mfa_LIB

## Data Stores
| Store | Type | Purpose |
|---|---|---|
| RSA Adaptive Authentication Server | Remote SOAP WS (Axis) | All MFA state: user enrollment, session state, risk scoring, authentication results |
| Application configuration / Spring context | In-memory (Spring beans) | `ApplicationSettings`, `MFAConfigurationOptions` — org/tenant configuration |
| Consuming application's database | External | `ApplicationSettings.orgName` etc. may be loaded from DB; `loadApplicationLocalSettings()` implies DB-backed config |

This library does **not** own or directly access a database. All MFA state is persisted in RSA. Configuration is injected by the consuming application.

## Schema / Tables
None owned by this library. All MFA user state is managed within the RSA Adaptive Authentication platform.

The consuming application may store:
- User's MFA enrollment status
- Session/transaction IDs from RSA challenge/authenticate flows
- Authentication level outcomes

## Sensitive Data Handled
| Data Element | Classification | Notes |
|---|---|---|
| User ID (plaintext) | PII | Passed in as `userId` to all operations |
| SHA-256 hashed user ID | Derived | Transmitted to RSA (`AuthenticationServiceImpl:185-192`) |
| Session ID | Security token | From RSA challenge response; must be propagated to authenticate request |
| Transaction ID | Security token | RSA-issued; stored in `mfaDeviceMap` |
| OTP token | Security credential | Passed to `validateOTP()`; transmitted to RSA |
| Phone number (array[3]) | PII | Passed to TeleSign for SMS/call delivery |
| RSA caller credential (password) | Secret | `SecurityHeader.callerCredential` set from `getPassword()` in `setGenericRequest()` |
| RSA caller ID | Service identity | `SecurityHeader.callerId` set from `getRsausername()` |
| Device fingerprint | Device data | `mfaDeviceMap` contains IP address, user agent, HTTP accept, referrer, device print |
| IP address | Network PII | Included in `DeviceRequest` to RSA |
| SSNInfo (KBA type) | PII — Federal ID | Present in RSA WS type `SSNInfo.java` for KBA identity verification |
| BirthdayInfo (KBA type) | PII | Present in RSA WS type `BirthdayInfo.java` for KBA verification |
| PersonInfo (KBA type) | PII (composite) | Name + birthday + address for KBA identity challenges |

## Encryption
### In Transit
- RSA calls use Apache Axis SOAP over HTTPS. The SSL socket factory is `TrustAllSSLSocketFactory`.
- **CRITICAL**: `TrustAllSSLSocketFactory.getContext()` at line 79-81 calls `SSLContext.init(null, null, null)` — this initialises an SSL context with no trust manager, meaning **all SSL certificates are accepted without validation**. This is a certificate trust-all vulnerability — susceptible to man-in-the-middle attacks.
- TeleSign calls are made via the RSA ACSP plugin WS types; transport security depends on RSA's Axis configuration.
- Phone numbers transmitted to TeleSign in cleartext within the SOAP payload.

### At Rest
- RSA caller credentials (password) are stored in Spring bean properties and kept in application memory — not encrypted at rest within this library.
- All MFA state is at rest within RSA infrastructure (outside this library's scope).

### Username Privacy
- User ID is SHA-256 hashed before transmission to RSA (`AuthenticationServiceImpl:185-193`). This is a positive privacy control — RSA does not store plaintext usernames.

## Data Flow
```
Consumer Application
  --> AuthenticationServiceImpl.analyzeUserScore(userId, mfaDeviceMap)
        --> SHA-256 hash userId
        --> Build AnalyzeRequest (SecurityHeader with RSA credentials)
        --> adaptiveAuthentication.analyze() [Apache Axis SOAP client]
              --> HTTPS (TrustAllSSLSocketFactory — NO CERT VALIDATION)
              --> RSA Adaptive Authentication SOAP Server
        <-- AnalyzeResponse (actionCode: ALLOW/CHALLENGE/DENY)

  --> AuthenticationServiceImpl.deliverOTP(userName, ..., phoneNumber, deliveryMethod)
        --> Build ChallengeRequest with TelesignSmsAcspChallengeRequest
        --> adaptiveAuthentication.challenge() [Axis SOAP]
              --> HTTPS (TrustAllSSLSocketFactory)
              --> RSA --> TeleSign SMS/Call
        <-- ChallengeResponse (sessionId for subsequent authenticate)

  --> AuthenticationServiceImpl.validateOTP(deliverOTPSessionId, token, ...)
        --> Build AuthenticateRequest with sessionId + OTP token
        --> adaptiveAuthentication.authenticate() [Axis SOAP]
        <-- AuthenticateResponse (PASS/FAIL)
```

## Data Quality / Retention
- OTP tokens are transient; RSA manages their expiry.
- No data persistence within this library.
- Session IDs must be propagated by the consuming application between challenge and authenticate calls.
- RSA audit logs all authentication events within the RSA platform.

## Compliance Gaps
1. **TrustAllSSLSocketFactory** (`TrustAllSSLSocketFactory.java:79-81`): `SSLContext.init(null, null, null)` — accepts any certificate. All MFA traffic (including OTP tokens and RSA credentials) is susceptible to MITM. This is a CRITICAL PCI DSS Requirement 6 and 4 violation.
2. **RSA credentials in Spring config**: Caller ID and password configured in Spring XML beans; if config files are readable by unauthorised parties, RSA service account is compromised.
3. **KBA SSNInfo**: The `SSNInfo.java` type in the RSA WS API facilitates transmission of SSNs for KBA identity challenges; any use of KBA identity must be audited for SSN data flow compliance (GLBA).
4. **Phone number to TeleSign**: Phone numbers are transmitted to TeleSign (third-party); this constitutes a data sharing arrangement that must be covered by DPA and cardholder consent.
5. **No credential rotation mechanism**: RSA password and caller ID are static in Spring config; no rotation schedule or vault integration evident.
