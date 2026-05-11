# MASTER DATA ARCHITECT VIEW — Onbe 363-Repo Estate
*(Generated: 2026-05-08 | Source: 363 repositories across 15 business domains)*

**Classification:** Internal — Restricted  
**Scope:** 363 repositories across 15 functional domains; three technology generations (Gen-1 eCount/Citi era, Gen-2 Wirecard/Northlane, Gen-3 NexPay/Onbe)  
**Regulatory context:** PCI DSS v4.0.1, GLBA, GDPR, CCPA, PIPEDA, NACHA, Reg E, OFAC, NIST CSF 2.0

---

## 1. Executive Summary

The Onbe 363-repo estate hosts one of the most complex data architectures in the mid-market fintech segment: a 20-year layered SQL Server OLTP core (ecountcore), surrounded by satellite operational databases (cbaseapp, jobsvc, ordersvc, notificationsvc, strongbox, greatplains, repositorysvc), fronted by five generations of Java service layers, fed by a 100-package SSIS ETL pipeline, and now incrementally succeeded by a Gen-3 PostgreSQL microservice layer. The estate processes PAN, CVV/CVC2, PIN, SSN, DDA (bank account numbers), DOB, and full cardholder PII across every one of its 15 domains.

**Data store count:** 27 distinct named databases and storage tiers have been identified across the 15 domains, spanning SQL Server, PostgreSQL, Oracle, MongoDB, Redis, Azure Blob Storage, IBM MQ, TIBCO EMS, Azure Service Bus, and local filesystem stores (see Section 2).

**Sensitive data categories present across the estate:**

| Category | PCI DSS Classification | Confirmed Locations |
|---|---|---|
| PAN (Primary Account Number) | Cardholder Data (CHD) | ecountcore (CLE-encrypted), request-file_LIB XML (plaintext), emboss extract XML (plaintext), test fixture XML/JSON (plaintext in Git) |
| CVV/CVC2 | Sensitive Authentication Data (SAD) — storage prohibited post-auth | ecountcore fdr_card_account_detail.cv_code (status unverified), Cardtype.cvcode in request-file_LIB (plaintext XML), CreditCardVO._cvCode in branded-currency_LIB |
| PIN / PIN blocks | SAD — HSM required | SetPinRequest model (STIP domain), IVR DTMF path, SOAP plaintext in account-management-payout, test fixtures |
| SSN / Government IDs | PII — GLBA, CCPA | ecountcore core_member_extended (implied), enrollment_LIB ExtractInfo (JVM heap + flat file), xml-converter_LIB XML files, test fixtures |
| DDA / Bank account numbers | Financial identifier — Reg E, GLBA | StrongBox vault, CBTS BENEFICIARY table, ieft-cp2e CP2E files, SASI Azure SQL, INFO-level logs across 8 domains |
| Full cardholder PII (name, address, email, phone, DOB) | PII — GDPR, CCPA, GLBA | ecountcore, cbaseapp, nexpay-recipient-profile-svc PostgreSQL, prepaid_warehouse dim.DimAccountHolder, notification logs, CBTS Oracle schemas |

**Critical data governance gaps:**

1. The cardholder data environment (CDE) boundary is undefined in code. There is no formal CDE scoping document derivable from the codebase; all 27 identified data stores must be presumed in scope until formally assessed against PCI DSS network segmentation evidence.
2. CVV storage in ecountcore fdr_card_account_detail.cv_code is unverified — if live CVV values are present post-authorisation this is an unconditional PCI DSS Req 3.3.1 violation affecting the entire estate.
3. PAN and CVV exist in plaintext in version-controlled test fixtures across at least six repositories — all permanently in Git pack file history.
4. The StrongBox vault co-locates symmetric key-encrypting keys with the ciphertext they protect in a single SQL Server database, violating PCI DSS Req 3.6.1.
5. Production secrets (database passwords, PGP private keys, API credentials, SFTP keys) are committed in plaintext to Git across every domain, making the Git repositories the de facto authoritative secret store for the entire platform.
6. No domain-wide log masking framework exists. PAN, CVV, SSN, DDA numbers, and cardholder PII appear in INFO-level application logs that are transmitted unencrypted to Syslog and archived in AWS S3 and ChaosSearch.

**Overall CDE boundary assessment:** The CDE encompasses at minimum the ecountcore SQL Server database, the cbaseapp database, the StrongBox database, the prepaid_warehouse analytics database, the SASI Azure SQL database, the nexpay-cardprocessor-svc PostgreSQL database, the crypto-service_SVC PGP keyring, and all application services that connect to these stores. This represents a very large attack surface. The absence of field-level encryption in the warehouse, the presence of plaintext PANs in emboss and batch files, and the absence of network flow logs (Domain 12 finding) mean the CDE cannot be formally bounded without infrastructure-level investigation beyond the codebase.

---

## 2. Estate-Wide Data Store Inventory

