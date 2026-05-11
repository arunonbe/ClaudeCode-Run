# workbench_WAPP — Data Architect View

## Data Stores
| Store | Type | Bean ID | Purpose |
|-------|------|---------|---------|
| CbaseappDataSource | SQL Server (JNDI) | `CbaseappDataSource` | Primary operational database for all workbench configuration, user, affiliate, and card data |
| JobSvcDataSource | SQL Server (via alias `JobSvcDataSourceSymbol`) | `JobSvcDataSourceSymbol` | Job service and symbol service data |
| Lucene RAMDirectory | In-memory full-text index | (via xContent / symbol-svc) | Symbol/content indexing (inherited from xSecurity/symbol dependencies) |

## Schema / Tables
All data access uses Spring JDBC `StoredProcedure` objects; no ORM entities are directly defined within this repo except for Hibernate-managed affiliate entities:

**Hibernate-mapped entities (in `CbaseappDataSource`):**
- `Affiliate` — core affiliate/program entity
- `AffiliateLocale` — locale language record per affiliate
- `AffiliateLocaleAffiliate` — junction table (affiliate to locale)
- `AffiliateLocaleCopy` — translated copy per locale
- `AffiliateLocaleCopyTag` — tag classification on copy
- `AffiliateLocaleSkin` — skin template record per locale
- `AffiliateLocaleCopyType` — copy type lookup
- `AffiliateDetail` — extended affiliate details

**Stored Procedure-accessed data (inferred from action names):**
- User and Group tables (add/update user, add/update group, change user status)
- Banker tables (banker authorization, settlement, notification)
- FDR card/DDA profile tables
- Fee, fee credit, dormancy fee schedule tables
- App promotion, promotion PPD, promotion event, promotion spin, promotion fee tables
- Job/file tables (job status, file submitted, job priority)
- Subscription tables (report subscriptions)
- Config scope, scope affiliate tables
- JobSvc profile, schedule tables
- PSC template tables
- Symbol configuration tables
- EMEA configuration tables
- Label type and label list tables
- One Platform affiliate configuration tables

## Sensitive Data
- **User credentials**: Stored as MD5 hashes in `CbaseappDataSource`; retrieved and compared via `passwordManager`
- **Session tokens**: Managed by Acegi Security `HttpSessionContextIntegrationFilter` — stored in JVM HTTP session
- **Program/affiliate configuration**: Includes fee schedules and product configuration — business confidential but not PAN/CHD
- **Banker financial data**: Banker authorization state and settlement data may contain financial exposure amounts
- No evidence that PANs, CVVs, or account numbers are stored or processed within this application directly; this is a configuration/ops portal

## Encryption
- **At-rest**: No encryption configuration is defined in the codebase for `CbaseappDataSource`; relies on SQL Server-level encryption if enabled in the infrastructure layer
- **In-transit**: `forceHttps=false` in `authenticationEntryPoint` (file: `applicationContext-xsecurity-web.xml`, line 99) — TLS is not enforced by the application; depends entirely on infrastructure-level enforcement
- **Password hashing**: MD5 via `EcountMd5PasswordEncoder` — MD5 is cryptographically broken and does not qualify as password hashing under current PCI DSS v4.0.1 requirements (Req 8.3.6 demands strong one-way hashing)

## Data Flow
```
Browser (operator) 
  → HTTPS (infrastructure-enforced, not app-enforced) 
  → Tomcat (WAR deployed as ROOT) 
  → Acegi filter chain → Struts action 
  → Spring action processor (e.g. AddFundsProcessAction) 
  → Spring JDBC StoredProcedure 
  → SQL Server (CbaseappDataSource via JNDI)
```
For job scheduling:
```
Workbench action processor 
  → HTTP Invoker (Spring remoting) 
  → JobSchedulerService endpoint (${jobscheduler.service.url}) 
  → External job scheduler
```

## Data Quality / Retention
- No data retention policies, archival rules, or purge configurations are defined in this repository
- Logging configuration references `workbench-SystemLog.config` and `Log.config` but content not analysed in this pass
- ehcache (`ehcache.xml`) is configured — caches affiliate data to reduce database round trips; cache invalidation strategy not visible in this repo

## Compliance Gaps
1. **PCI DSS Req 8.3.6**: MD5 password hashing is not an acceptable one-way function — must be replaced with bcrypt, scrypt, Argon2, or PBKDF2 with salt
2. **PCI DSS Req 4.2.1**: `forceHttps=false` means the application does not enforce TLS at the application tier; if infrastructure layer is misconfigured, credentials travel in cleartext
3. **PCI DSS Req 10**: No audit logging configuration is visible in the application layer for configuration-change events (configuration of fees, promotions, profiles)
4. **PCI DSS Req 7**: Role definitions (`ROLE_REPORTS`, `ROLE_VIEW_PROGRAM`) are broad; finer-grained access per data type is not observable
5. No database-level field encryption for sensitive configuration values (e.g., fee override amounts, banker thresholds)
