# api-security_SVC — Solution Architect View

## Technical Architecture

The service is a Maven multi-module Java 21 project composed of two deployable artefacts and three supporting tool projects:

```
api-security (parent POM, v3.0.1)
├── api-security-lib (JAR)        — shared runtime security library
│   ├── domain model              — Entity, Domain, EntityCandidate, identification types
│   ├── DAO layer                 — JdbcDaoSupport-based JDBC DAOs
│   ├── cache layer               — CacheEntityManager (ReentrantReadWriteLock, HashMap)
│   ├── filter                    — AuthenticationCheckFilter (jakarta.servlet.Filter)
│   ├── JMX                       — CacheJMXLoader, JMXLoader interface
│   └── audit                     — LoggingSecurityAudit (SLF4J)
│
├── api-security-web (WAR)        — administration UI
│   └── admin layer               — DefaultSecurityAdministrator, DistributedCacheManager
│
├── api-security-certificate-reader (C# WinForms)  — ops certificate enrollment tool
├── api-security-log-scanner (C# console)          — ops log analysis tool
└── api-security-web/src/main/c#  — duplicate C# source embedded in web module
```

### Key Design Patterns
- **In-process PEP (Policy Enforcement Point)**: No network call at authorisation time. `CacheEntityManager` serves requests from heap.
- **Read-copy-update cache**: `CacheEntityManager.populate()` acquires a write lock, replaces all internal collections atomically, then releases. Readers use a read lock, allowing concurrent read access. (`CacheEntityManager` lines 217-251.)
- **ThreadLocal credential propagation**: `CandidateStore` uses a `ThreadLocal<EntityCandidate>` to pass extracted credentials from the servlet filter into the application layer without method signature pollution. (`CandidateStore`, line 12.)
- **Strategy pattern for audit**: `SecurityAudit` interface with `LoggingSecurityAudit` singleton implementation. Swap-able without changing core logic.
- **Composite identification lookup**: Certificate preferred over IP exact match over IP range. No explicit priority configuration — order is hardcoded in `CacheEntityManager.findEntity` lines 136-151.

---

## API Surface

This service exposes **no REST or SOAP endpoints** of its own for runtime use. Its API surface is:

### 1. Java Library Interface (compile-time contract for consuming APIs)
| Interface/Class | Method | Purpose |
|---|---|---|
| `SecurityValidator` | `authorize(EntityCandidate, Domain) : boolean` | Core authorisation check |
| `Utility` | `createProgramDomain(api, method, programId)` etc. | Domain object factory helpers |
| `CacheRegistrar` | `selfRegister()`, `selfUnregister()` | Node lifecycle registration |
| `AuthenticationCheckFilter` | `doFilter(...)` | Servlet filter for credential extraction |
| `CandidateStore` | `getCandiate()` | ThreadLocal candidate retrieval |

### 2. JMX MBean Interface (`prepaid:name=APISecurityManager`)
| Operation | Signature | Notes |
|---|---|---|
| `reload()` | `() : boolean` | Reload entity cache from DB |
| `getLastUpdated()` | `() : Date` | Cache freshness indicator |
| `getRegisterdDomains()` | `() : List<String>` | Domains registered on this node |
| `getEntityNames()` | `() : List<String>` | All entity names in cache |
| `getEntityIdentifications(entityName)` | `(String) : List<String>` | Identifications for entity |
| `getEntityDomains(entityName)` | `(String) : List<String>` | Domains for entity |
| `testAccess(ip, api, method, programId, feature)` | `(5x String) : boolean` | Simulate authorisation |
| `testAccess(candidateMap, domainMap)` | `(2x Map) : boolean` | Simulate with certificate candidate |
| `register()` / `unregister()` | `() : boolean` | Domain registration control |

### 3. Admin Service Operations (XStream XML over HTTP, via ServiceTester framework)
Defined in `applicationContext.xml` as `StaticMethodLoader` beans. Methods on `SecurityAdministrator`:
`reloadEntityCache`, `reloadSpecifiedEntityCache`, `testAccess`, `listRemoteHosts`, `registerRemoteHost`, `unregisterRemoteHost`, `queryEntityIdentification`, `queryRegisteredDomains`, `grantAccess`, `revokeAccess`, `whitelist`, `unwhitelist`, `createEntity`, `removeEntity`.

No OpenAPI/Swagger specification exists.

---

## Security Posture

This section is deliberately thorough given the service's security role.

### Authentication Mechanisms

**mTLS (mutual TLS)**: The primary authentication method. `AuthenticationCheckFilter` extracts `javax.servlet.request.X509Certificate` from the servlet request attribute. The TLS termination is performed at the Tomcat/servlet container level. The filter then uses the first certificate in the chain (`certs[0]`). Certificate matching in the cache is done by Subject DN + Issuer DN + Serial Number (`CertificateIdentification.equals()`).

