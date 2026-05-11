# api-config-repo — Solution Architect View

## Technical Architecture

### Repository Structure
```
api-config-repo/
├── .github/workflows/
│   ├── codeql.yml                    # CodeQL SAST (Java runner, weekly + push)
│   └── file_share_sync.yml           # Azure Storage File Share deployment pipeline
├── account-management/
│   └── application.properties        # Alternate/legacy AM API config path
└── config/
    └── config/                       # All service configs under this path
        ├── [service-directories]/    # Per-service property/XML/log config
        ├── IEFTRules/                # Spring XML bean rules for 60+ countries
        ├── postman/                  # Postman collections and QA environment
        └── [shared ds files]         # Shared JDBC datasource .properties files
```

### Config Loading Model
1. GitHub Actions pushes `config/` to Azure Storage File Share `east-soap-config`.
2. Application servers mount the file share at `D:/c-base/` (Windows on-prem) or `/c-base/` (Linux).
3. Java services read properties files from the mounted path on startup.
4. Spring XML beans (IEFT rules) are loaded via Spring's `ClassPathXmlApplicationContext` or direct file path references.
5. `ecount-config.xml` is the root Spring context that bootstraps the Director client for all services.

### Technology Stack (inferred from config)
| Layer | Technology |
|---|---|
| Application servers | Apache Tomcat (most services), WebLogic 9.0 (CSA legacy) |
| Framework | Spring Framework 4.x or 5.x XML IoC; Spring HTTP Invoker; some Spring Boot (circuit breaker config implies Resilience4j + Spring Boot) |
| JDBC | Microsoft JDBC Driver for SQL Server; jTDS (legacy); ODBC bridge (FDR ODS) |
| Messaging | IBM MQ (order/job/request); TIBCO EMS (notification/job) |
| Logging | Log4j2 (primary); Log4j 1.x (legacy, residual); Syslog (local) |
| Caching | Ehcache 3 (notification templates and mappings) |
| API protocols | SOAP/WSDL (primary external); Spring HTTP Invoker (internal); REST/JSON (emerging — FiServ, KYC, Mailgun) |
| Security | Visa JWE; JWE (custom DDA encryption); PGP (file encryption via Strongbox); mTLS (DFAPI JKS, TIBCO PKCS12); RSA Adaptive Auth; CitiMFA SOAP |
| Cloud | Azure Storage File Share; Azure App Configuration; Azure App Service (KYC portal); Azure Entra ID (OAuth) |

## API Surface

The Postman QA environment (`qa_environment.json`) and service properties reveal the following external-facing API endpoints (QA):

| API | Base URL | Protocol | Auth Method |
|---|---|---|---|
| Account Management API | `https://webservice-qa.northlane.com:4005/accountmanagementapiws/services/AccountManagementApiWebServices` | SOAP | Application ID / security registration |
| Account Management Payout API | `https://webservice-qa.northlane.com:4007/accountmanagementpayoutapiws/services/AccountManagementApiWebServices` | SOAP | Application ID |
| Client API (Instant Issue) | `https://webservice-qa.northlane.com:4005/clientapiws` | SOAP | Security registration |
| CSWS v1 | `https://webservice-qa.northlane.com:4005/CardManagement/services/AccountManagement` | SOAP | Application ID |
| CSWS v3 | `https://webservice-qa.northlane.com:4005/CardManagementV3/services/AccountManagement` | SOAP | Application ID |
| CSWS v3 Payout | `https://webservice-qa.northlane.com:4007/CardManagementPayoutV3/services/AccountManagement` | SOAP | Application ID |
| Debit API | `https://webservice-qa.northlane.com:4005/debitapiws/services/DebitService` | SOAP | Member ID |
| IVR Web Service | `https://webservice-qa.northlane.com:4005/ivrws/services` | SOAP | App Key |
| Card Notification (RESTful) | `https://webservice-qa.northlane.com:4005/cardnotification/Cardnotification/CardnotificationService` | REST? | Application ID |
| Accept Prechecks | `https://webservice-qa.northlane.com:4005/acceptprechecks/AcceptPrecheckService` | SOAP | - |
| Banker Service | `https://bankerapi.onbe.io/banker-service/Banker/bankerServiceAPI?wsdl` (prod-like) / `https://d-app03.nam.wirecard.sys:9009` (QA Postman) | SOAP WSDL | User ID / Application ID |
| Order Service | `https://ordersvc.onbe.io/order` | Spring HTTP Invoker | Internal |
| eCount Core | `https://ecountcoresvc.onbe.io/service` | REST/HTTP | Internal |
| FiServ Debit API | `http://localhost:8082` (sidecar) | REST/JSON | Internal |
| Strongbox XMLRPC | `https://strongboxxmlrpcsvc.onbe.io/strong-box-xmlrpc` | XML-RPC | Internal |