| Database / Store | Technology | Domain(s) | Sensitive Data | Encryption at Rest | TDE Status | Known Issues |
|---|---|---|---|---|---|---|
| ecountcore | SQL Server | D01, D02, D03, D04, D06, D08, D09, D10, D14 | PAN (CLE), CVV (cv_code), DDA, SSN, full cardholder PII, transaction history | Column-Level Encryption on card_encrypted; SHA-1 card_hash | Unknown / unconfirmed for base tables | cv_code column may store post-auth CVV; SHA-1 card hash is cryptographically weak; plaintext PAN accepted as stored-procedure parameter |
| cbaseapp | SQL Server | D01, D03, D04, D05, D06, D07, D08, D09 | Cardholder auth, affiliate config, DDA, member profile, login history, api-security access entities | None visible at application layer | Unknown | MD5 password hashes active; DDA numbers logged to application logs |
| jobsvc | SQL Server | D01, D04, D06, D08, D10 | Job state, PUID↔ecountId mapping, NACHA addenda (SSN), Quartz QRTZ2_FIRED_TRIGGERS with potential payment data | None | Unknown | Quartz fired-trigger history unbounded; SSN in addenda columns plaintext |
| ordersvc | SQL Server | D01, D04, D06 | Order lifecycle, order memos | None | Unknown | No schema versioning; IBM MQ credentials in plaintext config |
| notificationsvc | SQL Server | D01, D06, D07 | SMS queue (mobile_phone, puid), email tracking, notification queue | None | Unknown | PII in append-only tables; no retention or erasure policy |
| strongbox | SQL Server | D01, D05, D08, D10, D12 | RSA private keys, AES symmetric keys, encrypted cardholder data blobs | AES-128-CBC (V2), DESede (V1 — deprecated) | Unknown | Keys and ciphertext co-located in same DB; V1 uses 3DES (PCI non-compliant); no key rotation mechanism; key material stored as plain VARCHAR |
| vendor / FDR ODS | SQL Server + ODBC/FDR | D01 | Chargeback records, FDR settlement data | None | Unknown | sun.jdbc.odbc.JdbcOdbcDriver removed in JDK 8; service inoperable on supported JVM |
| ecountbatchjobrepository | SQL Server | D01 | Spring Batch metadata | None | Unknown | No CHD; Spring Batch schema only |
| JobsvcDataSource / GreatPlains | SQL Server | D02, D13 | Payroll GL, ACH job data, disbursement records | None | Unknown | Database passwords committed in plaintext to source |
| CBTS SQL Server (cross-border) | SQL Server | D02, D13 | FX rates, BENEFICIARY (bank account, routing, IBAN, SWIFT, PII), REMITTER, TRANSFER, RECON_FILE | None | Unknown | No field-level encryption; TLS disabled in QA config; beneficiary PII logged at INFO |
| ATLYS_E / ATLYS_FcCR / ATLYS_RvCR | SQL Server | D04 | Financial GL, program forecasts, commissions, Durbin BIN exemptions | Password encryption via hardcoded key "WJKGRSCQ3#4yujfg" | Unknown | Hardcoded encryption key in source; AES/ECB cipher used |
| Banker_NA (Microsoft Dynamics GP) | SQL Server | D04, D13 | Fund authorization, sales orders, invoices, payments | GP-managed | Unknown | eConnect API-mediated access; no application-layer encryption |
| xsecurity SQL Server | SQL Server | D05 | Operator passwords (MD5 and PBKDF2-HMAC-SHA256), RBAC, session history, audit log | None | Unknown | MD5 hashes active for existing accounts; PBKDF2 iterations below NIST 600K recommendation |
| nexpay_claimable | SQL Server | D03, D11 | claim_code (NVARCHAR, unhashed), claimable_payment, recipient_registration (full PII) | None | Unknown | Claim codes stored in plaintext; no UNIQUE constraint on claim_code; employee email in Flyway seed |
| SASI Azure SQL (stand-in-processing-api) | Azure SQL | D09 | DDA numbers (DdaNumberStatus, DdaReservation), MemberAccountShadow, TransactionLog, SASIRequestDetail | TDE (Azure SQL default) | Enabled (Azure) | No column-level encryption for DDA; TDE alone does not protect against authorized SQL queries |
| nexpay-cardprocessor-svc PostgreSQL | PostgreSQL 15+ | D09, D11 | masked_pan (first6/Xs/last4), processor_card_id, FIS processor_metadata JSONB (cardNum field — masking unverified) | Azure Database TDE | Enabled (Azure) | FIS cardNum in JSONB may contain raw PAN; processorCardId has no immutability constraint |
| nexpay-recipient-profile-svc PostgreSQL | PostgreSQL | D03, D11 | first_name, last_name, DOB (VARCHAR), primary_email, primary_phone, postal address | None at column level | Enabled (Azure) | No field-level encryption on DOB, email, phone; no format constraint on DOB |
| Orchestrator saga PostgreSQL | PostgreSQL | D03, D11 | saga.claim_code (plaintext), saga_step.error_message (may embed PII fragments) | None at column level | Enabled (Azure) | Claim code stored plaintext; no UNIQUE constraint; error_message may hold PII |
| prepaid_warehouse | SQL Server | D10 | dim.DimAccountHolder (full PII, DDA), fact.FactPaymentTransactions (DDA), fact.FactCardAccountDetail (DDA), FactUtilizationTransactions (DDA) | None | Unknown | No Dynamic Data Masking; no row-level security; SSAS schema frozen since 2017; no CI/CD |
| Redis (Azure Cache) | Redis | D03, D04, D11 | Affiliate/program configuration, session data, orchestration state | Redis in-transit TLS | Azure-managed | Redis cache-update step commented out in oneplatform-azureaffiliate-function; Redis unavailability blocks all claim code flows |
| MongoDB | MongoDB | D04 | dmt-web user email and bcrypt passwords | None confirmed | Unknown | JWT blocklist is in-memory only; app restart re-validates all previously invalidated tokens |
| Oracle (Wirecard Gen-2) | Oracle 11g/12c | D13 | CORP_CONTACT.T_PIN (possible SAD), CHECK_TRANSACTION (payee name, address, amount), WireTransferOutTransaction (bank account, routing), NACHA records | None confirmed | Unknown | T_PIN column requires immediate data classification; Hibernate Envers audit present |
| Filesystem batch files | Local FS | D01, D02, D07, D10, D15 | Emboss XML (PAN in plaintext), CP2E files (DDA/routing), check files (cardholder name/address/DDA), request-file_LIB XML (PAN + CVV), Sunrise Banks flat-file (card number) | None | N/A | CVV and PAN written to disk in plaintext by multiple services; GPG encryption commented out in check-issuance |
| FTP/SFTP staging (enrollment) | FTP | D03 | SSN, DOB, full ACH account + routing (enrollment_LIB ExtractInfo flat files) | None | N/A | StrongBox-decrypted SSN and bank account in unencrypted fixed-width flat files; PGP encryption absent |
| Azure Blob Storage | Azure Blob | D07, D12 | Brand assets, content files; log archives (S3 for AWS path) | AES-256 (Azure default) | Enabled | No PII redaction before log archive; heterogeneous schema across services |
| Git repositories (CONFIG / api-config-repo / infrastructure) | Git | D12 | Production OAuth secrets, DB passwords, PGP private keys, SFTP keys, JWE keys, TLS certificates | None — plaintext | N/A | All production secrets reside in Git; this is the primary secret store for Gen-1/Gen-2 |
| Windows Registry (HKLM\SOFTWARE\ECount) | Win Registry | D01, D06 | All platform database passwords (Gen-1 Director) | None — REG_SZ plaintext | N/A | Any Windows process with HKLM read can extract all platform DB passwords |
| IBM MQ | IBM MQ | D06, D07 | Notification events, order messages, job queues | None at message level | N/A | MQ credentials committed in plaintext; DEV environment points to UAT MQ queue |

---

## 3. Sensitive Data Classification & Flows

### 3.1 PAN (Primary Account Number)

**Storage locations:** ecountcore core_card_master.card_encrypted (CLE-protected, decryptable by any principal with CONTROL DATABASE permission); emboss extract XML files at /upload/EmbossFileExtract/ (plaintext — emboss-extract_LIB, StaxEmbossExtractBuilder.java line 29); request-file_LIB Cardtype.cardnumber (plaintext XML via @XmlElement annotation, line 44); Sunrise Banks flat-file sunrise_wdccp_customer_YYYYMMDD.txt (DS_CCP_ccp-export, no confirmed post-SFTP deletion); MemberInquiryValue.getCardNumber() in xsearch stack (raw PAN field; raw vs. masked not enforced at serialization); test fixtures in six Domain 14 repositories (permanently in Git pack files).

**Transit risk:** XML-RPC wire transport in xml-rpc-clients_LIB uses HTTP POST with no code-level HTTPS enforcement; TLS depends entirely on Director-returned endpoint URLs. If any production Director instance returns an http:// URL, PAN traverses plaintext HTTP. CSA tool ↔ xsearch-xmlrpc_SVC traffic carries full MemberInquiryValue including raw PAN field.

**Logging incidents:** consumerload_API logs full SOAP request including PAN at DEBUG via XStream (Domain 01); XmlRPCServletHelper.java lines 280–285 and 309–323 log full RPC payloads at DEBUG (Domain 08); `given().log().all()` in all Domain 14 SOAP test suites logs full request/response bodies including PAN to CI pipeline logs.

**Masking compliance gap:** xsearch_LIB and xsearch-new_SVC implement first-4/last-4 masking (8 unmasked digits). PCI DSS Req 3.3.1 permits a maximum of first-6/last-4 (10 unmasked digits). Current masking is non-compliant — it exposes fewer digits than allowed but in the wrong positions. cs-api-v1 and cs-api-v2 mask last-8, also non-compliant.

### 3.2 SAD Post-Authorisation — CVV/CVC2 and Track Data

**CVV storage findings (P0):** ecountcore fdr_card_account_detail.cv_code — status unverified; if live CVV values are present post-authorisation this is an unconditional PCI DSS Req 3.3.1 violation. Confirmed by Domain 09 and Domain 10 independently. This finding requires immediate database-level inspection and QSA engagement. CreditCardVO._cvCode in branded-currency_LIB (Domain 01) — CVV accessible via public getter with no post-auth purge. Cardtype.cvcode in request-file_LIB — serialized to plaintext XML on disk (Domain 07 and Domain 15, @XmlElement annotation, Cardtype.java line 52). CORP_CONTACT.T_PIN in wirecard_corporate-client-module_LIB Oracle — column exists and requires immediate data classification; if any form of authentication PIN, storage is prohibited (Domain 13). CVV values committed to test fixtures across six Domain 14 repositories.

**CVV in memory:** CreditCard.getCvCode() returns CVV as a Java String in account-management-api before AES encryption. Java String immutability means heap dumps or garbage collection logs can expose SAD.

### 3.3 PIN / PIN Blocks

