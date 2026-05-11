# MASTER SOLUTION ARCHITECT VIEW — Onbe 363-Repo Estate
*(Generated: 2026-05-08 | Source: 363 repositories across 15 business domains)*

---

## 1. Executive Summary

### Code-Level Security Posture

The estate-wide analysis of 363 repositories across 15 business domains surfaces **29 P0 findings**, **74+ P1 findings**, and **100+ P2 findings** with file:line precision. These are not theoretical risks inferred from dependency graphs — they are confirmed code paths where sensitive data is written to cleartext, authentication is bypassed, or credentials are permanently committed to version history.

**The most dangerous individual vulnerabilities are:**

1. **director-svc_SVC `/dispatch.asp`** — zero-auth XML-RPC credential broker returning all platform database passwords to any caller on the internal network (PCI DSS Req 7, 8 simultaneous violation).
2. **DS_DB_ecountcore `fdr_card_account_detail.cv_code`** — CVV/CVC2 stored post-authorization in the core card database, the most direct and unambiguous PCI DSS Req 3.3.1 violation in the estate.
3. **crypto-service_SVC `ExternalCommandsHelper.java:81`** — OS command injection via string concatenation in a key-management service with no authentication whatsoever.
4. **recipient-screening-api `SecurityConfig.java:15-20`** — `anyRequest().permitAll()` on the OFAC enforcement point, allowing any internal caller to inject fake sanctions approvals or fabricate blocks against legitimate recipients.
5. **om-payment-api `JwtSecurityValidator.java:57`** — `return true` unconditionally; all payment operations (PAN retrieval, CVV retrieval, account creation) accessible without credentials.
6. **emboss-extract_LIB** — PAN transmitted to card bureau (NDM/Connect:Direct) as cleartext XML before any encryption layer.
7. **infrastructure repo** — Titan PROD SFTP private key + passphrase `n0ty0u` committed; controls the card emboss/personalisation data channel.
8. **cbts-client_LIB / rsa-mfa_LIB** — JVM-global TLS bypass via trust-all `X509TrustManager`; affects all HTTPS calls in cross-border-transfer-service and every MFA transaction.

### Technical Debt Load Blocking Gen-3

The Gen-3 NexPay/OnePlatform platform cannot be safely promoted to live payment traffic until three structural blockers are resolved:

1. **Saga compensation stubs**: Both nexpay-order-orchestrator and nexpay-recipientorchestrator-svc implement `compensateCardIssuance()` and `compensateRecipientCreation()` as log-and-return no-ops. Any saga failure after card issuance creates an uncompensated financial instrument with no automated reversal path — a direct Reg E violation.
2. **Authorization disabled on payment APIs**: om-payment-api (JwtSecurityValidator always returns true), recipient-screening-api (permitAll), and nexpay-config-svc (no Spring Security) are all in the CDE. No authenticated payment operation can be considered secure while these configurations are live.
3. **Credentials committed to production-branch YAML**: nexpay-ordervalidator-svc (`application.yaml`) contains a live Azure App Configuration connection string and OAuth2 client secret; stand-in-processing-api (`.env`) contains a live Azure App Config access key. Both grant write access to shared configuration stores and have been in version history since first commit.

The Gen-1/Gen-2 estate carries an additional **36–48 month** modernization backlog driven by EOL frameworks (Struts 1.3.8, Axis 1.4, Spring 2.x, Java 5/6 compile targets, Quartz 1.6.3, XStream 1.3.1, Log4j 1.x), an all-XML-RPC transport bus with no authentication, and an infrastructure estate where Git repositories serve as the primary runtime secrets store for production payment systems.

**Total estate: approximately 800,000 hours of deferred remediation and modernization work across all severity tiers.** The P0/P1 security backlog alone represents 60–90 engineering-days of focused remediation before the estate can pass a PCI DSS v4.0.1 QSA assessment without material findings.

---

## 2. Top 40 Code-Level Security Findings (P0 Complete + P1 Sample)

The following table covers all confirmed P0 findings across all 15 domains, plus the highest-severity P1 findings. All citations are grounded in the domain synthesis files.

