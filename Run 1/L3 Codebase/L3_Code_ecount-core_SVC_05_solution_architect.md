# 05 Solution Architect — ecount-core_SVC

## Module-Level Class Inventory

Because `ecount-core_SVC` is a large multi-module project with source files in many sub-modules that were not individually read in this analysis, the following inventory focuses on the WAR assembly and Spring context wiring — the most architecturally significant layer. Individual service and DAO classes are described by their Spring XML context wiring.

### eCoreWar — Wired Beans (Spring XML Contexts)

| Context XML | Key Beans | Purpose |
|---|---|---|
| `Configuration.xml` | `propertyConfigurer`, `Agent`, `fdrKnowledge`, `stateMap`, `internationalFlagService` | Core configuration bootstrap; loads external property files from CBASE_HOME_URL |
| `DataSources.xml` | `ecountCoreDS`, `jobsvcDS`, `strongboxDS`, `fdrODSDS`, `cbaseappDS`, `ecountCoreTxManager`, `strongboxTxManager`, `sqlTimeoutManager` | All JNDI datasource wiring and transaction managers |
| `EMemberService.xml` / `EMemberXMLRPC.xml` | EMember service beans and XML-RPC handler | Cardholder account management |
| `EManageService.xml` / `EManageXMLRPC.xml` | EManage service beans | Card/account management operations |
| `EDeviceService.xml` / `EDeviceXMLRPC.xml` | EDevice service beans | Card device lifecycle |
| `ETransferService.xml` / `ETransferXMLRPC.xml` | ETransfer service beans | Fund transfer operations |
| `EventService.xml` / `EventXMLRPC.xml` | Event service beans | Audit event recording |
| `EWebRequestLogService.xml` | Web request logger | HTTP request audit |
| `ACHDeviceLibrary.xml` | ACH library beans | ACH bank transfer |
| `IEFTDeviceLibrary.xml` | IEFT library beans | Interbank EFT |
| `FDRDebitServices.xml` | FDR debit service beans | First Data Resources integration |
| `KYCService.xml` | Actimize KYC bean | Identity verification |
| `RecipientScreeningService.xml` | Recipient screening bean | AML/sanctions screening |
| `StrongBoxService.xml` | StrongBox client | Cryptographic operations |
| `CountryRegulationLibrary.xml` | Country regulation bean | Jurisdiction rules |
| `AuditActivityLibrary.xml` | Audit activity bean | Audit trail management |
| `AzureService.xml` | Azure App Config / Key Vault beans | Cloud configuration and secrets |
| `DirectorySettings.xml` | Director client bean | DB config resolution |
| `GlobalRequestID.xml` | Correlation ID bean | Distributed request tracing |
| `HealthMonitor.xml` | Health bean | Service health |
| `RestController.xml` | Spring MVC REST controller beans | REST API wiring |
| `MethodTracerConfiguration.xml` | AOP method tracer | Performance monitoring |
| `ehcache.xml` | Cache manager | Ehcache configuration |

### REST API Layer

The `ecountCoreRestController` module exposes REST endpoints consumed by `embedded-payments-api` and other clients. Based on the service names and context files, inferred REST endpoints include:
- GET/POST for member lookup, account balance, transaction history
- POST for fund transfer (disburse)
- GET for card details (with PAN — PCI scope)
- Health check endpoint

## Security Vulnerabilities

### 1. Log4j 1.2-api Bridge in Classpath (P1 — High)
`eCoreWar/pom.xml` line 224 declares `log4j-1.2-api` as a runtime dependency. While the Log4j 2 core (which is patched for Log4Shell) handles actual logging, the 1.x bridge means any downstream code that calls `org.apache.log4j.Logger` still works. The risk is:
- The `log4j-1.2-api` bridge is provided by Log4j 2 team and does not re-introduce Log4j 1.x CVEs
- However, it suggests residual consumers of the old API who have not been updated
- Recommendation: Audit all callers and migrate to SLF4J / Log4j 2 directly; remove the bridge

### 2. Log4j 2 Version Pinning Must Be Verified (P1 — Critical)
The `eCoreWar/pom.xml` declares `log4j-api` and `log4j-core` without explicit version numbers — they come from `prepaid-parent`. The `prepaid-parent` version must be verified to include Log4j >= 2.17.1 (Log4Shell fix for CVE-2021-44228 / CVE-2021-45046 / CVE-2021-45105). The Dockerfile copies these JARs into Tomcat's `lib/` directory, so the container image version determines the actual running version. **This must be verified before any production deployment.**

### 3. SNAPSHOT Version in Production (P2 — High)
Version `3.1.9-SNAPSHOT` is deployed. This is a mutable artefact. In a PCI DSS environment, all production software must be traceable to a specific, immutable build.

### 4. Historical Hardcoded Credentials in DataSources.xml (P2 — Medium)
Commented-out datasource beans in `DataSources.xml` lines 22–41 contain credentials (`b2ctest/b2ctest`, `CBASEAPP/ECOUNT`). While commented out, they are visible in source control and represent credentials that may still be valid in some environments.

### 5. `mssql-jdbc` Version Discrepancy (P3 — Medium)
Tomcat lib copies `mssql-jdbc:12.5.0.jre11-preview` (Dockerfile build), while the POM test-scope dependency is `12.8.1.jre11`. These should be aligned. The preview version should not be used in production.

### 6. Ehcache PAN Caching Risk (P2 — High)
If any service puts PAN data into Ehcache (configured in `ehcache.xml`), the cache content must be encrypted at rest. Ehcache 3.x supports tiered storage (heap → off-heap → disk). Disk tier would constitute plaintext PAN storage if not configured with encryption. Requires audit of cache usage.

### 7. CBASE_HOME_URL External File Dependency (P3 — Medium)
The entire configuration bootstraps from `${CBASE_HOME_URL}/config/core2/ecountcore/ecountcore.properties`. If this mount is unavailable or misconfigured, the service fails to start. This is an operational risk and should be complemented with Azure App Configuration fallback (which `AzureService.xml` appears to provide).

## Technical Debt

1. Spring XML-based context (40+ XML files) — significant maintenance burden; should be migrated to annotation/Java config over time
2. Stored-procedure-only DAO pattern — limits query flexibility and makes schema migration difficult
3. IBM MQ dependency — creates infrastructure coupling; migration path to Azure Service Bus should be planned
4. jTDS still referenced in `ecount-system_LIB` (consumed library) — must align on mssql-jdbc
5. Multiple Spring XML files with commented-out code (credentials, legacy beans) — creates confusion and security risk

## Remediation Priority Summary

| Issue | Priority | Action |
|---|---|---|
| Log4j 2 version verification for Log4Shell | P1 — Critical | Verify `prepaid-parent` includes Log4j >= 2.17.1; add explicit version pins |
| Log4j 1.2-api bridge removal | P1 — High | Audit callers; migrate to Log4j 2 API; remove bridge |
| SNAPSHOT version | P2 — High | Release `3.1.9` |
| Ehcache PAN encryption audit | P2 — High | Review ehcache.xml; enable disk-tier encryption if used |
| Commented credentials in DataSources.xml | P2 — Medium | Remove commented code; purge from Git history |
| mssql-jdbc version alignment | P3 — Medium | Pin to `12.8.1.jre11` everywhere |
| CBASE_HOME_URL fallback | P3 — Medium | Ensure Azure App Configuration is a complete fallback |
