# banker_API — Data Architect View

## Data Stores

Banker uses three distinct SQL Server databases, each accessed through a Spring-managed datasource obtained from a "Director" service-discovery component (`DirectorConfiguredDBCPdatasourceCreator`).

| Logical Name | Bean ID | Config Property | Purpose |
|---|---|---|---|
| Banker DB (jobsvc) | `bankerJobSvcDS` | `${agent.banker}` / `${database.banker}` | Banker's own tables: reserved sources, preset funds, approval notifications, program datasource mappings |
| User DB (cbaseapp) | `bankerCbaseappDS` | `${agent}` / `${database.user}` | User/role lookup: `banker_get_user_info`, `banker_get_user_info_by_group_name` |
| Finance DB (Great Plains) | Dynamic, per-program | `${agent.gp}` + regex-mapped datasource name | GP ERP tables: program info, promotions, sales orders, invoices, payments, free funds, unsettled funds |

Configuration source: `banker-datasource.xml`, `user-datasource.xml`, `finance-datasource.xml`, and `banker-dao-manager.xml`.

The Finance DB datasource is **not static**. `ProgramStoredProcedureFactory` (`ProgramStoredProcedureFactory.java`) loads a map of program ID regular expressions to GP datasource names from the `banker_program_datasource` table at startup and when `updateProgramExpressionsDatasourceNames()` is called. This allows routing different programs to different GP database instances without service restart.

## Schema & Tables

### Banker DB (inferred from stored procedure names and parameters)

| Table / Object | Operation Classes | Columns (inferred) |
|---|---|---|
| `banker_reserved_sources` (or equivalent) | `StoredProcBankerGetReservedSources`, `StoredProcBankerUpdateReservedSource`, `StoredProcBankerDeleteReservedSource`, `StoredProcBankerDeleteReservedSources` | `program_id` (VARCHAR), `promotion_id` (INT), `source_prefix` (VARCHAR), `source_id` (INT), `ref_source_id` (INT), `source_desc` (VARCHAR), `is_under_parent_promo` (BIT), `action` (VARCHAR), `action_amount` (BIGINT), `num_promos_in_source` (INT), `updated_by` (VARCHAR/INT) |
| Banker audit/log table | Referenced by SP return code `-1` on log failure | Tracks all mutations to reserved sources |
| `banker_preset_funds_config` (or equivalent) | `StoredProcBankerGetPresetFundsConfigs`, `StoredProcBankerUpdatePresetFundsConfigs`, `JDBCBankerGetAllPresetFundsConfigs` | `program_id`, `promotion_id`, `preset_ratio`, `base_amount` |
| `banker_approval_notification` | `StoredProcBankerGetApprovalNotificationCounter`, `StoredProcBankerUpdateApprovalNotification` | `program_id`, `source_prefix`, `source_id`, notification counter |
| `banker_program_datasource` | `JDBCBankerGetAllProgramsDatasources`, `StoredProcBankerUpdateProgramDatasource`, `StoredProcBankerDeleteProgramDatasource` | `program_expression` (regex VARCHAR), `datasource_name` (VARCHAR) |
| Available funds rule table | `JDBCBankerGetAvailableFundsRule` | `program_id`, `promotion_id`, `on_off_flag` (BIT) — controls whether 3/2/1-day payments are included |
| Group authorization limits | `JDBCBankerGetGroupAuthorizationLimits` | Group name (VARCHAR), authorization amount limit (BIGINT) |
| Default promo exception programs | `JDBCBankerGetDefaultPromoExceptionPrograms` | `program_id` (VARCHAR) |

Evidence: `StoredProcBankerGetReservedSources.java` declares parameters `program_id`, `promotion_id`, `is_parent_promo` (input) and maps result columns `source_prefix`, `source_id`, `ref_source_id`, `source_desc`, `is_under_parent_promo`, `action`, `action_amount`, `num_promos_in_source`, `updated_by` (lines 36–48, 99–115).

