# cambridge-auth-service_LIB — Business Analyst View

## Business Purpose

This library provides a Java-based Single Sign-On (SSO) authentication client for the Cambridge FX Online platform (`cambridgefxonline.com`). Its sole purpose is to obtain a time-limited login token from the Cambridge SSO service on behalf of a cardholder or system user, so that downstream consumers (prepaid card portals, etc.) can redirect users into the Cambridge-hosted portal without requiring them to re-enter credentials. The library is packaged as a JAR and consumed by other services within the Citi Prepaid / Onbe platform.

## Business Capabilities

| Capability | Evidence |
|---|---|
| Federated SSO token generation | `ICambridgeAuthService.getLoginToken()` — `CambridgeAuthServiceImpl.java` |
| Digital-signature construction for anti-replay | `CambridgeAuthServiceHelper.getDigitalSignature()` — `CambridgeAuthServiceHelper.java` |
| SOAP/WSDL call to Cambridge service endpoint | `BasicHttpBinding_ISSOServiceStub.generateLoginToken()` — `BasicHttpBinding_ISSOServiceStub.java` |
| Spring-managed configuration injection | `appContext-CambridgeAuthService.xml` and `AuthServiceContext.java` |

The library exposes exactly **one business operation**: `getLoginToken()`.

## Business Entities

| Entity | Class / Location | Fields |
|---|---|---|
| SSO Login Token Request | `SSOGenerateLoginTokenRequest.java` | `digitalSignature`, `returnUrl`, `timestamp`, `username` |
| SSO Login Token Response | `SSOGenerateLoginTokenResponse.java` | `token`, `validationResult` |
| Validation Result | `SSOValidationResult.java` | `isValid` (Boolean), `messages` (String[]) |
| Auth Service Configuration | `AuthServiceContext.java` | `returnURL`, `userName`, `sharedSecretKey`, `algorithm`, `proxyHost`, `proxyPort` |

## Business Rules & Validations

1. **Shared-secret signature**: The digital signature is computed as a hash of the concatenation `sharedSecretKey|returnurl|<returnURL>|username|<userName>|timestamp|<millisecondEpoch>`. This is defined in `CambridgeAuthServiceHelper.getDigitalSignature()` (lines 26–32).
2. **Algorithm is externally configurable**: The hash algorithm is read from `AuthServiceContext.algorithm` and passed to `java.security.MessageDigest`; the test class (`AppTest.java`, line 91) hard-codes `"MD5"`, confirming the business default.
3. **Timestamp freshness**: A live `System.currentTimeMillis()` is used at call time (`CambridgeAuthServiceImpl.java`, line 55), making each request unique and time-bound — an anti-replay safeguard.
4. **Token validity check**: `SSOValidationResult.isValid` and `messages[]` are returned with every response but the production implementation (`CambridgeAuthServiceImpl.java`, line 71) only extracts the `token` string and does not check `isValid` before returning — a business logic gap.
5. **Proxy requirement**: HTTP proxy host/port must be set in JVM system properties before calling the external service (`CambridgeAuthServiceImpl.java`, lines 49–50), indicating the library is expected to run inside a corporate network.

## Business Flows

```
Caller
  |
  v
ICambridgeAuthService.getLoginToken()                  [CambridgeAuthServiceImpl]
  |
  +-- set JVM proxy properties
  |
  +-- read config from AuthServiceContext
  |     (returnURL, userName, sharedSecretKey, algorithm)
  |
  +-- CambridgeAuthServiceHelper.getDigitalSignature()
  |     concatenate: sharedSecret|returnurl|URL|username|user|timestamp|epoch
  |     hash with MessageDigest(algorithm)
  |
  +-- build SSOGenerateLoginTokenRequest
  |     (digitalSignature, timestamp, returnUrl, username)
  |
  +-- ServiceLocator.getISSOService()
  |     -> BasicHttpBinding_ISSOServiceStub (Apache Axis SOAP stub)
  |
  +-- ISSOService.generateLoginToken(request)
  |     SOAP 1.1 call over HTTP to:
  |     https://isbeta.cambridgefxonline.com/Service.svc/ssoBasic
  |     SOAPAction: http://tempuri.org/ISSOService/GenerateLoginToken
  |
  +-- return SSOGenerateLoginTokenResponse.token  -->  Caller
```

## Compliance & Regulatory Concerns

| Concern | Detail |
|---|---|
| **Shared secret in configuration** | `sharedSecretKey` is injected from a properties file at `d:/c-base/config/service/cambridgeAuthService/cambridgeAuthService.properties` (appContext XML, line 9). If this file is not encrypted at rest or access-controlled, it is a credential-exposure risk. |
| **MD5 in production test** | `AppTest.java` line 91 uses `"MD5"`. MD5 is cryptographically broken; if this reflects the production algorithm value, the digital signature does not provide collision resistance and could be forged. This is directly relevant to authentication integrity. |
| **No TLS certificate validation visible** | The SOAP stub sends requests over HTTPS but there is no evidence of certificate pinning or explicit trust-store configuration. Axis 1.4 uses the JVM default trust store. |
| **Credentials visible at runtime** | `sharedSecretKey` and `userName` are stored in plain `String` fields in `AuthServiceContext` with standard getters; there is no `char[]` or `SecretKey` usage, meaning secrets are held in the JVM heap and potentially visible in heap dumps. |
| **Regex / input validation absent** | No validation is applied to `returnURL`, `userName`, or the inbound token before use. |
| **Package attribution** | Source is in `com.citi.prepaid` — this is an artifact from Citi Prepaid heritage; the actual operator is Onbe. No PII/PCI card data is processed by this library directly. |

## Business Risks

1. **Algorithm downgrade**: If `algorithm` property is set to `MD5`, token signatures can be forged, enabling unauthorised SSO login tokens.
2. **No response validation in production code**: `CambridgeAuthServiceImpl` line 71 returns the raw token string without checking `isValid`. A failed or spoofed response with a non-null `token` would be silently accepted.
3. **Hard-coded beta endpoint in test code**: `AppTest.java` line 64 targets `https://isbeta.cambridgefxonline.com/Service.svc/ssoBasic`. If test code is ever executed against a production context, it hits the beta environment.
4. **Proxy credentials not authenticated**: Proxy host/port are set but no proxy authentication is handled, which may fail in hardened network environments.
5. **Dependency on external SaaS**: The library has a single point of failure — the Cambridge FX Online SSO SOAP service. No retry, circuit-breaker, or fallback logic is present.
