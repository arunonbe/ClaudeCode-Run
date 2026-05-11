# Data Architect View — CONFIG_qa

## Data Stores Configured

| Database / Store | Connection | Notes |
|-----------------|------------|-------|
| `cbaseapp` (SQL Server) | `jdbc:sqlserver://q-db01.nam.wirecard.sys:2431;databaseName=cbaseapp` | Primary app DB (port 2431 vs DEV's 2232) |
| `cbaseappsubaru` (SQL Server) | `cbaseappsubaru-ds.properties` | Subaru-specific app DB |
| `jobsvc` (SQL Server) | `jobsvc-ds.properties` | Job/scheduler database |
| `ecount-db` | `ecount-db.properties` | eCount core database |
| `ecountcore-ds` | `ecountcore-ds.properties` | eCount datasource |
| `greatplains-ds` | `greatplains-ds.properties` | Great Plains ERP |
| `order-ds` | `order-ds.properties` | Order management |
| `request-ds` | `request-ds.properties` | Request management |
| `webcertomaha-ds` | `webcertomaha-ds.properties` | WebCert/Omaha datasource |
| IBM MQ | `dflnxswmqu.nam.wirecard.sys:1414`, QM=`WLDF_UAT_QMGRS` | DFAPI remittance queue (different from DEV) |
| CMS (xContent) | `https://login-qa.northlane.com:443/xContent` | QA CMS via branded URL |
| CBTS | `http://q-na-app08.nam.wirecard.sys:9443/cross-border-transfer-service` | QA CBTS instance |
| BioCatch | `https://api-osiristest.us.v2.customers.biocatch.com` | QA fraud scoring API |
| KYC Portal | `https://app-activationportalapi-qa-westus2-001.azurewebsites.net` | Azure QA KYC |
| Cambridge FX (via CBTS) | `https://beta.cambridgelink.com` | Same beta endpoint as DEV |
| Strongbox | XML-RPC on internal app server | Crypto key service |
| Director | `http://ppnaut.nam.wirecard.sys:8080/service/dispatch.asp` | QA Director |

## Schema
Same file structure as DEV: `-ds.properties` for datasources, `applicationContext-*.properties` for Spring context, `application.yml` for Spring Boot services. QA additionally has `ecount-config.xml` present in the config folder (not found in DEV).

## Sensitive Data Handling

**Credentials committed to source control (file locations, no values reproduced):**

1. **`config/q-na-app01/config/cbaseapp-ds.properties`** — SQL Server username and password for cbaseapp (`gentran`/`gentran`)
2. **`config/q-na-app01/config/jobsvc-ds.properties`** — SQL Server credentials
3. **`config/q-na-app01/config/oneplatform/applicationContext-oneplatform.properties`**:
   - CBTS service username and password
   - Google reCAPTCHA site key and secret
   - KYC Microsoft Azure AD OAuth client secret
   - Western Union static key
   - BioCatch customer ID (test)
4. **`config/q-na-app01/config/csa/applicationContext-csa.properties`** — CBTS credentials, KYC client secret
5. **`config/q-na-app01/config/dfapiclient/jms.properties`** — IBM MQ hostname, port, channel, queue manager, queue names; `df.mq.principal=prepaid` (blank password)
6. **`config/q-na-app01/config/cardnotification/CardNotification.properties`** — SAP Mobile Services SMS gateway username and password
7. Multiple `*-ds.properties` files — SQL Server credentials for each datasource

## Encryption
- CMS accessed via HTTPS (`https://login-qa.northlane.com:443`) — improvement over DEV's HTTP
- CBTS accessed via HTTP in QA (not HTTPS as in DEV's `application.yml`) — potential regression
- TLS configuration handled at Tomcat/JVM level via JAVA_OPTIONS keystore/truststore

## Data Flow
```
QA request → Tomcat (D:\c-base\config\) → SQL Server (q-db01:2431)
  → Director (ppnaut:8080) → CMS (login-qa.northlane.com)
  → IBM MQ (dflnxswmqu:1414) → DFAPI remittance
  → CBTS (q-na-app08:9443) → Cambridge FX (beta)
  → BioCatch fraud scoring (test API)
  → KYC Portal (Azure QA)
  → SAP SMS gateway (UAT endpoint)
```

## Quality
- QA has more datasource configurations than DEV (ecount-db, greatplains, webcertomaha) — QA config is more complete/production-like
- `ecount-config.xml` is present in QA config folder (missing from DEV)
- `cz/clientzonebackup.properties` present — backup config file suggests manual config management practices

## Compliance Gaps
- Multiple plaintext credentials in source control — same pattern as DEV
- `cbaseapp.user=gentran` / `cbaseapp.password=[REDACTED — rotate immediately]` — trivially guessable SQL Server credentials committed
- IBM MQ credentials committed
- SMS gateway credentials committed (SAP Mobile Services)
- CBTS service credentials committed (same values as DEV — password reuse across environments)
- KYC client secret same value as DEV — environment-shared secret (not environment-isolated)
- `df.mq.credentials=` blank — unclear if authentication is disabled or managed separately