### User DB (cbaseapp)

| Table / Object | Operation Classes | Columns (inferred) |
|---|---|---|
| User/group lookup | `StoredProcBankerGetUserInfo`, `StoredProcBankerGetGroupLevelUsers` | `user_id`, `application_id`, banker role groups, email, first name, member ID |

### Finance DB (Great Plains)

All access is through named stored procedures invoked dynamically:

| Stored Procedure | Java Class | Purpose |
|---|---|---|
| `banker_get_free_funds` | `StoredProcBankerGetFreeFunds` | GP posted balance, credit memos, usable payments |
| `banker_get_program_info` | `StoredProcBankerGetProgramInfo` | Program name, credit limit type, currency |
| `banker_get_unsettled_funds` | `StoredProcBankerGetUnsettledFunds` | Per-source: original SO amount, invoices, void amounts |
| `banker_get_all_unsettled_funds` | `StoredProcBankerGetAllUnsettledFunds` | Batch unsettled funds for list of sources |
| `banker_get_active_promotions` | `StoredProcBankerGetActivePromotions` | Active GP promotion IDs for a program |
| `banker_get_documents` | `StoredProcBankerGetDocuments` | Sales orders, invoices, credit memos by doc type |
| `banker_get_payments` | `StoredProcBankerGetPayments` | Non-voided payments per source |
| `banker_get_3_2_1_payments` | `StoredProcBankerGet321Payments` | Pre-settlement ACH payments |
| `banker_get_ach_delay` | `StoredProcBankerGetACHDelay` | ACH delay day count |
| `banker_get_multiple_sos` | `StoredProcBankerGetMultipleSalesOrders` | Multiple original sales orders (error condition) |
| `banker_delete_multiple_sos` | `StoredProcBankerDeleteMultipleSalesOrders` | Delete duplicate SO records |
| `banker_insert_multiple_so` | `StoredProcBankerInsertMultipleSalesOrder` | Log duplicate SO |

GP program-promo IDs are constructed using `GPConversionTool.getGPProgramPromoId()`, which concatenates programId and promoId into the GP composite key format.

## Sensitive Data Handling

- **Monetary amounts** are stored as `long` (cents, BIGINT in SQL). No decimal/currency types are used, avoiding floating-point rounding risks.
- **User identity**: `userId` (integer) and `applicationId` (integer) are the only PII-proximate fields in request DTOs. No names, emails, or addresses pass through Banker's own transactional tables.
- **Email addresses**: The `BankerUserDTO` contains `email` and `firstName` fields (used in `SendApprovalNotification.java` line 376), but these are read from the user DB and used only transiently for email dispatch — they are not written to Banker's own tables.
- **Source descriptions** (`sourceDescription` / `source_desc`): May contain file names or job descriptors from calling services. This column is stored in `banker_reserved_sources`. Sensitivity depends on what Job Service / Order Service put there; no masking is applied in Banker.
- **XStream serialization**: `LoggingUtil.java` uses XStream to serialize any DTO to XML for logging (`toString()` on DTOs calls `LoggingUtil.toXML()`). If debug-level logging is enabled, full DTO payloads including amounts and user IDs will appear in logs.

## Encryption & Protection

- **Transport**: The service runs on plain HTTP port 80 in Docker (`server.xml` line 64, `Dockerfile` line 22 `EXPOSE 80`). No TLS is configured at the Tomcat level. TLS termination must occur upstream (load balancer / AKS ingress).
- **Database connections**: Credentials and connection strings are not in source code. They are resolved via the Director service (`director.address` property) and `DirectorConfiguredDBCPdatasourceCreator`. The actual secrets are external to the repository.
- **No field-level encryption**: Amounts and source IDs in `banker_reserved_sources` are stored in plaintext. This is expected for an internal operational database, but must be considered in CDE scoping for PCI DSS.
- **QA certificate**: `Dockerfile` lines 19–20 import a QA certificate (`certfile_qa.crt`) into the JVM truststore at build time. Production certificate handling is not visible in the repo.
- **Ignored CVEs**: `.trivyignore` suppresses `CVE-2024-47072`, `CVE-2024-52316`, `CVE-2024-22262`, `CVE-2024-38816`, `CVE-2024-50379`, `CVE-2024-38819`, `CVE-2024-56337`. The container scan allowlist (`allowedlist.yaml`) additionally suppresses `CVE-2018-1000632`, `CVE-2020-10683`, `CVE-2024-22262`. These include Spring Framework and XStream vulnerabilities.

