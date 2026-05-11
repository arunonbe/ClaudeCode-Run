# Data Architect View — screen-configs_LIB

## Data Models

screen-configs_LIB uses a sparse, generic column model for all screen configuration data:

**`InstIssueCZScreenCfgRecord`** — generic record with positional column fields:
- `column2`, `column3`, `column4`, `column5` — named columns with no semantic typing; the meaning of each column depends on the query context (e.g., for reversal reasons: column2=status, column3=type, column4=reason text; for payment reasons: column4=reason code, column5=amount)

**`InstIssueCZScreenCfgOptions`** — request/options object:
- `programId` — the primary key for all queries

**`InstIssueCZScreenCfgDaoResult`** — wrapper containing `List<InstIssueCZScreenCfgRecord>`

The generic column model (`column2..column5`) is a legacy pattern from the eCount architecture where stored procedures return position-based result sets rather than named fields. This makes the data contract fragile — any change to stored procedure column ordering would break the library silently.

## Sensitive Data Handled

| Data Category | Presence | Notes |
|---|---|---|
| PAN / CVV | None | Screen config data only |
| PII (cardholder) | Indirect | The `dspHidePIIFld` flag controls PII visibility; the library does not store PII itself |
| Payment amounts | Present | Payment reason amounts are stored as configuration data |
| Program ID | Primary key | Business identifier; not directly sensitive |
| CSA screen layout | Present | Screen configuration controlling agent workflow |

The library does not store cardholder PII directly. However, it controls whether PII is shown to agents, making it a control-plane component for PII data governance.

## Encryption and Protection Status

- No application-level encryption is implemented or expected for screen configuration data
- SQL Server connection uses the eCount standard JDBC driver (Microsoft SQL Server JDBC 1.1); TLS encryption on the database connection depends on the deployment configuration
- Spring XML application context (`applicationContext-instIssueCZScreenCfg.xml`) manages DataSource injection — connection credentials are externalized to the Spring context, not hardcoded
- The test context (`datasourceTestContext.xml`) connects to a live SQL Server instance for integration testing — test credentials must not be committed to the repository

## Database Schemas

All data access is through stored procedures via JDBC:

| Stored Procedure (inferred) | Operation | Key Parameters |
|---|---|---|
| `CallInquiryDisplayDefaultData` | Read display defaults | programId |
| `CallInquiryOAccountDetails` | Read o-account types | programId |
| `CallInquiryPaymentReasons` | Read payment reasons | programId |
| `CallInquiryReversalReasons` | Read reversal reasons | programId |
| `CallInquiryScreenDriverFlags` | Read screen driver flags | programId |
| `CallSaveInstIssueDisplayDefaultData` | Write display defaults | programId, config values |
| `CallSaveInstIssueDisplaySettings` | Write display settings | programId, config values |
| `CallSaveInstIssuePmtOrRevReasons` | Write payment/reversal reasons | programId, reason data |
| `CallSaveOAccountDetails` | Write o-account details | programId, account data |

The actual table names in SQL Server (likely `ecountcore` or `cbaseapp` database) are:
- Program-scoped configuration tables for instant-issue screen setup
- Likely tables: `InstIssueCZSetupScreenCfg`, `ScreenDriverFlags`, `PaymentReasons`, `ReversalReasons` (exact names inferred from stored procedure naming conventions)

## Data Flows

```
CSA Admin / ClientZone Admin
  → calling web application (clientzone_WAPP or cs-api)
    → InstIssueCZSetupScreenCfgManager (this library)
      → InstIssueCZScreenCfgDao (JDBC)
        → SQL Server stored procedures
          → ecountcore / cbaseapp database tables
```

Read path (CSA screen load):
```
CSA Agent → client application → inquireScreenDriverFlags(programId)
                               → inquirePaymentReasonSettings(programId)
                               → inquireReversalReasonSettings(programId)
```

Write path (admin configuration):
```
Admin → admin application → saveInstIssueDisplaySettings(options)
                          → savePaymentReasonSettings(options)
```

## Retention Concerns

- Screen configuration data is operational configuration, not transactional data — no defined retention period
- However, changes to the `dspHidePIIFld` flag and payment/reversal reason configurations should be audited with a change log for PCI DSS and GLBA compliance
- The `sample-data.xml` in test resources contains test configuration data — must not contain real program IDs or real payment configurations from production environments

## PCI DSS Data Storage Compliance

- This library stores no PANs, CVVs, or SAD — it is not a primary PCI DSS data store
- PCI DSS Requirement 7 (access control) applies indirectly: the `dspHidePIIFld` screen configuration controls which agents can see cardholder data. Onbe must ensure this configuration flag is set correctly for each program and that changes to it are subject to change management controls
- PCI DSS Requirement 10.2 (audit logs): write operations (`save*` methods) do not log changes — this is a compliance gap that should be addressed by the calling application layer
- PCI DSS Requirement 6.3.3: Spring 2.0.4 (dependency in pom.xml) is severely EOL; this library uses a version of Spring from 2007 that has numerous unpatched CVEs. This is a critical finding for any CDE-adjacent deployment.