| Rank | Domain | Repo | Vulnerability | File:Line | CVSS/Severity | Regulation | Priority |
|---|---|---|---|---|---|---|---|
| 1 | D01/D06/D08 | director-svc_SVC | `/dispatch.asp` returns all platform credentials to any caller; no authentication on XML-RPC dispatch | `dispatch.asp` (endpoint); `DirectoryImpl.get()` (no auth check) | 10.0 / Critical | PCI DSS Req 7, 8 | P0 |
| 2 | D10 | DS_DB_ecountcore | CVV/CVC2 in `fdr_card_account_detail.cv_code` post-authorization; `util_update_cvcode` uses `WITH ENCRYPTION` (obfuscation) | `fdr_card_account_create` INSERT + `cv_code` column | 10.0 / Critical | PCI DSS Req 3.3.1 | P0 |
| 3 | D09 | crypto-service_SVC | OS command injection via string concatenation in PGP key-removal operation; no application-layer auth on endpoint | `ExternalCommandsHelper.java:81` | 9.8 / Critical | PCI DSS Req 6.2.4 | P0 |
| 4 | D03/D05/D11 | recipient-screening-api | `anyRequest().permitAll()` + CSRF disabled — OFAC enforcement point fully unauthenticated; webhook injection can block/unblock any cardholder account | `SecurityConfig.java:15-20` | 9.8 / Critical | PCI DSS Req 7, 8; OFAC | P0 |
| 5 | D04/D11 | om-payment-api | `JwtSecurityValidator.java:57` returns `true` unconditionally; all payment ops (PAN, CVV, account creation, addFunds, withdraw) unauthenticated | `JwtSecurityValidator.java:57`; `ApiSecurityConfiguration` excluded from Spring Boot | 9.8 / Critical | PCI DSS Req 7.2 | P0 |
| 6 | D01 | emboss-extract_LIB | PAN transmitted to card bureau as cleartext XML before NDM/Connect:Direct encryption layer | `emboss-extract_LIB` output generation | 9.8 / Critical | PCI DSS Req 3.5.1 | P0 |
| 7 | D12 | infrastructure | Titan PROD SFTP private key + passphrase `n0ty0u` committed to Git; controls card personalisation data channel | `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private`; `key.txt` | 9.8 / Critical | PCI DSS Req 3.5, 8.3.1 | P0 |
| 8 | D02/D05/D13 | cbts-client_LIB / rsa-mfa_LIB | JVM-global TLS bypass: trust-all `X509TrustManager`, `SSLContext.setDefault()` — all HTTPS calls in cross-border-transfer-service and MFA operations exposed to MITM | `CBTSClient.java:126-151`; `TrustAllSSLSocketFactory.java:79-81` | 9.8 / Critical | PCI DSS Req 4.2.1 | P0 |
| 9 | D05 | secure-data_LIB | `GET /getData/{refId}` — unauthenticated vault secret endpoint; any caller retrieves any stored secret by reference ID | `SecureController.java` (no auth annotation) | 9.8 / Critical | PCI DSS Req 7, 8 | P0 |
| 10 | D05 | DS_DB_strongbox | RSA master key co-located with ciphertext in same SQL Server database; `SbGetAsymmetricKey.java:23-25` returns full private key as plaintext SQL output parameter | `SbGetAsymmetricKey.java:23-25`; `SbGetSymmetricKey.java:22-25` | 9.8 / Critical | PCI DSS Req 3.6.1 | P0 |
| 11 | D10 | DS_DB_GP_emeam / DS_DB_GP_emxn | TDE disabled on databases containing SSN and GDPR Art. 9 personal data | Database-level configuration | 9.5 / Critical | PCI DSS Req 3.5; GDPR Art. 9; GLBA | P0 |
| 12 | D13 | wirecard_sg-bank-agent_LIB | RSA private key (CIMB SFTP), PGP private key `0xCE5B683F-sec.asc`, AWS access key `[REDACTED — rotate immediately]`, AWS secret key, PGP passphrase `wirecard` — all four credential types committed | `application.yml:34-61, 154`; `gradle.properties:31-32`; `sgba-pgp/0xCE5B683F-sec.asc` | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 13 | D09 | stand-in-processing-api | Azure App Configuration live access key committed to `.env` | `.env:2` | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 14 | D04 | scheduler_WAPP | Unauthenticated Spring HTTP Invoker endpoint (`/scheduler.service`) with no class filter — Java deserialization RCE; DB credentials in `.env` files | `web.xml` (no `<security-constraint>`); `.env:7-14` | 9.8 / Critical | PCI DSS Req 7, 8.3.1; CVE-2015-4852 class | P0 |
| 15 | D15 | webapp-parent-pom_PARENT | Enforces Java 1.6 + Struts 1.3.8 (EOL RCE CVEs) on all inheriting web applications; no override mechanism at child level | `pom.xml:24-40` (properties); `:104-141` (struts profile) | 9.8 / Critical | PCI DSS Req 6.3.3 | P0 |
| 16 | D13 | cross-border-transfer-service_SVC | PGP private key `0x6392B27D-sec.asc` + SMTP API key + Cambridge client signatures + DB password committed to QA YAML | `application-qa.yml:41,71,281-384`; `pgp/0x6392B27D-sec.asc` | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 17 | D11/D03 | nexpay-ordervalidator-svc | Azure App Config connection string + OAuth2 client secret committed to source in dev-test and integration profiles | `application.yaml:126-127` (App Config key); `:179` (OAuth2 secret) | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 18 | D04 | manage-payment-rest-api | Visa API credentials committed to source in Dapr secrets file | `dapr-components/dapr-secrets.json` | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 19 | D07 | mailgun-event-tracker | Mailgun API key committed to `application.properties` | `application.properties:18` | 9.0 / Critical | PCI DSS Req 8.3.1 | P0 |
| 20 | D08 | xml-rpc_LIB | No authentication on RPC dispatch; HTTP headers directly control which Spring bean is invoked; reflection-based invocation with no allowlist or method signature validation | `XmlRPCServletHelper.java:230-341` (dispatch); `:270-278` (bean key from headers) | 9.8 / Critical | PCI DSS Req 7, 8.3.2 | P0 |
| 21 | D05 | strongbox-xmlrpc_SVC | RSA private keys returned as plaintext SQL Server output parameters; no auth on XML-RPC endpoints | `SbGetAsymmetricKey.java:23-25`; `SbGetSymmetricKey.java:22-25` | 9.8 / Critical | PCI DSS Req 3.6.1 | P0 |
| 22 | D12 | windows-scripts | SSN as plaintext CLI argument; commented example contains suspected real SSN `493025119` | `1099_ssn_update.vbs:18` | 9.5 / Critical | PCI DSS Req 3; GLBA | P0 |
| 23 | D07/D15 | request-file_LIB | CVV `@XmlElement` — marshalled to plaintext XML by JAXB; PAN at same location | `Cardtype.java:51-52` (CVV); `:43-44` (PAN) | 9.8 / Critical | PCI DSS Req 3.2.1, 3.3 | P0 |
| 24 | D06 | notification-requests-generator_LIB | Full cardholder PII (name, address, phone, email) logged at INFO to disk files and unencrypted Syslog UDP (`10.1.1.130:514`) | `NotificationRequestDetailsRowMapper.java:42-113` | 9.0 / Critical | PCI DSS Req 3.3, 4.2.1; GLBA | P0 |
| 25 | D02 | cross-border-transfer-service_SVC | JVM debug port 8000 exposed in `docker-compose.yml`; JDWP remote code execution vector on service holding Cambridge FX credentials | `docker-compose.yml` (JDWP port binding) | 9.8 / Critical | PCI DSS Req 6.3 | P0 |
| 26 | D02 | cross-border-transfer-service_SVC | Config server bootstrap password `s3cr3t` committed; invalidates all secrets distributed by the Spring Cloud Config Server | `bootstrap.yml` | 9.8 / Critical | PCI DSS Req 8.3.1 | P0 |
| 27 | D03 | enrollment_WAPP / oneplatform_WAPP | Struts 1.3.8/1.3.10 in active PCI CDE; CVE-2014-0114, CVE-2016-1181 (RCE via multipart), unpatched | `pom.xml` (both repos) | 9.8 / Critical | PCI DSS Req 6.3.3 | P0 |
| 28 | D03/D11 | nexpay-order-orchestrator / nexpay-recipientorchestrator-svc | Saga compensation stubs — `compensateCardIssuance()` and `compensateRecipientCreation()` log and return; no live rollback for failed financial instrument issuance | `SagaService.java` (both repos) | N/A / Critical | Reg E §1005.11; PCI DSS Req 6.2 | P0 |
| 29 | D10 | DS_DB_ecountcore | Plaintext PAN as stored procedure parameter `@card_number CHAR(16)` in `fdr_card_account_create`; captured by any active SQL monitoring tool | `fdr_card_account_create` SP definition | 9.5 / Critical | PCI DSS Req 3.4 | P0 |
| 30 | D01 | chargeback-engine_LIB | SQL injection via string concatenation + plaintext ODS credentials in committed properties file | `ChargebackHelper.java:60`; `ChargebackProcess.properties:13-14` | 8.8 / High | PCI DSS Req 6.2.4 | P1 |
| 31 | D05 | rsa-mfa_LIB | OTP tokens and phone numbers logged at INFO level; live OTP in logs enables MFA bypass within token validity window | `AuthenticationServiceImpl.java:871`; `:760-763` | 8.5 / High | PCI DSS Req 3 (SAD) | P1 |
| 32 | D10 | DS_DB_ordersvc / DS_DB_riskdb | SQL injection in stored procedures via dynamic SQL string construction | `app_func_build_achFundSql`; `app_func_build_ccFundSql` | 8.8 / High | PCI DSS Req 6.2.4 | P1 |
| 33 | D09 | nexpay-cardprocessor-svc | Saga compensation stubs — no live rollback for card issuance failures; `processorMetadata` JSONB may contain raw FIS PAN | `SagaService.java`; `card.processor_metadata` column | 8.5 / High | PCI DSS Req 3.4; Reg E | P1 |
| 34 | D13 | wirecard_test-utilities_LIB | PGP private key `0x6392B27D-sec.asc` in production main source (`src/main/resources`) compiled into published JAR; matches production Cambridge SFTP key | `src/main/resources/pgp/0x6392B27D-sec.asc` | 9.0 / Critical | PCI DSS Req 8.3.1 | P1 |
| 35 | D03 | nexpay-ivr-bff | Hardcoded SSN placeholder and card number in production stub controller exposed on external APIM | `FsCustomerInquiryController.java:55` | 8.5 / High | PCI DSS Req 3.3 | P1 |
| 36 | D14 | account-management-api_TESTING_AUTO / cs-api_TESTING_AUTO / selenium-framework-test | Real PANs (`5115531022041490`, `5445446554206695`, `5445446557563720`), CVVs, and SSNs in SOAP test fixtures permanently in git history | SOAP fixture XML files; `Registration.java` | 9.0 / Critical | PCI DSS Req 3.3, 3.4 | P1 |
| 37 | D04 | account-management-api_API | `CreateAccountService.java:221-226`: `validateAPISecurity()` and `testAPI()` commented out — security bypass for ClientZone requests with no documented justification | `CreateAccountService.java:221-226` | 8.8 / High | PCI DSS Req 7.2 | P1 |
| 38 | D06 | batch_LIB | CVV2 field in `PushtodebitTransactionVo` populated from Tabapay settlement CSV; no confirmed suppression before DB persistence | `PushtodebitTransactionVo.java:33` | 9.0 / Critical | PCI DSS Req 3.2.1 | P1 |
| 39 | D05/D04 | xsso_SVC | XStream deserialization without type allowlist on `TokenManagerServlet`; hardcoded DESede IV `"12345678".getBytes()`; default JKS keystore password `ecount` | `TokenManagerServlet.java:29-38`; `DESedeFactory.java:38-40`; `applicationContext-xSSO.properties:9-10` | 8.5 / High | PCI DSS Req 3.6, 8.3.6 | P1 |
| 40 | D15 | onbe-spring-boot | Insecure PRNG (`kotlin.random.Random`) used for password generation in Gen-3 SDK shared by all NexPay services | `TextUtils.kt:22` | 8.0 / High | PCI DSS Req 6.2.4 | P1 |

