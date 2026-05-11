# api-config-repo — Data Architect View

## Data Stores

The configuration files reference the following SQL Server databases, all accessed via JDBC with Microsoft SQL Server Driver or jTDS:

| DataSource Name | Database | Host (from config) | Notes |
|---|---|---|---|
| cbaseapp | cbaseapp | q-db01.nam.wirecard.sys:2431 | Core prepaid program/account master data |
| cbaseapp_Subaru | cbaseapp_Subaru_20080610 | q-db01.nam.wirecard.sys:2431 | Legacy Subaru program snapshot database |
| ecountcore | ecountcore | q-db02.nam.wirecard.sys (db02) | Core card ledger and transaction processing |
| ordersvc | ordersvc | q-db01.nam.wirecard.sys (db01) | Order and request processing |
| jobsvc | jobsvc | q-db01.nam.wirecard.sys:2431 | Job scheduling and batch tracking |
| repositorysvc | repositorysvc | q-db01.stage.ecount.com:1984 | Service registry / configuration repository |
| strongbox | Strongbox | q-db02.stage.ecount.com:2112 | PGP key and cryptographic material storage |
| greatplains (etest) | etest | stagetransition/stage1a1 | GP ERP integration for payroll/finance |
| fdrODS | CBASClntCATM (ODBC) | N/A — ODBC DSN | FDR card processor ODS (ODBC, legacy) |
| banker | banker | (resolved via WSDL/service) | Fund authorisation data |

Non-relational / messaging data stores:
- **IBM MQ**: `Q_NA_MQ_HA` queue manager on `Q-MQ01:51516` — order submission, job agent, and notification queues.
- **TIBCO EMS**: `gtstibemsuat.nam.nsroot.net:50643` — `PrepaidJMS_159547` account — notification events, messages, job workflow.
- **Azure App Configuration**: `appcs-shared-qa-ss.azconfig.io` — centralised FiServ/debit configuration key-value store (connection string present in ecountcore.properties).
- **Azure Storage File Share**: `east-soap-config` on `ecntqastorgage` — the deployment target for this entire config repository.
- **Mailgun**: API-based transactional email store (domain `mail.mypaymentvault.com`).
- **Strongbox (PGP)**: File-system PGP key storage under `/c-base/runtime/strongbox/`.

## Schema & Tables

Tables referenced in monitor health-check SQL queries (confirming schema existence):

| Table | Database | Purpose |
|---|---|---|
| order_detail | ordersvc | Order records with primary key `id` |
| request_detail | ordersvc | Request/transaction records |
| job_account_map | jobsvc | Maps ecount IDs to job runs |
| fdr_profile_symbols | ecountcore | FDR card processor profile symbol table |
| program_promotion | cbaseapp | Program-to-promotion mapping |
| sch_job_exec_status | jobsvc | Scheduler job execution status (via stored procs) |
| schedule | jobsvc | Job schedule definitions |
| schedule_history | jobsvc | Historical schedule changes |

Stored procedures referenced in jobscheduler.properties confirm a SQL Server stored-procedure-centric design pattern (`dbo.SCH_PROC_*`).

## Sensitive Data Handling

The following categories of sensitive data are handled by the configured services:

| Data Type | Evidence | PCI / Regulatory Classification |
|---|---|---|
| Primary Account Number (PAN / DDA) | `accountNumberValue=[0-9]{16}` regex; `account-management-api_API-AccountNumber` in Postman QA env; `jwe.encryptDDA=Y` flag | PCI DSS SAD/CHD |
| CVV / CVC | `cvvValue=[0-9]{3,4}` regex; `returnCVV` security feature flag; `cvvInquiry` API method | PCI DSS SAD |
| PIN | `newPinValue=[0-9]{4}` regex; `setPin` API method; Strongbox used for PIN storage | PCI DSS SAD |
| SSN | `ssnValue=[0-9]{9}` regex in APIValidation.properties and clientapi.properties | GLBA PII |
| Bank Account / Routing Number | `routing_numberValue=[0-9]{9}`; `account_numberValue=[0-9]{4,17}` | GLBA / Reg E PII |
| Full Name | `firstNameValue`, `account_holder_nameValue` regexes | PII |
| Date of Birth | `clientapi.regexp.dob=[0-9]{8}` | PII |
| Email Address | Stored and transmitted; domain-restriction rules applied | PII / GDPR |
| Phone Number | `phoneNAValue` and `phoneValue` regexes | PII |
| KYC Data | OAuth tokens issued to KYC portal; provision/KYC status addenda fields | GLBA / GDPR |

## Encryption & Protection