**Security methods registered in api-security.properties** (accountmanagementapi):
- updateProvisionStatus, updateAccountStatus, updateRegistration, addFunds, requestStatus, createAccount, issueCard, linkCard, stopPayment, setPin, assignPackage, createPackage, bulkOrder, withdraw, activationStatusInquiry, cardInquiry, cvvInquiry, activateCard, getBalance
- Feature flags: Return-Card-Number, Return-VISA-JWE, Return-Encrypted-Card, Return-CVV

## Security Posture (Hardcoded Secrets / Credentials — existence noted, values not reproduced)

The following files contain hardcoded credentials, keys, or sensitive tokens. **Values are not reproduced here.**

| File | Secret Type | Location |
|---|---|---|
| `accountmanagementapi/accountmanagementapi.properties` | Visa JOSE key and shared secret; KYC OAuth client secret; JWE encryption secret key | Lines 50–67 |
| `accountmanagementapi/api-security.properties` | Visa JOSE key and shared secret | Lines 36–37 |
| `account-management/application.properties` | Visa JOSE key and shared secret | Lines 75–76 |
| `CSWS/applicationContext-CSWS.properties` | JWE secret key and JWE secret token (hex); CBTS username and password | Lines 46–48, 115–116 |
| `oneplatform/applicationContext-oneplatform.properties` | Google reCAPTCHA secret key; KYC OAuth client secret; CBTS username and password; Western Union static key | Lines 103, 135, 116, 64 |
| `csa/applicationContext-csa.properties` | KYC OAuth client secret; CBTS username and password | Lines 62, 38–39 |
| `csa/build.properties` | WebLogic admin password | Line 4 |
| `cbaseapp-ds.properties` | SQL Server password (cbaseapp database) | Line 4 |
| `ecountcore-ds.properties` | SQL Server password (ecountcore database) | Line 4 |
| `ecount-db.properties` | SQL Server password (FDR ODS); SQL Server passwords for ecountcore, jobsvc, cbaseapp, ordersvc, repositorysvc, strongbox | Lines 13–20 |
| `greatplains-ds.properties` | SQL Server password | Line 4 |
| `jobsvc-ds.properties` | SQL Server password | Line 4 |
| `order-ds.properties` | SQL Server password | Line 4 |
| `request-ds.properties` | SQL Server password | Line 4 |
| `cbaseappsubaru-ds.properties` | SQL Server password | Line 4 |
| `service/notificationStrategy/mailer/deliveryChannel/smtp.email.channel.properties` | Mailgun SMTP password; Mailgun API key | Lines 8, 12 |
| `cardnotification/CardNotification.properties` | Sinch/SAP SMS password | Line 9 |
| `service/order/service.jms.tibco.properties` | TIBCO JMS SSL keystore password; JNDI security credentials | Lines 2, 12 |
| `service/prepaidJms/tibcojms.properties` | TIBCO JMS SSL password; P12 identity password; connection factory password | Lines 9–14 |
| `dfapiclient/httpclient.properties` | JKS keystore password | Line 9 |
| `service/edelivery/edelivery.properties` | eDelivery service password | Line 17 |
| `ivrws/ivrws.properties` | Application key (appKey) | Line 1 |
| `core2/ecountcore/ecountcore.properties` | Azure App Configuration connection string with embedded secret; FDR password hash | Lines 30, 14 |
| `core2/ecountcore/FDRConfig.properties` | FDR password hash | Line 2 |
| `postman/environments/qa_environment.json` | Bearer JWT token (expired at time of export — 2024-04-25) | Line 198 |