---

## 3. CVE Inventory (Critical/High CVSS)

| CVE | Technology | Version | CVSS | Repos Affected | Domains | Exploitability | Priority |
|---|---|---|---|---|---|---|---|
| CVE-2025-24813 | Apache Tomcat (partial PUT RCE) | 10.x | 9.8 | order_SVC (suppressed in `.trivyignore` without formal risk acceptance) | D04, D09 | High — partial PUT deserialization; no auth required | P0 — patch immediately |
| CVE-2021-39144 / CVE-2021-29505 | XStream | 1.3.1 / 1.4.12 | 9.8 | batch_LIB (1.3.1), job_LIB (1.3.1), clientzone_WAPP (1.4.12), xsso_SVC (various) | D04, D06, D08 | High — deserialization gadget chains; exploitable wherever XStream processes attacker-influenced XML | P0 — upgrade to 1.4.21+ |
| CVE-2024-52316 | Apache Tomcat | 10.x | 9.8 | crypto-service_SVC, banker_API (suppressed) | D04, D09 | High — authentication bypass | P0 — patch immediately |
| CVE-2024-50379 | Apache Tomcat | 10.x | 9.8 | crypto-service_SVC (suppressed), scheduler_WAPP | D04, D09 | High — RCE via race condition | P0 — patch immediately |
| CVE-2019-17571 | Log4j | 1.2.x | 9.8 | autoclaim-split-svc_LIB, batch_LIB, cancel-tx, notification-requests-generator_LIB, enrollment_WAPP, ivrintegration_API, oneplatform_WAPP, clientzone_WAPP | D01, D03, D04, D06, D07 | High — deserialization via SocketServer appender; EOL, no patch available | P0 — replace Log4j 1.x with SLF4J+Logback |
| CVE-2014-0114 / CVE-2016-1181 / CVE-2016-1182 | Apache Struts | 1.3.8 / 1.3.10 / 1.2.7 | 9.8 | enrollment_WAPP, oneplatform_WAPP, clientzone_WAPP, csa_WAPP, workbench_WAPP, rebate-inquiry_WAPP | D01, D03, D04 | High — ClassLoader manipulation RCE, multipart RCE; EOL, no patch available | P0 — WAF interim; full migration required |
| CVE-2019-13990 / Quartz 1.x | Quartz Scheduler | 1.6.3 | 9.8 | notification-framework_SVC, scheduler_WAPP | D04, D06, D07 | High — Java serialization deserialization via job store; EOL | P0 — upgrade to Quartz 2.3.2+ |
| CVE-2012-5783 | Apache Commons HttpClient | 3.x | 8.8 | xml-rpc_LIB, xml-rpc-clients_LIB, enrollment_LIB (StrongBoxClient), Gen-1 services (all) | D01, D02, D03, D08 | High — no SSL hostname verification by default; MITM on all HTTPS calls | P0 — replace with HttpClient 5.x |
| sqljdbc 1.1 / TLS 1.0 only | Microsoft SQL Server JDBC | 1.1 | 8.5 | ecore-batch_LIB, reminder-notification_LIB | D07, D08 | High — TLS 1.0 is prohibited by PCI DSS since 2018; MITM on all DB connections | P0 — upgrade to mssql-jdbc 12.x |
| CVE-2024-47072 | XStream | Various | 8.0 | banker_API (suppressed), xsso_SVC (suppressed) | D04, D05 | Medium — deserialization; compensating controls claimed but not verified | P1 — upgrade or formally risk-accept |
| CVE-2022-40151 | XStream | 1.4.12 | 8.8 | clientzone_WAPP | D04 | High — active deserialization RCE; not suppressed | P1 — upgrade to 1.4.21+ |
| CVE-2015-6420 | commons-collections | 3.2 | 8.8 | clientzone_WAPP | D04 | High — the original gadget chain CVE; not suppressed | P1 — upgrade to 3.2.2 |
| CVE-2017-7525 | jackson-mapper-asl | 1.9.2 | 8.8 | clientzone_WAPP | D04 | High — polymorphic deserialization; not suppressed | P1 — replace with jackson-databind 2.x |
| CVE-2019-0227 | Apache Axis | 1.4 | 8.5 | cambridge-auth-service_LIB, account-management-api_API, account-management-payout_API, banker_API | D02, D04, D05, D13 | High — SSRF via SOAP; EOL since 2006 | P1 — replace with CXF or Spring-WS |
| CVE-2020-10683 | dom4j | Various | 7.5 | crypto-service_SVC (suppressed) | D09 | Medium — XXE; XML Spring configuration context | P2 — upgrade dom4j |

---

## 4. Authentication & Authorization Failures

### Severity: Critical — No Authentication (OFAC / Payment / Key Management)

**recipient-screening-api (`SecurityConfig.java:15-20`):** `anyRequest().permitAll()` with CSRF disabled. Both the synchronous OFAC screening endpoint (`POST /api/v1/screening/request`) and the sanctions webhook (`POST /sanction/webhook`) are fully unauthenticated. A spoofed `DECLINED` webhook triggers permanent blocking of all beneficiary accounts linked to a targeted DDA. A spoofed `APPROVED` webhook unblocks a sanctioned recipient. This is a live OFAC enforcement bypass. **Affects Domains 03, 05, 11.**

**om-payment-api (`JwtSecurityValidator.java:57`):** `return true;` — the entire JWT validation block (lines 31-57) is commented out. `ApiSecurityConfiguration` is excluded from Spring Boot auto-configuration. Every payment operation — `GET /v1/accounts/cvv` (SAD retrieval), `GET /v1/accounts/card` (PAN retrieval), `POST /v1/accounts`, `addFunds`, `withdraw`, `cardInquiry` — is callable without any credential. **Affects Domains 04, 11.**

**crypto-service_SVC (`/cryptokeysvc/httpCryptoService/HTTPCryptoService-httpinvoker`):** No application-layer authentication; no TLS. Any internal process can add or remove PGP keys used for card bureau file encryption. **Affects Domain 09.**

**scheduler_WAPP (`web.xml`):** No `<security-constraint>` on `/scheduler.service`. The Spring HTTP Invoker endpoint processes arbitrary Java object deserialization with no class filter — full RCE on a service managing card lifecycle and disbursement schedules. **Affects Domain 04.**

**strongbox-xmlrpc_SVC:** XML-RPC endpoints (`repositoryServiceRead/Write`, `encryptPGP`, `decryptPGP`) have no authentication. Any internal host can retrieve any named cryptographic key. **Affects Domain 05.**

**xsso_SVC:** `POST /tokenManagerServlet`, `/encryptOPTokenManagerServlet`, `/decryptOPTokenManagerServlet` — no authentication. Any caller can encrypt or decrypt SSO tokens, effectively impersonating any cardholder session. **Affects Domain 05.**

### Severity: Critical — Always-True Validators

**om-payment-api `JwtSecurityValidator.java:57`:** `return true` unconditionally (see above).

**stand-in-processing-api `SecurityConfig.java:29`:** `@Value("${sasi.dev.disable-security-filter:false}")` — a production code property that bypasses all authentication. If any deployment fails to set this property, authentication is disabled. **Affects Domain 09.**

**stand-in-processing-api `SecurityConfig.java:66-70`:** SOAP authentication failures return HTTP 200 rather than 401/403. Monitoring cannot detect authentication failures. Automated SOAP clients cannot distinguish success from auth failure. **Affects Domain 09.**

### Severity: High — Missing RBAC / Unauthenticated Admin Controls

**spring-refer-a-friend_WAPP (`SearchController.java:138`):** `?site_admin=maintenance` URL parameter puts the application in maintenance mode for all users with no authentication check. Cache management parameters are similarly unauthenticated.

