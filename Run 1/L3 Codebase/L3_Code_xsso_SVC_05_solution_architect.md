# Solution Architect View — xsso_SVC

## Technical Architecture
- **Language:** Java 21; Lombok `@Slf4j` throughout
- **Build:** Maven; parent `prepaid-parent:6.0.12`; artifact `xSSO:xsso:3.0.1-SNAPSHOT` WAR
- **Runtime:** Tomcat 10.1.28 / Jakarta EE 10 (Jakarta Servlet 6.0 — `web-app_6_0.xsd`)
- **Architecture style:** Servlet-based service; Spring XML IoC; no REST framework
- **Key classes:**
  - `SSOTokenHandler` — RSA encrypt/decrypt using JKS keystores
  - `SSOTokenManagerImpl` — token lifecycle orchestration, affiliate resolution, PUID search
  - `DESedeFactory` — 3DES key generation utility (presence of hardcoded IV is critical)
  - `Base64Coder` — custom Base64 implementation
  - `TokenManagerServlet` — partner SSO token validation servlet
  - `EncryptOPTokenManagerServlet` — One Platform token encryption
  - `DecryptOPTokenManagerServlet` — One Platform token decryption
  - `DecryptExternalTokenManagerServlet` — external affiliate token decryption with timestamp validation
  - `SSOFilter` — request filter (incomplete implementation — see risks)
  - `RequestContextFilter` — sets agent context on all requests

## API Surface

| Endpoint | Method | Auth | Description |
|---|---|---|---|
| `POST /tokenManagerServlet` | HTTP POST | None | Decrypt partner token → return memberId |
| `POST /encryptOPTokenManagerServlet` | HTTP POST | None | Encrypt identity → return One Platform token |
| `POST /decryptOPTokenManagerServlet` | HTTP POST | None | Decrypt One Platform token → return XML payload |
| `POST /decryptExternalTokenManagerServlet` | HTTP POST | None | Decrypt external token with affiliate key → return XML |
| `GET /hc` | HTTP GET | None | Health check |
| `GET /tokenManagerServlet` | HTTP GET | None | Returns "Hello World!!" — diagnostic only |

**No endpoint has authentication or authorisation controls.**

## Security Posture

### Authentication
- **None.** All endpoints are unauthenticated. Any network-reachable client can call any endpoint.
- `web.xml` has no `<security-constraint>`, no `<login-config>`, no authentication filter on the servlet mappings
- `RequestContextFilter` only sets the agent context; it does not authenticate requests
- `SSOFilter` is defined in code but is **not registered in web.xml** — it has no effect

### Cryptography

#### RSA Token Encryption/Decryption (primary path)
- **Algorithm:** `RSA/ECB/PKCS1PADDING` — RSA with PKCS#1 v1.5 padding
- **Key size:** 2048-bit (from `generateKeys()` in `SSOTokenHandler`)
- **Key storage:** JKS files on filesystem at `${jks.configfile.path}/{affiliateName}_keystore.jks`
- **PKCS#1 v1.5 padding vulnerability:** PKCS#1 v1.5 RSA encryption is vulnerable to the Bleichenbacher padding oracle attack. RSA/OAEP padding (`RSA/ECB/OAEPWithSHA-256AndMGF1Padding`) is the recommended replacement.
- **JKS format:** Legacy; Java 9+ recommends PKCS12. JKS uses a proprietary format with weaker key protection.

#### 3DES / DESedeFactory (secondary / legacy path)
- **Hardcoded IV:** `DESedeFactory.generateInitializationVector()` returns `"12345678".getBytes()` — **a static, hardcoded 8-byte initialization vector**
- A fixed IV for a block cipher in CBC mode eliminates semantic security entirely — each encryption of the same plaintext produces the same ciphertext
- **This is a critical cryptographic flaw.** Even if this factory is only used in tests or deprecated flows, its presence in production source code and the fact it is callable means it may be used

#### Base64Coder
- Custom implementation rather than `java.util.Base64` (available since Java 8)
- Custom Base64 is a code maintenance risk; correctness is not independently verified

### Secrets Management — Critical Finding
`applicationContext-xSSO.properties` (committed to source control):
```
keystore.password=ecount
certificate.password=ecount
```
These passwords protect the RSA private keys for every affiliate. If this default values file is used in any non-development environment, all affiliate private keys are accessible to anyone with the repository access.

The properties file is externalised at runtime via `${CBASE_HOME_URL}/config/xSSO/applicationContext-xSSO.properties` — the committed file appears to be a template/default. However, the committed file itself contains the sensitive placeholder values.

Additionally:
- `mac.address=00:50:DA:20:19:8F` — a specific MAC address hardcoded in the committed properties file
- `ecount.agent=B2CTEST` — agent identifier committed

### Token Replay Vulnerability
- Timestamp in `TokenValue` is validated for format only (`MMddyyyyHHmm`) — no maximum age check
- A captured token remains valid forever — no expiry, no nonce, no revocation
- `DecryptExternalTokenManagerServlet.isValidTimeStamp()` validates format but does not compare against `now()`

### XStream Deserialization
- `TokenManagerServlet` uses XStream to deserialise the decrypted XML into `TokenValue`
- XStream is registered with type aliases only (`login` → `TokenValue`; `puid` → `String`; etc.)
- If XStream is not configured with a type whitelist/allowlist, arbitrary class deserialization is possible (CVE class of vulnerabilities)
- XStream `allowTypesByWildcard()` or explicit type restrictions are not visible in `TokenManagerServlet`