**Findings:** PIN transmitted as plain xsd:string in SOAP in account-management-payout (Domain 04); no application-layer encryption. SetPinRequest model in stip-generated (Domain 09) — if PIN values are processed in JVM memory, transmitted over any non-HSM path, or stored without HSM protection, this is a PCI DSS Req 9 violation. IVR DTMF PIN entry in ivrintegration_API / ivr-ws_API (Domain 03) — must be protected by telephony-layer DTMF masking. PIN values committed in test fixture files in account-management-api_TESTING_AUTO and Automation_ClientZone (Domain 14).

### 3.4 SSN / Government IDs

**Storage:** ecountcore core_member_extended (SSN implied by 1099/KYC context); enrollment_LIB ExtractInfo.ssn — JVM heap in plaintext after StrongBox decryption, emitted to fixed-width flat file without encryption; xml-converter_LIB federaltaxid XML element (plaintext on operator filesystem); actimize-kyc_LIB Git artifact files contain SSN 405415342 (Domain 05); test fixtures: SSN 741859632 in account-management-api_TESTING_AUTO UpdateReg.xml, SSN in client-api-v4 UpdateRegV4.xml, SSN 987654321 in Automation_ClientZone mypaymentvault.json (Domain 14). request-file_LIB federaltaxid serialized via Secureprofileaddendatype without field-level encryption (Domain 15). Windows-scripts passes SSN as CLI argument — OS command history retains these values (Domain 12).

**Logging:** csa_WAPP audit.properties line 48 explicitly lists SSN.SSNAreaNumber, SSN.SSNGroupNumber, SSN.SSNSerialNumber as audited state fields (Domain 04). xml-rpc_LIB XmlRPCServletHelper logs full RPC payloads at DEBUG including SSN fields.

### 3.5 DDA / Bank Account Numbers

**Highest-volume sensitive data element in the estate by prevalence.** DDA numbers appear in: StrongBox-protected paths (correct), CBTS BENEFICIARY table plaintext, ieft-cp2e CP2E files plaintext, check-issuance output files, SASI Azure SQL DdaNumberStatus and DdaReservation (no column-level encryption), issuing-classic-selfservice_WAPP four audit tables in plaintext, auto-card-batch_LIB ThresholdProgramVirtualCardSP.java line 49 as unmasked SP parameter, chargeback-engine_LIB ChargebackHelper.java line 60 as unmasked SP parameter.

**Critical logging incidents:** recipient-screening-api RecipientScreeningService.java lines 65 and 84 log full DDA number at INFO (confirmed in Domains 03, 05, and 11 independently). account-management-payout AccountManagementHandlerImpl.java line 100 logs fully decrypted DDA at INFO. cbts-client_LIB Beneficiary.toString() logged at INFO includes bank account and routing numbers. enrollment_LIB flat files transmitted via FTP with no encryption.

### 3.6 PII — Name, Address, Phone, Email, DOB

**Logging violations (systemic):** notification-requests-generator_LIB NotificationRequestDetailsRowMapper.java lines 42–113 logs every PII field at INFO level — up to 1 GB of PII-containing log files on disk, transmitted via unencrypted Syslog to 10.1.1.130. ecore-batch_LIB EcountCoreServiceHelperImpl.java lines 80–82 logs cardholder email, first name, last name at INFO. rsa-mfa_LIB logs OTP tokens at INFO (AuthenticationServiceImpl.java:871) and phone numbers at INFO (:760–763). spring-refer-a-friend_WAPP logs phone number in plain text.

**Unencrypted at-rest PII stores:** nexpay-recipient-profile-svc stores DOB (VARCHAR(10)), primary_email, primary_phone as unencrypted PostgreSQL columns. prepaid_warehouse dim.DimAccountHolder stores all PII fields (FirstName, LastName, MiddleName, Address1, Address2, ZipCode, City, State, Country, HomePhone, BusinessPhone, HomeEmail, BusinessEmail, DDANumber) unencrypted and queryable by any SQL principal with SELECT grants.

**Retention violations:** sms_notification_queue, claim_code_issuance_info, sms_cardnotification_log, sms_cardnotification_profile — append-only tables with no DELETE or archival path in any repo (Domain 01). GDPR Art. 17 right to erasure cannot be satisfied.

---

## 4. Top 20 Data Architecture Findings (P0/P1)

