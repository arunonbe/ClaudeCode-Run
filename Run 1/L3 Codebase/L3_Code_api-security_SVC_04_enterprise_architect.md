# api-security_SVC — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 / Gen-2 boundary.**

Evidence supporting this classification:

- **Spring XML configuration**: All Spring wiring is in classic `applicationContext.xml` and `appCtx-*.xml` files using `<bean>` declarations. No `@Configuration` classes, no Spring Boot auto-configuration.
- **Spring Framework version**: Managed by `prepaid-parent:6.0.12` (Spring 6.x indicates some modernisation effort), but the application wiring style is pre-Boot.
- **Java 21 target**: A recent compiler target (`maven.compiler.source=21`, root `pom.xml`) and a `feature/java-21-upgrade` branch suggest an active upgrade effort — this is a Gen-1 service undergoing partial modernisation.
- **Packaging**: WAR deployed to a manually-managed Tomcat instance (`ServiceTester` Windows service). No Docker image, no Kubernetes manifests, no Spring Boot embedded server.
- **Persistence**: Hand-coded JDBC with `JdbcDaoSupport`, inline SQL strings, `PreparedStatementCreator` anonymous classes. No JPA, no Spring Data.
- **Serialisation**: XStream XML serialisation for admin request/response objects (a Gen-1 pattern; Gen-3 services would use JSON/REST or gRPC).
- **Management**: JMX MBeans over RMI for distributed cache management. A Gen-3 service would use an actuator endpoint, a sidecar, or a service mesh control plane.
- **Dual CI**: Both GitLab (legacy on-premises) and GitHub Actions (Onbe platform) pipelines exist simultaneously, consistent with a service mid-migration.

---

## Business Domain

**Cross-cutting Platform Security Infrastructure.**

`api-security_SVC` does not belong to any single business domain (card issuance, account management, disbursements). It is a horizontal infrastructure service consumed by every domain API. Its closest analogue in modern architectures is a Policy Enforcement Point (PEP) or an API Gateway authorization plugin.

The service was originally built under the Citi Prepaid brand (package namespace `com.citi.prepaid.security.api`) and has been adopted by Onbe as part of the platform inheritance.

---

## Role in Platform

| Role | Description |
|---|---|
| Shared security library | `api-security-lib` JAR is consumed as a compile-time dependency by every platform API that needs to enforce caller access control. APIs include this JAR, configure the Spring beans, and call `APISecurityValidator.authorize()`. |
| Administration service | `api-security-administration` WAR provides the operational UI for managing entities, granting/revoking access, managing the whitelist, and triggering distributed cache reloads. |
| JMX management endpoint | Each node running `api-security-lib` exposes a `prepaid:name=APISecurityManager` MBean that the admin service calls remotely to synchronise cache state across the cluster. |
| Audit log producer | Structured security audit events are written to `security.api.audit.*` logger namespaces, consumed downstream by log management/SIEM. |

The service is a **required dependency** for all platform APIs that enforce caller identity. Its failure or misconfiguration is platform-wide in impact.

---

## Dependencies

### Upstream (what api-security_SVC depends on)

| Dependency | Artifact | Version | Notes |
|---|---|---|---|
| prepaid-parent BOM | `com.parents:prepaid-parent` | `6.0.12` | Governs Spring, mssql-jdbc, log4j2, junit versions |
| spring-dbctx-container | `com.citi.prepaid.spring-dbctx:spring-dbctx-container` | `2.0.1` | Provides `CbaseappDataSource` and Spring transaction manager wiring |
| spring-dbctx-mock | `com.citi.prepaid.spring-dbctx:spring-dbctx-mock` | `2.0.1` | Test DataSource |
| springutils-generic | `com.citi.prepaid.springutils:springutils-generic` | `3.0.2` | Admin UI framework (`com.ecount.service.tester.*`) |
| XStream | `com.thoughtworks.xstream:xstream` | `1.4.20` | XML serialisation; multiple known CVEs suppressed |
| Spring Framework | `spring-context`, `spring-jdbc` | Via parent BOM | Core IoC container + JDBC template |
| mssql-jdbc | `com.microsoft.sqlserver:mssql-jdbc` | Via parent BOM | Provided by Tomcat |
| SQL Server `cbaseapp` | External database | N/A | Authoritative store |

### Downstream (what depends on api-security_SVC)

