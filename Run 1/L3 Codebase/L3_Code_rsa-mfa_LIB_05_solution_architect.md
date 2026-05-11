# Solution Architect Analysis: rsa-mfa_LIB

## Technical Architecture
- **Language**: Java 8 (implied by parent POM `service-parent:8`)
- **SOAP Framework**: Apache Axis 1.x (Axis-generated binding stubs in `rsa-mfa-impl`)
- **Spring**: Version 2.0 (DI only; XML bean wiring in `rsa-mfa-Context.xml`)
- **Logging**: Apache Commons Logging
- **SSL**: Custom `TrustAllSSLSocketFactory` (CRITICAL: bypasses certificate validation)
- **Build**: Maven multi-module; version `2019.4.1`

### Module Structure
```
rsa-mfa-common/
  - Interface: AuthenticationService (all MFA operations)
  - Exception: AuthenticationServiceException (typed error enum)
  - Config: MFAConfigurationOptions, ApplicationSettings, MFACommonConstants, PrintObject
  - RSA WS Types (SOAP-generated, 100+ classes):
      com.rsa.csd.ws.*         — Core RSA Adaptive Auth types (Analyze, Authenticate, Challenge,
                                   Query, UpdateUser, Notify, security headers, device data)
      com.rsa.csd.kba.ws.*    — KBA types (questions, answers, SSNInfo, PersonInfo, BirthdayInfo)
      com.rsa.csd.oobsms.ws.* — OOB SMS types
      com.rsa.csd.oobgen.ws.* — OOB generic types  
      com.rsa.csd.oobbio.ws.* — OOB biometric types
      com.rsa.acsp.trxsign.ws.* — Transaction signing types
  - TeleSign WS Types: com.telesign.plugin.rsaaa.* (SMS, call ACSP types)

rsa-mfa-impl/
  - Implementation: AuthenticationServiceImpl
  - Axis Stubs: AdaptiveAuthenticationSoapBindingStub, AdaptiveAuthenticationLocator,
                AdaptiveAuthenticationInterfaceProxy, AsyncAdaptiveAuthentication variants
  - SSL Override: TrustAllSSLSocketFactory
  - Spring context: rsa-mfa-Context.xml
```

## API Surface
Library-only (no REST/SOAP surface exposed by this library itself):

**AuthenticationService interface** (13 operations):
- `analyzeUserScore(userId, mfaDeviceMap)` → `AnalyzeResponse`
- `getQuestions(userName, groupCount, questionCount, userLanguage, mfaDeviceMap)` → `ChallengeQuestionGroup[]`
- `setUserQA(userName, challengeQuestionList, userLanguage, mfaDeviceMap)`
- `authenicateQusetion(userName, challengeQuestion, userLanguage, mfaDeviceMap)` → `ChallengeQuestionMatchResult`
- `getUserQA(userId, userLanguage, mfaDeviceMap)` → `ChallengeQuestion[]`
- `getUserQAResponse(userId, userLanguage, mfaDeviceMap)` → `ChallengeResponse`
- `loadApplicationLocalSettings(applicationId)`
- `notifyRequest(userId, mfaDeviceMap)`
- `getCallerEventType(caller)` → `String`
- `deliverOTP(userName, userLanguage, mfaDeviceMap, phoneNumber[], deliveryMethod)` → `ChallengeResponse`
- `validateOTP(deliverOTPSessionId, token, deliveryMethod, userName, userLanguage, mfaDeviceMap)` → `AuthenticateResponse`
- `updateUserOTP(userName, userLanguage, mfaDeviceMap[, deliveryMethod])`
- `getPhoneCountryCodeMap()` → `Map<String, String>`

## Security Posture — CRITICAL FINDINGS

### SSL Certificate Validation Disabled — CRITICAL
**File**: `TrustAllSSLSocketFactory.java:79-81`
```java
SSLContext context = SSLContext.getInstance("TLSv1.2");
context.init(null, null, null);
return context;
```
Passing `null` as the `TrustManager` array to `SSLContext.init()` falls back to the default trust manager implementation, but combined with the class's override of `initFactory()`, this effectively disables certificate chain validation. All RSA SOAP calls traverse this socket factory. **Any MITM on the network between the application server and RSA server can intercept OTP tokens and RSA service credentials**.

This must be remediated immediately. The commented-out code (lines 55-76) shows the original intent to load a proper keystore — this should be restored.

### OTP Token Logged at INFO Level — HIGH
**File**: `AuthenticationServiceImpl.java:871`
```java
LOG.info(">>> calling validateOTP, deliverOTPSessionId: " + deliverOTPSessionId + ", token: " + token);
```
OTP tokens written to application logs allow log access to compromise MFA security. Must be masked (e.g., `LOG.info(">>> calling validateOTP, deliverOTPSessionId: {}", deliverOTPSessionId)` — omit token from log).