| Rank | Domain | Repo(s) | Finding | Data Category | PCI DSS / Regulation | Citation | Priority |
|---|---|---|---|---|---|---|---|
| 1 | D09, D10 | ecountcore (fdr_card_account_detail) | CVV/CVC2 potentially stored post-authorisation in cv_code column — unconditional violation if true | SAD | PCI DSS Req 3.3.1 | DS_DB_ecountcore/02_data_architect.md; DA_domain09 F-DA-09-02; DA_domain10 F-DA-10-01 | P0 |
| 2 | D01, D15 | emboss-extract_LIB, request-file_LIB | PAN written in plaintext to filesystem (emboss XML at /upload/EmbossFileExtract/; Cardtype.cardnumber via @XmlElement to disk) | PAN | PCI DSS Req 3.4, 3.5.1 | Extractor.java:29; Cardtype.java:44 | P0 |
| 3 | D07, D15 | request-file_LIB | CVV committed to disk in plaintext XML via Cardtype.cvcode @XmlElement annotation — SAD storage prohibited unconditionally | SAD (CVV) | PCI DSS Req 3.2.1 | Cardtype.java:52; DA_domain07 Finding 2; DA_domain15 | P0 |
| 4 | D01, D05, D12 | director-svc_SVC, CONFIG repos, all Gen-1 services | All platform database passwords stored in plaintext in Windows Registry (HKLM\SOFTWARE\ECount as REG_SZ) and in Git-committed config files (app-config/qa/appsettings.json) | System credentials | PCI DSS Req 3.5, 8.3, 8.6 | DA_domain01 Finding 2; DA_domain12 | P0 |
| 5 | D05 | strongbox-xmlrpc_SVC, strongbox-lib_LIB | StrongBox vault co-locates RSA private key-encrypting key and AES symmetric key with encrypted data blobs in the same SQL Server database — complete decryption chain exposed in a single stored-procedure call | Cryptographic keys | PCI DSS Req 3.6.1, NIST SP 800-57 | SbGetAsymmetricKey.java:23–25; DA_domain05 | P0 |
| 6 | D02, D13 | cross-border-transfer-service_SVC, wirecard_test-utilities_LIB, wirecard_sg-bank-agent_LIB | Multiple PGP private keys committed to Git repositories and packaged into Docker images / production JARs (0x6392B27D-sec.asc, 0xCE5B683F-sec.asc); CIMB SFTP RSA private key in application.yml:34–61; AWS access key [REDACTED — rotate immediately] committed in gradle.properties:31–32 | Cryptographic keys, credentials | PCI DSS Req 3.5.1, 3.7.1, 8.3.2 | DA_domain02 P0-1; DA_domain13 R-1 | P0 |
| 7 | D14 | account-management-api_TESTING_AUTO, cs-api_TESTING_AUTO, Automation_ClientZone, CucumberPOC | PANs (5115531022041490 BIN 511553; 5445446554206695 BIN 544554; 5445446557563720 BIN 544554), CVVs (308, 319, 331), PINs, SSNs (741859632; 987654321), bank account 99087060252122451, routing 096001013 permanently committed to Git across six repos | PAN, SAD, SSN | PCI DSS Req 3.3/3.4, GLBA, CCPA | DA_domain14 P0-1, P0-2 | P0 |
| 8 | D03, D05 | recipient-screening-api | OFAC screening API and webhook are completely unauthenticated. A spoofed DECLINED webhook triggers block of all cardholder DDA accounts in EcountCore with no authentication check | DDA, cardholder identity | OFAC / BSA-AML, PCI DSS Req 6 | DA_domain03 P0-01; DA_domain05 compliance gap 4 | P0 |
| 9 | D02 | cross-border-transfer-service_SVC | No OFAC screening before funds released for cross-border FX transfers — all Cambridge CBTS beneficiary records created and transfers executed without SDN check | Beneficiary PII, financial | OFAC / BSA-AML | DA_domain02 P0-4 | P0 |
| 10 | D04 | cs-api-v3, oneplatform-rest_API, account-management-api | JWE/DDA encryption keys committed to source (applicationContext-CSWS.properties); default JWE key hardcoded in accountmanagementapi.yaml ('$C&F)J@NcRfUjWnZr4u7x!A%D*G-KaPd'); AES/ECB mode (no IV) in clientzone_WAPP EncryptionUtil.java | DDA, CHD encryption keys | PCI DSS Req 3.5, 3.7 | DA_domain04 findings 1, 2, 7 | P0 |
| 11 | D01, D02 | branded-currency_LIB, cbts-client_LIB | Trust-all X509TrustManager installed via SSLContext.setDefault() in cbts-client — all HTTPS connections in the JVM unvalidated. CreditCardVO exposes full PAN and CVV via public getters with no tokenisation, masking, or post-auth purge | PAN, CVV | PCI DSS Req 4.2.1, 3.3 | DA_domain01 Finding 3; DA_domain02 P0-3; brandedCurrencyTestContext.xml:27–33 | P0 |
| 12 | D03 | enrollment_LIB | SSN, DOB, full ACH account and routing numbers StrongBox-decrypted into JVM heap and emitted to fixed-width flat files staged to FTP without PGP or AES encryption | SSN, DDA, DOB | PCI DSS Req 3.4, GLBA Safeguards Rule | DA_domain03 P0-02; ExtractInfo.java | P0 |
| 13 | D07 | notification-requests-generator_LIB | Full cardholder PII (name, email, address, phone) logged at INFO level — up to 1 GB log files on disk; PII transmitted over unencrypted Syslog to 10.1.1.130 | Full PII | PCI DSS Req 3.3, GDPR Art. 32, GLBA | NotificationRequestDetailsRowMapper.java:42–113; DA_domain07 Finding 3 | P0 |
| 14 | D04 | scheduler_WAPP | All four core platform database passwords (cbaseapp, ecountcore, jobsvc, ordersvc) in plaintext in .env and .env-dev files committed to Git | Database credentials | PCI DSS Req 8.3, 2.2.2 | DA_domain04 Finding 1 | P0 |
| 15 | D05, D08 | strongbox-lib_LIB, rsa-mfa_LIB | Decrypted plaintext and RSA key material logged at DEBUG (RepositoryServiceLibrary.java:87; AsymmetricKey.java:40–41); OTP tokens logged at INFO (AuthenticationServiceImpl.java:871); DDA numbers at INFO in recipient-screening-api (lines 65, 84) | Key material, SAD, DDA | PCI DSS Req 3.3, 10.3, GLBA | DA_domain05 compliance gaps 1, 4 | P1 |
| 16 | D01, D04, D06 | accept-prechecks_API, auto-card-batch_LIB, consumerload_API, csa_WAPP, account-management-payout | Financial data and SSN logged unmasked: checkNumber/lastName at INFO (AcceptPrecheckServiceImpl.java:58,70); memberId at DEBUG globally (AutoCardCreateWriter.java:63); full SOAP including PAN/CVV at DEBUG (consumerload_API); SSN components at INFO in audit log (audit.properties:48); decrypted DDA at INFO (AccountManagementHandlerImpl.java:100) | PAN, SAD, SSN, PII | PCI DSS Req 10.3, CCPA, GLBA | DA_domain01 Finding 4; DA_domain04 findings 5, 6 | P1 |
| 17 | D10 | DS_ETL_warehouse, DS_CCP_ccp-export | DPAPI machine-bound credential encryption for all warehouse ETL passwords tied to individual user account NAM\nick.doan — single-person key-man risk; flat-file card number export in DS_CCP_ccp-export with no confirmed post-SFTP deletion step; SMTP mail connection with EnableSsl=False | Credentials, PAN | PCI DSS Req 3.5, 3.7, 4.2 | DA_domain10 F-DA-10-03, F-DA-10-06 | P1 |
| 18 | D09 | stand-in-processing-api | Azure App Configuration HMAC access key committed to .env (line 2) — Azure App Configuration may store Key Vault references for multiple services; committed key enables interception of all service configuration at application startup | System credentials | PCI DSS Req 8.3.6 | DA_domain09 F-DA-09-01; stand-in-processing-api/03_devops_operations.md | P0 |
| 19 | D08 | xplatform-library_LIB, xsso_SVC | Broken cryptographic algorithms publicly callable: MD5, SHA1, DES, RC4, RC2; active use in xsso_SVC with hardcoded IV "12345678".getBytes() in DESedeFactory.java:38 — fixed IV eliminates CBC security | Key material, credentials | PCI DSS Req 6.3, NIST SP 800-131A Rev 2 | DA_domain08 P1-04; DESedeFactory.java:38 | P1 |
| 20 | D01, D06 | branded-currency_LIB, autoclaim-split-svc_LIB | Non-atomic dual-database writes: MoneyTransferHelper.transferCommit() writes to EcountCore, then dbo.claim_payment to cbaseapp with no XA/saga coordination — failure between calls leaves money moved but payment status unclaimed; double-disbursement risk via autofile ScheduleFundsRetry idempotency bug | Financial integrity | Reg E, internal financial controls | DA_domain01 Finding 6; DA_domain02 P1-7; ClaimTransactionImpl.java:326–419 | P1 |

---

## 5. Encryption & Key Management Assessment

### 5.1 Encryption at Rest

**ecountcore PAN protection:** SQL Server Certificate-Level Encryption (CLE) using card_number_cert symmetric key protects core_card_master.card_encrypted. The decryption function app_func_get_card_number_by_id returns CHAR(16) plaintext PAN. Any principal with CONTROL DATABASE permission can access the symmetric key and decrypt all PANs. No key management documentation (dual control, split knowledge, rotation schedule) is evidenced in any repository, as required by PCI DSS Req 3.7. The SHA-1 card_hash (hashbytes('sha1', card_number)) provides a cross-database matching token but SHA-1 is cryptographically broken and pre-computable.

**StrongBox vault encryption:** V1 data uses DESede/CBC/PKCS5Padding — non-compliant (NIST-deprecated, disallowed by PCI DSS v4.0 for new implementations). V2 uses AES-128-CBC — minimum bar but AES-256-GCM with authenticated encryption is required for new implementations. Key wrapping uses RSA/ECB/NoPadding — no semantic security; CCA-vulnerable. No V3 cipher suite (AES-256-GCM + RSA-OAEP) has been implemented. No key rotation mechanism is present in any StrongBox codebase.

**Warehouse (prepaid_warehouse):** No column-level encryption. No Dynamic Data Masking on dim.DimAccountHolder. TDE at SQL Server instance level provides at-rest protection for database files but does not protect data from authorized SQL queries. The full PII and DDA surface in the warehouse is queryable by any database role member with SELECT grants.

**Gen-3 services:** nexpay-recipient-profile-svc stores DOB, email, and phone as plain VARCHAR with no @Convert encryption annotation and no pgcrypto column encryption. nexpay-cardprocessor-svc stores only masked PANs (first6/Xs/last4) — compliant for the card table, pending FIS JSONB audit.

**Filesystem batch files:** Plaintext in all cases identified. Emboss XML, CP2E files, check files, enrollment flat files, and request-file_LIB XML all lack file-level encryption. GPG encryption for check files is commented out in check-issuance_LIB. No filesystem encryption (BitLocker/LUKS) is confirmed in any repo configuration.

### 5.2 Encryption in Transit

**TLS validation bypass (systemic):** trustServerCertificate=true is present in JDBC connection strings across Domains 01, 03, 04, 05, 09, and 14 — disabling TLS hostname certificate validation on SQL Server connections carrying PAN, DDA, and SSN. This pattern eliminates MITM protection for database traffic. cbts-client_LIB installs a trust-all X509TrustManager via SSLContext.setDefault(), affecting all HTTPS connections in the JVM. rsa-mfa_LIB uses TrustAllSSLSocketFactory. wirecard_sftp-common-utilities_LIB sets setAllowUnknownKeys(true) on all SFTP connections — enabling SFTP host impersonation for payment file delivery.

