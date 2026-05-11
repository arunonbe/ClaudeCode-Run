# Solution Architect View — xplatform-library_LIB

## Technical Architecture
- **Language:** Java 21 (compiler target/source); source encoding `Windows-1252`
- **Build:** Maven, parent POM `prepaid-parent:6.0.13`; artifact `xplatformlibrary:4.2.0`
- **Packaging:** JAR library
- **Architecture style:** Infrastructure utility library — no business logic, no HTTP surface
- **Key subpackages:**
  - `com.cbase.cache` — distributed cache (SwarmCache/JGroups)
  - `com.cbase.pi.encryption` — cryptographic algorithms (symmetric, asymmetric, hashing, signing, key agreement)
  - `com.cbase.pi.encryption.symmetric` — DES, 3DES, RC2, RC4, RC5, DESX, Twofish, Jsafe wrappers
  - `com.cbase.pi.encryption.asymmetric` — RSA cipher, key, key pair classes
  - `com.cbase.pi.encryption.hashes` — MD5, SHA1
  - `com.cbase.pi.strongbox` — SPI for secure key/data stores
  - `com.cbase.pi.configfile` — INI-style config file parser
  - `com.cbase.pi.log` — custom logging framework
  - `com.cbase.pi.sqlaccess` — JDBC wrappers
  - `com.ecount.saxtool` — SAX XML parsing with factory pooling
  - `com.ecount.msmapxml` — XML-to-Java property mapping
  - `ECount.System.RPC` — custom HTTP RPC framework
  - `ECount.System.Config` — `ConfigDB` with RPC-based config lookup

## API Surface
Public API is the full set of public classes in the JAR. Key stable interfaces:
- `ICache` — cache abstraction
- `CacheManager.getCache(String)` — cache factory
- `CryptoCipher`, `CryptoFactory` — cipher abstraction and factory
- `ConfigurationFile` — INI config file reader
- `StoredProcedure`, `JdbcConnection` — JDBC wrappers
- `SaxTool`, `MapFromXML`, `MapToXML` — XML parsing utilities
- `DataRepository`, `DataRepositoryConnection` — StrongBox SPI

## Security Posture

### Authentication
- No authentication within the library itself
- `request-context` module provides `RequestContext` — agent/programme context propagation only

### Cryptography — Critical Findings
| Algorithm / Class | Status | Risk |
|---|---|---|
| `MD5` (`com.cbase.pi.encryption.hashes.MD5`) | Broken (collision) | Must not be used for integrity checks or password hashing |
| `SHA1` (`SHA1`) | Deprecated (collision resistance) | Replace with SHA-256 or higher |
| `DESCipher` / `DESKey` | Broken (56-bit key) | Must not be used for new encryption; legacy data may be encrypted with it |
| `RC4Cipher` / `RC4Key` | Broken (multiple biases) | Must not be used |
| `RC2Cipher` / `RC2Key` | Weak (variable key size, attacks known) | Must not be used |
| `DES3Cipher` / `TripleDESCipher` | Acceptable for legacy, not recommended for new | 112-bit effective security; monitor PCI DSS guidance |
| `RsaCipher` (2048-bit) | Acceptable | Used in xsso_SVC with 2048-bit keys — acceptable |
| `TwofishCipher` | Acceptable for legacy | Not a NIST standard but cryptographically sound |
| `JsafeCipher` | Unknown — commercial SDK | Cannot assess without Jsafe SDK CVE/version information |

### Key Management
- `StrongBox` SPI provides a structured key management abstraction (`AsymmetricKeyStore`, `SymmetricKeyStore`) — positive architectural intent
- Actual key storage implementation is JDBC-based (`JdbcAccess`) — key material in a database is not HSM-grade
- No evidence of Hardware Security Module (HSM) integration — relevant for PCI DSS P2PE and key custodian requirements

### Secrets Management
- No hardcoded secrets detected in reviewed source
- Jsafe SDK configuration (if requiring license keys) is not visible in repo

### Known CVE Exposure
- **ORO** (`oro`) — Apache ORO is dormant since ~2010; no CVE tracking; regex DoS risk if used with untrusted input
- **Jsafe SDK** (`jsafe`) — proprietary library; CVE data not publicly available; FIPS 140-2 certification must be verified with RSA Security
- **SwarmCache / JGroups** — JGroups has had CVEs related to cluster message deserialization; version must be verified
- **commons-text** — Apache Commons Text has had CVEs (e.g., CVE-2022-42889 "Text4Shell"); version must be verified against parent POM

## Technical Debt
| Item | Severity | Detail |
|---|---|---|
| MD5 and SHA1 hash implementations | Critical | Broken algorithms; presence implies active use risk |
| DES, RC4, RC2 cipher implementations | Critical | Broken algorithms; must audit all call sites |
| `Windows-1252` source encoding | High | Non-standard; encoding issues on CI/Linux |
| Jsafe SDK dependency | High | Legacy commercial crypto; no public CVE history; replacement required |
| ORO / regexp libraries | High | Dormant projects; no security updates |
| Custom RPC (`ECount.System.RPC`) | High | Proprietary protocol; no observability, no standard security controls |
| `request-context` from `com.citi.prepaid.module` | Medium | Citi-branded internal module in an Onbe library |
| No JaCoCo / no test coverage enforcement | Medium | Cryptographic code without test coverage is high risk |
| No automated security scanning in CI | Medium | No SAST or dependency scanning visible in this repo |

## Gen-3 Migration Requirements
1. Formally audit and remove or quarantine all use of MD5, SHA1, DES, RC4, RC2 — replace with SHA-256, AES-256
2. Replace Jsafe SDK with a FIPS 140-3 certified JCA provider or HSM integration
3. Replace SwarmCache/JGroups with a cloud-native distributed cache
4. Replace the custom RPC framework with standard REST or gRPC
5. Change source encoding from `Windows-1252` to `UTF-8`
6. Re-evaluate and re-own the `request-context` module dependency
7. Remove ORO and regexp dependencies; use `java.util.regex` throughout
8. Implement proper unit and integration tests for all cryptographic operations

## Code-Level Risks
| Risk | File | Detail |
|---|---|---|
| Broken hash algorithms available | `com.cbase.pi.encryption.hashes.MD5`, `SHA1` | MD5 and SHA1 classes are public and callable by all consumers |
| Broken symmetric ciphers available | `com.cbase.pi.encryption.symmetric.DESCipher`, `RC4Cipher`, `RC2Cipher` | Weak ciphers not gated; any consumer can use them |
| Fixed IV in consumer (xsso_SVC) | `DESedeFactory.java:38` (xsso_SVC) | `"12345678".getBytes()` as IV — this library's TripleDES infrastructure is called with a hardcoded IV |
| JGroups deserialization (SwarmCache) | `com.cbase.cache.SwarmCache` | JGroups multicast messages involve object deserialization — attack surface if network is not isolated |
| `CacheManager` singleton with HashMap | `CacheManager.java:24` | Static `HashMap<String, ICache>` — no size bound; potential memory leak if many unique cache names are created |