## Data Flow

```
Calling Service (Job Service / Order Service)
        |
        | SOAP over HTTP (Apache Axis 1.4 / JAX-RPC)
        |
BankerServiceAPIImpl (servlet endpoint)
        |
BankerServiceManagerImpl (singleton, Spring-managed)
        |
  +-----+-----+
  |           |
BankerDAOServiceImpl   FinanceDAOServiceImpl       UserDAOServiceImpl
  |                      |                              |
Banker DB (jobsvc)   Finance DB (GP, per-program regex)  User DB (cbaseapp)
```

The Finance DB routing is dynamic: `ProgramStoredProcedureFactory.getInstance(programId, StoredProcClass)` matches the program ID against regex keys in `programFinanceStoredProceduresMap` (longest match wins) to obtain the correct DataSource and stored procedure instance.

## Data Quality & Retention

- **Startup cache load**: On `init()`, `BankerServiceManagerImpl` loads `bankerDefaultPromoExceptionPrograms`, `outstandingPaymentsProgramPromoMap`, `userGroupCodeAuthorizationAmountLimitsMap`, and `presetFundsConfigsMap` from DB. These are not refreshed automatically during runtime (except `presetFundsConfigsMap`, which is lazily refreshed per-program by `PresetFundsConfig.updatePresetFundsConfigDTO()` when a cache miss occurs).
- **Reserved source TTL**: No TTL or expiry column is visible in the reserved-source schema. Records persist until explicitly deleted (by `unAuth`, `cancelReservedSource`, `forceSettleReservedSource`, or `settleReservedSources`). Orphaned records could accumulate if calling services fail between auth and unauth.
- **Approval notification counter**: Stored as `short` (16-bit), meaning it saturates at 32,767 notifications before overflow. This is a data quality risk for very long-running programs.
- **Multiple SO table**: `banker_insert_multiple_so` inserts with return code `-1` if already exists, suggesting a uniqueness constraint, but duplicate detection logic is minimal.

## Compliance Gaps

1. **No data retention policy enforcement**: Reserved source records and approval notification records are never automatically purged. For GLBA and GDPR data minimization, a retention/archival policy should be defined and enforced.

2. **Debug logging of full DTOs**: `BankerRequestDTO.toString()` calls `LoggingUtil.toXML(this)` (XStream). With debug logging enabled, entire request objects including user IDs, program IDs, and amounts are written to log files. Log files must be protected and retained under the same controls as the application data.

3. **XStream CVE**: `CVE-2020-10683` (suppressed) and `CVE-2018-1000632` (suppressed) are known XStream deserialization vulnerabilities. XStream is used in `LoggingUtil` for serialization only (not deserialization of external input), but the suppressed CVEs should be formally assessed and documented as accepted risks.

4. **No explicit PII inventory**: `BankerUserDTO` holds `userName`, `email`, `firstName`, and `memberId`. These flow transiently through the application. Their presence in logs (via XStream `toString()`) means they could appear in log data without explicit audit control.

5. **Plain HTTP endpoint**: The Tomcat connector runs on port 80 without TLS (`server.xml`). All SOAP traffic including user IDs and financial amounts is unencrypted in transit unless encrypted by infrastructure (AKS ingress TLS). This should be documented as a network control dependency.