**XML-RPC transport:** xml-rpc_LIB and xml-rpc-clients_LIB have no code-level enforcement of HTTPS. All sensitive data (PAN, SSN, DDA, SecureUserProfile PIN hashes) traverses this transport. TLS depends entirely on Director-returned endpoint URLs. Any HTTP URL in Director configuration produces a plaintext data transmission.

**Syslog transport:** notification-requests-generator_LIB transmits full cardholder PII over unencrypted UDP Syslog to 10.1.1.130 — plaintext PII on the internal network.

**TIBCO EMS and Filebeat:** ssl_enable_verify_host=false (TIBCO EMS in CONFIG) and ssl.verification_mode: none (Filebeat) disable certificate validation for message bus and log shipping transport.

**Gen-3 services:** nexpay-cardprocessor-svc uses Azure Managed Identity for passwordless database auth; Azure Key Vault for all credentials. Gen-3 pattern is the target architecture.

### 5.3 Key Management

**HSM absence:** No Hardware Security Module integration is evidenced in any of the 363 repositories. The StrongBox vault stores all key material in SQL Server. PCI DSS Req 3.7 dual-control and split-knowledge requirements for key-encrypting keys are not met anywhere in the Gen-1/Gen-2 estate.

**Key material in Git:** PGP private keys (cross-border-transfer-service_SVC, wirecard_test-utilities_LIB, wirecard_sg-bank-agent_LIB), JWE/DDA encryption keys (cs-api-v3 applicationContext-CSWS.properties, account-management-api accountmanagementapi.yaml), SFTP RSA private key (Titan PROD in infrastructure repo), and JKS keystore files (xsso_SVC, default password "ecount") are all committed to version control.

**Key rotation:** No key rotation mechanism is present in StrongBox. DPAPI machine-bound ETL encryption in DS_ETL_warehouse is tied to a single user account (NAM\nick.doan), creating a key-man risk for all warehouse ETL operations.

**Hashing:** SHA-1 is the active PAN hashing algorithm in ecountcore core_card_master.card_hash. SHA-1 is considered cryptographically broken and pre-computable for PAN values (limited search space). Migration to SHA-256 with per-card random salt is required for PCI DSS Req 3.5.1 compliance.

**Password hashing:** MD5 password hashes are active in xsecurity_SVC BasicUserValidationInformation, clientzone_WAPP, csa_WAPP, and workbench_WAPP. MD5 is not an acceptable password hashing algorithm under PCI DSS Req 8. PBKDF2-HMAC-SHA256 at 10,240 iterations (xsecurity_SVC) is below the NIST SP 800-63B current recommendation of 600,000 iterations.

---

## 6. Data Lineage: Critical Financial Flows

### 6.1 Card Issuance — Order Through Embossing

```
clientapi_API
  → order_SVC (ProcessInstantIssueRequest via HTTP Invoker)
  → account-service_LIB (AddFunds.execute())
    → TransferDelegate.quickLoad() → EcountCore ecountcore DB [PAN assigned]
    → AchTransferDetailCreate SP → jobsvc DB
    → ClaimCodeIssuanceInfoDao → ecountcore DB (if claimable)
    → SmsQueueDao.insertQueueMessage() → notificationsvc DB

auto-card-batch_LIB (batch path)
  → Director → ecountcore credentials (Windows Registry plaintext)
  → SP: dbo.auto_card_creation_order_load → ecountcore DB
  → SP: dbo.autocard_get_record → ecountcore DB (retrieves candidates)
  → IDeviceManager.createECard() → ecountcore (card provisioning, PAN assigned)

emboss-extract_LIB (bureau egress)
  → SP: dbo.core_process_emboss_queue_extract → ecountcore (PANs extracted)
  → StaxEmbossExtractBuilder → XML file /upload/EmbossFileExtract/ [PAN PLAINTEXT ON DISK]
  → NDM/Connect:Direct transmission to FDR / PSX / ARROWEYE / CITI-NAOT
```

**Gaps and risks:** PAN is written in plaintext to the local filesystem at the emboss step. There is no PGP encryption of the emboss file before transmission. The transmission protocol (NDM/Connect:Direct) provides transport-layer encryption but the at-rest window on the host filesystem is unprotected. Credential management for the Director-to-ecountcore path relies on Windows Registry plaintext passwords, meaning any process on the host can extract all database passwords. The batch card issuance flow has no atomic dual-database transaction management — a failure between card provisioning and the threshold check can leave a partially-issued card record.

### 6.2 ACH Disbursement — Order Through NACHA File

```
ach-withdrawal-initiator
  → Director → JobsvcDataSource, EcountCoreDataSource, CbaseappDataSource
  → ACH request table (SQL Server) — PENDING status
  → StrongBox XML-RPC → bank account number + routing number (DDA)
  → Tabapay REST API call (SharedServiceHelper logs full request at INFO [DDA, name, amount])
  → autofile_funds_retry_queue → retry table (no purge job; idempotency bug → duplicate entries)

ieft-cp2e
  → StrongBox → DDA and routing number (plaintext in JVM heap after decryption)
  → CP2E fixed-width file (128-char records, bank account numbers) written to local FS [PLAINTEXT]
  → file-transfer-service → SFTP to Citibank
     [SFtpConnection.java logs SFTP password at INFO level]
```

**Gaps and risks:** DDA numbers are written to CP2E files in plaintext on the local filesystem between batch steps. GPG encryption for check files is commented out. Tabapay API request body (including cardholder name, disbursement amount, card identifiers, and partial card numbers) logged at INFO level — shipped to log aggregation. The autofile_funds_retry_queue idempotency bug can generate duplicate disbursements (Reg E erroneous transfer). The retry queue has no bounded purge job.

### 6.3 STIP / Stand-In Auth Flow

```
Card network authorization request
  → stand-in-processing-api (Azure SQL SASI DB, 5 JPA configurations)
    → ecountcore: fdr_card_account_create SP (reads @cv_code parameter → fdr_card_account_detail.cv_code)
    → cbaseapp: product rules (DDA serial allocation)
    → LegacyCryptoService (eCount field encryption format)
    → DdaNumberStatus / DdaReservation (DDA numbers, no column-level encryption)
  → SetPinRequest model (if PIN operation — HSM path unconfirmed)
  → Azure Service Bus (async failover)
  ← stand-in-recovery-service (STIR)
    → on-premises cbaseapp and ecountcore via Wirecard network segment
      [trustServerCertificate=true — TLS cert validation disabled]
    → RecoverySession / RecoverySnapshot (no retention policy)
```

**Gaps and risks:** The cv_code column in ecountcore (accessed during SASI card creation stored procedure) requires immediate verification — if CVV is stored post-authorisation this is a P0 PCI DSS finding. DDA numbers in the SASI primary database are protected only by Azure SQL TDE (not column-level encryption). PIN processing path does not confirm HSM integration. Wirecard-era network segment connections (wirecard.sys domain) disable TLS certificate validation. Stand-in recovery records accumulate indefinitely with no purge.

### 6.4 OFAC Screening — DDA Lookup Through Decision

```
Payout orchestrator (nexpay-recipientorchestrator-svc)
  → POST /api/v1/screening/request [UNAUTHENTICATED ENDPOINT]
    Body: firstName, lastName, dob, phone, emails, address, ddaNumber, memberId
  → recipient-screening-api
    [DDA number logged at INFO — RecipientScreeningService.java lines 65 and 84]
    → om-recipientsanctioning-svc (OAuth2 client_credentials)
    → Sanctions vendor
    → EcountCore DB: resolve DDA → member records
    → SanctionMemberHandler: block/unblock eCount devices
  ← POST /sanction/webhook [UNAUTHENTICATED WEBHOOK]
    → SanctionMemberHandler: apply DECLINED/APPROVED
       → update_core_records_to_block_all_beneficiary_accounts() [DDA block on EcountCore]
```