**account-management-api_API (`CreateAccountService.java:221-226`):** `validateAPISecurity()` and `testAPI()` commented out for ClientZone request path — security bypass for a specific entry point with no documented justification.

**banker_API:** No `<security-constraint>` in `web.xml`. Axis SOAP servlet `/Banker/*` relies solely on `userId`/`applicationId` in the SOAP body — application-level identity claims with no cryptographic verification.

**nexpay-config-svc:** No Spring Security visible; actuator `env` endpoint exposed; V5 seed data in production migration path.

**issuing-classic-selfservice_WAPP:** IDOR in `block_global_deposit/models.py:49` and `change_usernames/models.py:30` — no server-side validation that a staff user's submitted DDA or username belongs to their authorized programme scope.

### Severity: High — Session / Token Management Gaps

**clientzone_WAPP:** `MultiFactorAuthenticationFilter` in `web.xml:202-230` entirely commented out — MFA not enforced on primary B2B portal login. `SsoUserUtil.java:119` sets `"DisablePasswordExpiration, DisableStrongPassword"` for Azure AD SSO users, disabling both password controls for all SSO-migrated portal users.

**oneplatform-react_WAPP:** JWT access tokens stored in `localStorage` — accessible to any XSS payload on the cardholder portal domain. `networkCall.js` logs full financial API responses to browser console.

**xsso_SVC:** No token expiry enforcement — tokens valid indefinitely once issued (`DecryptExternalTokenManagerServlet.java` validates timestamp format only, not freshness).

**nexpay-recipientweb-bff:** Password material placed in JWE payload (`JweHelper.java:122-139`) — unusual architectural pattern with single-key compromise risk.

---

## 5. Cryptography Assessment

### Key Management Failures — Keys in Git

The estate exhibits a pervasive pattern of cryptographic key material in version control that constitutes a fundamental secret management failure:

| Key Type | Repository | Location | Passphrase in Same Repo |
|---|---|---|---|
| RSA private key (CIMB SFTP) | wirecard_sg-bank-agent_LIB | `application.yml:34-61` | `application.yml:154` (`wirecard`) |
| PGP private key 0xCE5B683F | wirecard_sg-bank-agent_LIB | `sgba-pgp/0xCE5B683F-sec.asc` | Yes (`wirecard`) |
| PGP private key 0x6392B27D | cross-border-transfer-service_SVC | `pgp/0x6392B27D-sec.asc` | `application-qa.yml` |
| PGP private key 0x6392B27D | wirecard_test-utilities_LIB | `src/main/resources/pgp/` (compiled into production JAR) | Test source (`PGPUtilsTest.java:21`) |
| Logstash TLS private key | docker-logstash_INFRA_CONT | `pki/server.key` (baked into Docker image) | N/A |
| JKS keystore | cross-border-transfer-service_SVC | `config/server.jks` | Inline |
| Android release keystore | wirecard_mobile-payout-citi_LIB | `android/app/keystore/payoutnam_release.keystore` | Inline |
| Titan PROD SFTP key | infrastructure | `platform-certificates-keys/titan/PROD/sftp.northlane.com_Private` | `key.txt` (`n0ty0u`) |
| Harland QA SFTP key | infrastructure | `platform-certificates-keys/harland/QA/qa_private.ppk` | `key.txt` (`n0ty0u`) |

### Key Management Failures — Keys in Database Alongside Ciphertext

**DS_DB_strongbox (Domain 05/08):** RSA private keys and AES symmetric keys are stored in the same SQL Server database as the ciphertext they protect. A single stored-procedure call (`SbGetAsymmetricKey.java:23-25`, `SbGetSymmetricKey.java:22-25`) returns the full decryption chain in a single roundtrip. This is a fundamental architectural flaw in the vault design. PCI DSS Req 3.6.1 requires that key-encrypting keys are stored separately from the keys they protect. Interim fix: SQL Server Always Encrypted with Azure Key Vault column master key on `private_key` and `key_value` columns.

### Weak Algorithms

| Algorithm | Usage | Locations | Status |
|---|---|---|---|
| MD5 | Password hashing (no salt) | xsecurity_SVC `EcountMd5PasswordEncoder`, clientzone_WAPP `EcountMd5PasswordEncoder` | Cryptographically broken since 2004; rainbow tables trivially reverse all stored passwords |
| MD5 | Cambridge HMAC authentication | cambridge-auth-service_LIB `AppTest.java:91` (hardcoded); `algorithm` parameter has no guard | Algorithm downgrade risk; charset-dependent `getBytes()` adds cross-platform failure mode |
| SHA-1 | PAN hashing | ecountcore `core_card_master.card_hash`; `hashbytes('sha1', card_number)` | GPU SHA-1 rainbow attacks on known BIN ranges are feasible |
| 3DES/DESede | SSO token encryption | xsso_SVC `DESedeFactory.java`, strongbox-xmlrpc_SVC V1 cipher suite | NIST disallowed; fixed IV `"12345678"` eliminates all semantic security |
| RSA/ECB/NoPadding | Key wrapping | strongbox-xmlrpc_SVC V1+V2 | Textbook RSA; no semantic security (identical plaintext produces identical ciphertext) |
| RSA/PKCS#1 | SSO token RSA | xsso_SVC | Bleichenbacher-vulnerable |
| AES/ECB | Password encryption for Azure AD SSO | clientzone_WAPP `EncryptionUtil.java` (`Cipher.getInstance("AES")` defaults to ECB) | Deterministic; leaks plaintext patterns |
| DES, RC4, RC2 | Platform crypto library (public API) | xplatform-library_LIB (`DESCipher`, `RC4Cipher`, `RC2Cipher`) | All cryptographically broken; publicly callable from any Gen-1 service |

### TLS Bypass Patterns

- **JVM-global TLS bypass**: `cbts-client_LIB` (`CBTSClient.java:126-151`) calls `SSLContext.setDefault()` with trust-all `X509TrustManager`. Affects cross-border-transfer-service and global-deposit-batch — all HTTPS calls in those processes, not just CBTS API calls.
- **rsa-mfa_LIB**: `TrustAllSSLSocketFactory.java:79-81` uses `context.init(null, null, null)` — null TrustManager. All 13 MFA operations traverse this factory.
- **Commons HttpClient 3.x (CVE-2012-5783)**: `XMLRPCClient.java:36-43` — no `SSLSocketFactory` configured; hostname not verified by default. Affects all Gen-1 XML-RPC services.
- **`trustServerCertificate=true`**: Confirmed in production configs for recipient-screening-api (`appsettings.json:3-4`), manage-payment-rest-api, om-payment-api, mailgun-event-tracker, stand-in-recovery-service `DataSourceConfig`, and Automation_ClientZone JDBC URL.
- **TIBCO EMS `ssl_enable_verify_host=false`**: Notification messaging channel MITM-vulnerable (`tibcojms.properties` in api-config-repo).
- **AJP/1.3 cleartext**: All cardholder-facing web traffic (ClientZone, login, CSA portals) traverses the internal VNet via unencrypted AJP/1.3 from IIS to Tomcat.

### PRNG Weaknesses

**onbe-spring-boot `TextUtils.kt:22`**: `kotlin.random.Random` (deterministic PRNG seeded from system clock) used for password generation in the Gen-3 SDK. All Gen-3 services that call `randomPassword()` receive passwords with statistically predictable entropy. Must be replaced with `java.security.SecureRandom`.

**DPAPI machine-binding (Domain 10)**: `DS_ETL_warehouse` SSIS packages are protected with DPAPI bound to the account `NAM\nick.doan` and server `P-NA-DB11`. If either the account or the server is unavailable, all ETL encryption is irrecoverable — a business continuity failure affecting all analytical capabilities.

---

## 6. Injection Vulnerability Inventory

### SQL Injection

