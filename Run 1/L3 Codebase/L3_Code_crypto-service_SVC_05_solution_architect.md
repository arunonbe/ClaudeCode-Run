# Solution Architect View — crypto-service_SVC

## 1. Architecture Summary

`crypto-service_SVC` is a Spring MVC WAR deployed on Tomcat 10.1.28 that exposes a Spring HttpInvoker endpoint for PGP public-key lifecycle management. It wraps three OS-level `pgp` CLI commands (add, remove, list) using `Runtime.getRuntime().exec()`. There is no database, no REST API, no TLS at the application layer, and no authentication. The service is described in its own README as a utility for the Wizard UI only.

## 2. API Design

### Protocol
Spring HttpInvoker (deprecated). The server exports a `HttpInvokerServiceExporter` bean (`HTTPCryptoService-servlet.xml`, line 22). The client consumes it via `HttpInvokerProxyFactoryBean` (`httpCryptoService-client.xml`, line 24). Transport is serialised Java objects over HTTP POST.

**There is no REST, SOAP, or OpenAPI contract.** The service cannot be described in a standard API specification format in its current form.

### Endpoint
```
POST /cryptokeysvc/httpCryptoService/HTTPCryptoService-httpinvoker
```
Content-Type: `application/x-java-serialized-object`

### Service Interface (`ICryptoService.java`)
```java
KeyDetailsBean addClientPublicKey(String keyPath, String programId) throws CryptoServiceException;
KeyDetailsBean removeClientPublicKey(String keyName) throws CryptoServiceException;
List<KeyDetailsBean> getPGPKeyList() throws CryptoServiceException;
```

### Health
```
GET /cryptokeysvc/hc → 200 OK "OK"
```

## 3. Security Analysis (Thorough)

### 3.1 Cryptographic Algorithms

This service does **not implement any cryptographic algorithm itself**. It manages the registration of PGP public keys on a native PGP keyring. The actual cryptographic operations (key generation, encryption, decryption, signing) are performed by the external `pgp` CLI binary.

| Aspect | Finding |
|---|---|
| Algorithm used | Determined entirely by the external `pgp` binary and the keys registered. Not visible in or controlled by this codebase. |
| Key size enforcement | None. The service accepts any key file path provided by the caller without validating algorithm, key size, or expiry. |
| Hash algorithm | Not applicable at this service layer. |
| Java cryptography APIs | **Zero usage**. No `javax.crypto`, `java.security`, `javax.crypto.Cipher`, `MessageDigest`, `KeyStore`, or Bouncy Castle imports anywhere in the codebase. |
| HSM integration | None. |
| Key material in memory | Not present. Key file content is never read by the Java code; only the file path is passed to the subprocess. |

**Acceptable vs. Broken algorithm risk**: Because algorithm choice is entirely delegated to the PGP binary and key material, this service cannot be assessed for algorithm strength independently. The risk is that weak keys (DSA-1024, RSA-1024, deprecated SHA-1 signatures) could be registered without detection. There is no key validation layer.

### 3.2 Key Management Assessment

| Control | Status | Detail |
|---|---|---|
| Key registration authentication | ABSENT | No authentication on the add/remove endpoints |
| Key ownership verification | ABSENT | `keyPath` is a caller-supplied string; any file accessible to the Tomcat process can be registered |
| Key expiry tracking | ABSENT | `createdDate` field exists in `KeyDetailsBean` but is never populated (line 21 declared, never set) |
| Dual control / split knowledge | ABSENT | A single HTTP call by any authorised network-level caller can add or remove any key |
| Key audit log | PARTIAL | Operations are logged at INFO with key name and ID, but log integrity and retention are not controlled by this service |
| Key revocation | Manual only | Remove operation exists but is not tied to any PKI revocation check |
| Key storage security | Delegated | PGP keyring managed by OS/PGP binary; filesystem-level controls not in scope |

### 3.3 Transport Security

- **No TLS at the application layer** (`server.xml` line 105: HTTP/1.1 connector on port 80; HTTPS block lines 127–137 commented out).
- Spring HttpInvoker uses Java object serialisation over HTTP. Without TLS, the serialised payload is transmitted in cleartext.
- **Java serialisation over HTTP is a known attack surface**: deserialisation vulnerabilities (e.g., CVE-2015-4852, CVE-2016-3510) affect Spring HttpInvoker when it processes untrusted input. Mitigations include serialisation filters (JEP 290); none are configured here.
- The QA certificate is imported into the JRE cacerts using the default keystore password `changeit` (`Dockerfile` line 20). This password is public knowledge and should be considered unprotected.

### 3.4 Authentication and Authorisation

