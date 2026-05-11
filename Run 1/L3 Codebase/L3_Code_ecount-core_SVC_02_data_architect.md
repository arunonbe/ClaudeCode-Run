# 02 Data Architect — ecount-core_SVC

## Database Architecture

EcountCore connects to multiple SQL Server databases. All connections are managed via JNDI datasources declared in `eCoreWar/src/main/resources/DataSources.xml`, populated by Tomcat's server.xml JNDI resource configuration.

| JNDI Name | Bean ID | Database | Purpose |
|---|---|---|---|
| `jdbc/ecountCoreDS` | `ecountCoreDS` | `ecountCore` | Primary business database — cardholder accounts, transactions, cards |
| `jdbc/jobsvcDS` | `jobsvcDS` | `jobsvc` | Job and order scheduling |
| `jdbc/strongboxDS` | `strongboxDS` | `strongbox` (or shared) | HSM/cryptographic key references |
| `jdbc/fdrODSDS` | `fdrODSDS` | FDR ODS (ODBC) | First Data Resources operational data store |
| `jdbc/CbaseappDataSource` | `cbaseappDS` | `cbaseapp` | CBASE application database |

Additional datasources visible from the parent POM and CLAUDE.md of `embedded-payments-api`:
- `ecountcore` database (accessed by embedded-payments-api as a separate Spring datasource)
- `jobservice` database

## Transaction Management

Transactions are managed at the DAO (not service) layer, using `DataSourceTransactionManager`:

- `ecountCoreTxManager` — wraps `ecountCoreDS`; no-rollback for `DataExceptionReturnCode`, `CoreException`
- `strongboxTxManager` — wraps `strongboxDS`; all-or-nothing

(`DataSources.xml` lines 100–123)

This per-database transaction model reflects the fact that EcountCore spans multiple databases and does not use a distributed transaction coordinator (XA).

## Data Domains and Key Entities

The `ecountCoreDAO` module (not directly readable in this analysis) maps to the following logical entities in the EcountCore database (inferred from service names and XML context files):

| Entity Group | Service | Tables (inferred) |
|---|---|---|
| Member (Cardholder) | EMemberService | `member`, `member_address`, `member_contact` |
| Card Device | EDeviceService | `card`, `card_device`, `card_status` |
| Transaction | ETransferService | `transaction`, `transaction_detail` |
| Job/Order | JobService | `job`, `job_order` (in `jobsvc` DB) |
| Emboss Queue | CallCoreProcessEmbossQueueExtract | `emboss_queue`, `emboss_file` |
| FDR ODS | FDRDebitService | `CBASClntCATM` (ODBC/ODS) |
| StrongBox | StrongBoxService | `strongbox_key`, `strongbox_value` |
| Audit Event | EventService | `audit_event`, `web_request_log` |
| Country Regulation | CountryRegulationLibrary | `country_regulation` |

## Sensitive Data Flows

### PAN Flow (Primary Account Number)
1. PANs are stored in the `ecountcore` SQL Server database (encrypted at the database tier via StrongBox integration)
2. EcountCore retrieves PANs via stored procedures in `ecountCoreDAO`
3. For embossing: the full PAN is returned by `dbo.core_process_emboss_queue_extract` and written to the XML emboss file by `emboss-extract_LIB`
4. For the embedded payments widget: PAN is returned by the `getDisbursementInfo` REST endpoint (see `embedded-payments-api`); the `openapi.yaml` schema `DisbursementInfoResponse` includes `cardNumber`, `cvCode`, `expiryMonth`, `expiryYear`

### Credential Flow (Database)
Connection credentials are managed externally:
- **Production**: Injected via Tomcat JNDI (`server.xml`) — credentials never appear in application WAR
- **Director integration**: `ecount-system_LIB`'s `DirectorConfiguredDBCPdatasourceCreator` can resolve credentials from Director at runtime

The commented-out datasource beans in `DataSources.xml` (lines 21–41) show historical hardcoded credentials (`b2ctest/b2ctest`, `CBASEAPP/ECOUNT`) — these are dev/test credentials, not production, and have been replaced with JNDI.

## Configuration Management

The `Configuration.xml` Spring context loads properties from:
```
${CBASE_HOME_URL}/config/core2/ecountcore/ecountcore.properties
${CBASE_HOME_URL}/config/core2/ecountcore/FiServRestConfig.properties
```

`CBASE_HOME_URL` is set as a Docker environment variable (`ENV CBASE_HOME_URL=file:///cbase` in `Dockerfile` line 27). This is an external configuration mount, allowing environment-specific properties without rebuilding the WAR.

## Caching Architecture

EcountCore uses **Ehcache** for in-process caching (`ehcache.xml`). Cached entities include frequently-read configuration data, country codes, and potentially cardholder lookup results. PCI DSS Req 3.5.1 applies to any PAN data placed in cache — cache encryption must be verified.

## Spring Context Modules (XML-based)

The WAR wires the entire service via Spring XML context files. Key patterns:
- `AzureService.xml` — Azure integration (App Configuration / Key Vault)
- `DirectorySettings.xml` — Director service client configuration
- `RestController.xml` — Spring MVC REST controller wiring
- `MethodTracerConfiguration.xml` — AOP method-level performance tracing