| Vulnerability | Location | File:Line | Attack Vector |
|---|---|---|---|
| SQL injection via string concatenation | chargeback-engine_LIB | `ChargebackHelper.java:60` | Chargeback input data directly controls WHERE clause |
| Dynamic SQL injection risk | ecountcore | `app_func_build_achFundSql`, `app_func_build_ccFundSql` | ACH/CC fund SQL built from potentially user-influenced input |
| SQL injection in stored procedures | DS_DB_ordersvc / DS_DB_riskdb | Dynamic SQL in stored procs | Input parameters without parameterized queries |
| SQL injection (WCF servlet) | atlys_WAPP | `wsAtlys.svc.cs:847` | `RelMgrId` parameter concatenated into SQL WHERE clause |
| SQL injection (utility class) | clientzone_WAPP | `SsoUserUtil.java:91` | String concatenation in Azure AD SSO utility |
| SQL injection pattern (test framework) | Automation_ClientZone | `SearchableAddendaSteps.java` | String-concatenated JDBC queries — unsafe code pattern regardless of input source |

### OS Command Injection

**crypto-service_SVC `ExternalCommandsHelper.java:81`:** PGP key-removal command built as a string (`"pgp --key-remove " + keyName + " --force"`) and passed to `Runtime.getRuntime().exec(cmd)` in String form. JVM StringTokenizer on Windows does not protect against shell metacharacters. An unauthenticated internal caller can achieve arbitrary OS command execution as the Tomcat service user. Fix: use `Runtime.exec(String[])` with isolated arguments and validate `keyName` against an alphanumeric-plus-PGP-UID-character allowlist.

### Java Deserialization / Spring HTTP Invoker / XStream RCE

| Vector | Location | File/Endpoint | Auth |
|---|---|---|---|
| Spring HTTP Invoker (no class filter) | scheduler_WAPP | `/scheduler.service` — `web.xml` missing `<security-constraint>` | None |
| Spring HTTP Invoker (no class filter) | crypto-service_SVC | `/cryptokeysvc/httpCryptoService/HTTPCryptoService-httpinvoker` | None |
| Spring HTTP Invoker | job-order-synchronization_LIB | Order Service calls — schema change causes silent ClassNotFoundException | Internal |
| XStream deserialization (no allowlist) | xsso_SVC | `TokenManagerServlet.java:29-38` | None |
| XStream deserialization (no allowlist) | batch_LIB, job_LIB | XStream 1.3.1 JMS message processing | Internal MQ |
| XStream deserialization (no allowlist) | clientzone_WAPP | XStream 1.4.12 (CVE-2022-40151) | Session |
| XStream deserialization | banker_API | `LoggingUtil.java:7` (`new XStream()` with no security config) | SOAP body |

### JNDI / Log4j 1.x

Log4j 1.x (CVE-2019-17571) present in: autoclaim-split-svc_LIB, batch_LIB, cancel-transaction-process_LIB, notification-requests-generator_LIB, enrollment_WAPP, ivrintegration_API, oneplatform_WAPP, clientzone_WAPP. Log4j 1.x SocketServer deserialization enables arbitrary code execution via JNDI lookups. EOL — no patch available.

### Path Traversal

**om-content-management-api:** `targetFilePath` from `XContentFileUploadRequest` passed directly to `containerClient.getBlobClient(targetFilePath)` in `GitHubAPIService.java` without path normalization. A caller can traverse outside the `xContent/recipient/` prefix to access arbitrary Azure Blob Storage paths. Fix: `Paths.get(targetFilePath).normalize()` with prefix check.

### SSRF

**scheduler_WAPP:** `callbackPath` stored as a string in Quartz DB (`QRTZ2_*` schema), issued as HTTP POST when triggers fire with no allowlist validation in `QuartzServiceProviderImpl`. An unauthenticated caller (the endpoint has no auth) can register any internal URL — SQL Server, Director service, Kubernetes metadata endpoint — as a callback target.

---

## 7. Technical Debt by Domain

| Domain | Estimated Debt Load | Primary Debt Type | Migration Blocker | Sprint Estimate |
|---|---|---|---|---|
| D01 — Card Program Management | Very High | Gen-0/1/3 four-layer coexistence; XML-RPC bus; SOAP/Axis; Spring HTTP Invoker | No unified API surface; no shared identity plane; no distributed trace context | 24–36 months |
| D02 — Disbursements & Payment Rails | Very High | No auth on XML-RPC; TLS bypass; EOL protocols (Axis, Commons HttpClient); zero test coverage | Protocol replacement requires coordinated consumer migration; SNAPSHOT binary coupling | 18–24 months |
| D03 — Recipient & Cardholder Experience | Very High | Struts 1 RCE in CDE; saga stubs; Gen-1 (Java 1.5-1.8) alongside Gen-3 (Java 25) | Struts migration; saga compensation; RecipientApp source acquisition | 18–30 months |
| D04 — Client Admin Portal | Very High | om-payment-api auth disabled; scheduler WAP Java deser RCE; Silverlight EOL; commons-collections RCE | Spring HTTP Invoker removal (Spring 6 incompatible); Axis SOAP replacement requiring partner coordination | 24–36 months |
| D05 — Authentication & Identity | Very High | Broken crypto (3DES, MD5, fixed IV); keys in DB co-located with ciphertext; no auth on StrongBox XML-RPC; OTP in logs | StrongBox vault redesign (SQL Always Encrypted required as interim); EOL Axis in rsa-mfa_LIB | 24–36 months |
| D06 — Order & Workflow Orchestration | Very High | XStream 1.3.1 RCE; CVV2 post-auth; Log4j 1.x; all credentials in filesystem property files on D:\ | TIBCO JMS replacement; Active Batch scheduler replacement; stored procedure cataloguing (hundreds of SPs, no DDL in Git) | 36–48 months |
| D07 — Content & Notification | High | CVV/PAN in XML (`@XmlElement`); PII to unencrypted Syslog; Mailgun key committed; SMS delivery stub | request-file_LIB XML refactor; Syslog TLS; Log4j upgrade | 6–12 months |
| D08 — Search & Platform Core | Very High | Unauthenticated RPC dispatch; Commons HttpClient SSL bypass; PAN masking non-compliant (8 digits unmasked); PII in logs | Commons HttpClient 5.x migration is API-breaking; all consumers require coordinated rebuild | 12–18 months |
| D09 — STIP & Card Processing | High | App Config key committed; SOAP auth returns 200; command injection in crypto-service_SVC; forgeable auth header | stip-models and stip-generated entirely empty — no STIP schema exists; crypto-service_SVC stranded | 6–12 months |
| D10 — Data Platform & Analytics | Very High | CVV post-auth in ecountcore; SHA-1 PAN hashing; DPAPI machine-bound ETL encryption; no CI/CD for any database | Manual deployments only; SSIS 2012 EOL; Wirecard infrastructure dependencies | 24–36 months |
| D11 — NexPay Greenfield | High | Auth disabled (3 services); saga stubs; CSP `frame-ancestors: *`; iFrame XSS risk (`allow-same-origin`); credentials committed | Production readiness checklist unmet; nexpay-parent SNAPSHOT; Java 25 non-LTS (EAR) | 3–6 months |
| D12 — Infrastructure & DevOps | Very High | Entire Gen-1/Gen-2 Git-as-secrets-store pattern; SFTP keys committed with passphrases; SSN in VBScript; AJP cleartext | No Terraform CI; Config Server auth status unknown; Windows-only deployment pipeline uncontainerizable | 18–24 months |
| D13 — Co-brand & Wirecard Partners | Very High | 12+ committed credential types across 3 repos; Spring Boot 1.5.x EOL; SFTP host key verification disabled; `T_PIN` column unencrypted | ActiveMQ → Azure Service Bus; Oracle → Azure SQL; Spring Boot 1.5 → 3.x (two major version jumps) | 24–36 months |
| D14 — Testing & QA Automation | High | Real PANs/CVVs/SSNs permanently in git history (6 repos); no CI execution for Gen-1 API suites; headless disabled prevents CI | SAD remediation (git filter-repo) is a prerequisite for all other automation investment | 6–12 months |
| D15 — Developer Tooling & Libraries | Medium-High | Struts 1.3.8 enforced by parent POM with no child override; PRNG in Gen-3 SDK; CVV in XML; Dapr secrets not zeroed post-injection | webapp-parent-pom_PARENT consumer migration (clientzone, csa, enrollment, oneplatform) requires full framework replacement | 12–18 months (parent); 24–36 months (all consumers) |