**Gaps and risks:** Both the screening submission endpoint and the webhook callback are unauthenticated. A spoofed DECLINED webhook can permanently block any legitimate cardholder's DDA accounts in EcountCore without authentication. DDA numbers are logged in plaintext at INFO on every screening request — persisted in log aggregation systems for the full retention period. For cross-border transfers (Cambridge CBTS), no OFAC screening is implemented at all — beneficiary records are created and funds transferred without any SDN check.

---

## 7. Compliance Gap Table

| Regulation | Requirement | Current State | Gap | Domain(s) Affected | Remediation |
|---|---|---|---|---|---|
| PCI DSS Req 3.2.1 | SAD (CVV, PIN, Track) must not be stored post-authorisation | ecountcore cv_code status unverified; Cardtype.cvcode written to disk XML; CORP_CONTACT.T_PIN column exists; CVV in CreditCardVO Java heap; CVVs in test fixtures | Critical — multiple violations confirmed or suspected | D01, D04, D07, D09, D10, D13, D14, D15 | Immediately verify cv_code column content; apply @XmlTransient to Cardtype.cvcode; classify T_PIN; remove CVVs from test fixtures and rewrite Git history |
| PCI DSS Req 3.3.1 | PAN must be rendered unreadable wherever stored | CLE on ecountcore card_encrypted (compliant); PAN in emboss XML plaintext; PAN in request-file_LIB XML; PAN in Sunrise flat file; PANs in test fixtures; Ehcache disk tier unverified | Critical — plaintext PAN on disk in multiple repos | D01, D07, D08, D10, D14, D15 | Encrypt emboss files before disk write; apply @XmlTransient to Cardtype.cardnumber; confirm Ehcache disk encryption; purge PANs from test fixtures |
| PCI DSS Req 3.5 / 3.7 | Protect cryptographic keys; key management procedures | StrongBox keys and ciphertext co-located in same DB; RSA keys as plain VARCHAR; JWE keys, PGP keys, SFTP keys committed to Git; no HSM; no key rotation; SHA-1 card hash | Critical across entire estate | D01, D02, D04, D05, D08, D12, D13 | Implement Azure Key Vault for all secrets; migrate StrongBox to HSM-backed; rotate all committed keys; migrate SHA-1 to SHA-256 with salt; establish key rotation schedule |
| PCI DSS Req 4.2.1 | Strong cryptography for CHD in transit | trustServerCertificate=true on JDBC across 6+ domains; cbts-client trust-all X509TrustManager; rsa-mfa TrustAllSSLSocketFactory; SFTP setAllowUnknownKeys=true; Syslog unencrypted; AJP/1.3 unencrypted; no code-level HTTPS enforcement in XML-RPC | Critical — MITM exposure on all database, MFA, and SFTP connections | D01, D02, D03, D04, D05, D07, D08, D09, D12, D13 | Remove trustServerCertificate=true from all JDBC URLs; fix cbts-client TLS; enforce HTTPS at XML-RPC transport layer; migrate Syslog to TLS (RFC 5425) |
| PCI DSS Req 7 / 8 | Access control; unique IDs; credential management | Production passwords in Git (all CONFIG repos); Windows Registry (Gen-1 Director); database credentials in test fixtures; default JWE key in source; shared b2cstage credentials across services; MD5 password hashes active | Critical — credential exposure across entire estate | D01, D02, D04, D05, D06, D12, D13, D14 | Rotate all committed secrets; implement Azure Key Vault for all services; replace MD5 with bcrypt/Argon2; enforce Managed Identity for Gen-3 |
| PCI DSS Req 10.2 / 10.3 | Audit log all CHD access; protect logs | DDA, SSN, PAN in plaintext INFO logs; Syslog unencrypted; no search audit trail in xsearch stack; ThreadLocal lost across thread pools breaks audit correlation; CloudWatch 14-day retention (minimum 12 months required) | High — log integrity and completeness failures | D01, D04, D05, D07, D08, D12, D15 | Implement log masking library; enforce TLS Syslog; implement xsearch audit log; fix ThreadLocal propagation; extend CloudWatch retention to 365 days |
| GLBA Safeguards Rule | Protect consumer financial information | enrollment_LIB flat files contain SSN and full bank account details unencrypted; DDA numbers logged at INFO across 8 domains; SSN in csa_WAPP audit log; SSN in command-line arguments (windows-scripts) | High | D01, D03, D04, D06, D07, D12 | PGP-encrypt enrollment flat files; mask DDA numbers in all log statements; remove SSN from audit log fields; prohibit PII in CLI arguments |
| GDPR Art. 9, 17, 32 | Special category data; right to erasure; appropriate security | DOB, email, phone unencrypted in nexpay-recipient-profile-svc; append-only SMS/notification tables with no erasure path; saga error_message may embed PII; employee PII in Flyway seed (nexpay-claim-code-svc V5__create_recipient_registration.sql:40); soft-delete in message-center_SVC does not satisfy Art. 17 | High — erasure and security obligations unmet | D01, D03, D07, D11 | Encrypt DOB/email/phone at column level; implement data retention and deletion schedules; implement hard-delete for message-center; remove employee email from Flyway seed |
| CCPA | Right to deletion; data minimization | PII in append-only tables; no deletion mechanism for warehouse dim.DimAccountHolder; saga records accumulate indefinitely; aml-name-screening_LIB writes full PII to XLS files with no retention or deletion | High | D01, D03, D05, D10, D11 | Implement warehouse partition drop for aged data; GDPR/CCPA deletion procedure for dim.DimAccountHolder; define saga retention TTL and archival |
| SOC 2 (CC6, CC7) | Logical access; monitoring | No VPC Flow Logs; no SBOM CVE correlation; Spring Config Server with no confirmed auth; SNAPSHOT dependency chain breaks reproducible builds; no schema versioning across 22+ Gen-1 repos | Medium — control evidence gaps for QSA/auditor | D06, D12, D14, D15 | Enable VPC Flow Logs; deploy OWASP Dependency-Track; pin all SNAPSHOT dependencies; implement Flyway/Liquibase for ecountcore and cbaseapp |
| NACHA / Reg E | ACH file integrity; error resolution | autofile_funds_retry_queue idempotency bug → duplicate disbursements; no Reg E provisional credit artefacts in chargeback automation; expired eCheck activation_date not validated in autoclaim; ACH return code validation absent | High | D02, D06 | Fix ScheduleFundsRetry idempotency; add unique constraint on retry queue; validate eCheck expiration_date; add Reg E investigation window artefacts |
| OFAC / BSA-AML | Sanctions screening before fund release | Cross-border CBTS transfers executed without SDN check; OFAC screening API unauthenticated; autoclaim beneficiary routed without OFAC check; no OFAC check in any Domain 01 repo | Critical — retroactive assessment required | D01, D02, D03, D06 | Engage Legal/Compliance immediately; add OFAC screening to Cambridge CBTS pre-transfer flow; authenticate screening API and webhook |

---

## 8. Data Platform & Analytics Assessment (Domain 10)

### Overview

Domain 10 encompasses approximately 80 DS_-prefixed repositories, representing two decades of organic SQL Server growth. The analytical layer is built on a SQL Server 2012-era SSIS ETL toolchain (~100 packages in DS_ETL_warehouse) populating a dimensional warehouse (DS_DB_prepaid_warehouse) and an SSAS Multidimensional OLAP cube (Domestic_OLAP in DS_WH_ecount-warehouse) last meaningfully updated on 2017-06-05. This frozen analytical layer is now eight years behind the product's current cardholder data model.

### Schema Coverage Gaps

The Prepaid Warehouse.dsv (Data Source View) frozen at 2017 means any new dimensions, measures, or fact tables added since 2017 are absent from OLAP cube definitions. Gen-3 NexPay data (nexpay-cardprocessor-svc PostgreSQL, nexpay-recipient-profile-svc PostgreSQL, saga databases) is not represented in any analytical table. The SSAS Domestic_OLAP cube is unaware of Onbe's current product offerings and post-Wirecard cardholder programs. The SSAS Multidimensional model cannot be refreshed with the Tabular migration path without significant schema rework.

