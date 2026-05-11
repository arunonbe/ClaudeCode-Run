# autoclaim-split-svc_LIB — Data Architect View

## Data Stores

| Store | Role | Technology | Evidence |
|---|---|---|---|
| `CbaseappDataSource` | Primary transactional database | Microsoft SQL Server (jTDS JDBC driver) | `appCtx-AutoclaimSplit_test.xml` line 22-28; root `pom.xml` dependency `net.sourceforge.jtds:jtds:1.2.2` |
| IEFT Configuration / Profile Service | Member allotment profile | eCount Core profile service (XML-RPC) | `AutoclaimSplitImpl` imports `IEFTConfigurationLoader`; test context references `ECoreDevice`, `ECoreTransfer`, `DeviceManagerImpl`, `MemberManagerImpl` |
| In-memory profile cache | Program autoclaim profile cache | Java heap (ICache / ThreadLocal) | `AllotmentConfigLoaderImpl` (commented-out implementation), `DEFAULT_CACHE_TIMEOUT = 120000L` |

The database is accessed through a connection pool created by `DirectorConfiguredDBCPdatasourceCreator` (Commons DBCP), pointing to a Director-managed datasource identified by runtime properties `director.address`, `ecount.agent`, and `cbaseapp_database`.

## Schema & Tables

No DDL scripts are present in the repository. Schema knowledge is inferred from `PaymentDaoImpl` and `PaymentDTO`.

### Stored Procedure: `get_payment_detail_echeck_member_program`

Called in `PaymentDaoImpl.PaymentQuerySP` constructor (line 56). Parameters and return shape:

| Direction | Name | SQL Type | Mapped Java field |
|---|---|---|---|
| IN | `@echeck_id` | VARCHAR | `PaymentVO.echeckId` |
| IN | `@member_id` | VARCHAR | `PaymentVO.memberId` |
| IN | `@program_id` | VARCHAR | `PaymentVO.programId` |
| OUT | `RETURN_VALUE` | INTEGER | Error/status code |
| OUT (ResultSet) | `rs` | ResultSet | List of `PaymentDTO` |

### Columns read from ResultSet (`PaymentDTO.mapRow`, `PaymentDaoImpl` lines 83-87):

| Column | Java Type | Business Meaning |
|---|---|---|
| `amount` | Integer | Payment amount (minor currency units, cents) |
| `action_code` | int | Payment state/action code |
| `echeck_id` | String | eCheck identifier |
| `verification_code` | String | Claim/authorization code — used as `claimCode` on the `Allotment` result |

Additional `PaymentDTO` fields declared but **not populated** from the SP result set (no `rs.get*` calls for them): `buyer_id`, `recipient_first_name`, `recipient_last_name`, `created`, `activation_date`, `payment_type`, `expiration_date`.

## Sensitive Data Handling

| Data Element | Classification | Handling |
|---|---|---|
| `memberId` (UUID string) | PII / financial identifier | Passed in log statements at DEBUG/INFO level without masking (`PaymentDaoImpl` line 40; `UserAllotmentAllocation` multiple INFO log calls) |
| `echeckId` (UUID string) | Financial transaction ID | Logged at DEBUG level; embedded in exception messages |
| `verification_code` | Authorization code | Stored in `Allotment.claimCode` and returned to caller; not logged directly |
| `amount` (monetary) | Financial — not PCI SAD | Logged at INFO level with device IDs |
| `deviceId` | Account reference | Logged at INFO/DEBUG level |
| `beneficiaryName` | PII | Populated from IEFT profile into `DeviceVO`; logged at INFO level |
| `recipient_first_name` / `recipient_last_name` | PII | Declared in `PaymentDTO`; not currently populated from DB results |
| Maven `settings.xml` passwords | Credentials — CRITICAL | Plaintext passwords (`acmng`, `dwil15?`, `d3v0nly`) committed in `.mvn/wrapper/settings.xml` |