---

## 8. API Surface Security Audit

### Unauthenticated External / Internal Endpoints

| Endpoint | Service | Protocol | Risk |
|---|---|---|---|
| `/dispatch.asp` | director-svc_SVC | XML-RPC/HTTP | Returns all platform credentials to any internal caller |
| `POST /api/v1/screening/request`, `POST /sanction/webhook` | recipient-screening-api | REST/HTTPS | OFAC bypass; webhook injection blocks/unblocks cardholder accounts |
| All payment ops (`/v1/accounts/*`) | om-payment-api | REST/HTTPS | Full payment API with PAN/CVV retrieval, account creation, fund operations |
| `/scheduler.service` | scheduler_WAPP | Spring HTTP Invoker | Unauthenticated Java deserialization RCE on payment scheduler |
| `/cryptokeysvc/httpCryptoService/HTTPCryptoService-httpinvoker` | crypto-service_SVC | Spring HTTP Invoker | Unauthenticated key management with command injection |
| All StrongBox XML-RPC methods | strongbox-xmlrpc_SVC | XML-RPC/HTTP | Returns any cryptographic key by name |
| `POST /tokenManagerServlet` and variants | xsso_SVC | HTTP Servlet | SSO token encryption/decryption unauthenticated |
| `GET /getData/{refId}` | secure-data_LIB | REST | Returns any vault secret by reference ID |
| `?site_admin=maintenance` | spring-refer-a-friend_WAPP | HTTP GET param | Puts application in maintenance mode; DoS via URL parameter |
| `/{application}/{profile}` | Spring-Config-Server | REST | Returns full property set for any service including secrets (if running with defaults) |

### Missing Input Validation

- **crypto-service_SVC `ExternalCommandsHelper.java:81`**: `keyName` not validated before string interpolation into OS command.
- **om-content-management-api `GitHubAPIService.java`**: `targetFilePath` not normalized; path traversal to arbitrary blob storage paths.
- **scheduler_WAPP `QuartzServiceProviderImpl`**: `callbackPath` URLs not validated against allowlist; SSRF via callback registration.
- **xsso_SVC `TokenManagerServlet.java:29-38`**: XStream deserializes attacker-supplied XML without type allowlist.
- **xml-rpc_LIB `XmlRPCServletHelper.java:239-243`**: `agentName`/`agentAffiliate` pulled from HTTP headers without sanitization.

### CORS Misconfiguration

**embedded-payments-api `application.yaml:122-123`**: `allowed-ancestors: "*"` (CSP `frame-ancestors: *`) and `shim-allowed-origins: "*"`. Any page on any domain can iframe the payment widget. The `DomainWhitelistService` validates embedding at the API layer but the CSP directive is `*`. Combined with CORS `*` on the shim endpoint, this enables clickjacking and CSRF-adjacent attacks.

**embedded-payments-sdk `shim.ts:134`**: `iframe.sandbox.add('allow-scripts', 'allow-forms', 'allow-popups', 'allow-same-origin')` — combined with `allow-scripts`, XSS in the widget SPA can read the `X-Onbe-Session-Token` HttpOnly cookie. `CardDetailsComponent` renders full PAN and CVV in the DOM.

### Spring Boot Actuator Exposure

- **wirecard_sg-bank-agent_LIB `application.yml:72-79`**: All actuator endpoints exposed without authentication.
- **nexpay-config-svc**: Actuator `env` endpoint exposed — returns runtime configuration including resolved secret values.
- **Spring-Config-Server_INFRA_CONT**: Empty repository; production image source unknown. If running with Spring Cloud Config defaults, `/actuator/health`, `/{application}/{profile}` (full property dump), `/encrypt`, and `/decrypt` are all unauthenticated.
- **stand-in-processing-api / recipient-screening-api `Dockerfile:14`**: `EXPOSE 50505` — probable JDWP debug port; if accessible from service mesh, enables remote debugger attachment and arbitrary code execution from within the ACA/AKS network.

### Missing Rate Limiting

No service in the estate implements application-layer rate limiting. Rate limiting is entirely delegated to Azure APIM for Gen-3 services and completely absent for all Gen-1/Gen-2 services, which bypass APIM via direct internal network access.

---

## 9. Gen-3 Code Quality Assessment — Production Readiness

### Must Remediate Before Live Payment Traffic

| Service | Blocker | Required Action |
|---|---|---|
| recipient-screening-api | `anyRequest().permitAll()` — live OFAC enforcement bypass | 10-line Spring Security OAuth2 resource server config + HMAC webhook signature validation in `SanctionWebhookRequestValidator` |
| om-payment-api | `JwtSecurityValidator.java:57` returns `true` unconditionally | Uncomment lines 31-57; restore `ApiSecurityConfiguration` to Spring Boot app context |
| nexpay-order-orchestrator | Saga compensation stubs — no live financial reversal | Implement `compensateCardIssuance()` as real call to nexpay-cardprocessor-svc cancel endpoint |
| nexpay-recipientorchestrator-svc | Saga compensation stubs + no UNIQUE constraint on `claim_code` | Implement live compensation; add `UNIQUE INDEX` on `saga.claim_code` (partial: `WHERE status NOT IN ('FAILED','COMPENSATED')`) |
| nexpay-ordervalidator-svc | Live Azure App Config key committed; hardcoded `FUND_LIMIT = 1000.0`; AI-generated code without formal peer review; zero/negative amounts pass validation | Rotate credentials; externalize limit to nexpay-config-svc; formal peer review sign-off; fix validation to reject non-positive amounts |
| nexpay-ivr-bff | Hardcoded SSN placeholder and card number at `FsCustomerInquiryController.java:55` on external APIM | Block APIM route returning HTTP 503 `Retry-After` until stub is replaced |
| nexpay-config-svc | No Spring Security; actuator `env` exposed; V5 seed data in production migration path | Add OAuth2 resource server; disable/auth-protect actuator; separate seed data from production migrations |
| stand-in-processing-api | App Config key committed; SOAP auth returns HTTP 200 on failure; `disable-security-filter` property in production code | Rotate key; fix SOAP fault response; remove bypass property from production code entirely |
| crypto-service_SVC | Command injection; no application auth; Windows CMD in Linux container (`cmd /c` fails on Alpine); all tests skipped | Array-form `Runtime.exec()`; add shared-secret or mTLS auth; fix OS assumption; enable CI test execution |
| embedded-payments-api | CSP `frame-ancestors: *`; CORS `shim-allowed-origins: *`; truststore committed to source; version 0.0.1-SNAPSHOT | Restrict to registered partner domains via `DomainWhitelistService`; move truststore to Key Vault |

### Near-Production-Safe (named caveats required)

| Service | Status | Outstanding Caveats |
|---|---|---|
| nexpay-cardprocessor-svc | Near-production | No circuit breaker on `POST /v1/cards` path; `processorMetadata` JSONB PAN risk unverified; no `USER` in Dockerfile; container scan disabled |
| nexpay-claim-code-svc | Near-production | No UNIQUE constraint on `claim_code` in saga table; claim code logged at INFO (`ClaimableControllerApiDelegateImpl.java:58`) |
| nexpay-auth-svc | Near-production | Email PII logged at INFO; Java 25 early-access JDK (not LTS); SNAPSHOT parent |
| nexpay-recipient-profile-svc | Near-production | PII unencrypted at rest; Swagger UI enabled in QA/prod profiles; TRACE-level Hikari/PostgreSQL logging in prod |

### Structural Absences

- **stip-models**: Entirely empty. No canonical STIP authorization request/response schema exists. This blocks all STIP contract work across Domain 09.
- **stip-generated**: Entirely empty. No generated STIP Maven artifacts; no build or CI pipeline defined.
- **RecipientApp**: Empty. Source for the recipient-facing application has not been acquired or committed.
- **OP_Mobile_TESTING_PT**: No artifacts. Mobile platform testing for OnePlatform has zero automation.

---