**IP Address**: Secondary/fallback authentication. The filter reads `X-Forwarded-For` if present (to handle Azure Application Gateway), else `request.getRemoteAddr()`. IP matching is exact (`HashMap<InetAddress, ...>`) or CIDR range (bitwise AND in `AccessEntityIPRange.matches()`).

**Identifier priority**: Certificate match is attempted first; if no certificate match, IP exact match; if no IP match, IP range match (`CacheEntityManager.findEntity` lines 136-151). There is no multi-factor requirement — a match on either certificate OR IP is sufficient for entity identification.

### Token Handling

No JWT, OAuth2, or bearer tokens. The service uses certificate- and IP-based caller identity exclusively. There are no token issuance, validation, or revocation mechanisms.

### Key Management

X.509 certificate private keys are **never stored** in this service. The service stores only the public certificate attributes (Subject DN, Issuer DN, Serial Number) as identifiers. The actual certificate validation (chain trust, revocation) is delegated entirely to the TLS stack / servlet container. The application-level check is purely "is this certificate's identity registered in our database?"

This means:
- A certificate with a valid TLS handshake but an expired or revoked PKI chain could still pass the application-level identity check if it remains in the database and its `effective`/`expiration` dates are still valid.
- No OCSP or CRL check is performed at the application layer.

### Whitelist Bypass

`APISecurityValidator.isWhiteListed()` (line 70-76) short-circuits all entity identification when the requested Domain matches any Domain attached to the `WHITE-LIST` entity. The whitelist is loaded from the database and cached in-memory. This is a privileged bypass and must be managed with strict change control.

### Identification Validity

`AbstractEntityIdentification.isValid()` (used at `APISecurityValidator` line 41) checks that the identification record is within its `effective`-to-`expiration` window. `Domain.isValid()` performs the same check for domain grants. Both use `Utility.isBeforeNow(effective)` and `Utility.isAfterNow(expiration)`, which use `System.currentTimeMillis()`. No NTP synchronisation guarantee is enforced at the application level.

### Audit Trail

`LoggingSecurityAudit` logs all six decision events at INFO level to `security.api.audit.*` logger namespaces. All audit paths are covered: requested, whitelisted, entity identified, access granted, access denied, access denied-expired, entity not identified. However:
- Logs are write-only via SLF4J; there is no tamper-evident storage.
- Log format is human-readable `MessageFormat` strings, not structured JSON. The `api-security-log-scanner` C# tool re-parses these strings, which is fragile.
- No correlation identifier is generated by this service; the `GRID` (Global Request ID) parsed by the log scanner is extracted from log lines that presumably contain it from a surrounding MDC context.

### Administrative Security

The admin WAR (`applicationContext.xml`) defines four roles used by the `ServiceTester` framework: `ReadRole`, `WriteRole`, `CacheUpdateRole`, `CacheAdminUpdateRole`. The enforcement mechanism for these roles is within the `springutils-generic` / `com.ecount.service.tester` framework, which is an internal library not present in this repository. Whether these roles are enforced via LDAP, Active Directory, or another mechanism cannot be determined from this source alone.

The `reloadSpecifiedEntityCache` method (which takes a user-provided list of remote hosts) is assigned `CacheAdminUpdateRole`, while the standard `reloadEntityCache` (which uses the database-registered host list) uses `CacheUpdateRole`. This separation is appropriate.

### JMX Security Gaps (Critical)

`DistributedCacheManager.createConnection()` line 49: `JMXConnectorFactory.connect(url, null)` — the second argument is the environment map; `null` means no credentials, no SSL. The JMX channel is unauthenticated and unencrypted. Any network-adjacent attacker can:
- Reload the cache (denying service by causing a database round-trip under load).
- Call `testAccess()` to enumerate which IPs/certificates have access to which programs.
- Call `register()`/`unregister()` to alter domain registrations.

This violates PCI DSS Requirement 2.2.7 (all non-console administrative access must be encrypted).

---

## Technical Debt

