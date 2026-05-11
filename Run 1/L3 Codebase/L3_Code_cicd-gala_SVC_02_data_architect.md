# cicd-gala_SVC — Data Architect View

## Data Stores

The service accesses three distinct SQL Server databases, each resolved at runtime through a "Director" connection factory (`DirectorConfiguredDBCPdatasourceCreator`). No connection strings are hardcoded in source; they are supplied via Spring property placeholders at startup.

| Logical Name | Spring DataSource Bean | Property Keys | Purpose |
|---|---|---|---|
| Banker DB (jobsvc) | `bankerJobSvcDS` | `${agent.banker}`, `${database.banker}` | Stores `banker_reserved_source`, `banker_approval_notification`, `banker_preset_funds_config`, `banker_program_datasource`, rule/config tables |
| User DB (cbaseapp) | `bankerCbaseappDS` | `${agent}`, `${database.user}` | User lookup: `banker_get_user_info`, `banker_get_user_info_by_group_name` stored procedures |
| Finance DB (Great Plains) | Dynamic per program | `${agent.gp}`, datasource name from `banker_program_datasource` | GP ERP: free funds, unsettled funds, active promotions, documents, payments, sales orders, program info, ACH delay days |

The Finance DB connection is **not static**. At startup `ProgramStoredProcedureFactory.init()` reads the `banker_program_datasource` table and creates one `DataSource` per program-expression/datasource-name pair. This means multiple GP database schemas may be accessed concurrently, one per client program group. The datasource map is held in memory and can be refreshed without restart via `updateProgramExpressionsDatasourceNames`.

## Schema & Tables

Source code, DAO classes, and stored procedure wrappers reveal the following logical schema in the Banker DB:

### `banker_reserved_source`
Accessed by: `StoredProcBankerGetReservedSources`, `StoredProcBankerGetReservedSource`, `StoredProcBankerUpdateReservedSource`, `StoredProcBankerDeleteReservedSource`, `StoredProcBankerDeleteReservedSources`

Inferred columns (from `ReservedSourceDTO` fields and stored proc parameters):
- `program_id` (VARCHAR)
- `promo_id` (INTEGER)
- `source_id` (INTEGER)
- `ref_source_id` (INTEGER) — same as `source_id` for originals; differs for reference/exception sources
- `source_prefix` (VARCHAR)
- `source_amount` (BIGINT, in cents)
- `source_description` (VARCHAR)
- `action` (VARCHAR) — values: `auth`, `unauth`, `settle`, `cancel`, `force settle`
- `updated_by` (INTEGER, userId)
- `is_under_parent_promo` (BIT/BOOLEAN)
- `num_promos_in_source` (INTEGER)

Isolation: SERIALIZABLE with 120-second timeout applied to all `BankerServiceManager` operations via AOP (`banker-transaction.xml`).

### `banker_approval_notification`
Accessed by: `StoredProcBankerGetApprovalNotificationCounter`, `StoredProcBankerUpdateApprovalNotification`

Inferred columns (from `BankerEmail` and method signatures):
- `program_id`, `source_prefix`, `source_id` — composite key
- `notification_count` (SMALLINT) — incremented on each `sendApprovalNotification` call

### `banker_preset_funds_config`
Accessed by: `JDBCBankerGetAllPresetFundsConfigs`, `StoredProcBankerGetPresetFundsConfigs`, `StoredProcBankerUpdatePresetFundsConfigs`

Maps program+promo to a preset funds ratio percent and base amount. Loaded entirely into memory at startup into `PresetFundsConfig` object.

Inferred columns (from `PresetFundsConfigDTO`):
- `program_id`, `promo_id` — composite key
- `preset_ratio_percent` (NUMERIC)
- `base_amount` (BIGINT)

### `banker_program_datasource`
Accessed by: `JDBCBankerGetAllProgramsDatasources`, `StoredProcBankerUpdateProgramDatasource`, `StoredProcBankerDeleteProgramDatasource`

Maps a program regex expression to a GP datasource name. Used by `ProgramStoredProcedureFactory` to route GP stored procedure calls to the correct database.

Inferred columns:
- `program_expression` (VARCHAR) — regex key
- `datasource_name` (VARCHAR) — name registered in Director service registry

### `banker_default_promo_exception` (inferred name)
Accessed by: `JDBCBankerGetDefaultPromoExceptionPrograms`

A list of program IDs for which promotion `1` is treated as the parent instead of `0`.

### `banker_available_funds_rule` (inferred name)
Accessed by: `JDBCBankerGetAvailableFundsRule`

Maps program+promo string to a boolean flag: whether 3/2/1-day pending payments may be included in the available funds calculation.

### `banker_group_authorization_limits` (inferred name)
Accessed by: `JDBCBankerGetGroupAuthorizationLimits`

Maps banker group code (e.g., `bankerlevelone`) to a monetary ceiling (BIGINT, cents).

### `banker_multiple_sales_order` (inferred name)
Accessed by: `StoredProcBankerGetMultipleSalesOrders`, `StoredProcBankerDeleteMultipleSalesOrders`, `StoredProcBankerInsertMultipleSalesOrder` (all in finance DB)

Tracks sources that have multiple original GP sales orders — an exception condition that must be resolved before authorization can complete.

### User DB (cbaseapp) tables
Accessed via: `StoredProcBankerGetUserInfo` → `banker_get_user_info`, `StoredProcBankerGetGroupLevelUsers` → `banker_get_user_info_by_group_name`

Returns `BankerUserDTO` fields: userId, firstName, lastName, userName, email, memberId, bankerGroups[].

## Sensitive Data Handling