## 10. Remediation Roadmap (Technical)

### Immediate — This Week (Days 1–7)

Security incident-grade actions. Execute in parallel. Assign a named engineer and a named reviewer to each item.

**Action 1 — Rotate all committed credentials (CISO-owned):** In order: (1) Titan PROD SFTP key — coordinate with Northlane card bureau for key exchange; (2) wirecard_sg-bank-agent CIMB SFTP RSA key and PGP key `0xCE5B683F` — coordinate with CIMB Bank Singapore; (3) PGP key `0x6392B27D` — notify Cambridge/Corpay; (4) AWS IAM key `[REDACTED — rotate immediately]` (`aws iam delete-access-key`); (5) nexpay-ordervalidator-svc App Config connection string and OAuth2 client secret; (6) stand-in-processing-api App Config access key; (7) manage-payment-rest-api Visa credentials (`dapr-secrets.json`); (8) mailgun-event-tracker API key (`application.properties:18`); (9) cross-border-transfer-service Cambridge client signatures, DB password, SMTP API key. After rotation, purge from Git history using `git filter-repo`. Publish patched `wirecard_test-utilities_LIB` JAR without the PGP private key.

**Action 2 — Fix recipient-screening-api `SecurityConfig.java:15-20`:** Replace `anyRequest().permitAll()` with `http.oauth2ResourceServer(oauth2 -> oauth2.jwt(...)).authorizeHttpRequests(auth -> auth.requestMatchers("/actuator/health").permitAll().anyRequest().authenticated())`. Wire HMAC-SHA256 signature validation in `SanctionWebhookRequestValidator` (scaffolding already exists). Deploy to production as emergency change. Document fix for compliance as closure of open regulatory finding.

**Action 3 — Fix om-payment-api `JwtSecurityValidator.java:57`:** Uncomment lines 31-57. Restore `ApiSecurityConfiguration` to the Spring Boot application context (remove from exclusion list). Verify 401 is returned without a valid JWT for all payment endpoints. Deploy as emergency change.

**Action 4 — Block nexpay-ivr-bff external APIM route:** Add APIM policy returning HTTP 503 with `Retry-After: 604800` for all routes to nexpay-ivr-bff until `FsCustomerInquiryController.java:55` is replaced with a real implementation.

**Action 5 — Assess DS_DB_ecountcore CVV storage:** Execute `SELECT TOP 10 cv_code FROM fdr_card_account_detail WHERE cv_code IS NOT NULL` on production ecountcore. If non-null values exist post-authorization, engage QSA immediately for breach notification assessment per PCI DSS Req 12.10. Implement post-activation purge stored procedure. Disable SQL parameter capture in all monitoring tools for `fdr_card_account_create`.

**Action 6 — Add `@XmlTransient` to `Cardtype.java:51-52` and `:43-44`** (request-file_LIB, Domain 07/15): Two-line annotation change. Prevents CVV and PAN from being JAXB-marshalled to plaintext XML in any batch run. Confirm with QSA whether existing batch output files on disk require forensic audit and secure deletion.

**Action 7 — Replace `kotlin.random.Random` with `java.security.SecureRandom` in `TextUtils.kt:22`** (onbe-spring-boot, Domain 15): One-line change in password generator. Release as `0.0.22` patch so all Gen-3 services receive the fix on their next dependency resolution cycle.

---

### Sprint 1 — Days 1–14 (Security Baseline)

Teams: Security Engineering, Platform, NexPay

**Item 8 — Rotate scheduler_WAPP DB credentials and begin replacement planning:** Rotate the four `SCHDULERWAAP_*_PASSWORD` database credentials. Remove `.env` and `.env-dev` from VCS with `git filter-repo`. Catalog all QRTZ2_* consumer callback registrations as the input to an Azure Scheduler or AWS EventBridge replacement evaluation.

**Item 9 — Fix stand-in-processing-api SOAP auth response:** Change `SecurityConfig.java:66-70` to return HTTP 401 with a SOAP Fault body on authentication failure. Remove `sasi.dev.disable-security-filter` property from production code entirely. Gate on Spring profile if local development requires it.

**Item 10 — Fix crypto-service_SVC command injection and add auth:** Change `Runtime.getRuntime().exec(cmd)` (String form) to `Runtime.getRuntime().exec(new String[]{...})` with isolated arguments. Validate `keyName` against allowlist pattern. Add shared-secret or mTLS authentication to the HttpInvoker endpoint. Fix the `cmd /c` Windows CMD assumption (fails on Alpine Linux). Enable test execution in CI.

**Item 11 — Fix cbts-client_LIB JVM-global TLS bypass:** Remove trust-all `X509TrustManager` and `SSLContext.setDefault()` from `CBTSClient.java:126-151`. Implement scoped `SSLContext` for CBTS `HttpClient` instance only, enforcing TLS 1.2+, standard X.509 chain validation, and hostname verification. Rebuild and redeploy cross-border-transfer-service and global-deposit-batch.

**Item 12 — Fix rsa-mfa_LIB TLS bypass and OTP logging:** Restore keystore-based TrustManager in `TrustAllSSLSocketFactory.java:79-81` (commented-out code at lines 55-76 shows original intent). Remove `token` variable from log statement at `AuthenticationServiceImpl.java:871`. Remove phone number from log statements at `:760-763`.

**Item 13 — Implement saga compensation in both Gen-3 orchestrators:** For both nexpay-order-orchestrator and nexpay-recipientorchestrator-svc: implement `compensateCardIssuance()` as a real HTTP call to nexpay-cardprocessor-svc cancel/deactivate endpoint. Add `UNIQUE INDEX` on `claim_code` in both saga state tables (partial index: `WHERE status NOT IN ('FAILED', 'COMPENSATED')`). This is a go/no-go gate for any production disbursement via the Gen-3 path.

**Item 14 — Fix autofile ScheduleFundsRetry duplicate disbursement:** Correct `ScheduleFundsRetry.java` so the "retry already exists" code path returns without calling `insertFundsRetryQueue()`. Add `UNIQUE` constraint on the retry queue table. Add HTTP timeouts (10s connection, 30s socket) to `SharedServiceHelper.invokePushPayService()` in ach-withdrawal-initiator.

---

### Sprint 2 — Days 15–30 (Credential Hygiene + Critical CVEs)

Teams: Security Engineering, Infrastructure, Platform Engineering

**Item 15 — Upgrade XStream estate-wide to 1.4.21+:** Priority order: batch_LIB (1.3.1 — critical RCE), job_LIB (1.3.1), then clientzone_WAPP (1.4.12), then xsso_SVC. Add `xstream.allowTypesByWildcard(new String[]{"com.ecount.**", "com.onbe.**"})` and deny all other types in all locations that process XML from untrusted sources.

**Item 16 — Patch Tomcat CVE-2025-24813 in order_SVC; CVE-2024-52316 and CVE-2024-50379 in crypto-service_SVC:** Remove CVEs from `.trivyignore`. Upgrade Tomcat to patched versions. Create formal risk acceptance documentation for all remaining suppressed CVEs with named owners, review dates, and remediation targets. Apply same governance to banker_API CVE suppressions.

**Item 17 — Replace Log4j 1.x with SLF4J + Logback (Phase 1):** Target in this sprint: autoclaim-split-svc_LIB, batch_LIB, cancel-transaction-process_LIB, notification-requests-generator_LIB. Remaining Log4j 1.x consumers in Sprint 3.

**Item 18 — Centralize secrets for Gen-2 cross-border stack:** Move Cambridge API credentials, CBTS credentials, SFTP credentials, and DB passwords for cross-border-transfer-service_SVC, global-deposit-batch, cbts-client_LIB, and file-transfer-service to Azure Key Vault with Managed Identity. Remove from YAML after migration. Pin all `xml-rpc` SNAPSHOT dependencies to published GA releases.

**Item 19 — Fix ecountcore SHA-1 card hashing:** Add `card_hash_v2` column using `hashbytes('sha2_256', CONVERT(VARBINARY, card_number + per_card_random_salt))` with the salt stored in a separate `card_hash_salt` column. Backfill for all existing cards. Update all stored procedures referencing `card_hash`. Deprecate and drop `card_hash` after validation.

