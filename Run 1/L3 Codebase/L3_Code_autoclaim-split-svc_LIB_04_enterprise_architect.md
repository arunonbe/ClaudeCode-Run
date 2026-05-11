# autoclaim-split-svc_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1 (legacy monolith-era shared library)**

Evidence:
- Root POM parent is `com.citi.prepaid.service:service-parent:8` — this parent POM lineage originates from the Citi Prepaid / eCount era, which predates the Northlane and Onbe platform re-platforming.
- Spring Framework 2.5.6 (released 2008) and Java 1.6 target (released 2006). No Spring Boot, no reactive stack, no cloud-native patterns.
- Configuration via local Windows file path (`D:/c-base/config/...`) indicates on-premise deployment on a named Windows host, characteristic of Gen-1 infrastructure.
- The `Director` service pattern (`DirectorConfiguredDBCPdatasourceCreator`) and `ECore*` SPI classes are distinctive eCount Core Gen-1 platform primitives.
- Artifact group ID `com.ecount.service` and internal package names `com.citi.prepaid.core` confirm dual Citi/eCount heritage.
- SCM path `gitlab.com/northlane/development/application-development/libraries/autoclaimsplitsvc` confirms it has been retained under Northlane (Gen-2 transition) but not yet re-architected.

## Business Domain

**Disbursements / Payments — Autoclaim / Fund Split sub-domain**

This library sits within the **disbursement lifecycle** domain: a cardholder or program participant has received an eCheck (digital payment coupon) and is claiming the funds. The autoclaim split capability determines how those funds are distributed across the recipient's registered disbursement instruments (ACH/DDA, prepaid eCard, IEFT, etc.).

Within Onbe's current taxonomy this maps to:
- **B2C Disbursements** — prepaid card loads, ACH push, push-to-card
- **Multi-rail orchestration** — the splitting logic itself is a rail-routing decision engine
- **Cardholder data environment (CDE) adjacent** — handles monetary amounts and account references

## Role in Platform

This is a **shared library** (JAR), not a standalone microservice. It is expected to be:
1. Imported by a host service (likely an autoclaim processing service or a cardholder portal backend) that calls `AutoclaimSplit.performSplit(PaymentVO)`.
2. Deployed as part of that host service's WAR/EAR on an application server (consistent with Spring 2.5 era deployment).

The library encapsulates the fund-split algorithm and the payment DB query, exposing a single clean interface (`AutoclaimSplit`) from `autoclaimsplit-common`. This separation into `-common` (contract JAR) and `-svc` (implementation JAR) is a deliberate API/SPI pattern allowing the host to depend only on the contract.

## Dependencies

### Upstream (this library depends on)

| Dependency | Version | Type | Scope |
|---|---|---|---|
| `com.citi.prepaid.service:service-parent` | 8 | Parent POM | Build |
| `com.ecount.service.Core2:ecount-system` | 2.0.0 | Platform core | Compile |
| `com.ecount.service.Core2.director:director-client` | 1.0.11 | Platform infra | Compile |
| `com.ecount:xPlatform` | 2013.1.2 | Platform SDK | Compile |
| `com.cbase.business.*` | (transitive) | Core business SPI | Compile (via ecount-system) |
| `com.citi.prepaid.business.ieft.*` | (transitive) | IEFT module | Compile |
| `com.citi.prepaid.context.*` | (transitive) | Request context | Compile |
| `org.springframework:spring` | 2.5.6 | Framework | Compile |
| `net.sourceforge.jtds:jtds` | 1.2.2 | JDBC driver | Compile |
| `commons-dbcp:commons-dbcp` | 1.2.2 | Connection pool | Compile |
| `commons-pool:commons-pool` | 1.4 | Pool support | Compile |
| `commons-logging:commons-logging` | 1.1.1 | Logging | Compile |
| `log4j:log4j` | 1.2.15 | Logging impl | Compile |
| `junit:junit` | 4.7 | Testing | Test |

### Downstream (who depends on this library)

