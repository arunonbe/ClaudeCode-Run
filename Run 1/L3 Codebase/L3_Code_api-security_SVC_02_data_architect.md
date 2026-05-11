# api-security_SVC — Data Architect View

## Data Stores

| Store | Type | Name | Purpose |
|---|---|---|---|
| SQL Server | RDBMS | `cbaseapp` | Single authoritative database for all access control data. JNDI name `jdbc/CbaseappDataSource`, context-linked in `api-security-web/src/main/webapp/META-INF/context.xml`. |
| JVM Heap | In-memory cache | `CacheEntityManager` | Read-through cache of the full entity tree, loaded at startup and refreshed on demand via JMX. Implemented with `HashMap` and `ArrayList` protected by `ReentrantReadWriteLock`. |

There is no secondary cache layer (no Redis, no Hazelcast, no EhCache). The in-memory cache is local to each JVM node.

---

## Schema & Tables

All objects reside in `[cbaseapp].[dbo]`. DDL scripts are under `api-security-lib/src/main/sql/`.

### Core Tables

| Table | Primary Key | Key Columns | Notes |
|---|---|---|---|
| `access_entity` | `id` INT IDENTITY | `name` VARCHAR(50) UNIQUE NOT NULL, `comment` VARCHAR(250), `created`, `updated`, `updated_by` | Named access subjects. Two seed rows: `WHITE-LIST`, `REGISTRAR`. |
| `access_entity_domain` | `id` INT IDENTITY | `entity_id` FK, `effective` DATETIME, `expiration` DATETIME, `comment`, `created`, `updated` | One row per domain grant. Properties stored in a child table. |
| `access_entity_domain_property` | (implicit via domain_id + type) | `domain_id` FK, `type` FK to `access_entity_domain_property_type`, `value` VARCHAR | Key-value store for domain properties (API, METHOD, PROGRAM, OTHER, FEATURE). `value` contains Java regex strings. |
| `access_entity_domain_property_type` | `id` INT IDENTITY | `name` (API, METHOD, PROGRAM, OTHER, FEATURE) | Reference/lookup table, seeded in `DDL.sql`. |
| `access_entity_ip` | `id` INT IDENTITY | `entity_id` FK, `ip_address` VARBINARY(16) UNIQUE, `effective`, `expiration`, `comment` | IP addresses stored as raw binary (supports IPv4 and IPv6). |
| `access_entity_ip_range` | `id` INT IDENTITY | `entity_id` FK, `ip_address` VARBINARY(16), `net_mask` VARBINARY(16), UNIQUE(ip_address, net_mask) | CIDR-style ranges. |
| `access_entity_certificate` | `id` INT IDENTITY | `entity_id` FK, `subject_dn` VARCHAR(650), `issuer_dn` VARCHAR(650), `serial_number` VARCHAR(250), `effective`, `expiration` | Certificate identity, keyed on `(issuer_dn, serial_number)` (UNIQUE constraint). |
| `access_entity_host` | PK on (hostname, port) | `label` VARCHAR(250), `hostname` VARCHAR(100), `port` INT, `registration_date` | JMX endpoint registry for distributed cache management. |

### Views

| View | Purpose |
|---|---|
| `access_entity_domain_view` | Flattened join of `access_entity_domain` + `access_entity_domain_property` + `access_entity_domain_property_type`. Used by `JdbcEntityDao` in `SQL_DOMAIN_INQUIRY`. |
| `access_entity_ip_view` | Converts binary IP to dotted-decimal string representation. |
| `access_entity_ip_range_view` | Similar for IP ranges. |
| `access_entity_certificate_view` | Joins entity + certificate columns. |
| `access_entity_ip_program_view` | Joins entity + IP + domain properties for reporting. |
| `access_entity_certificate_program_view` | Joins entity + certificate + domain properties for reporting. |

### Stored Procedures

`access_entity_create`, `access_entity_remove`, `access_entity_grant_access`, `access_entity_revoke_access`, `access_entity_whitelist`, `access_entity_unwhitelist`, `access_entity_domain_add`, `access_entity_domain_remove`, `access_entity_ip_map`, `access_entity_ip_unmap`, `access_entity_ip_range_map`, `access_entity_ip_range_unmap`, `access_entity_host_create`, `access_entity_host_remove`.

Note: The Java JDBC layer (`JdbcEntityDao`, `JdbcAccessEntityIPAddressDao`, etc.) uses **inline SQL**, not the stored procedures, for runtime CRUD operations. The stored procedures appear to be provided as operational/DBA convenience scripts.

---

## Sensitive Data Handling

| Data Element | Location | Sensitivity |
|---|---|---|
| X.509 Subject DN | `access_entity_certificate.subject_dn`, logged in audit events via `LoggingSecurityAudit`, emitted in `AuthenticationCheckFilter` line 73 at INFO level | May contain individual names (e.g., `CN=John Doe`). PII under GDPR/CCPA. |
| X.509 Issuer DN | Same table and log paths | Lower sensitivity but contributes to certificate fingerprint. |
| X.509 Serial Number | Same table and log paths | Combined with Issuer DN forms a unique certificate identifier. |
| IP Addresses | `access_entity_ip`, `access_entity_ip_range`, logged at INFO level (`AuthenticationCheckFilter` line 73, `LoggingSecurityAudit` all methods) | Personal data under GDPR when linked to an individual. |
| Client certificate (PEM-encoded) | Logged at DEBUG level only: `Utility.logDebugCertificate`, `AuthenticationCheckFilter` lines 56-61. | Full certificate data logged in debug mode. Must be disabled in production. |
| Program IDs | `access_entity_domain_property.value` where type=PROGRAM | Business-sensitive; maps to prepaid card programme IDs. |