### Implemented Controls (as configured)
- **Visa JWE**: Feature flags `Return-VISA-JWE` and `Return-Encrypted-Card` in api-security.properties indicate Visa JSON Web Encryption for card number return to client.
- **DDA JWE Encryption**: `jwe.encryptDDA=Y` configured across CSWS, accountmanagementapi, and account service. JWE secret key and expiration time (180 seconds) are externalised — however, the secret key value is stored in plaintext in these config files (see Security Posture in File 05).
- **PGP Encryption**: Strongbox service manages PGP key pairs stored under `/c-base/runtime/strongbox/encryptPGP` and `decryptPGP`. `httpCryptoService` at `cryptokeysvc.onbe.io` supports PGP key operations.
- **DFAPI TLS/mTLS**: DFAPI client uses a JKS keystore (`dfapi.jks`) with a certificate for `*.northlane.com` (Wirecard North America). Keystore password is stored in plaintext in httpclient.properties.
- **TIBCO EMS TLS**: PKCS12 identity file (`PrepaidJMS_159547.p12`) with SSL trusted certs (`entrust_root_dev.cert.pem`). SSL password stored in plaintext in tibcojms.properties. `ssl_enable_verify_host=false` disables hostname verification — a significant TLS security weakness.
- **FDR Password Hash**: `fdr.passwordHash` in FDRConfig.properties is stored as a hex string (not plaintext), suggesting a legacy hash, but the algorithm is not documented in config.
- **Azure App Configuration**: Managed identity client ID and connection string (with secret) present in ecountcore.properties.
- **Google reCAPTCHA**: Site key and server-side secret key stored in plaintext in oneplatform properties.

### Missing Controls / Gaps
- Database passwords for cbaseapp, ecountcore, ordersvc, requestsvc, jobsvc, greatplains are all stored in plaintext in `*-ds.properties` files.
- JWE secret key (`jwe.secretKey`) stored in plaintext — not retrieved from a secrets vault.
- Mailgun SMTP password and API key stored in plaintext.
- SMS service (Sinch/SAP) username and password stored in plaintext.
- CBTS (Cross-Border Transfer Service) username and password stored in plaintext.
- Western Union static key stored in plaintext.
- Azure App Configuration connection string (with embedded secret) stored in plaintext.

## Data Flow

```
Cardholder / Client API Consumer
        |
        v
accountmanagementapi / CSWS / clientapi / debitapi / ivrws
        |
        v
Order Service (ordersvc.onbe.io)  ←→  IBM MQ / TIBCO EMS (JMS)
        |
        v
ecountcore (core ledger)  ←→  FDR Card Processor (ODS via ODBC / queue FDR.ODS.TRM.QUEUE)
        |                              |
        v                              v
Strongbox (PIN/key vault)        FiServ Debit API (card issuance)
        |
        v
Banker Service  ←→  GreatPlains DB (fund accounting)
        |
        v
Notification Service  →  Mailgun (email) / Sinch-SAP (SMS)
        |
        v
Job Scheduler  →  Autofile Service (bulk disbursements)
        |
        v
DFAPI Client  →  Citi DFAPI SOAP (wire/ACH international)
```

Cardholder-facing portals (oneplatform, clientzone, CSA, op508, enroll) sit above the API layer and consume the same order/account services. The eDelivery service connects to a Citi eDelivery SOAP endpoint for electronic statement delivery.

## Data Quality & Retention

- **Monitoring probes** (`service.monitor.properties`, `cz/monitor.properties`) perform `SELECT top 1` row-existence checks on key tables — confirming a basic liveness-check approach but no data quality measurement framework is configured here.
- **Inventory expiry**: `cardExpiryEnable=true` and `autoReorderEnable=true` in InventoryMgmt.properties indicate automatic reorder and expiry lifecycle management for physical card stock.
- **Database timeouts**: Default JDBC timeouts are configured at 600 seconds (10 minutes) for most databases; jobsvc uses 300 seconds. JDBC SQL timeouts for job services are 40 seconds (`jdbc.sqltimeout=40`).
- **No data retention or archival policy** is visible in the configuration files. Retention rules would reside in application code or database schemas not present in this repo.
- **Backup configuration**: `cbaseappsubaru-ds.properties` references a dated snapshot database (`cbaseapp_Subaru_20080610`), suggesting backup/snapshot databases are given their own datasource entries rather than being managed through a backup framework.

## Compliance Gaps

| Gap | Detail | Regulatory Concern |
|---|---|---|
| Plaintext secrets in Git | Database passwords, JWE keys, API keys, OAuth secrets, SMTP passwords all stored in `.properties` files committed to version control | PCI DSS Req 3.5 (protection of keys), Req 8.3 (access control) |
| TLS hostname verification disabled | `ssl_enable_verify_host=false` in TIBCO JMS SSL config | PCI DSS Req 4.2 (strong cryptography in transit) |
| ODBC legacy FDR connection | `fdrODSDS.url=jdbc:odbc:CBASClntCATM` using hardcoded plaintext credentials | PCI DSS Req 6.2 (secure development); potential unencrypted transport |
| Azure App Config connection string with secret | Full connection string including `Secret=` stored in property file | PCI DSS Req 3.5; Azure security baseline |
| OFAC screening limited to email domain suffix | Not a full SDN list integration | OFAC compliance gap for non-email-based identity |
| Production eDelivery endpoint in stage config | `edelivery.properties` active config points to `edvap1p` (production) | Risk of test data reaching production systems |
| No field-level encryption at rest for PAN | Config shows JWE for card number *return* and *in transit*, but no evidence of at-rest database column encryption configured here | PCI DSS Req 3.5 |