Not determinable from this repository alone. The host service(s) that import `autoclaimsplit-svc` are not identified here. Discovery requires a dependency graph search across the broader platform.

### External System Dependencies (runtime)

| System | Interface | Notes |
|---|---|---|
| SQL Server (CbaseApp DB) | JDBC stored procedure | `get_payment_detail_echeck_member_program` |
| Director service | TCP / proprietary | DB connection pool configuration |
| eCount Core (DeviceManager, MemberManager) | In-process SPI | `ECoreDevice`, `ECoreMember` via Spring beans |
| eCount Profile Service | XML-RPC (commented out) | `AllotmentConfigLoaderImpl` is fully stubbed |

## Integration Patterns

1. **Library / in-process call** — Primary pattern. The caller (host service) injects `AutoclaimSplit` as a Spring bean and calls `performSplit()` synchronously.
2. **Spring XML IoC (Spring 2.5 bean wiring)** — No annotations; all wiring through `appCtx-AutoclaimSplit.xml`. Consumers must merge this context file into their application context.
3. **Spring JDBC / StoredProcedure** — DB access via `org.springframework.jdbc.object.StoredProcedure` pattern.
4. **Director-managed DBCP** — Connection pool lifecycle managed by an external Director service; datasource is obtained via factory method (`DirectorConfiguredDBCPdatasourceCreator.getNewDatasource`).
5. **SPI / Adapter** — `ECoreDevice` and `ECoreTransfer` are eCount Core SPI adapters wired to `DeviceManagerImpl` and `TransferManagerImpl`.
6. **No messaging/eventing** — No JMS, Kafka, or async patterns. Prior commented-out dependencies include `springutils-jms` and `xstream`, suggesting event-driven patterns were considered but not implemented in this module.

## Strategic Status

**Status: Legacy — Candidate for Gen-3 Migration or Decommission**

- The library is in active maintenance (GitLab CI, GitHub CodeQL, Dependabot) but has no active test suite and has significant stubbed/commented-out implementation.
- The `AllotmentConfigLoaderImpl` (program profile loading) and fee retrieval (`FeeStructureProfileClass`) are both commented out, indicating the library may be partially functional or dependent on another library providing the wired dependencies at runtime.
- The eCount Core dependencies (`ecount-system 2.0.0`, `director-client 1.0.11`, `xPlatform 2013.1.2`) are vintage platform artifacts unlikely to have public CVE fix support.
- Spring 2.5.6 and Java 1.6 cannot be brought into compliance with current PCI DSS TLS 1.2 requirements without a framework upgrade.
- The business capability (fund-split routing on disbursement claims) is a core Onbe competency that must be preserved; the implementation needs replacement, not the capability.

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| Java 1.6 target bytecode | Critical | Incompatible with modern JVM TLS, security managers, and module system |
| Spring 2.5.6 | Critical | EOL; no Spring Boot path without full rewrite of XML context and bean wiring |
| eCount Core SPI dependencies (`cbase.business.*`, `IEFTConfigurationLoader`, `ECoreDevice`) | Critical | Proprietary Gen-1 platform primitives; must be replaced with Gen-3 equivalents or REST/gRPC calls |
| Director service for DB connections | High | Proprietary connection pool factory; must be replaced with standard JDBC pool (HikariCP, etc.) |
| jTDS JDBC driver | High | Abandoned; no support for SQL Server 2019+ features or modern TLS. Should move to Microsoft JDBC 12.x |
| Hardcoded Windows config path | High | `file:///d:/c-base/...` prevents containerisation |
| Log4j 1.x | High | CVE-2019-17571; upgrade to Log4j 2.x or SLF4J + Logback |
| AllotmentConfigLoaderImpl entirely stubbed | Medium | Program profile loading is non-functional; migration must restore or replace this capability |
| Fee retrieval commented out | Medium | Allotment fee is always zero; financial accuracy depends on restoring this integration |
| Plaintext credentials in SCM | Critical (security) | `.mvn/wrapper/settings.xml` — must be purged from git history and rotated |