The prepaid_warehouse schema contains approximately 60 date-stamped procedure variants (rpt_Inventory_Management_Report_card_reissue_06042013, rpt_T_Mobile_weekly02182014) and work/staging/hold table variants — evidence of changes made by copying objects rather than versioning them. SqlServerVerification is False in the SSDT project settings, allowing broken SQL to compile without build failure.

### SSIS / SSAS EOL Risk

SQL Server Integration Services 2012 and SQL Server Analysis Services Multidimensional 2012/2014 are in the extended support phase. Microsoft ended mainstream support for SQL Server 2012 in 2017 and extended support in 2022. The DS_ETL_warehouse packages use CDC Control tasks with LSN watermarks that are version-coupled to the source ecountcore database. Any upgrade of the source database SQL Server version requires ETL retesting across all 100 packages.

### Wirecard-Era Infrastructure Still Referenced

The ecountcore source for DS_ETL_warehouse is configured against server P-NA-DB11 (p-db06\db06 in the data lineage map) and the DPAPI credential encryption is bound to user NAM\nick.doan — both are Wirecard-era naming conventions. The DS_CCP_ccp-export project connects to Oracle DWH via Oracle Net (TNS) without confirmed encryption. DW_ETL_Master.dtsConfig production connection strings are not in version control — only the DPAPI-encrypted project-level credentials are tracked in Git.

### PAN and DDA in Analytical Tables

dim.DimAccountHolder stores DDANumber as CHAR(16) unencrypted, alongside HomeEmail, BusinessEmail, HomePhone, BusinessPhone, Address1, Address2, ZipCode, City, State, Country, FirstName, LastName, MiddleName, SuffixName — all as plaintext VARCHAR columns, queryable by any warehouse role member. fact.FactPaymentTransactions, fact.FactUtilizationTransactions, and fact.FactCardAccountDetail all store DDANumber VARCHAR(16) unencrypted. ecountcore accepts PAN as a @card_number parameter in stored procedures — if SQL monitoring tools are configured with parameter capture enabled, PANs appear in query execution logs. No Dynamic Data Masking is applied in prepaid_warehouse.

### CI/CD Absence

Zero CI/CD exists across all Domain 10 database repositories. No automated build, test, or deployment pipeline is present in any DS_-prefix repo. Schema changes are applied manually by DBAs. SSIS package execution is managed by SQL Server Agent jobs on the host servers. The SBOM for ecountcore dependencies is not tracked. This means vulnerable database components are not subject to any automated CVE alerting.

### Recommendations (Domain 10 Specific)

1. Immediately verify cv_code storage and engage QSA; implement purge procedure for any live CVV values.
2. Disable SQL monitoring parameter capture for all stored procedures that accept @card_number or @dda_number parameters.
3. Migrate DS_ETL_warehouse SSIS protection level from EncryptSensitiveWithUserKey to DontSaveSensitive; implement SSIS Catalog environment variables backed by Azure Key Vault; version-control all configuration equivalents of .dtsConfig.
4. Implement Dynamic Data Masking for dim.DimAccountHolder in non-production; apply row-level security and column masking in production SSAS roles; restrict CubeReader role from DDA and PII columns.
5. Plan a warehouse modernization programme: migrate SSAS Multidimensional to Fabric/Synapse Analytics tabular model; incorporate Gen-3 NexPay data sources; implement SHA-256 card hashing before warehouse refresh; establish GDPR/CCPA right-to-deletion stored procedure for dim.DimAccountHolder.

---

## 9. Strategic Data Architecture Recommendations (Top 10)

### Recommendation 1 — Immediate Secret Remediation and Vault Migration (P0, Week 1–2)

**What:** Rotate all credentials, PGP private keys, JWE keys, SFTP keys, and API secrets committed to Git across all 15 domains. Purge from Git history using git-filter-repo or BFG Repo Cleaner across every affected repository. Rebuild all Docker images from clean sources. Implement Azure Key Vault as the authoritative runtime secret store for all Gen-1/Gen-2 services (using Spring Cloud Azure Key Vault Secrets as the injection mechanism); Gen-3 services should use Azure Managed Identity with no secrets in source.

**Why:** Git repositories are currently the de facto authoritative secret store for the entire platform. Any developer with clone access holds production database passwords, PGP private keys, and encryption keys. This is the single highest-severity finding in the estate because it undermines every other security control.

**Domains affected:** All 15. Priority order: cross-border-transfer-service_SVC (PGP private key); wirecard_sg-bank-agent_LIB (SFTP RSA key, AWS access key, PGP key); scheduler_WAPP (four database passwords); cs-api-v3 (JWE DDA key); stand-in-processing-api (App Config HMAC key); api-config-repo (JWE keys, CBTS credentials); director-svc_SVC (database passwords in appsettings.json).

**Priority:** P0

---

### Recommendation 2 — CVV Storage Verification and Elimination (P0, Sprint 1)

**What:** Execute an immediate SQL query against ecountcore fdr_card_account_detail to determine whether the cv_code column contains live CVV values or null/masked values. If live CVV values are present: (a) engage the PCI QSA immediately; (b) implement a purge procedure that runs after each card creation transaction; (c) assess whether a breach notification obligation exists. Separately: apply @XmlTransient to Cardtype.cvcode in request-file_LIB; classify CORP_CONTACT.T_PIN in wirecard_corporate-client-module_LIB; remove CVV from CreditCardVO public getter in branded-currency_LIB; remove CVV from all test fixtures and rewrite Git history for six Domain 14 repositories.

**Why:** Storing CVV post-authorisation is an unconditional PCI DSS Req 3.2.1 violation. No compensating control exists. If confirmed, this finding invalidates Onbe's PCI DSS compliance posture entirely until remediated.

**Domains affected:** D01, D07, D09, D10, D13, D14, D15.

**Priority:** P0

---

### Recommendation 3 — Domain-Wide Log Masking Framework (P1, Weeks 2–6)

**What:** Implement a platform-wide log masking library with a Luhn-validated regex pattern for PAN detection (not just element-name matching), plus explicit masks for DDA (last-4 only), SSN (full redaction), CVV (full redaction), OTP tokens, RSA/PGP key material, and passwords. Deploy as a mandatory SLF4J/Logback/Log4j2 appender decorator across all services. Migrate Syslog transport to TLS (RFC 5425). Apply immediately to: notification-requests-generator_LIB (PII at INFO); recipient-screening-api (DDA at INFO lines 65, 84); rsa-mfa_LIB (OTP and phone at INFO); account-management-payout (DDA at INFO, line 100); strongbox-lib_LIB (key material at DEBUG); csa_WAPP (SSN in audit log); XmlRPCServletHelper.java (full RPC payload at DEBUG, lines 280–285, 309–323).

**Why:** Unmasked sensitive data in application logs creates a secondary, uncontrolled retention pathway that persists through log aggregation systems (ChaosSearch, Splunk, S3) for years beyond the retention window of the originating application. This directly violates PCI DSS Req 3.3.1, GDPR Art. 32, and GLBA.

**Domains affected:** D01, D02, D03, D04, D05, D06, D07, D08, D12.

**Priority:** P1

---

### Recommendation 4 — Emboss and Batch File Encryption (P0, Weeks 2–4)

**What:** Implement PGP encryption of emboss XML output in emboss-extract_LIB before writing to /upload/EmbossFileExtract/. Use a managed PGP key stored in Azure Key Vault (not committed to Git). Re-enable GPG encryption for check issuance output files in check-issuance_LIB. Add AES-256 file encryption for CP2E output in ieft-cp2e before file-transfer-service picks up the file. Add PGP encryption to enrollment_LIB fixed-width flat files before FTP staging. Confirm and document filesystem ACLs for all batch output directories. Coordinate with FDR, PSX, ARROWEYE, CITI-NAOT, Sterling NDM, and partner banks for encrypted file acceptance.