### Allowlisted CVEs (from `.github/containerscan/allowedlist.yaml`)
| CVE | Note |
|---|---|
| CVE-2018-1000632 | dom4j XML injection |
| CVE-2020-10683 | dom4j XXE |
| CVE-2017-9096 | iText PDF (likely transitive) |
| CVE-2024-22262 | Spring Web (URL parsing) |
| CVE-2024-38816 | Spring Web path traversal |
| CVE-2024-47072 | XStream |
| CVE-2024-52316 | Apache Tomcat |
| CVE-2024-50379 | Apache Tomcat |

**Two Tomcat CVEs (CVE-2024-52316, CVE-2024-50379) and one XStream CVE (CVE-2024-47072) are explicitly allowlisted.** These are being accepted as known risks. They should be reviewed with the security team for current exploitability and mitigating controls.

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| Default credentials in properties | Critical | `keystore.password=ecount`, `certificate.password=ecount` in committed file |
| Hardcoded IV in DESedeFactory | Critical | `"12345678".getBytes()` at `DESedeFactory.java:38` |
| PKCS#1 v1.5 RSA padding | High | Bleichenbacher-vulnerable; replace with OAEP |
| No token expiry | High | Replay attacks possible with captured tokens |
| No endpoint authentication | High | All servlets unauthenticated; network isolation is sole control |
| JKS keystore format | High | Deprecated; replace with PKCS12 |
| XStream deserialization without type allowlist | High | Potential arbitrary class instantiation |
| `spring-dbctx-mock` in compile scope | High | Test mock in production WAR |
| `SSOFilter` not registered in web.xml | Medium | Dead code; filter has no effect |
| SNAPSHOT version | Medium | Non-deterministic builds |
| Custom Base64Coder | Medium | Reinvents `java.util.Base64`; custom crypto implementations are high risk |
| Allowlisted Tomcat CVEs | Medium | CVE-2024-52316, CVE-2024-50379 accepted — must confirm mitigating controls |
| Wirecard host IPs in docker-compose | Medium | `qa.nam.wirecard.sys` entries — legacy infrastructure dependency |
| `SHA1PRNG` SecureRandom | Low | `SecureRandom.getInstance("SHA1PRNG")` in `SSOTokenHandler.generateKeys()` — algorithm-specific; use `new SecureRandom()` |

## Gen-3 Migration Requirements
1. Replace custom RSA/JKS SSO with an industry-standard IdP (Azure AD B2C, Keycloak, Okta) using JWT with short expiry and refresh tokens
2. Migrate JKS keystores to PKCS12 format; back with Azure Key Vault or HSM
3. Replace PKCS#1 v1.5 RSA padding with OAEP (`RSA/ECB/OAEPWithSHA-256AndMGF1Padding`)
4. Remove `DESedeFactory` with hardcoded IV entirely
5. Implement token expiry and replay protection (short-lived nonces)
6. Add authentication on all SSO endpoints (mTLS or API key minimum)
7. Replace custom `Base64Coder` with `java.util.Base64`
8. Remove `spring-dbctx-mock` from compile scope
9. Register or remove `SSOFilter`
10. Resolve allowlisted CVEs: Tomcat 10.1.28 → patched version; XStream → updated or replaced
11. Implement audit logging for all token operations (PCI DSS Req 10.2)

## Code-Level Risks
| Risk | File:Line | Detail |
|---|---|---|
| Hardcoded IV | `DESedeFactory.java:38` | `return "12345678".getBytes()` — fixed 3DES IV |
| Default keystore passwords | `applicationContext-xSSO.properties:9-10` | `keystore.password=ecount`, `certificate.password=ecount` |
| PKCS#1 v1.5 RSA | `SSOTokenHandler.java:37` | `algorithmModePadding = "RSA/ECB/PKCS1PADDING"` |
| No auth on any servlet | `web.xml:39-84` | No `<security-constraint>` for any servlet mapping |
| XStream without type allowlist | `TokenManagerServlet.java:29-38` | `new XStream()` with alias-only config; no class allowlist |
| `SSOFilter` not in web.xml | `SSOFilter.java`, `web.xml` | Filter class exists but is never registered |
| Null check logic error | `TokenManagerServlet.java:82` | `if (programId != null \|\| programId.length() > 0)` — OR should be AND; null check bypassed |
| Null check logic error | `TokenManagerServlet.java:109` | `if (requestToken != null \|\| requestToken.length() > 0)` — same OR-instead-of-AND flaw; NullPointerException risk |
| Null check logic error | `DecryptOPTokenManagerServlet.java:64` | `if (requestToken != null \|\| requestToken.length() > 0)` — same pattern |
| Null check logic error | `DecryptExternalTokenManagerServlet.java:96` | `if (requestToken != null \|\| requestToken.length() > 0)` — same pattern |
| `SHA1PRNG` explicit algorithm | `SSOTokenHandler.java:65` | Use `new SecureRandom()` instead of algorithm-specific instance |
| `e.printStackTrace()` in servlet handlers | `SSOTokenManagerImpl.java:71`, multiple | Stack traces to stderr — potential information disclosure |
| Hardcoded MAC address | `applicationContext-xSSO.properties:3` | `mac.address=00:50:DA:20:19:8F` — environment-specific value in source |