| Item | Severity | Location | Detail |
|---|---|---|---|
| Spring XML-only wiring | Medium | All `appCtx-*.xml` files | Classic `<bean>` config; no `@Configuration`, no Boot auto-configure. Increases verbosity and maintenance cost. |
| Raw JDBC with anonymous inner classes | Medium | All `Jdbc*Dao.java` files | Pre-lambda `PreparedStatementCreator` anonymous classes. Verbose, no connection pool visibility. |
| Raw `RowMapper` without generics | Low-Medium | `JdbcEntityDao`, `JdbcHostDao` | `@SuppressWarnings("unchecked")` present; `RowMapper` used without type parameter. |
| DAO timeout concatenation bug | High | `appCtx-APISecurityDAO.xml` line 24 | `timeout_${api.security.entity.identification.dao.timeout}1000` literally appends `1000`, making the timeout ~14 days. |
| JMX unauthenticated | Critical | `DistributedCacheManager.createConnection()` | `null` environment map on JMX connect; no credentials, no SSL. |
| XStream CVEs suppressed | High | `allowedlist.yaml` | CVE-2024-22259 (2024) and two older CVEs accepted. XStream deserialization vulnerabilities are a high risk in admin APIs. |
| Hardcoded Windows path | Medium | `config.properties` line 5 | `CBASE_HOME_URL=file:///d:/c-base` — development artefact. |
| Test skip in all CI | High | All CI pipeline files | `-Dmaven.test.skip=true` in every pipeline. Security regressions will not be caught before deployment. |
| `javax.management` import | Low | `DistributedCacheManager.java` | Uses `javax.management.*` (Java EE namespace) instead of Jakarta namespace. Inconsistent with `jakarta.servlet` used in filter. |
| `Utility.SimpleDateFormat` shared state | Low | `Utility.java` lines 21, 46, 52 | `SimpleDateFormat` is not thread-safe; accesses are `synchronized(formatter)` which is correct but serialises all date parsing/formatting. |
| C# duplicate source | Low | `api-security-web/src/main/c#/` | C# source (`Program.cs`, `SecurityEvent.cs`, `AssemblyInfo.cs`) embedded inside the Java WAR module's source tree. No csproj, not compiled as part of the Maven build. Dead code or misplaced files. |
| `getIssuerDN()` from deprecated `X509Certificate.getIssuerDN()` | Low-Medium | `CertificateIdentification.java` line 24 | `getSubjectDN()` and `getIssuerDN()` methods on `X509Certificate` are deprecated since Java 9 (replaced by `getSubjectX500Principal()`). |
| Typo: "NON-FAITAL" | Low | `DistributedCacheRegistrar.java` lines 47, 69 | Misspelled "FATAL" in warning messages. Minor but indicates code quality. |
| Typo in DAO method name | Low | `CandidateStore.java` | `setCandiate` / `getCandiate` — misspelling of "Candidate". Public API methods on a singleton. |
| `getRegisterdDomains` misspelling | Low | `EntityModel`, `CacheEntityManager`, `JMXLoader` | "Registered" misspelled as "Registerd" — appears in public interface and JMX method names. |

---

## Gen-3 Migration Requirements

To migrate `api-security_SVC` to a Gen-3 pattern (Spring Boot, containerised, REST/JSON, OAuth2), the following must be addressed:

### Must Have
1. **Replace JMX RMI cache management** with a modern invalidation mechanism. Options: Redis pub/sub cache invalidation, database CDC (Change Data Capture), or periodic TTL-based reload with configurable interval. Eliminate the need for `access_entity_host` table and distributed JMX.
2. **Replace XStream serialisation** with Jackson JSON for all admin request/response objects. Retire the C# `CertificateReader` tool or rewrite as a REST client.
3. **Spring Boot migration**: Replace `appCtx-*.xml` with `@Configuration` classes, Spring Boot auto-configuration, and `application.yml`. Replace WAR packaging with Spring Boot embedded Tomcat JAR.
4. **Secure JMX or eliminate it**: If JMX is retained for observability, enable `com.sun.management.jmxremote.authenticate=true` and `com.sun.management.jmxremote.ssl=true`. In a Gen-3 container environment, JMX should be replaced with a Spring Boot Actuator endpoint protected by mTLS or OAuth2.
5. **Replace raw JDBC with Spring Data JDBC or JPA**: Eliminate `JdbcDaoSupport` and manual `PreparedStatementCreator` anonymous classes.
6. **Fix the DAO timeout bug**: Correct `appCtx-APISecurityDAO.xml` line 24 before or during migration.
7. **Enable CI tests**: Remove `-Dmaven.test.skip` from all pipelines; add a test gate.
8. **Resolve XStream CVEs**: Eliminate `xstream` dependency. CVE-2024-22259 has no suppression justification in source.

### Should Have
9. **Replace deprecated `getIssuerDN()`/`getSubjectDN()`** with `getIssuerX500Principal().getName()` / `getSubjectX500Principal().getName()`.
10. **Structured JSON logging** for audit events (replace `MessageFormat` strings in `LoggingSecurityAudit`).
11. **Health and readiness endpoints**: `/actuator/health` exposing cache last-updated and database connectivity.
12. **Metrics**: Micrometer counters for authorisation grant/deny rates and cache load duration.
13. **Move C# tooling** out of the Java Maven module tree or formalise as separate .NET projects with their own CI.
14. **Rename deprecated method spellings** (`getCandiate` → `getCandidate`, `getRegisterdDomains` → `getRegisteredDomains`) — this is a breaking API change requiring consumer updates.

