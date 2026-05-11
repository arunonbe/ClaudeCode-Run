# cambridge-auth-service_LIB — Data Architect View

## Data Stores

This library has **no local data store**. It is a stateless client library that:
- Reads configuration from a flat `.properties` file at runtime.
- Makes a synchronous outbound SOAP call to an external service.
- Returns the received token string to its caller.

There are no databases, message queues, caches, or file-write operations.

## Schema & Tables

No database schema exists. The effective "schema" is the SOAP contract with Cambridge SSO, defined implicitly by the XML namespace:
- `http://schemas.datacontract.org/2004/07/Cambridge.Service.Integration.SSOService.Contract`
- `http://schemas.datacontract.org/2004/07/Cambridge.Service`

**Request payload (XML/SOAP):**
| Field | XML Name | Type | Nullable |
|---|---|---|---|
| digitalSignature | `DigitalSignature` | xsd:string | true (minOccurs=0, nillable=true) |
| returnUrl | `ReturnUrl` | xsd:string | true |
| timestamp | `Timestamp` | xsd:long | false (nillable=false) |
| username | `Username` | xsd:string | true |

**Response payload (XML/SOAP):**
| Field | XML Name | Type | Nullable |
|---|---|---|---|
| token | `Token` | xsd:string | true |
| validationResult | `ValidationResult` | `SimpleValidationResult` | true |
| validationResult.isValid | `IsValid` | xsd:boolean | false |
| validationResult.messages | `Messages` | ArrayOfstring | true |

Sources: `SSOGenerateLoginTokenRequest.java` (lines 98–128), `SSOGenerateLoginTokenResponse.java` (lines 97–113), `SSOValidationResult.java` (lines 117–134).

## Sensitive Data Handling

| Data Element | Classification | Where Held | Risk |
|---|---|---|---|
| `sharedSecretKey` | Secret / Credential | `AuthServiceContext.sharedSecretKey` (String field, heap) | Plaintext in JVM heap; visible in heap dumps and thread-dump logs |
| `userName` | Non-public (system account) | `AuthServiceContext.userName` (String field) | Low PII risk if a service account name, higher if a cardholder username |
| `returnURL` | Internal URL | `AuthServiceContext.returnURL` | Low sensitivity |
| `digitalSignature` | Derived secret | `SSOGenerateLoginTokenRequest.digitalSignature` (String) | Transmitted over HTTPS; should not be logged |
| SSO `token` (response) | Session credential | Returned as `String` to caller | Caller is responsible for protecting this token; library itself does not store it |

Properties file path (from both context XMLs, line 9):
`d:/c-base/config/service/cambridgeAuthService/cambridgeAuthService.properties`
Properties keys: `return.url`, `user.name`, `sharedSec`, `algorithm`, `http.proxyHost`, `http.proxyPort`, `cambridge.auth.address`, `cambridge.auth.name`.

The actual properties file is **not present in this repository** — it is read from the local filesystem at a hard-coded Windows path (`d:/c-base/...`).

## Encryption & Protection

| Mechanism | Present | Notes |
|---|---|---|
| Transport encryption (TLS) | Yes — HTTPS endpoint | Test code uses `https://isbeta.cambridgefxonline.com/Service.svc/ssoBasic`; production address from properties |
| Certificate validation | JVM default | No custom `SSLContext` or trust-store configuration found; relies on JVM cacerts |
| Secret storage encryption | None in code | `sharedSecretKey` read from `.properties` as plaintext `String` |
| Hash algorithm | Configurable | `getHash()` in `CambridgeAuthServiceHelper.java` uses `MessageDigest.getInstance(algorithm)` — no constraint preventing MD5 |
| Data-at-rest encryption | Not applicable | No data written to disk by this library |
| Token encryption/masking | None | Token returned and printed to `System.out` in `App.java` line 24: `System.out.println("Token is "+token)` |

**Critical finding**: `App.java` line 24 prints the SSO token to standard output. If this `main` method is ever exercised in production, live session tokens appear in process stdout / container logs.

## Data Flow

```
Properties file (d:/c-base/...)
        |
        | Spring PropertyPlaceholderConfigurer
        v
AuthServiceContext (in-memory POJO)
        |
        | sharedSecretKey, returnURL, userName, algorithm
        v
CambridgeAuthServiceHelper.getDigitalSignature()
        |
        | concatenated string -> MessageDigest hash
        v
SSOGenerateLoginTokenRequest (in-memory POJO)
        |
        | Apache Axis 1.4 SOAP serialisation (BeanSerializer)
        | SOAP 1.1 over HTTPS
        v
Cambridge SSO Service (https://<host>/Service.svc/ssoBasic)
        |
        | SOAP response (BeanDeserializer)
        v
SSOGenerateLoginTokenResponse (in-memory POJO)
        |
        | .getToken()
        v
Caller (token String — in-memory only)
```

No data is persisted at any step within this library.

## Data Quality & Retention

- **No input validation**: `returnURL`, `userName`, and `sharedSecretKey` are used verbatim from the properties file without sanitisation (`CambridgeAuthServiceImpl.java`, lines 52–57).
- **No null checks**: If `AuthServiceContext` properties are null (e.g., missing properties file entries), `NullPointerException` will propagate as an unchecked exception.
- **No retention**: Library is stateless; tokens are not cached or stored.
- **No token expiry awareness**: The library generates a new token on every call to `getLoginToken()` but has no concept of token TTL or caching for reuse.

## Compliance Gaps

| Gap | Detail | Standard |
|---|---|---|
| Weak hash algorithm permitted | No guard prevents `algorithm=MD5`; test code hard-codes MD5 (`AppTest.java` line 91) | NIST SP 800-131A (MD5 disallowed for authentication); PCI DSS v4.0.1 Req 6.2.4 |
| Secret in plaintext properties | `sharedSec` stored as plaintext in `.properties` file | PCI DSS v4.0.1 Req 8.3.2 (strong cryptography for credentials at rest) |
| Token printed to stdout | `App.java` line 24 — token visible in logs | PCI DSS v4.0.1 Req 3.3 (not displaying SAD/tokens in logs) |
| No audit trail | No logging of token issuance (who requested, when, outcome) | SOC 2 CC7 / NIST CSF DE.CM |
| Transport cert not validated explicitly | Relies on JVM default cacerts; no explicit pinning | NIST CSF PR.DS-2 |