**Critical finding:** `.mvn/wrapper/settings.xml` contains plaintext credentials for Nexus (`deployment`/`dwil15?`), a Wirecard/eCount Maven proxy (`acmng`/`acmng`), and internal release repos. These must be treated as compromised and rotated immediately.

## Encryption & Protection

- **No encryption at the library level.** No TLS configuration, no field-level encryption, no JCE usage found anywhere in the source.
- The JDBC connection to SQL Server via jTDS does not enforce TLS in the configuration visible here; encryption depends on the DBCP `url` property set at runtime by the Director framework.
- No credential vault (HashiCorp Vault, AWS Secrets Manager, etc.) integration is present; all credentials are injected via Spring property placeholders sourced from a file path `file:///d:/c-base/config/service/autoclaimsplitsvc/db-config.properties` — a local Windows filesystem path, implying on-premise deployment.
- Logging framework is Log4j 1.x (version 1.2.15), which has known vulnerabilities and provides no built-in PII masking.

## Data Flow

```
Caller System
  │
  ▼
AutoclaimSplitImpl.performSplit(PaymentVO)
  │  ┌─────────────────────────────────────────────────────────────────┐
  ├─►│ PaymentDaoImpl (Spring JDBC / StoredProcedure)                 │
  │  │   SP: get_payment_detail_echeck_member_program                 │
  │  │   DataSource: CbaseappDataSource (DBCP pool → SQL Server)      │
  │  │   Returns: amount, action_code, echeck_id, verification_code   │
  │  └─────────────────────────────────────────────────────────────────┘
  │
  ├─►  IEFTConfigurationLoader.populateIEFTConfiguration(...)
  │       (reads from eCount Core profile service via ECoreDevice/ECoreMember)
  │
  ├─►  UserAllotmentAllocation.execute(...)
  │       (pure in-memory computation on PaymentDTO + IEFTConfiguration)
  │
  ▼
Allotment (in-memory result returned to caller)
  - No write-back to database from within this library
```

**Data at rest:** None within this library; it is stateless.
**Data in transit:** JDBC over TCP to SQL Server; RPC calls to eCount Core profile service. Neither transport encryption configuration is defined within this library.

## Data Quality & Retention

- **No data validation** on the `amount` field from the SP — `PaymentDTO.amount` is `Integer` (nullable). A null `amount` would cause a NullPointerException in `UserAllotmentAllocation.execute()` at line 35 (`long eCheckAmt = paymentDetail.getAmount()`).
- **No date/expiry validation** — `PaymentDTO` carries `activation_date` and `expiration_date` but these are never checked. An expired eCheck could be processed without detection within this library.
- **`action_code` is read but never checked** — Payment state transitions are not enforced here.
- **No retry or idempotency** — The library is a pure computation; idempotency of the overall autoclaim transaction must be guaranteed by the caller.
- **Retention:** This library emits no persisted data. Retention obligations for the underlying eCheck and payment data fall on the SQL Server database hosting `get_payment_detail_echeck_member_program`.

## Compliance Gaps

| Gap | Regulation | Detail |
|---|---|---|
| Plaintext credentials in SCM | PCI DSS Req 8.6 / NIST CSF PR.AC | `settings.xml` contains passwords for Nexus and release repos |
| PII/financial data in logs without masking | GLBA / CCPA / PCI DSS Req 3 | `memberId`, `echeckId`, device IDs, and amounts logged at INFO/DEBUG without redaction |
| No payment expiry check | Reg E | `expiration_date` in `PaymentDTO` is unused; stale eChecks may be claimed |
| `action_code` not validated | Reg E / internal controls | Payment may be in an ineligible state (already claimed, cancelled) without detection |
| `double` for monetary field | Internal financial control | `Allotment.eCheckAmt` uses IEEE 754 double; subject to rounding errors |
| No OFAC screening | OFAC / BSA-AML | `beneficiaryName` and `country` are routed without sanctions check |
| Log4j 1.x EOL | Security best practice | Version 1.2.15 has known vulnerabilities (CVE-2019-17571 etc.) |