### Could Have
15. **Cache TTL**: Configurable maximum age for the in-memory cache with automatic background refresh, eliminating the need for manual reload operations.
16. **OAuth2/OIDC integration**: Long-term, consider replacing the IP/certificate identity model with OAuth2 client credentials, aligning with industry-standard API security patterns.

---

## Code-Level Risks

### Risk 1 — Silent access grant after revocation (High)
**Location**: `CacheEntityManager`, `DistributedCacheManager`
Cache is only reloaded when an operator explicitly calls `reloadEntityCache` or a JMX reload is triggered. Between a database revocation and the next reload, a revoked entity continues to pass `authorize()`. There is no TTL, no DB polling, and no event-driven invalidation. In a distributed cluster, each node's cache can be at a different staleness level.

### Risk 2 — DAO timeout disabled by concatenation bug (High)
**Location**: `api-security-lib/src/main/resources/com/citi/prepaid/security/api/appCtx-APISecurityDAO.xml`, line 24
```xml
<prop key="*">timeout_${api.security.entity.identification.dao.timeout}1000</prop>
```
This resolves to `timeout_1201000` (with default value `120`), not `timeout_120`. The Spring `TransactionProxyFactoryBean` timeout attribute format is `timeout_N` where N is seconds. This timeout value is so large it is effectively infinite, meaning a slow or hanging query to the `entityIdentificationDao` will block a thread indefinitely. Under load, this can exhaust the thread pool and cause a platform-wide outage.

### Risk 3 — X-Forwarded-For spoofing (Medium-High)
**Location**: `AuthenticationCheckFilter.java`, lines 46-49
```java
String clientIPAddressString = (null != request.getHeader("X-Forwarded-For") 
    ? request.getHeader("X-Forwarded-For") 
    : request.getRemoteAddr());
```
If the Azure Application Gateway is removed from the path (e.g., direct access, internal bypass), any caller can supply an arbitrary `X-Forwarded-For` header and impersonate an IP address that has been granted access. There is no validation that `X-Forwarded-For` was set by a trusted proxy. This is an IP spoofing vector.

### Risk 4 — JMX unauthenticated cache/test endpoint (Critical)
**Location**: `DistributedCacheManager.java`, line 49
```java
JMXConnector jmxc = JMXConnectorFactory.connect(url, null);
```
`null` environment = no credentials, no SSL. `testAccess()` over JMX allows any network-adjacent party to enumerate which IP addresses and certificate DNs have access to any program/API combination, effectively leaking the complete access control policy.

### Risk 5 — Concurrent modification risk in domain registration (Low-Medium)
**Location**: `CacheEntityManager.register()`, lines 76-98
The method iterates `registredDomains` (a non-thread-safe `ArrayList`) without a lock before deciding to add. The populate callback acquires a write lock on the separate `entityList`/`ipEntityMap`/`certificateEntityMap` structures but `registredDomains` uses a separate unguarded list. Concurrent calls to `register()` from multiple threads (e.g., multiple APIs starting simultaneously) could result in duplicate domain registrations.

### Risk 6 — XStream deserialisation in admin API (High)
**Location**: `api-security-web/src/main/webapp/WEB-INF/applicationContext.xml` (XStream marshaller bean)
XStream is used to deserialise admin request objects from user-provided XML. Three CVEs are suppressed: CVE-2018-1000632 (DoS), CVE-2020-10683 (XML injection), CVE-2024-22259 (security restriction bypass). An admin user with `WriteRole` could potentially exploit these to cause DoS or bypass security restrictions within the JVM. The `XStream.mode=1001` (NO_REFERENCES) mitigates some but not all attack vectors.

### Risk 7 — `reloadSpecifiedEntityCache` null operation check (Medium)
**Location**: `DefaultSecurityAdministrator.reloadSpecifiedEntityCache()`, lines 566-567
```java
if (request.getOperation() == null)
if (ReloadOperation.RELOAD.equals(request.getOperation()) || ...)
```
The first `if` statement has no body (no braces). The second `if` immediately follows. If `operation` is `null`, the second condition evaluates `ReloadOperation.RELOAD.equals(null)` which returns `false` — no exception, but the `null` branch silently falls through to `refreshLocalCache`. This is a logic bug; the intent was likely to throw an exception or return an error on `null` operation.

### Risk 8 — Duplicate C# source in Java module (Low)
**Location**: `api-security-web/src/main/c#/Program.cs`, `SecurityEvent.cs`, `AssemblyInfo.cs`
C# source files are present inside the Java WAR Maven module tree. They are not referenced by any csproj or Maven plugin. They will not be compiled, tested, or scanned by CodeQL (which is Java-only in the workflow). Any vulnerabilities in this C# code are invisible to the CI pipeline.