**Item 20 — Add OFAC pre-screening in cross-border-transfer-service_SVC:** Implement `SanctionsScreeningService` call in `CreateTransferHandlerImpl` between validation and `SpotServiceImpl.instructDeal()`. Compliance must define fail-open vs. fail-closed policy before implementation.

**Item 21 — SAD remediation in Domain 14 test repositories:** Use `git filter-repo` to remove PANs `5115531022041490`, `5445446554206695`, `5445446557563720`, CVVs, and SSNs from account-management-api_TESTING_AUTO, cs-api_TESTING_AUTO, client-api-v4_TESTING_AUTO, selenium-framework-test, and Automation_ClientZone. Replace with clearly synthetic values (Luhn-valid, non-issued BINs). Deploy `gitleaks` as mandatory pre-commit hook and GitHub Actions step across all Domain 14 repos.

---

### Sprint 3 — Days 31–60 (Auth Hardening + Protocol Debt)

Teams: Platform Engineering, Security Engineering, Data Engineering

**Item 22 — Add authentication to xml-rpc_LIB dispatch layer:** Implement HMAC-SHA256 request signing (`RPC-Signature` header computed over `(txID + interfaceName + methodName + agentName + timestamp)` with a shared secret) validated in a Servlet Filter before any request reaches `XmlRPCServletHelper.processRequest()`. Implement interface/method allowlist in `xmlrpc-allowlist.properties` rejecting any unlisted pair with HTTP 403. Remove `doGet()` delegation — return HTTP 405. Deploy across all XML-RPC servers in a single coordinated release wave.

**Item 23 — Apply SQL Server Always Encrypted to StrongBox key columns:** Column master key in Azure Key Vault; column encryption keys in the strongbox database encrypted by the CMK. Modify `SbGetAsymmetricKey` and `SbGetSymmetricKey` stored procedures to decrypt at the JDBC driver layer. No consumer-side application changes required. This is the highest-impact vault security improvement achievable without a full vault migration.

**Item 24 — Fix MaskCCHelper PAN masking in xsearch_LIB and xsearch-new_SVC:** Both `MaskCCHelper.java` instances (identical code in two codebases) expose first-4 + last-4 = 8 unmasked digits. Fix: unmasked positions 0–5 (BIN, 6 digits) and `length-4` to `length-1` (last 4 digits); mask all intermediate positions with `X`. Deploy simultaneously to both codebases. Add unit test asserting `4111111111111111` produces `411111XXXXXX1111`. Submit to QSA as Req 3.3.1 compliance evidence.

**Item 25 — Fix xsecurity_SVC and clientzone_WAPP MD5 password hashing:** Replace `EcountMd5PasswordEncoder` with bcrypt (cost factor ≥ 12) or Argon2id. Force-expire all legacy MD5 password records (require reset on next login). Increase PBKDF2 iterations from 10,240 to 260,000 minimum for the existing PBKDF2 path. Fix AES/ECB usage in `clientzone_WAPP EncryptionUtil.java` (`Cipher.getInstance("AES")`) to AES/GCM.

**Item 26 — Restore account-management-api_API security controls:** Re-enable `validateAPISecurity()` and `testAPI()` in `CreateAccountService.processWebRequest():221-226`. Make OFAC screening blocking — catch all exceptions, return a defined error code rather than continuing account creation. Remove `log.debug(">>> Retrieved Shared Secret ...")` from `CvvInquiryService.java:64`. Remove hardcoded `jwe.secretKey` default from committed YAML; enforce Key Vault fail-fast at startup.

**Item 27 — Remove PII from all confirmed INFO-level log statements:** Priority targets: (a) `NotificationRequestDetailsRowMapper.java:42-113` — remove all 12 field-level `log.info()` calls; configure SyslogAppender with TLS RFC 5425; (b) `EcountCoreServiceHelperImpl.java:80-82` — replace 3 PII log statements with synthetic member ID; (c) `RecipientScreeningService.java:65,84` — mask DDA to last-4 digits; (d) `AuthenticationServiceImpl.java:871` — remove `token` variable from log statement; (e) `account-management-payout_API:100` — mask or remove decrypted DDA.

**Item 28 — Implement CI/CD validation for ecountcore and prepaid_warehouse:** SSDT build with `SqlServerVerification=True` on every PR. Enable DBA approval gate with named approvers. Change ecountcore deployment source from development branch to `main` with branch protection rules enforced in GitLab/GitHub.

---

### Sprint 4 — Days 61–90 (Architecture & Observability)

Teams: Platform Engineering, Data Engineering, DevOps

**Item 29 — Replace Spring HTTP Invoker in priority consumer chain:** (a) `clientapi_API → order_SVC` — define REST endpoint on order_SVC; update clientapi_API to use `RestTemplate`; decommission HTTP Invoker bean; eliminates XStream deserialization RCE risk and creates a publishable API contract. (b) `job-order-synchronization_LIB → Order Service` — replace with typed `WebClient` or OpenFeign client; add integration tests against a WireMock Order Service stub. (c) `account-management-api_API → SynchronousOrderProcessor` — replace with REST client call.

**Item 30 — Migrate DS_ETL_warehouse SSIS protection level:** Change from machine-bound DPAPI (`NAM\nick.doan` / `P-NA-DB11`) to `DontSaveSensitive`. Implement SSIS Catalog environment variables for all credentials. Update ETL failure notification from `colin.treat@northlane.com` to an active team distribution list. Enable SMTP TLS on the notification relay.

**Item 31 — Establish observability foundation (Gen-1/Gen-2):** Introduce OpenTelemetry SDK in jobservice_SVC, workflow-service, and director-svc_SVC. Export to Azure Monitor Application Insights. Add `DisbursementCorrelationId` UUID propagation through autofile, ach-withdrawal-initiator, cross-border-transfer-service, and ieft-cp2e as MDC context key in all log statements. Emit Micrometer counters for retry queue depth, SFTP transfer latency, and Cambridge API error rate. Add alerting: retry queue depth > 100, Cambridge API error rate > 5%.

**Item 32 — Enforce Gen-3 production readiness checklist:** Formalize as a required PR approval gate for any Gen-3 service promotion to production: (a) saga compensation implemented and integration-tested with rollback verification; (b) saga uniqueness constraints (UNIQUE INDEX on claim_code or equivalent) in place; (c) container scan enabled and passing with zero critical CVEs; (d) Dockerfile with non-root `USER` instruction; (e) nexpay-parent released to stable GA version (no SNAPSHOT); (f) production IaC defined (ACA/AKS manifests in Git); (g) per-service Managed Identity with scoped Key Vault access — no inline credentials; (h) Swagger UI disabled in all non-local Spring profiles; (i) no SNAPSHOT dependencies in production classpath; (j) Spring Security OAuth2 resource server configured; (k) no `trustServerCertificate=true` in production JDBC URLs.

**Item 33 — Decommission atlys_WAPP and dmt_WAPP:** Confirm zero active users with business stakeholders. Shut down IIS host serving atlys_WAPP. Revoke all database accounts (ATLYS_E, ATLYS_FcCR, ATLYS_RvCR, RiskDB access). Revoke dmt_WAPP RiskDB access. Archive both repositories with a decommission tag. No further security investment in these applications is warranted given the Silverlight 4.0 EOL platform and VBA macro architecture.

**Item 34 — Establish CIMB wire transfer via renewed key material and formal key exchange process:** After CIMB SFTP key rotation (Week 1), coordinate with CIMB Bank Singapore on new public key exchange procedure. Document the procedure in a formal operational runbook stored outside Git. Audit all historical files encrypted with compromised key `0xCE5B683F` for potential exposure. Extend same procedure to Cambridge/Corpay PGP key `0x6392B27D`.

---

*Document classification: Internal — PCI DSS Level 1 CDE. Distribution restricted to Security Engineering, Solution Architecture, and named QSA engagement team. Do not distribute externally or store in systems accessible to third parties without explicit authorization from the CISO.*
