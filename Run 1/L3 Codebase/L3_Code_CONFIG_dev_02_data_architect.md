# Data Architect View — CONFIG_dev

## Data Stores Configured

| Database / Store | JDBC URL / Connection | Notes |
|------------------|-----------------------|-------|
| `cbaseapp` (SQL Server) | `jdbc:sqlserver://d-na-db01.nam.wirecard.sys:2232;databaseName=cbaseapp` | Primary application database |
| `jobsvc` (SQL Server) | `jdbc:sqlserver://d-na-db01.nam.wirecard.sys:2232;databaseName=jobsvc` | Job/scheduler database |
| `CBTS` (SQL Server) | `jdbc:sqlserver://d-na-db01.nam.wirecard.sys\db01:2232;databaseName=CBTS` | Cross-border transfer service DB |
| `ecount-db` | Referenced in `ecount-db.properties` (QA equivalent present in QA repo) | eCount core data |
| `ecountcore-ds` | `ecountcore-ds.properties` | eCount core datasource |
| `greatplains-ds` | `greatplains-ds.properties` | Great Plains ERP integration |
| `order-ds` | `order-ds.properties` | Order management datasource |
| `request-ds` | `request-ds.properties` | Request management datasource |
| IBM MQ | `hostname=gppswmqu, port=1514, QM=REMIT_QM.UAT` | DEV JMS/MQ for DFAPI (points to UAT MQ) |
| CMS (xContent) | `http://d-na-app03.nam.wirecard.sys:9001/xContent` | Content management store |
| Strongbox | `http://d-na-app03.nam.wirecard.sys:9301/strong-box-xmlrpc` | Cryptographic key store |
| Director dispatch | `http://d-na-app01.nam.wirecard.sys:8080/service/dispatch.asp` | Internal routing service |
| Cambridge FX API | `https://beta.cambridgelink.com` | FX rate/booking API (3rd party) |
| KYC Portal | `https://app-activationportalapi-qa-westus2-001.azurewebsites.net` | Azure-hosted KYC service (QA endpoint used from DEV) |

## Schema
Configuration is in Java `.properties` files and Spring Boot `application.yml`. Key schema patterns:
- **`-ds.properties`** files: `driver`, `url`, `user`, `password` — JDBC datasource definitions
- **`applicationContext-*.properties`** files: Spring application context configuration (URLs, member IDs, feature flags)
- **`application.yml`** (CBTS): Full Spring Boot configuration with datasource, JPA, resilience4j, Cambridge API clients
- **Log4j config** (`log4j.xml`, `log4j.properties`): Logging configuration per service

## Sensitive Data Handling

**Credentials committed to source control (file locations, no values reproduced):**

1. **`config/d-na-app01/config/cbaseapp-ds.properties`** — SQL Server username and password for `cbaseapp` database
2. **`config/d-na-app01/config/jobsvc-ds.properties`** — SQL Server username and password for `jobsvc` database
3. **`config/d-na-app04/config/service/cbts/application.yml`** — SQL Server username and password for `CBTS` database; Mailgun SMTP password; Cambridge FX partner signature; Cambridge RCCL and Disney client API signatures and settlement account IDs
4. **`config/d-na-app01/config/oneplatform/applicationContext-oneplatform.properties`** — CBTS service username and password (same values as in application.yml); Google reCAPTCHA site key and secret key; KYC Microsoft OAuth client secret; Western Union static key
5. **`config/d-na-app01/config/dfapiclient/jms.properties`** — IBM MQ hostname, port, queue manager, queue names, and MQ principal credentials
6. **`config/d-na-app01/config/csa/applicationContext-csa.properties`** — CBTS service username and password; KYC Microsoft OAuth client secret

## Encryption
- JDBC connections: `tlsEnabled: true` configured for CBTS SQL Server connection; other datasource files do not show explicit TLS configuration
- Application SSL: Tomcat keystores configured via JAVA_OPTIONS (in UAT repo: `javax.net.ssl.keyStore=*.jks`) — same pattern applies to DEV
- Cambridge API: HTTPS with API signatures
- No at-rest encryption configuration visible in these property files

## Data Flow
```
External request → Tomcat (reads D:\c-base\config\ at startup)
  → SQL Server (cbaseapp, jobsvc) on d-na-db01
  → Director dispatch service (d-na-app01:8080)
  → CMS xContent (d-na-app03:9001)
  → Strongbox (d-na-app03:9301)
  → IBM MQ → DFAPI (remittance)
  → Cambridge FX API (CBTS) → international transfers
  → KYC Portal (Azure, QA endpoint)
  → SMS gateway (SAP Mobile Services — in UAT/prod notification configs)
```

## Quality
- Configuration files lack validation — incorrect values cause runtime failures only
- Multiple commented-out alternative configurations remain in files, increasing maintenance burden
- `ecount-config.xml` referenced in multiple files but not present in the config repo itself
- Some property values are duplicated across files (e.g., `cbtsClient.UserName`/`cbtsClient.Password` appear in both `applicationContext-csa.properties` and `applicationContext-oneplatform.properties`)

## Compliance Gaps
- **Multiple plaintext credentials committed to Git** — violates PCI DSS Requirement 8 (authentication management) and Requirement 6.3 (secure development practices); secrets should be in a vault (e.g., HashiCorp Vault, AWS Secrets Manager, Azure Key Vault)
- DFAPI MQ connection (`jms.properties`) shows DEV config pointing to a UAT queue manager — cross-environment data leakage risk
- KYC portal URL in DEV config points to QA Azure endpoint — cross-environment boundary violation
- `df.mq.credentials=` is blank in the committed file — password field present but empty, suggesting either test/no-auth or that the value is set elsewhere