### Phone Numbers Logged at INFO Level — HIGH
**File**: `AuthenticationServiceImpl.java:760-763`
Phone number array elements logged — PII in log files.

### RSA Credentials in Spring Config (No Vault) — HIGH
`rsausername` and `password` fields are set via Spring bean properties. These credentials grant access to the RSA MFA service for all platform users. Must be migrated to StrongBox or Azure Key Vault.

### Application ID Hard-Coded Switch — MEDIUM
**File**: `AuthenticationServiceImpl.java:282-299`
Only application IDs 6 and 10 are valid; all others throw an exception. This hard-coded switch makes the library non-extensible and creates a change risk for new application onboarding.

### Authentication
- No authentication on the library itself — library is invoked by trusted internal application code.
- RSA service authentication via `SecurityHeader` with `callerId` + `callerCredential` (plaintext password in SOAP header).

### Known CVEs / Vulnerable Dependencies
| Library | Version | Risk |
|---|---|---|
| Apache Axis 1.x | (implied by stubs) | CVE-2012-5784 (SOAP action spoofing), multiple other CVEs; EOL |
| Spring 2.0 | 2.0 | EOL since 2013; no security patches; multiple historical CVEs |
| `xPlatform` | 2017.1.1 | Internal; unknown CVEs |
| TLSv1.2 with null trust | Runtime | MITM via disabled cert validation |

## Technical Debt
1. **TrustAllSSLSocketFactory** (entire file): Must be replaced with proper TrustManager loading from a keystore. **P0 security issue.**
2. **Spring 2.0**: Complete Spring upgrade required before any other modernisation. Spring 2.0 dependency may also pull in Hibernate 2/3 or other EOL libraries transitively.
3. **Apache Axis 1.x SOAP stubs** (100+ generated classes): Entire SOAP layer must be replaced when RSA is decommissioned.
4. **OTP/phone logging** (`AuthenticationServiceImpl.java:760-763, 871`): Immediate log masking required.
5. **Thread.sleep in retry** (`AuthenticationServiceImpl.java:374`): Blocks the calling thread; acceptable for low-volume use but dangerous under load.
6. **`authenicateQusetion` typo** in interface and implementation method name — should be `authenticateQuestion`; indicates no interface review was performed.
7. **WSDL marked "OLD"** (`wsdl/OLD/AdaptiveAuthentication_6_5.xml`): Stub source WSDL stored in an "OLD" directory; unclear if current stubs are from this or a newer WSDL.
8. **No timeout on Axis SOAP calls**: RSA server slowness can block calling threads indefinitely.
9. **Version `2019.4.1`**: 5+ year-old library with no apparent maintenance.

## Gen-3 Migration Requirements
1. **Immediate**: Fix `TrustAllSSLSocketFactory` to validate certificates against a proper trust store.
2. **Immediate**: Mask OTP tokens and phone numbers in log statements.
3. **Immediate**: Move RSA credentials to StrongBox/Azure Key Vault.
4. **Near-term**: Replace RSA Adaptive Authentication with a modern MFA provider (Microsoft Entra MFA, Okta, Auth0).
5. Replace Apache Axis with JAX-WS or REST client if RSA exposes a newer REST API.
6. Upgrade Spring 2.0 to Spring Boot 3.x.
7. Replace Commons Logging with SLF4J + Logback.
8. Add explicit connection timeouts to all SOAP/HTTP calls.
9. Remove hard-coded application ID switch; make extensible via configuration.
10. Fix `authenicateQusetion` method name typo across all consumers.

## Code-Level Risks (File:Line References)
- `TrustAllSSLSocketFactory.java:79-81` — `SSLContext.init(null, null, null)` — ALL RSA calls vulnerable to MITM. **CRITICAL.**
- `AuthenticationServiceImpl.java:871` — `token` logged at INFO. **HIGH.**
- `AuthenticationServiceImpl.java:760-763` — phone number logged at INFO. **HIGH.**
- `AuthenticationServiceImpl.java:101-102` — `rsausername` and `password` fields set from Spring config; no vault integration. **HIGH.**
- `AuthenticationServiceImpl.java:282-299` — hard-coded `switch` on applicationId accepting only 6 or 10. **MEDIUM.**
- `AuthenticationServiceImpl.java:374` — `Thread.sleep(getRetryInterval())` blocks calling thread under load. **MEDIUM.**
- `rsa-mfa-common/src/main/java/com/rsa/csd/kba/ws/SSNInfo.java` — SSN field in KBA WS type; if KBA identity challenge is used, SSN flows to RSA. **HIGH — verify if used.**
