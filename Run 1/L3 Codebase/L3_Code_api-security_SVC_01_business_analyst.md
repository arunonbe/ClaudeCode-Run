# api-security_SVC — Business Analyst View

## Business Purpose

`api-security_SVC` is a shared, platform-level security library and administration service. Its sole purpose is to answer one question at runtime: "Is this calling system (identified by IP address and/or X.509 certificate) authorised to invoke this API, for this method, against this program/product?" Every other internal API in the prepaid platform delegates its access-control check to this service rather than implementing its own.

The service also provides an administrative web UI and a distributed cache reload facility so that operations teams can manage access grants without redeploying application code.

---

## Business Capabilities

| Capability | Description |
|---|---|
| Entity registration | Create named entities (clients, batch systems, partner organisations) in the access control database |
| Domain access grant | Associate an entity with one or more API/method/program combinations it is allowed to call |
| Domain access revoke | Remove an access grant from an entity |
| IP address mapping | Bind a specific IP address to an entity for identification purposes |
| IP range mapping | Bind a CIDR-style IP range (IP + netmask) to an entity |
| Certificate mapping | Bind an X.509 client certificate (identified by Subject DN, Issuer DN, serial number) to an entity |
| Whitelist management | Mark entire API/method/program combinations as open to all callers without entity identification |
| Cache reload | Force all nodes in the cluster to refresh their in-memory access control data from the database |
| Distributed test | Simulate an authorisation decision against all live nodes via JMX to verify consistency |
| Audit logging | Record every access attempt (requested, identified, granted, denied, whitelisted, expired) to structured log categories |

---

## Business Entities

| Entity | Meaning |
|---|---|
| `Entity` (Java: `com.citi.prepaid.security.api.domain.Entity`) | A named access subject — a partner, internal service, or batch job. Has a name (unique), optional comment, and a list of allowed Domains. Two special entities exist at all times: `WHITE-LIST` and `REGISTRAR` (seeded in `DDL.sql`). |
| `Domain` (Java: `com.citi.prepaid.security.api.domain.access.Domain`) | An access point defined by a set of properties: API name, method name, program ID, and optionally a FEATURE. Property values may be regular expressions to enable wildcard grants. Has optional effective/expiration dates. |
| `EntityIdentification` | The link between an Entity and a caller's observed credentials. Three concrete types: IP address, IP range, X.509 certificate. |
| `EntityCandidate` | The runtime representation of an incoming request — its IP address and, if presented, its client certificate. |
| `RemoteHost` | A registered API node that participates in distributed cache synchronisation. Stored in `access_entity_host`. |

---

## Business Rules & Validations

1. **Identification precedence**: Certificate match is checked before IP match; IP exact match before IP range. (`CacheEntityManager.findEntity`, lines 136-151.)
2. **Whitelist short-circuit**: If the requested Domain is matched by the `WHITE-LIST` entity's domains, the caller is granted access immediately without entity identification. (`APISecurityValidator.authorize`, lines 26-29.)
3. **Effective/expiration enforcement**: Both the `EntityIdentification` and the `Domain` carry effective and expiration dates. Access is denied if the identification record has expired, even if the entity otherwise has access. (`AbstractEntityIdentification.isValid`, referenced in `APISecurityValidator` lines 40-53; `Domain.isValid` checks `effective <= now < expiration`.)
4. **Regex matching**: Domain property values stored in the database are treated as Java regular expressions. A stored value of `.*` matches any requested value. (`Domain.matches`, line 252: `Pattern.matches(value, requestedValue)`.)
5. **Domain uniqueness on entity**: `saveDomainIntoEntity` throws `InvalidObjectException` if the entity already has access to that domain, preventing duplicate grants. (`JdbcEntityDao`, line 92.)
6. **Entity name uniqueness**: `access_entity.name` has a `UNIQUE NONCLUSTERED` constraint (`access_entity.sql`, line 31). The Java layer also checks for existence before creating (`DefaultSecurityAdministrator.createEntity`, line 88).
7. **X-Forwarded-For header respected**: When an Azure Application Gateway is in the path, the filter reads `X-Forwarded-For` to obtain the real client IP rather than the gateway IP. (`AuthenticationCheckFilter`, lines 46-49.) This is a compliance-relevant rule for accurate audit trails.
8. **Registration label required**: When an API node self-registers, it must supply a `startupRegistrationLabel` config property; without a JMX port, self-registration is skipped with a non-fatal warning. (`DistributedCacheRegistrar`, lines 79-83.)