- **No payment card data (PAN, CVV, track)**: The service never stores, transmits, or processes card numbers or authentication data. Monetary amounts are handled as long integers (cents).
- **User PII**: `BankerUserDTO` contains first name, last name, username, email address, and memberId. These are retrieved from the user DB and used transiently:
  - Email addresses are used as notification recipient addresses in `SendApprovalNotification` and are not persisted by this service.
  - `BankerEmail.senderUserId` and `senderUserName` are stored in the `banker_approval_notification` table.
- **Program financial data**: Posted balances, free funds, credit limits, and payment amounts are financial data. They flow over the SOAP wire unencrypted (no HTTPS enforcement visible in web.xml; `http` is the configured protocol in `.gitlab-ci.yml`).
- **Logging**: `LoggingUtil.toXML(this)` serializes DTO objects (including `BankerUserDTO` with name and email) to XML for debug logging. If debug logging is enabled in production, PII would appear in log files.
- **`System.out.println` leak**: `SendApprovalNotification.java` line 274 prints label type IDs and values directly to stdout — operational data leak in production.

## Encryption & Protection

- **At rest**: No evidence of column-level encryption in the service code. Database-level encryption depends on SQL Server configuration (not visible in this repo).
- **In transit**: The client configuration (`bankerServiceAxis-client.xml`) uses `${banker.service.wsdl.url}` which could be HTTP or HTTPS depending on deployment properties. The CI/CD configuration explicitly uses `http` (`PROJECT_SERVICE_PROTO: http`). TLS enforcement is not enforced within the application code.
- **Maven transport**: `MAVEN_OPTS` in CI pipelines specifies `-Dhttps.protocols=TLSv1.2`, enforcing TLS 1.2 for Maven dependency downloads only.
- **Credentials**: Banker DB credentials, GP agent credentials, and user DB credentials are all injected via Director service at runtime. No credentials appear in source code.
- **Axis timeout**: The SOAP client has a configurable `axis.connection.timeout` (from `${banker.service.timeout}`). No TLS client certificate or mutual authentication configuration is present.

## Data Flow

```
Caller Application
     |  (SOAP over HTTP, Apache Axis 1.4)
     v
BankerServiceAPIImpl (extends ServletEndpointSupport)
     |
     v
BankerServiceManagerImpl (singleton, SERIALIZABLE TX)
     |
     +---> BankerDAOServiceImpl ---------> Banker DB (jobsvc)
     |         stored procs / JDBC        banker_reserved_source
     |                                    banker_approval_notification
     |                                    banker_preset_funds_config
     |                                    banker_program_datasource
     |
     +---> UserDAOServiceImpl -----------> User DB (cbaseapp)
     |         stored procs               user / group tables
     |
     +---> FinanceDAOServiceImpl --------> Finance DB (Great Plains, per-program datasource)
               ProgramStoredProcedureFactory   free_funds, unsettled_funds, 
               (dynamic routing by program)    active_promotions, documents,
                                               payments, sales_orders
     |
     +---> cbase profile services -------> ECountCore DB (via RequestContext/Agent)
               AppProfileProgramCurrencyClass  currency multiplier
               AppPromotionLabelProfileClass   program/relationship manager labels
               NotificationManagerImpl         email delivery
```

## Data Quality & Retention

- **No data retention policy** is defined in the application code. Reserved source records are deleted by stored procedures on unauth/settle/cancel; no archival logic exists in this layer.
- **Monetary amounts in cents**: All `long` monetary values (e.g., `sourceAmount`, `freeFunds`, `availableFundsAmount`) are stored and calculated as integers in cents. Division by 100 happens only at presentation layer (email formatting in `SendApprovalNotification`).
- **Startup data load**: `BankerServiceManagerImpl.init()` loads `bankerDefaultPromoExceptionPrograms`, `outstandingPaymentsProgramPromoMap`, `userGroupCodeAuthorizationAmountLimitsMap`, and `presetFundsConfig` entirely into JVM memory at startup. There is no TTL or cache invalidation mechanism except the `updateProgramExpressions*` API (which only refreshes the `ProgramStoredProcedureFactory` map, not the other maps).
- **Approval notification counter**: The `banker_approval_notification` counter is incremented but there is no maximum-notification-count enforcement visible in the code; the business rule for escalation thresholds lives outside this service.

## Compliance Gaps

1. **HTTP in production**: The CI/CD pipeline explicitly declares `PROJECT_SERVICE_PROTO: http`. SOAP messages carrying financial amounts and user PII (email addresses, source amounts) are transmitted unencrypted. This is a PCI DSS requirement 4.2.1 gap (protect cardholder data in transit — and, more broadly, financial data in transit).
2. **Debug logging of PII**: `BankerUserDTO.toString()` (via `LoggingUtil.toXML`) serializes name and email. If `DEBUG` log level is active, this constitutes uncontrolled PII logging.
3. **`System.out.println` in `SendApprovalNotification`**: Uncontrolled stdout output of program label data; violates principle of controlled audit logging.
4. **No log masking for financial amounts**: Debug logs in `Authorize.java` and `BankerServiceManagerImpl.java` log source amounts and available funds amounts in clear text. For a payment service these should be treated as financial PII.
5. **In-memory config cache without TTL**: Changes to `banker_available_funds_rule` or `banker_group_authorization_limits` in the database require a service restart to take effect, creating a risk of stale authorization decisions.
6. **No explicit data retention policy** for `banker_reserved_source` and `banker_approval_notification` tables. PCI DSS and GDPR/CCPA require defined retention and purge schedules for records containing financial and personal data.