**Why:** PAN-in-plaintext on disk is a PCI DSS Req 3.4/3.5.1 violation. The emboss file is the highest-risk data artefact produced by the platform: it contains full PANs and expiry dates for all newly issued cards, transmitted directly to card bureaus. SSN and full bank account numbers in enrollment flat files create GLBA Safeguards Rule exposure.

**Domains affected:** D01, D02, D03.

**Priority:** P0

---

### Recommendation 5 — StrongBox Key Management Remediation (P1, Quarter 1)

**What:** Phase 1 (immediate): Apply SQL Server Always Encrypted with Azure Key Vault column master keys to the private_key and key_value columns in the strongbox database. This fixes the PCI DSS Req 3.6.1 co-location violation without a full vault migration. Phase 2 (quarter): Implement a V3 cipher suite (AES-256-GCM + RSA-OAEP for key wrapping) as the default for all new StrongBox writes. Migrate high-priority data categories (SSN records, bank account records) to V3. Retire V1 DESede data by migration. Phase 3 (6–12 months): Migrate StrongBox key material to Azure Key Vault (cloud-deployed services) or an HSM appliance (on-premises Gen-1 services), eliminating the JDBC-backed DataRepository as the key store.

**Why:** The StrongBox architecture is the antithesis of key management best practice: the RSA private key-encrypting key is co-located with the AES symmetric keys and ciphertext in a single database. A single stored-procedure call delivers the complete decryption chain. This violates PCI DSS Req 3.6.1 and NIST SP 800-57 Section 8.2.3.

**Domains affected:** D01, D05, D08, D10.

**Priority:** P1

---

### Recommendation 6 — PAN Masking Standardisation and SHA-1 Migration (P1, Quarter 1)

**What:** Fix MaskCCHelper.maskThisCC() in xsearch_LIB and xsearch-new_SVC to implement first-6/last-4 masking (currently exposes first-4/last-4, non-compliant). Update cs-api-v1, cs-api-v2, and clientzone_WAPP to use first-6/last-4 format. Remove raw cardNumber field from MemberInquiryValue or enforce masking at the setter so raw PAN is never serialized on the XML-RPC wire. Separately: migrate ecountcore core_card_master.card_hash from SHA-1 (hashbytes('sha1', card_number)) to SHA-256 with a per-card random salt. Coordinate cross-database migration of all consuming systems that use card_hash for matching.

**Why:** Non-compliant PAN masking (first-4/last-4) violates PCI DSS Req 3.3.1. SHA-1 is cryptographically broken and pre-computable for the limited PAN search space, violating PCI DSS Req 3.5.1 for hashed PANs.

**Domains affected:** D04, D08, D10.

**Priority:** P1

---

### Recommendation 7 — DDA Number Protection at Rest and in Transit (P1, Quarter 1)

**What:** Apply column-level encryption (Azure SQL Always Encrypted or application-layer AES-256) to DDA number fields in the SASI primary database (DdaNumberStatus, DdaReservation, MemberAccountShadow). Apply the same control to CBTS BENEFICIARY.ACCOUNT_NUMBER and ROUTING_CODE in SQL Server. Mask DDA numbers to last-4 in all log statements across recipient-screening-api, account-management-payout, chargeback-engine_LIB, auto-card-batch_LIB, and cbts-client_LIB. Confirm TDE is enabled on all SQL Server databases holding DDA data.

**Why:** DDA numbers are bank account numbers regulated under GLBA and NACHA. They appear in INFO-level logs across at least eight domains, in plaintext database columns without column-level encryption, and in plaintext batch files. TDE alone does not protect against authorized SQL queries.

**Domains affected:** D01, D02, D03, D04, D09, D13.

**Priority:** P1

---

### Recommendation 8 — Analytics Modernisation and PII Access Controls (P2, Quarter 2)

**What:** Implement Dynamic Data Masking on dim.DimAccountHolder in non-production environments; implement SSAS role-level column masking for CubeReader and ClientServices roles in production; create a data classification registry for all warehouse tables. Implement a GDPR/CCPA right-to-deletion stored procedure for dim.DimAccountHolder (delete or anonymise all PII for a given cardholder across all partitions). Implement a rolling partition drop for fact tables beyond the defined retention window. Plan warehouse modernisation: migrate from SSAS Multidimensional to Azure Synapse Analytics or Microsoft Fabric; incorporate Gen-3 NexPay PostgreSQL data sources; establish CI/CD pipeline for all DS_-prefix repositories.

**Why:** The prepaid_warehouse contains full cardholder PII and DDA numbers queryable by any warehouse role with SELECT grants. The SSAS cube is eight years out of date and does not reflect current product offerings. Zero CI/CD across 80+ database repos means vulnerable components receive no automated CVE alerting.

**Domains affected:** D10.

**Priority:** P2

---

### Recommendation 9 — Data Retention, Erasure, and Schema Versioning (P1, Quarter 1–2)

**What:** Define and implement data retention schedules for: sms_notification_queue and claim_code_issuance_info (Domain 01) — 24 months for Reg E, then deletion; mailgun_events_queue (Domain 07) — 90 days operational, 7 years Reg E compliance records; saga tables in both orchestrators (Domain 11) — archive to cold storage after 7 years, then delete PII fields. Implement hard-delete or PII-stripping in message-center_SVC to satisfy GDPR Art. 17. Remove real employee email (andrew.smirnoff@onbe.com) from V5 Flyway migration seed in nexpay-claim-code-svc. Introduce Flyway or Liquibase schema versioning for ecountcore and cbaseapp as a prerequisite for any Gen-3 migration.

**Why:** Append-only tables with no deletion or anonymisation mechanism cannot satisfy GDPR Art. 17 right to erasure or CCPA deletion rights. The absence of schema versioning across 22+ Gen-1 repositories makes database drift between environments undetectable and Gen-3 migration dependent on complete reverse-engineering of the stored procedure layer.

**Domains affected:** D01, D03, D06, D07, D11.

**Priority:** P1

---

### Recommendation 10 — OFAC Screening Hardening and Credential Cryptography Uplift (P0/P1, Quarter 1)

**What:** Authenticate the OFAC screening API submission endpoint and webhook callback in recipient-screening-api (add OAuth2 client_credentials on submission; validate signed HMAC on webhook). Implement OFAC SDN screening for all Cambridge CBTS beneficiary records before fund release in cross-border-transfer-service_SVC. Replace MD5 password hashing with bcrypt or Argon2 in xsecurity_SVC, clientzone_WAPP, csa_WAPP, and workbench_WAPP; force-expire all existing MD5-hashed credentials. Upgrade PBKDF2 iteration count from 10,240 to minimum 600,000 per NIST SP 800-63B. Replace DES/3DES and RC4 in xplatform-library_LIB with AES-256-GCM for all CHD-adjacent operations. Remove the hardcoded IV ("12345678".getBytes()) from xsso_SVC DESedeFactory.java:38.

**Why:** The unauthenticated OFAC webhook is a critical financial integrity risk — a spoofed DECLINED message permanently blocks legitimate cardholders. The absence of OFAC screening for Cambridge FX transfers is a regulatory violation requiring retroactive assessment. MD5 password hashing is brute-force feasible via rainbow tables and is explicitly prohibited by PCI DSS Req 8.

**Domains affected:** D02, D03, D05, D08.

**Priority:** P0 (OFAC/webhook), P1 (credential cryptography)

---

*This document was produced by automated synthesis of 15 domain-level Data Architect analyses covering all 363 repositories in the Onbe estate. All findings are grounded in domain synthesis files generated 2026-05-08. File:line citations reference source code locations as identified during the domain-level analysis phase. This document should be treated as a living artefact: the CVV storage verification (Recommendation 2) and OFAC screening gap (Recommendation 10) require immediate action before the next QSA assessment cycle regardless of any other prioritisation decisions.*