No PANs, CVV, PINs, or other SAD are stored or processed in this service.

---

## Encryption & Protection

- **Data at rest**: No application-level encryption is applied to any table. Relies entirely on SQL Server transparent data encryption (TDE) at the infrastructure level if enabled. Not verified from source.
- **Data in transit**: X.509 certificates are transported over TLS (the service is configured for HTTPS per `.gitlab-ci.yml` `SHARED_SERVICE_PROTO: https`). The certificate attribute extraction in `AuthenticationCheckFilter` uses the servlet container's `javax.servlet.request.X509Certificate` attribute, implying mutual TLS termination at the container.
- **JMX communication**: `DistributedCacheManager` connects to remote nodes using plain `service:jmx:rmi:///jndi/rmi://...` (line 31). There is no evidence of JMX authentication, SSL, or credentials in the JMX connector setup (`JMXConnectorFactory.connect(url, null)` — `null` environment map). This is an unencrypted, unauthenticated management channel.
- **Database credentials**: Managed externally via JNDI DataSource (`CbaseappDataSource`), not hardcoded in application properties. Connection string details not visible in source.
- **Certificate encoding utility**: `Utility.toString(Certificate)` encodes full PEM certificates using XStream's `Base64Encoder` and logs them. This is only invoked at DEBUG level; however, if debug logging is inadvertently enabled in production, full certificate data would appear in logs.

---

## Data Flow

```
[Client/Caller]
       |  HTTPS + optional mTLS
       v
[AuthenticationCheckFilter]  -- extracts IP, X509 cert --> [EntityCandidate]
       |
       v
[APISecurityValidator.authorize()]
       |
       v
[CacheEntityManager] (in-memory HashMap/List)
       |                                          ^
       | (on startup or reload)                  |
       v                                          |
[DefaultEntityLoader]                     [JMX reload trigger]
       |                                    via CacheJMXLoader
       v
[JdbcEntityDao / JdbcAccessEntityCertificateDao / JdbcAccessEntityIPAddressDao / JdbcAccessEntityIPRangeDao]
       |
       v
[SQL Server: cbaseapp database]
```

Admin write path:
```
[Admin WAR UI] --> [DefaultSecurityAdministrator] --> [JdbcEntityDao / JdbcEntityIdentificationDao]
                                                       --> [SQL Server: cbaseapp]
                   --> [DistributedCacheManager] --(JMX RMI)--> [Remote nodes: CacheJMXLoader.reload()]
```

---

## Data Quality & Retention

- **Effective/expiration dates**: Enforced at both the Java layer (`Domain.isValid()`, `AbstractEntityIdentification.isValid()`) and available in DB columns, but there is no automated purge or archival job for expired records. Expired records accumulate in the database.
- **Duplicate detection**: The cache loader logs warnings for duplicate IP addresses or certificates loaded from the database (`CacheEntityManager.populate`, lines 228-239). Duplicates are silently skipped in the cache; the second entry wins or is ignored.
- **Audit log retention**: Audit events are written to SLF4J/Log4j2 appenders only. There is no database audit table. Retention is entirely dependent on log management infrastructure configuration; no policy is encoded in this service.
- **No soft-delete**: All delete operations are hard deletes (`DELETE` statements in JDBC DAOs, cascade deletes in FK constraints).
- **Timestamp accuracy**: `Utility.datesMatch()` uses a 100ms delta, indicating loose timestamp comparison. This is used in testing only, not in access control decisions.

---

## Compliance Gaps

1. **No application-level encryption on sensitive columns**: `subject_dn`, `issuer_dn`, `serial_number` are stored in plaintext VARCHAR columns. PCI DSS Requirement 3.5 and GDPR Article 32 may require encryption or pseudonymisation depending on data classification.
2. **No audit table**: All audit events flow to application logs only. There is no tamper-evident database audit trail. PCI DSS Req 10.2 requires audit trails for access to data with cardholder data scope; if the access control decisions are considered in-scope, a log-only approach may not satisfy tamper-proof requirements.
3. **JMX channel is unencrypted and unauthenticated**: `DistributedCacheManager.createConnection` passes a `null` environment map. Any party with network access to the JMX port can reload the cache or test access on behalf of any IP/certificate combination. This violates PCI DSS Req 2.2.7 (encrypt non-console administrative access) and Req 7 (least privilege).
4. **DEBUG-level PEM logging risk**: `Utility.toString(Certificate)` emits full certificate PEM strings. If debug logging is enabled (e.g., during incident triage), certificates appear in log files, creating a potential PII/sensitive data exposure.
5. **No data retention/purge policy**: Expired identifications and domains are never cleaned up, leading to unbounded growth and potential exposure of historical access grants in query results.
6. **IP addresses stored as VARBINARY without masking in logs**: Full IP addresses are emitted at INFO level in audit logs and `AuthenticationCheckFilter`. Under GDPR, IP addresses may require pseudonymisation in log pipelines.