**Total count**: Credentials present in at least 24 configuration files across 18+ distinct secret types.

**PCI DSS Impact Assessment**:
- JWE secret key for DDA encryption stored in plaintext — violates PCI DSS Requirement 3.5 (protection of cryptographic keys).
- Visa JOSE shared secret stored in plaintext — violates PCI DSS Req 3.5 and Req 8 (key management).
- CVV inquiry is a defined API method — the system stores/returns CVV data, which is classified as PCI DSS SAD. Ensure CVV is never logged.
- DEBUG logging is active — risk of SAD appearing in log files (PCI DSS Req 3.2).

## Technical Debt

| Item | Severity | Notes |
|---|---|---|
| All secrets in plaintext property files in version control | Critical | Must be remediated before any production readiness. PCI DSS direct violation. |
| ODBC bridge for FDR ODS | High | `jdbc:odbc:CBASClntCATM` — requires Windows ODBC DSN, not containerisable. Legacy technology. |
| jTDS JDBC driver | High | `jdbc:jtds:sqlserver://` — jTDS is abandoned. Replace with Microsoft JDBC Driver 12.x. |
| WebLogic 9.0 application server (CSA) | High | EOL product. CSA needs migration to Tomcat / Spring Boot. |
| TIBCO EMS + IBM MQ dual-broker complexity | High | Operating two message brokers with overlapping function increases operational complexity. |
| Log4j 1.x residual config files | Medium | EOL library. All services should be confirmed on Log4j2 only. |
| Spring XML IoC (IEFT rules) | Medium | 60+ country XML bean definition files — difficult to test, version, or validate individually. |
| `com.citi.prepaid.*` package names | Medium | Legacy branding not yet updated post-acquisition. |
| Multiple overlapping log4j XML variants per service | Medium | CSWS has 3 variants; oneplatform has 5 variants. Operational confusion about which is active. |
| `ssl_enable_verify_host=false` (TIBCO) | High | Disables TLS hostname verification — man-in-the-middle attack vector. |
| `LocalLoggingLevel=DEBUG` in ecount-config.xml | High | DEBUG-level logging active — may capture CHD/PII in logs. |
| Production eDelivery endpoint active in stage config | High | Cross-environment contamination risk. |
| `migrated.bins=` (empty) | Medium | BIN migration incomplete — platform operating in a transitional state. |
| Delete-then-upload deployment (no atomic swap) | Medium | Config availability gap during deployment. |
| PR-triggered config deployment | Medium | Unmerged PRs can alter the shared QA environment. |
| `cbtsClient.Password` in plaintext (Cross-Border Transfer) | High | Long credential in plaintext; cross-border transfer service integration credentials exposed. |
| Duplicate config directories (account-management/ root vs config/config/accountmanagementapi/) | Low | Unclear which path takes precedence; duplication creates drift risk. |
| `westernUnion.statickey` in plaintext | Medium | Static API key for Western Union integration hardcoded. |
| Backup config files committed (`clientzonebackup.properties`, `Backup - applicationContext-oneplatform.properties`) | Low | Old backup files clutter the repo and may contain stale/conflicting values. |
| `cbaseapp_Subaru_20080610` snapshot DB still referenced | Low | 2008 database snapshot configured as live datasource. |

## Gen-3 Migration Requirements

To migrate the services configured in this repository to a Gen-3 cloud-native architecture, the following changes are required to the configuration layer:

### 1. Secrets Management (Pre-requisite — must complete first)
- Move all credentials to Azure Key Vault or HashiCorp Vault.
- Remove all plaintext secrets from property files.
- Implement runtime secret injection via environment variables or Key Vault references.
- Rotate all secrets after migration (existing secrets must be considered compromised).

### 2. Config Format Migration
- Replace `.properties` files with Spring Boot `application.yml` / `application-{profile}.yml`.
- Implement Spring Cloud Config Server or Azure App Configuration for centralised, environment-aware config.
- Eliminate file-system path dependencies (`D:/c-base/`); use classpath or environment variable references.