`api-security-lib` is a shared library; any platform API that needs access control pulls it as a JAR dependency and includes its Spring XML context files. Specific consuming services are not enumerated in this repository's source, but the admin WAR's `applicationContext.xml` references API names `InstantIssue` and `AccountManagement` as example domains, confirming at minimum those two services are consumers.

---

## Integration Patterns

| Pattern | Implementation |
|---|---|
| Library embedding | `api-security-lib` JAR included by consuming API WARs; Spring contexts imported via `<import resource="classpath*:com/citi/prepaid/security/api/appCtx-APISecurityValidator.xml"/>`. |
| Servlet filter | `AuthenticationCheckFilter` (implementing `jakarta.servlet.Filter`) intercepts every request, extracts credentials, and stores an `EntityCandidate` in a ThreadLocal `CandidateStore`. |
| In-process function call | Runtime authorisation check is a direct method call: `securityValidator.authorize(candidate, domain)`. No network hop for the runtime decision path. |
| JMX RMI | `DistributedCacheManager` connects to remote nodes at `service:jmx:rmi:///jndi/rmi://{host}:{port}/jmxrmi` for cache synchronisation. |
| XStream XML RPC | Admin request/response objects are serialised to XStream XML for the `ServiceTester` UI framework. |
| JNDI DataSource | Database connections obtained via JNDI `jdbc/CbaseappDataSource`, decoupling database configuration from application config. |
| Spring Transaction Proxy | All DAO beans are wrapped in `TransactionProxyFactoryBean` with configurable timeouts. |

---

## Strategic Status

| Dimension | Assessment |
|---|---|
| Active maintenance | Yes — Java 21 upgrade branch, GitHub Actions integration, Dependabot enabled. |
| Strategic alignment | Partially aligned. The service is actively used but architecturally dated. A Gen-3 replacement would likely be an OAuth 2.0/OIDC authorization server or an OPA (Open Policy Agent) policy engine, not a JMX-managed in-memory cache. |
| Technical debt level | High (see 05_solution_architect.md for detail). Spring XML-only config, raw JDBC, JMX over unencrypted RMI, XStream with suppressed CVEs, hand-written admin UI. |
| Replacement risk | High. This service is a transitive dependency of the entire platform. Any replacement must be backward compatible at the `SecurityValidator.authorize()` interface level and must preserve the existing Entity/Domain/Identification data model or provide migration tooling. |
| Migration complexity | Very high. Schema migration, replacement of the `AuthenticationCheckFilter` in all consuming APIs, replacement of the JMX-based distributed cache with a modern invalidation mechanism (e.g., Redis pub/sub, database CDC), and re-testing of every access control grant across all environments. |

---

## Migration Blockers

1. **Pervasive library coupling**: `api-security-lib` is a compile-time dependency embedded in every platform API. Migrating the security service requires coordinated changes to all consumer services simultaneously or a compatibility shim layer.
2. **JMX-based cluster management**: The distributed cache reload mechanism is tightly coupled to JMX RMI, which is inherently JVM-specific and cannot be replicated in a polyglot or container-based deployment without a full redesign.
3. **XStream serialisation in admin protocol**: The admin UI (and the C# `CertificateReader` tool) serialises request/response objects as XStream XML. Any replacement of the admin layer must convert to a standard protocol (REST/JSON) while preserving operational tooling.
4. **Citi heritage package namespace**: The entire codebase uses `com.citi.prepaid.security.api.*` packages. A rebranded Gen-3 service would require either namespace migration or maintained aliases, which is a significant refactoring effort across all consumers.
5. **Suppressed XStream CVEs**: CVE-2018-1000632, CVE-2020-10683, and CVE-2024-22259 are explicitly suppressed in `allowedlist.yaml`. CVE-2024-22259 is particularly recent. Any migration must resolve these CVEs, which likely requires replacing XStream entirely.
6. **No contract tests**: `VERIFY_PROVIDER_PACT: false` means there are no automated contract tests between this service and its consumers. A migration has no automated safety net to detect breaking changes.
7. **Windows-only operational tooling**: The `api-security-certificate-reader` (WinForms, ClickOnce) is the primary tool for generating certificate-based access grant payloads. It has no cross-platform equivalent and no automated tests. Replacement requires building new tooling before decommissioning the old.
8. **`WHITE-LIST` and `REGISTRAR` sentinel entity names**: These are hardcoded in Java source, C# source, SQL scripts, and the admin Spring XML. A schema migration that renames these would require coordinated changes across all artefacts.