- **None at the application layer**. There is no Spring Security configuration, no filter chain, no credential check, and no token validation anywhere in the codebase.
- Access control is entirely network-perimeter-based. If an attacker reaches the internal network segment where this service listens, they have unrestricted access to add or remove PGP keys.
- This is a **critical gap** for a key-management service in a PCI DSS cardholder data environment.

### 3.5 Command Injection

**High-severity finding.**

The following code paths construct OS commands using user-supplied or externally-supplied strings without sanitisation:

#### `ExecuteCommands.execPGPAddKeyCommand()` — line 38
```java
String[] command = { "cmd", "/c", "start/min", addBatFileName, keyPath, pgpTempAddKeyOutPutFile };
Process p = Runtime.getRuntime().exec(command);
```
- `keyPath` originates from the Wizard UI caller (ultimately from the `addClientPublicKey(keyPath, programId)` call). While it is passed as an array element (reducing shell injection risk versus string concatenation), the `.bat` file named by `addBatFileName` could itself process `keyPath` in an unsafe manner.

#### `ExecuteCommands.execPGPRemoveKeyCommand()` — line 118
```java
Process p = Runtime.getRuntime().exec(cmd);
```
- `cmd` is a **single string** built by concatenation in `ExternalCommandsHelper.removeClientPublicKey()` (line 81):
```java
String remove_pgp_key = PGPCommands.REMOVE_PGP_KEY_CMD + keyName + PGPCommands.FORCE_PGP_KEY_CMD;
// = pgp --key-remove "  + keyName + " --force
```
- `keyName` arrives from the Wizard UI caller. If `keyName` contains shell metacharacters (e.g., `" & calc` or `" | del C:\`), the resulting string passed to `Runtime.exec(String)` is split by the JVM using `StringTokenizer`, which **does not protect against shell metacharacter injection** on Windows because the CMD shell interprets metacharacters after tokenisation.
- **This is a command injection risk**. An adversary who can call `removeClientPublicKey` with a crafted key name can execute arbitrary OS commands as the Tomcat service user.

#### `ExecuteCommands.execPGPKeyListCommand()` — line 163
```java
Process p = Runtime.getRuntime().exec(cmd);
```
- `cmd` is the constant string `pgp --key-list "` from `PGPCommands.PGP_KEY_LIST_CMD`. No user input, no injection risk here, but the unclosed double-quote is a correctness bug.

### 3.6 Path Traversal

- `keyPath` parameter: a filesystem path supplied by the caller and passed directly to a subprocess. An attacker supplying `..\..\..\..\windows\system32\config\sam` as `keyPath` could cause the PGP binary to attempt to read arbitrary files. No path validation or canonicalisation is performed.
- `pgpFilesFolderName` is injected from configuration and not user-supplied, so no traversal risk from that path.

### 3.7 Deserialisation

Spring HttpInvoker uses Java built-in serialisation. The `ObjectInputStream` in Spring's `HttpInvokerServiceExporter` will deserialise any object sent to the endpoint. Without a serialisation filter (allowlist), this is a classic gadget-chain attack vector. No `ObjectInputFilter` is configured in this application.

### 3.8 Ignored CVEs — Security Posture

The following CVEs are actively suppressed (`.trivyignore` + `allowedlist.yaml`). Risk acceptance rationale is not documented in the repository:

| CVE | Severity | Component | Risk to This Service |
|---|---|---|---|
| CVE-2024-52316 | Critical | Apache Tomcat 10.x | Authentication bypass — directly relevant to a service with no application-layer auth |
| CVE-2024-50379 | Critical | Apache Tomcat | Race condition potentially leading to RCE — high risk for a key-management service |
| CVE-2024-38819 | High | Spring Web | Path traversal — relevant given unvalidated path parameters |
| CVE-2024-22262 | High | Spring Framework | URL parsing / open redirect — moderate relevance to HttpInvoker URL construction |
| CVE-2024-38816 | High | Spring Web | Path traversal — same as CVE-2024-38819 |
| CVE-2020-10683 | High | dom4j | XXE — moderate relevance given XML Spring config |
| CVE-2018-1000632 | Medium | dom4j | XML injection |
| CVE-2024-56337 | High | Apache Tomcat | Case-sensitive bypass — relevant on case-insensitive filesystems (Windows) |

Suppressing CVE-2024-52316 and CVE-2024-50379 for Tomcat on a key-management service without documented compensating controls is not acceptable under PCI DSS v4.0.1 Req 6.3.3 (all applicable security patches).

### 3.9 Information Disclosure via Logging

- `CryptoServiceImpl.java` constructor (lines 35–36) emits `log.info` and `log.error` as static test calls on every bean instantiation. This is dead debug code in production.
- `KeyManipulationHelper.java` logs full key names and key IDs at INFO level (lines 65, 84, 99, 180).
- `ExternalCommandsHelper.java` logs full filesystem paths at INFO level (lines 55, 116 area).
- If log aggregation feeds SIEM or external systems, key metadata is broadly visible.

## 4. Technical Debt Register

| Item | File / Line | Severity | Description |
|---|---|---|---|
| `NAVIN\` sentinel in output | `ExecuteCommands.java` lines 77, 127, 132, 171, 176 | High | Developer debug marker shipped to production; affects data parsing |
| Unclosed double-quote in key-list command | `PGPCommands.java` line 23 | High | `pgp --key-list "` — command argument not properly closed |
| Command injection via string concat | `ExternalCommandsHelper.java` line 81 | Critical | Remove command built by string concatenation with unsanitised user input |
| No application-layer authentication | All | Critical | Any internal caller can add/remove keys |
| Java deserialisation with no filter | All endpoints | High | Spring HttpInvoker `ObjectInputStream` with no allowlist filter |
| Hard-coded 5-second sleep | `ExecuteCommands.java` line 61 | Medium | Fragile timing assumption |
| Windows CMD in Linux container | `ExecuteCommands.java` line 38 | Critical | `cmd /c` will fail on Alpine Linux |
| All tests commented out | `HTTPCryptoServiceClientTest.java` | High | Zero automated test coverage |
| README version mismatch | `README.md` | Low | States Java 8 / Tomcat 8.5.57; actual is Java 21 / Tomcat 10.1.28 |
| Dead bean fields | `KeyDetailsBean.java` lines 21–24 | Low | `username`, `createdDate`, `modifiedDate`, `content` never populated |
| Test class not extending JUnit | `HTTPCryptoServiceClientTest.java` | Medium | Does not extend `TestCase` or use JUnit annotations; tests will never run |
| `CryptoServiceException` swallows cause | `CryptoServiceException.java` lines 22–26 | Medium | Constructor accepting `(String, Throwable)` ignores the `Throwable`; stack trace is lost |
| Static constructor log calls | `CryptoServiceImpl.java` lines 35–36 | Low | Test `log.info` / `log.error` calls in constructor |
| `groupId` not rebranded | `pom.xml` line 13 | Low | `com.citi.prepaid` origin artifact ID retained |
| Dual CI pipeline | `.gitlab-ci.yml` + `.github/workflows/` | Medium | Two deployment pipelines; operational status of GitLab pipeline unclear |
| `springRemoting` deprecated transport | All | High | Spring HttpInvoker removed from Spring 6; `jakarta-spring-remoting` is a community shim |

## 5. Code Risk Summary

| Risk Category | Count | Highest Severity |
|---|---|---|
| Command injection | 1 confirmed (remove), 1 potential (add via .bat) | Critical |
| Missing authentication / authorisation | Service-wide | Critical |
| Java deserialisation attack surface | Service-wide | High |
| No TLS enforcement | Service-wide | High |
| Active CVE suppression without documented rationale | 8 CVEs | Critical (2x) |
| Missing test coverage | Service-wide | High |
| OS/platform mismatch (Windows on Linux container) | `ExecuteCommands.java` line 38 | Critical |
| Key validation absent | Service-wide | High |

## 6. Recommended Remediation Priorities

1. **Immediate**: Sanitise `keyName` input before constructing the remove command string. Reject inputs containing shell metacharacters or switch to `Runtime.exec(String[])` with properly isolated arguments.
2. **Immediate**: Add application-layer authentication (at minimum, a shared secret or mTLS) to all three key-management endpoints.
3. **Short-term**: Resolve the Windows/Linux platform contradiction — either commit to Windows-only deployment or rewrite `ExecuteCommands` to use platform-independent Bouncy Castle PGP APIs.
4. **Short-term**: Add a Java serialisation filter (`ObjectInputFilter`) to the Spring HttpInvoker endpoint to block gadget-chain attacks.
5. **Short-term**: Upgrade Tomcat to a version patching CVE-2024-52316 and CVE-2024-50379 and remove those entries from `.trivyignore`.
6. **Medium-term**: Replace Spring HttpInvoker with a REST/JSON API protected by TLS and OAuth2/JWT.
7. **Medium-term**: Implement key validation (algorithm, key size, expiry) before registration.
8. **Medium-term**: Write a functional test suite and enable tests in CI pipelines.
9. **Long-term**: Evaluate HSM integration for keyring protection (PCI DSS Req 3.7.7 recommendation for cryptographic key protection devices).