### 3. Service Discovery Migration
- Replace proprietary Director service with Kubernetes service discovery (ClusterIP + DNS) or Consul.
- Eliminate `director.address` properties across all service configs.

### 4. Messaging Migration
- Replace TIBCO EMS and IBM MQ with a cloud-native broker: Azure Service Bus or Azure Event Hubs / Kafka.
- Rewrite JMS connection factories, queue names, and consumer configurations.

### 5. SOAP-to-REST Migration
- All Tier 1 APIs (accountmanagementapi, clientapi, CSWS, debitapi, ivrws, etc.) need REST/JSON API facades or full rewrites.
- Postman collections exist for all APIs — these can seed OpenAPI 3.x specifications.

### 6. IEFT Rules Migration
- Replace Spring XML bean definitions with code-based rule configuration (Java, Kotlin, or a rules engine such as Drools) or YAML-based country rule definitions.
- Implement automated unit tests for each country rule set.

### 7. Database Driver Standardisation
- Replace jTDS with Microsoft JDBC Driver 12.x across all datasource configs.
- Replace ODBC FDR ODS access with a modern REST API or JDBC connection (requires FDR / processor coordination).

### 8. Logging Standardisation
- Standardise on Log4j2 (or Logback via Spring Boot) with structured JSON output.
- Remove all Log4j 1.x configurations.
- Disable DEBUG logging for production; enforce log masking for CHD/PII fields.
- Integrate with a centralised SIEM / log management platform (Azure Monitor, Splunk).

### 9. Environment Separation
- Create separate config branches or Config Server profiles for `dev`, `qa`, `uat`, `prod`.
- Eliminate production endpoint references from non-production config files.

### 10. CI/CD Hardening
- Add a secret-scanning step (e.g., GitHub Secret Scanning, Trufflehog) to the CI pipeline to prevent credential commits.
- Replace delete-then-upload deployment with atomic file share updates or Kubernetes ConfigMap rolling updates.
- Prevent PR-triggered deployments to shared environments.
- Add config validation pipeline steps (YAML linting, property key schema checks).

## Code-Level Risks

| Risk | Location | Severity |
|---|---|---|
| Visa JOSE key and shared secret hardcoded | `accountmanagementapi/api-security.properties`, `account-management/application.properties` | Critical — PCI DSS |
| JWE DDA encryption key hardcoded | `CSWS/applicationContext-CSWS.properties`, `accountmanagementapi/accountmanagementapi.properties` | Critical — PCI DSS |
| Azure App Config connection string (with secret) hardcoded | `core2/ecountcore/ecountcore.properties` | Critical |
| Google reCAPTCHA secret key hardcoded | `oneplatform/applicationContext-oneplatform.properties` | High — enables CAPTCHA bypass |
| TLS hostname verification disabled | `service/prepaidJms/tibcojms.properties` (`ssl_enable_verify_host=false`) | High — MitM attack vector |
| Debug logging enabled globally | `config/ecount-config.xml` | High — CHD/PII in logs risk |
| Production eDelivery endpoint active in stage | `service/edelivery/edelivery.properties` | High |
| ODBC bridge (Windows-only, non-containerisable) | `ecount-db.properties` | High |
| JWT Bearer token in Postman environment file | `postman/environments/qa_environment.json` | Medium — token is expired but sets a precedent for credential storage |
| `citi.crt` and `talxkeystore.jks` referenced as local filesystem paths | `oneplatform/applicationContext-oneplatform.properties` | Medium — certificate management tied to local files |
| WebLogic admin password in build.properties | `csa/build.properties` | Medium |
| CBTS long-form password in plaintext | `oneplatform/`, `csa/` properties files | High |
| Biocatch fraud scoring disabled (`biocatch.switch=N`) | `oneplatform/applicationContext-oneplatform.properties` | Medium — fraud control not active |
| Western Union static key hardcoded | `oneplatform/applicationContext-oneplatform.properties` | Medium |
| `ssnValue=[0-9]{9}` regex indicates SSN accepted as input | `APIValidation.properties`, `clientapi.properties` | Requires data minimisation review |
| Multiple backup/redundant config files committed to repo | Various | Low — operational risk of wrong file being used |