---

## Business Flows

### Runtime Authorisation (per-request)
1. `AuthenticationCheckFilter.doFilter` intercepts inbound HTTP requests.
2. Extracts client IP (honouring `X-Forwarded-For`) and client X.509 certificate, building an `EntityCandidate`.
3. Stores candidate in `CandidateStore` (ThreadLocal).
4. The consuming API calls `APISecurityValidator.authorize(candidate, domain)`.
5. Whitelist check → entity lookup → identification validity check → domain access check → audit log entry.
6. Returns `true` (allow) or `false` (deny).

### Administrative Grant Flow
1. Operator invokes `SecurityAdministrator.grantAccess(AccessRequest)` via the `api-security-administration` WAR.
2. `DefaultSecurityAdministrator` looks up or resolves the named entity.
3. Persists domain and/or IP/certificate identification via JDBC DAOs.
4. Operator initiates cache reload via `reloadEntityCache` or `reloadSpecifiedEntityCache`.
5. `DistributedCacheManager` contacts each registered remote host via JMX RMI and calls `JMXLoader.reload()`.
6. Each node re-queries the database and replaces its in-memory maps under a `ReentrantReadWriteLock` write lock.

### Whitelist Flow
1. Operator calls `SecurityAdministrator.whitelist(WhitelistRequest)`.
2. The `WHITE-LIST` entity has the domain added to it in the database.
3. After cache reload, all runtime nodes grant access to that domain without identification.

---

## Compliance & Regulatory Concerns

- **PCI DSS Req 7 / 8 (Access Control)**: This service is the access control enforcement point for all prepaid APIs. A misconfiguration (overly broad regex, incorrect whitelist, expired certificate not revoked) directly violates least-privilege access requirements.
- **PCI DSS Req 10 (Audit Trails)**: All access decisions are logged to `security.api.audit.*` logger categories via `LoggingSecurityAudit`. The log scanner tool (`api-security-log-scanner`) parses these logs into structured CSV. Log completeness and retention must be verified against PCI DSS 10.7 (12-month retention, 3-month immediately available).
- **Reg E / NACHA**: Because the platform processes ACH and prepaid disbursements, incorrect authorisation grants could expose funds movement APIs to unauthorised parties, creating direct financial crime exposure.
- **GLBA / GDPR**: IP addresses and X.509 subject distinguished names logged in audit events may constitute personal data (particularly if subject DNs contain individual names). Retention and masking controls should be confirmed.
- **OFAC / AML**: No OFAC screening logic is present in this service; it is purely a network-layer access control mechanism. OFAC compliance relies on the calling APIs.

---

## Business Risks

1. **Overly broad regex grants**: A stored domain property value of `.*` for the PROGRAM field grants access to all programs. There is no UI-level warning against this pattern. Risk: inadvertent access to programmes an entity was never intended to reach.
2. **Whitelist persistence**: The `WHITE-LIST` entity bypass is stored in the shared `cbaseapp` database. A SQL injection or insider threat targeting this table would bypass all entity-level controls platform-wide.
3. **Cache staleness**: Between a revocation in the database and the next cache reload across all nodes (which is a manual or triggered operation), a revoked entity continues to pass runtime checks. No time-to-live (TTL) on the in-memory cache is implemented.
4. **Hardcoded `WHITE-LIST` / `REGISTRAR` names**: These sentinel entity names are hardcoded in multiple places (`CacheEntityManager`, `DefaultSecurityAdministrator`). A rename in the database without coordinated code change silently disables whitelist and registration logic.
5. **No rate limiting or brute-force protection**: The authorisation logic makes no attempt to throttle or alert on repeated access denial for the same candidate, which could mask credential enumeration.
6. **Tooling dependency**: The `api-security-certificate-reader` and `api-security-log-scanner` are Windows Forms / console C# tools with no automated testing and a dependency on the deprecated `System.Deployment.Application` API, representing an operational risk if tooling needs to be updated.
