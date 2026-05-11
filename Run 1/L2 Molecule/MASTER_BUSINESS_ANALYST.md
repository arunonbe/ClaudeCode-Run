# MASTER BUSINESS ANALYST VIEW — Onbe 363-Repo Estate

*Generated: 2026-05-08 | Source: 363 repositories across 15 business domains*

---

## 1. Executive Summary

### What Onbe's Technology Estate Does

Onbe is a PCI DSS Level 1 payments service provider that delivers B2C disbursements, prepaid card programs, ACH transfers, push-to-card payouts, international wire and FX transfers, and cardholder self-service across insurance, healthcare, auto finance, gig/creator economy, marketplace, and consumer rebate client segments. The technology estate analyzed across 363 repositories encompasses the full payment lifecycle: corporate client onboarding and program configuration, fund authorization, multi-rail disbursement (prepaid card, virtual card, ACH, push-to-debit, paper check, international wire/FX, PayPal, Venmo, Western Union), cardholder identity verification and OFAC screening, recipient self-service portals, customer service operations, financial reporting, and the underlying data and infrastructure platforms that sustain all of the above.

The estate serves hundreds of thousands of payment recipients annually across programs bearing the brands of clients such as Disney, Royal Caribbean, Subaru of America, and 40-plus additional named corporate programs visible in configuration files. Card programs operate under Visa and Mastercard network rules; ACH origination operates under NACHA rules; cardholder disclosures are governed by Regulation E; and the entire estate is subject to PCI DSS v4.0.1 Level 1, GLBA, GDPR/CCPA, OFAC, and SOC 1/SOC 2 obligations.

### Three Platform Generations

**Gen-1 — eCount / Citi Prepaid Heritage (~60% of live transaction volume)**
The oldest layer, built between approximately 2003 and 2016 under the eCount and then Citi Prepaid brand, remains the primary production system of record. It is characterized by SQL Server stored-procedure-centric data access, Java 5-8 runtimes, Apache Axis 1.4 SOAP interfaces, a proprietary XML-RPC inter-service bus, and Windows-hosted batch jobs on fixed filesystem paths (D:\c-base\). The eCountCore SQL Server database has been in continuous operation for approximately 20 years and is the authoritative ledger for cardholder accounts, card lifecycle, ACH transactions, and fee processing. Every other analytical and operational capability in the estate depends on it. The Director service is Onbe's proprietary service registry for this generation and is a platform-wide single point of failure: it distributes database credentials and endpoint URLs to every Gen-1 and Gen-2 service at startup with no caller authentication.

**Gen-2 — Wirecard / Northlane Platform (~30% of live transaction volume)**
Acquired through the Wirecard/Northlane corporate transaction, the Gen-2 platform adds containerized Spring Boot 2.x microservices on AWS ECS, an OAuth 2.0 JWT service-to-service authentication mesh, SFTP/PGP-based bank file exchange, and ActiveMQ event-driven orchestration for ACH, wire, check, and cross-border FX disbursements. The Gen-2 estate still carries wirecard.com and wirecard.sys namespace artifacts in production DNS, server names, and configuration. Wirecard AG entered insolvency in 2020; any dependency on Wirecard-operated infrastructure is an existential availability risk.

**Gen-3 — NexPay / OnePlatform (~10% of current transaction volume, primary investment)**
The strategic greenfield platform, built on Azure Container Apps and AKS, Java 21/25, Spring Boot 3.x/4.x, PostgreSQL, OpenAPI-first contracts, Azure Managed Identity, and event-driven orchestration. Gen-3 introduces the claim-code entitlement model, Orchestration Saga pattern for transactional integrity, Microsoft Entra External ID for cardholder authentication, and Azure Key Vault for secrets management. However, Gen-3 is not yet production-safe at scale: saga compensation logic is unimplemented in both orchestrators, the OFAC screening API is fully unauthenticated, payment authorization is disabled in at least one production-deployed API, an IVR BFF stub returns hardcoded PII values through an external-facing endpoint, and the shared parent POM ships as an unstable SNAPSHOT version.

### Compliance Posture — Business Summary

The estate carries a compliance posture that is deeply inconsistent across generations. Gen-1 carries the highest volume of active regulatory violations: PAN transmitted in plaintext emboss files sent to card bureaus, CVV potentially stored post-authorization in the primary card database, credentials committed to version control across more than 100 distinct secret values, an unauthenticated credential registry exposed to any network-reachable host, and no OFAC screening in any disbursement path within the domain. Gen-2 adds a TLS bypass that eliminates certificate validation JVM-wide for cross-border payment API calls, committed RSA and PGP private keys in production repositories, and a Reg E disclosure service that crashes at runtime. Gen-3's primary compliance risk is that several nominal controls -- OFAC screening, payment authorization, saga compensation -- are architecturally present but functionally disabled or stubbed in production code.

### Estate-Wide Finding Count

Across all 15 domains:

- **P0 (Critical -- immediate action required):** 29 findings
- **P1 (High -- remediate within 30-90 days):** 47 findings
- **P2 (Medium -- remediate within 90 days):** 31 findings

---

## 2. Business Capability Map (15 Domains)

| Domain | Business Capability | Client Impact | Generation | Maturity / Risk |
|---|---|---|---|---|
| **01 -- Card Program Management** | Full lifecycle of prepaid card programs: issuance, funding, account operations, notifications, FDR settlement, program configuration. Core of B2C prepaid for insurance, healthcare, auto, gig, rebate clients. | Outage halts card issuance and fund loading for all programs. | Gen-0/1 core; Gen-2/3 wrapping in migration | Low maturity. 3 P0 findings. PAN in plaintext emboss egress; unauthenticated Director; credentials in VCS. |
| **02 -- Disbursements & Payment Rails** | Multi-rail money movement: ACH, check, wire (Citi CP2E), FX (Cambridge/Corpay), push-to-debit (Tabapay). Covers Disney, RCCL, OnbeSunrise, and 40+ programs. | Outage stops all scheduled fund disbursements. Duplicate-payment bug in production. | Gen-1 batch dominant; Gen-2 FX services; Gen-3 nascent | Low maturity. 4 P0 findings. No OFAC screening on cross-border; TLS disabled JVM-wide; PGP key committed; idempotency bug creates duplicate disbursements. |
| **03 -- Recipient / Cardholder Experience** | Multi-rail payment choice, cardholder enrollment, IVR access, OFAC screening gate, claim code lifecycle, Gen-3 orchestration sagas. The sole channel through which recipients access funds. | Any failure creates Reg E dispute obligation and CFPB-reportable service event. | Gen-1 EOL portals; Gen-2 Django; Gen-3 NexPay active | Medium maturity for Gen-3; critical Gen-1 EOL risk. 3 P0 findings. Unauthenticated OFAC API; unimplemented saga compensation; Struts 1 RCE in CDE. |
| **04 -- Client Administration & Portal** | B2B client self-service (ClientZone), CSA agent desktop, distributed job scheduler, banker fund authorization, Great Plains ERP bridge, multi-API CS tier, cardholder self-service. | Scheduler outage blocks all batch disbursement timing. ClientZone is primary B2B channel. | Gen-1/2 dominant; Gen-3 partial | Low maturity. 3 P0 findings. Unauthenticated scheduler RCE; OFAC non-blocking; authorization disabled in payment APIs; committed JWE keys. |
| **05 -- Authentication & Identity** | KYC/CIP (Actimize), OFAC/sanctions screening, SSO, MFA, StrongBox cryptographic key vault, operator RBAC, API IP/cert access control, Gen-3 Entra External ID. | Compromise of StrongBox decrypts all Gen-1/Gen-2 cardholder data. OFAC bypass creates sanctions exposure. | Gen-1 StrongBox dominant; Gen-3 Entra | Very low maturity for Gen-1 stack. 4 P0 findings. Co-located keys and ciphertext; TLS disabled for MFA; MD5 passwords active; OFAC API unauthenticated. |
| **06 -- Order & Workflow Orchestration** | Batch disbursement processing for all file-based client programs: insurance, auto, marketplace. Job lifecycle, scheduling, workflow state machine, dual-authorization, client file integration. | Outage stops all batch client fund distributions, triggering SLA penalties. No Gen-3 equivalent exists. | Gen-1 exclusively | Very low maturity. 4 P0 findings. CVV2 potentially stored from push-to-debit settlement; plaintext credentials; SMS notification stub delivers nothing; Director SPOF. |
| **07 -- Content & Notification** | Multi-channel cardholder notifications (email, SMS stub), in-portal message center, brand asset delivery, batch payment file generation triggering downstream notifications. | SMS channel silently fails. Unfilled template placeholder violates Reg E. | Gen-1 notification; Gen-3 content assets | Low maturity. 3 P0 findings. CVV/PAN in batch XML files; SMS delivery stub; PII in plaintext logs. |
| **08 -- Search, Platform Core & Infrastructure** | eCountCore transaction processing, cardholder member/card search for CSA, fund transfer primitives, XML-RPC universal bus, platform cryptographic library, inter-service RPC clients. | xml-rpc_LIB failure simultaneously halts all Gen-1/Gen-2 services. Non-PCI PAN masking in CSA search. | Gen-1 exclusively | Very low maturity. 3 P0 findings. Unauthenticated XML-RPC dispatch; PIN hashes over HTTP; broken crypto in production infrastructure. |
| **09 -- STIP & Card Processing** | Card issuance (Thredd/FIS via nexpay-cardprocessor-svc), stand-in transaction authorization during outages, post-outage serial state recovery to prevent duplicate card/DDA issuance, PGP key lifecycle. | Stand-in failure during primary outage causes transaction declines. Duplicate card number issuance violates Visa/MC network rules. | Gen-1 crypto-service; Gen-3 SASI/STIR | Mixed. Gen-3 services are architecturally sound but have critical security defects. 4 P0 findings. Committed Azure credential; SOAP auth returns HTTP 200 on failure; security bypass flag in production; STIP contract layer empty. |
| **10 -- Data Platform & Analytics** | Operational databases (eCountCore 20-year OLTP), ETL pipelines (SSIS), analytical warehouse (SSAS/SSRS), CCP bank partner data exchange, client reporting. | Warehouse powers escheatment, AML surveillance export, and all client-facing reporting. ETL failure corrupts Reg E and state unclaimed property reporting. | Gen-1 SQL Server entirely | Critical maturity risk. 3 P0 findings. CVV potentially stored in ecountcore; PAN as plaintext SP parameter; SSIS non-portable due to user-bound encryption; no CI/CD for any database. |
| **11 -- NexPay Greenfield & OnePlatform** | Cloud-native Gen-3 platform: claim code disbursement, recipient orchestration, embedded partner payments, multi-rail payout (card, ACH, push-to-debit, PayPal, Venmo, WU, Ria), cardholder self-service SPA, IVR BFF, client admin BFF. | Primary investment for Onbe's future revenue. Currently carrying critical security defects that block safe production scaling. | Gen-3 primary; Gen-2 OnePlatform hybrid | Medium-low. 3 P0 findings (OFAC unauthenticated; saga compensation stubs; om-payment-api auth disabled). Multiple committed credentials. |
| **12 -- Infrastructure & DevOps** | Environment configuration management, CI/CD pipeline governance, AWS/Azure IaC (Terraform), log aggregation, Spring Config Server, Windows batch production operations, SBOM aggregation. | Leaking a CONFIG_prod credential gives direct access to production databases. VBScript operational scripts will break on next Windows upgrade. | Gen-1/2 on AWS; Gen-3 on Azure | Critical risk. 3 P0 findings. 100+ secret values committed; SSN as CLI argument; unrestricted eCountCore RPC via VBScript. |
| **13 -- Co-brand, Wirecard & Partner Programs** | Cambridge FX/Corpay international wire, Wirecard Gen-2 ACH/wire/check/Singapore bank agents, Subaru dealer rewards, Great Plains ERP/procurement integrations. | Cambridge wires (~30% of cross-border volume) fully lacking OFAC screening. Committed CIMB SFTP key enables payment file injection. | Gen-2 Wirecard dominant | Very low maturity. 5 P0 findings. No OFAC screening anywhere in cross-border stack; committed RSA/PGP/AWS keys; Cambridge beta endpoint as default; Reg E disclosure crashes at runtime. |
| **14 -- Testing & QA Automation** | API regression (SOAP/REST), UI end-to-end automation (Selenium/Playwright), CI/CD pipeline validation, Fiserv mock service, QA orchestration. | No automated regression gate for Gen-1 payment services. Committed PANs/CVVs/SSNs in test repos constitute a data breach event. | Gen-1 SOAP suites; Gen-2 Selenium; Gen-3 Playwright | Low maturity. 4 P0 findings. SAD and PII committed to VCS; no CI test execution for Gen-1 APIs; empty pen test evidence repository. |
| **15 -- Developer Tooling & Shared Libraries** | Build governance (parent POMs), Gen-3 SDK, log sanitization, correlation/audit trail, SBOM aggregation, Jakarta migration tooling, AI guidelines. | Defect in shared library propagates simultaneously to all consumer services. PRNG in Gen-3 SDK weakens all generated credentials. Struts 1 EOL in parent POM locks all inheriting portals to unpatched RCE CVEs. | All three generations | Mixed. Gen-3 SDK is well-structured but carries P0 findings. Gen-1 parent POMs are critically outdated. |

---

## 3. Cross-Domain Business Flows

### Flow 1: New Card Issuance (B2B Batch)

**Domains touched:** 04 (Client Portal / scheduler), 06 (Order & Workflow Orchestration), 01 (Card Program Management / order_SVC, emboss-extract_LIB), 08 (eCountCore processing), 07 (Notification), 10 (Data Platform -- ecountcore ledger)

**Flow summary:** A corporate client submits a file of cardholder records to Onbe via SFTP. Domain 06's js-import_SVC parses the file and writes records to the jobsvc database. Domain 04's scheduler triggers Domain 06's jobservice_SVC, which validates and dual-authorizes the batch (banker_API queries Great Plains for available funds). Domain 01's auto-card-batch_LIB issues cards through IDeviceManager; emboss-extract_LIB writes a PAN-containing XML file to disk for transmission to card bureaus via Sterling NDM. Domain 07's notification-framework_SVC sends cardholder email via Mailgun. Domain 10's ETL pipelines pull the resulting account records into the warehouse for reporting.

**Business risk if broken:** Complete halt of batch card issuance for all file-based client programs. SLA penalties and cardholder access-to-funds failures.

**Critical gaps identified:** PAN written in plaintext to emboss files (Domain 01 P0); CVV2 potentially persisted from Tabapay settlement files (Domain 06 P0); SMS notification stub delivers nothing (Domains 06, 07 P0); Director SPOF cascades to all components (Domains 01, 06, 08); no automated test gate exists for any component (Domains 01, 06, 14 -- universal CI test-skip pattern).

---

### Flow 2: ACH Disbursement (Gig / Insurance / Auto Finance)

**Domains touched:** 06 (Order & Workflow / job-scheduler), 02 (Disbursements -- ACH rail / autofile_SVC, ach-withdrawal-initiator_LIB), 08 (xml-rpc_LIB transport), 05 (StrongBox for bank credentials), 10 (ecountcore ledger), 07 (Notification)

**Flow summary:** autofile_SVC authorizes funds and schedules withdrawal requests; ach-withdrawal-initiator_LIB retrieves bank account credentials from StrongBox via XML-RPC and submits ACH debit instructions to the bank. job-scheduler_SVC enforces NACHA cutoff-time blackout windows. Domain 07 delivers Reg E electronic fund transfer disclosure notifications.

**Business risk if broken:** ACH disbursements fail for all affected recipients. Missing NACHA cutoff triggers next-day settlement and ODFI obligation failures. Reg E error resolution obligations activate if recipients report failed or erroneous transfers.

**Critical gaps identified:** ScheduleFundsRetry idempotency bug in autofile_SVC causes duplicate disbursements -- a live Reg E erroneous EFT event (Domain 02 P1); StrongBox keys and ciphertext co-located in same database (Domain 05 P0); PII logged at INFO level including full Tabapay API request body (Domain 02 P1); xml-rpc_LIB unauthenticated -- any host can invoke fund transfer operations (Domain 08 P0); SMS channel notification stub fails silently (Domain 07 P0).

---

### Flow 3: Cross-Border / FX Wire Disbursement

**Domains touched:** 02 (Disbursements -- Cambridge/CBTS rail), 13 (Wirecard Partner / cross-border-transfer-service, cbts-client), 05 (Authentication -- absent for OFAC screening in this flow), 03 (Recipient Experience -- beneficiary creation), 10 (Data Platform -- audit trail)

**Flow summary:** A client-triggered cross-border disbursement is received by cross-border-transfer-service_SVC, which authenticates with Cambridge Global Payments (now Corpay), retrieves a spot FX quote, books the rate, and instructs the wire against a named beneficiary bank account. cbts-client_LIB provides the REST interface to the Cambridge API.

**Business risk if broken:** International disbursements fail entirely. Rate-booking failures due to batch latency leave funds in intermediate state. Wire instructions disappear without automated recovery.

**Critical gaps identified:** No OFAC/SDN screening exists anywhere in the cross-border stack (Domains 02, 13 P0 -- direct exposure to 31 CFR Part 501 enforcement); TLS validation disabled JVM-wide in cbts-client (Domain 02 P0 -- MITM feasible for all Cambridge traffic containing beneficiary bank account numbers); PGP private key committed to production JAR in test-utilities_LIB (Domain 13 P0); Cambridge beta endpoint is hardcoded as the default in cambridge-service_LIB, meaning live wires silently route to sandbox if endpoint override is omitted (Domain 13 P0); Reg E remittance disclosure service crashes at runtime with ArrayIndexOutOfBoundsException (Domain 13 P1).

---

### Flow 4: Gen-3 Recipient Self-Service Disbursement (NexPay)

**Domains touched:** 11 (NexPay / OnePlatform), 03 (Recipient Experience -- nexpay-recipientweb-bff, orchestrators), 05 (Authentication -- recipient-screening-api, nexpay-auth-svc), 09 (Card Processing -- nexpay-cardprocessor-svc), 10 (Data Platform -- ACL write-back to legacy)

**Flow summary:** A recipient presents a claim code at the oneplatform-react_WAPP portal. The nexpay-recipientweb-bff validates the affiliate, resolves the claim code, and submits a registration/disbursement request to nexpay-recipientorchestrator-svc, which runs a five-step Orchestration Saga: validate claim code, screen recipient (recipient-screening-api), create recipient profile, issue card or payout (nexpay-cardprocessor-svc), write back to the legacy ACL.

**Business risk if broken:** Recipients cannot access their disbursement funds. A failed saga with no compensation logic leaves a funded card at the processor with no claim record, creating double-payment risk and orphaned financial instruments.

**Critical gaps identified:** recipient-screening-api is fully unauthenticated -- OFAC screening gate can be bypassed or injected by any internal actor (Domains 03, 05, 11 P0); saga compensation logic is stubbed (no-op) in both orchestrators -- card reversal does not execute on ACL failure (Domains 03, 11 P0); no UNIQUE constraint on claim_code in saga table -- network retries trigger duplicate payment issuance (Domain 11 P1); nexpay-ivr-bff returns hardcoded SSN and card number through an external APIM endpoint (Domain 03 P1); om-payment-api authorization unconditionally returns true -- any caller can retrieve CVV or disburse funds (Domain 11 P0); AI-generated validation code with hardcoded fund limit cannot respond to fraud events without full deployment (Domain 03 P1).

---

### Flow 5: OFAC Sanctions Screening

**Domains touched:** 05 (Authentication & Identity -- recipient-screening-api, actimize-kyc_LIB, aml-name-screening_LIB), 03 (Recipient Experience -- orchestrators call screening), 04 (Client Admin -- OFAC check in account-management-api), 02 (Disbursements -- absent in cross-border), 13 (Co-brand Partners -- absent throughout)

**Flow summary:** For Gen-3 disbursements, recipient-screening-api is the designated OFAC enforcement gate, called synchronously by both orchestrators before any payment instrument is issued. For Gen-1/Gen-2, account-management-api wraps OFAC calls in a broad exception catch that logs and continues. aml-name-screening_LIB queries only the internal eCountCore database, not any external OFAC watchlist.

**Business risk if broken:** Disbursement of funds to OFAC-designated individuals or entities. Criminal exposure under 31 CFR Part 501, regulatory fines, reputational damage, and potential loss of banking relationships.

**Critical gaps identified:** recipient-screening-api has no authentication on any endpoint (Domains 03, 05, 11 P0); OFAC screening is non-blocking in account-management-api (Domain 04 P0); no OFAC screening exists anywhere in the cross-border stack (Domains 02, 13 P0); aml-name-screening_LIB does not query OFAC/SDN lists -- it is not an OFAC control at all (Domain 05 P2); OFAC tipping-off risk is present: a declined screening result surfaces as an unhandled exception to the recipient rather than a generic error message (Domain 03).

---

### Flow 6: Client Admin -- Program Configuration and Launch

**Domains touched:** 04 (Client Admin -- bmcwizard, workbench, scheduler, clientzone), 01 (Card Program Management -- xaffiliate, screen-configs), 09 (STIP -- crypto-service for PGP key registration), 07 (Content -- xContent-recipient asset deployment), 12 (Infrastructure -- CONFIG repos, IaC)

**Flow summary:** A new client program is configured through bmcwizard_WAPP (guided wizard) and workbench_WAPP (configuration management). PGP keys for the program's encrypted file exchange are registered through crypto-service_SVC. Brand assets are committed to xContent-recipient and deployed to Azure Blob Storage. Program identifiers, fee schedules, and affiliate settings are distributed to all runtime services via the Director credential registry, the Spring Config Server, and Redis caching.

**Business risk if broken:** New programs cannot launch. Misconfiguration propagates immediately to live cardholders (no maker-checker workflow in bmcwizard or workbench). An incorrectly registered PGP key redirects all encrypted cardholder files to an unintended recipient. An unvalidated fee schedule goes live without required CFPB disclosures.

**Critical gaps identified:** bmcwizard and workbench have no maker-checker workflow -- configuration changes take immediate effect on live cardholders (Domain 04 UDAAP risk); crypto-service_SVC is unauthenticated and susceptible to command injection (Domain 09 P0/P1); fee schedule HTML not validated before production deployment (Domain 07 P2); Director is unauthenticated and a SPOF for all program runtime configuration distribution (Domains 01, 04, 06, 08 P0).

---

## 4. Top 20 Business-Impact Findings (P0/P1)

| Rank | Domain | Finding | Business Impact | Regulatory Exposure | Priority |
|---|---|---|---|---|---|
| 1 | **05** Authentication & Identity | RSA private keys co-located with encrypted ciphertext in StrongBox vault database (SbGetAsymmetricKey.java). A single database backup yields keys and data to decrypt all Gen-1/Gen-2 cardholder records. | Complete exposure of all Gen-1/Gen-2 encrypted cardholder data (SSN, DOB, bank account, PAN). | PCI DSS Req 3.6.1 | P0 |
| 2 | **01** Card Program Management | Full PAN written in plaintext to emboss XML files at /upload/EmbossFileExtract/ for transmission to card bureaus via NDM/Connect:Direct (StaxEmbossExtractBuilder). No encryption applied before or during transmission. | Exposure of cardholder PANs at the primary card data egress boundary for all physical card programs. | PCI DSS Req 3 & 4 | P0 |
| 3 | **02** Disbursements & Payment Rails | TLS certificate validation disabled JVM-wide in cbts-client_LIB (SSLContext.setDefault() with trust-all X509TrustManager). Eliminates TLS for all HTTPS calls in any JVM that loads this library, including all Cambridge FX traffic carrying beneficiary bank account numbers and transaction amounts. | MITM feasible for all cross-border wire traffic. Financial fraud via payment instruction interception. | PCI DSS Req 4.2.1 | P0 |
| 4 | **02 / 13** Disbursements & Co-brand Partners | No OFAC/SDN screening in cross-border disbursement stack (cross-border-transfer-service, cbts-client, all Wirecard bank agents). Onbe as instructing party bears direct regulatory liability. | Criminal exposure under 31 CFR Part 501. Potential OFAC enforcement action, fines, and reputational damage. | OFAC / BSA-AML | P0 |
| 5 | **13** Co-brand & Partner Programs | RSA private key for CIMB SFTP (Singapore bank agent) committed to application.yml. PGP private key and AWS access key also committed to same repository. Any repository reader can authenticate to CIMB, download or inject payment files, and access AWS resources. | Fraudulent payment file injection affecting Singapore cardholder disbursements. AWS key exposure for forensic assessment. | PCI DSS Req 3.5.1, 8.3.2 | P0 |
| 6 | **12** Infrastructure & DevOps | More than 100 distinct credential values committed to CONFIG_prod, api-config-repo, and infrastructure repositories. Includes production IBM MQ credentials, SAP SMS gateway credentials, KYC OAuth2 client secret, BioCatch credentials, Western Union static key, CBTS passwords, and SFTP private keys for card manufacturer Harland and card bureau Titan. | Any repository reader gains access to production payment infrastructure. Card manufacturing SFTP enables fraudulent card orders. Identity verification can be spoofed. | PCI DSS Req 8.3.2, 3.5; GLBA | P0 |
| 7 | **03 / 05 / 11** Recipient Experience / Auth / NexPay | OFAC screening API (recipient-screening-api) is fully unauthenticated (anyRequest().permitAll()). Any internal actor can inject fake APPROVED or DECLINED webhook results, enabling a sanctioned entity to receive funds or blocking a legitimate recipient permanently. | Live OFAC enforcement bypass. Sanctions violations. Fraudulent account unblocking. | OFAC; PCI DSS Req 7/8 | P0 |
| 8 | **04** Client Administration | Unauthenticated Spring HTTP Invoker deserialization endpoint on scheduler_WAPP with four production database passwords committed in the same repository. Any internal host can achieve RCE on the scheduler, which has direct JDBC access to CbaseApp, JobSvc, RequestDB, and EcountCore. | RCE on the system that controls all batch disbursement timing. Combined with credential exposure, full database access. | PCI DSS Req 8.3, 6.4 | P0 |
| 9 | **10** Data Platform | CVV potentially stored post-authorization in ecountcore.fdr_card_account_detail.cv_code. The util_update_cvcode procedure is obfuscated WITH ENCRYPTION, suggesting deliberate concealment. PAN accepted as plaintext stored procedure parameter @card_number char(16), captured by any SQL Server trace or Query Store session. | Core PCI DSS violation in the primary card database. QSA notification required. | PCI DSS Req 3.3.1, 3.4 | P0 |
| 10 | **09** STIP & Card Processing | Three compounding P0 defects in stand-in-processing-api: (a) Azure App Configuration key committed to .env; (b) SOAP authentication silently returns HTTP 200 on failure; (c) sasi.dev.disable-security-filter security bypass flag in production code. SASI targets 99.999% uptime as the last line of defence for cardholder transaction continuity. | Compromise of the stand-in processor during a primary system outage. Authentication bypass enables fraudulent transaction authorization. | PCI DSS Req 6.3.3, 8.2; FFIEC BCM | P0 |
| 11 | **11 / 03** NexPay / Recipient Experience | Saga compensation logic is unimplemented (compensateCardIssuance() is a no-op log statement) in both nexpay-order-orchestrator and nexpay-recipientorchestrator-svc. A funded prepaid card issued at the processor with a failed ACL write-back creates an orphaned financial instrument with no claim record and no reversal path. | Double-payment risk. Orphaned funded cards. Reg E error resolution obligation with no evidence trail. | Reg E; PCI DSS Req 6 | P0 |
| 12 | **11 / 04** NexPay / Client Admin | Payment authorization unconditionally disabled in two production APIs: om-payment-api (JwtSecurityValidator.java returns true on line 57) and account-management-payout (all validateAPISecurity() calls commented out under "JIRA 476"). These services expose CVV retrieval, card number retrieval, PIN operations, and fund disbursement to any caller. | Any authenticated network caller can retrieve CVVs, disburse funds, and perform PIN operations on any program without authorization check. | PCI DSS Req 7; Reg E | P0 |
| 13 | **08** Search, Platform Core | xml-rpc_LIB XmlRPCServlet accepts any POST with forged RPC-Interface / RPC-Method headers and invokes any Spring bean method with no authentication or authorization. Consumers include ecount-core, cs-api, clientapi, jobservice, strongbox-xmlrpc, xsearch-xmlrpc, xsso, and all VBScript operational scripts. | Unauthorized fund transfers, cardholder data retrieval, and administrative card operations by any network-reachable host. | PCI DSS Req 6.4, 7/8 | P0 |
| 14 | **12** Infrastructure | RPC-EXEC.vbs grants any Windows-authenticated user with filesystem access to the production batch server unrestricted invocation of any eCountCore interface method -- profile updates, financial data modification -- with On Error Resume Next swallowing all errors and no audit trail. | Uncontrolled privileged access path to the Gen-1 card ledger for any user with batch server access. | PCI DSS Req 7/8; GLBA | P0 |
| 15 | **01** Card Program Management | Director service XML-RPC endpoint (/dispatch.asp) exposes all platform database passwords via System\DataCredentials\* to any network-reachable host with no caller authentication (DirectoryImpl.get() has no auth check). | Complete exposure of all Gen-1/Gen-2 database credentials from a single unauthenticated call. | PCI DSS Req 7/8 | P0 |
| 16 | **02** Disbursements | ScheduleFundsRetry.java in autofile_SVC has an idempotency bug: both "already exists" and "new entry" code paths call insertFundsRetryQueue(), creating duplicate disbursement queue entries. ach-withdrawal-initiator processes duplicates as new disbursements, triggering duplicate Tabapay push-to-debit payments. Defect is confirmed in production. | Double-payment to recipients. Direct financial loss. Reg E erroneous EFT event with 10-business-day investigation obligation. | Reg E | P1 |
| 17 | **05** Authentication & Identity | SSL certificate validation completely disabled for RSA Adaptive Authentication MFA traffic (TrustAllSSLSocketFactory in rsa-mfa_LIB). OTP tokens, RSA caller credentials, and cardholder phone numbers traverse this socket factory. MD5 password hashing active for new registrations in xsecurity_SVC. | MFA bypass via MITM on every OTP transaction. MD5-crackable operator and client portal passwords. | PCI DSS Req 4.2, 8.3.6 | P0/P1 |
| 18 | **14** Testing & QA | Cardholder PANs, CVVs, SSNs, and PINs committed to at least six testing repositories (account-management-api_TESTING_AUTO, cs-api_TESTING_AUTO, client-api-v4_TESTING_AUTO, Automation_ClientZone, selenium-framework-test, CucumberPOC). Git history permanently retains these values. | Potential data breach event. QSA notification likely required upon disclosure of real vs. synthetic determination. | PCI DSS Req 3.3, 3.4 | P0 |
| 19 | **04** Client Admin | OFAC screening non-blocking in account-management-api: performRecipientScreening() catches all exceptions and continues account creation regardless of screening outcome or service failure. Every account created while this code is active may require retroactive OFAC screening review. | Potential disbursement to sanctioned individuals through the primary account creation API. | OFAC / BSA | P0 |
| 20 | **13** Co-brand Partners | Cambridge beta endpoint (https://isbeta.cambridgefxonline.com) is the hardcoded default in all cambridge-service_LIB stub constructors. Any consuming service that does not explicitly override the endpoint silently routes live payment instructions to Cambridge's sandbox. Wire payments appear to succeed but funds do not move. | Live cross-border wire instructions routing to sandbox. Recipients do not receive funds; no error raised. | Reg E; NACHA; OFAC compliance gap during sandbox routing | P0 |

---

## 5. Regulatory Compliance Summary

### PCI DSS v4.0.1

**Current posture:** Failing across multiple requirements. The estate is a PCI DSS Level 1 service provider with cardholder data environments spanning all three platform generations.

**Key gaps:**

- *Req 3.2.1 (No SAD storage post-authorization):* CVV potentially stored in ecountcore fdr_card_account_detail.cv_code (Domain 10); CVV2 in PushtodebitTransactionVo in batch_LIB (Domain 06); CVV field serializable to XML batch files in request-file_LIB (Domains 07, 15).
- *Req 3.3.1 (PAN masking):* CSA search (xsearch_LIB) exposes first 4 + last 4 digits (8 unmasked); CS API v1/v2/singlewar exposes last 8 digits. PCI DSS permits at most first 6 (BIN) + last 4.
- *Req 3.5/3.6 (Key management):* StrongBox RSA keys co-located with ciphertext (Domain 05); cryptographic keys committed to 15+ repositories across Domains 01, 02, 04, 05, 09, 12, 13.
- *Req 4.2.1 (Encrypt data in transit):* TLS disabled JVM-wide in cbts-client (Domains 02, 13); AJP/1.3 cleartext on internal web tier for cardholder portals (Domain 12); Filebeat transmitting logs with no TLS cert verification (Domain 12); StrongBox keys delivered over default plaintext HTTP (Domain 05).
- *Req 6.3.3 (Vulnerable components):* Java 5/6 targets, Spring 2.x (EOL 2013), Struts 1.x (EOL 2013), Log4j 1.x (CVE-2019-17571), Apache Axis 1.4 (CVE-2019-0227), XStream (multiple RCE CVEs), Commons HttpClient 3.x (CVE-2012-5783) -- widespread across Domains 01, 02, 03, 04, 05, 06, 07, 08, 13, 15.
- *Req 7/8 (Access control and authentication):* At least eight production endpoints are unauthenticated: Director, xml-rpc servlet, scheduler HTTP Invoker, OFAC screening API, StrongBox XML-RPC, crypto-service, xsso, and xsearch-xmlrpc.
- *Req 10.7 (Log retention):* CloudWatch default 14-day retention across all Gen-2 ECS services; PCI DSS requires 12 months.

**Business consequence of non-compliance:** QSA assessment failure, potential loss of PCI certification, inability to process card payments under Visa/Mastercard network rules, and exposure to card brand fines.

---

### Regulation E (Electronic Fund Transfer Act)

**Current posture:** Partially compliant. Formal compliance controls are present in the Gen-3 orchestration saga audit trail and the Gen-1 job service dual-authorization. However, multiple active defects undermine Reg E obligations.

**Key gaps:** ScheduleFundsRetry duplicate disbursement bug creates erroneous EFT events with no automated detection (Domain 02); SMS notification channel silently returns success without sending -- Reg E required disclosures may not be delivered (Domains 06, 07); saga compensation stubs mean a failed disbursement may not be reversible (Domains 03, 11); chargeback-engine_LIB automates no-authorization chargebacks with no provisional credit, investigation window, or cardholder notification (Domain 01); Reg E remittance disclosure service for international transfers crashes at runtime (Domain 13).

**Business consequence:** Reg E violations expose Onbe to CFPB enforcement, cardholder dispute liability, and potential UDAAP findings for failure to disclose.

---

### NACHA Operating Rules

**Current posture:** Partially compliant. ACH formatting, return code handling, and blackout-window enforcement are present in the estate.

**Key gaps:** job-scheduler_SVC enforces ACH origination blackout windows, but a scheduler outage causes Onbe to miss same-day ACH cutoff times (Domains 04, 06); ACH-specific format validation is absent from Domain 01's service layer; NACHA return codes R01-R85 handling was not confirmed in Domain 02 test coverage; duplicate ACH instructions are possible via the autofile idempotency bug (Domain 02).

**Business consequence:** NACHA rule violations result in ODFI penalties and potential suspension of ACH origination privileges.

---

### OFAC / Sanctions Screening

**Current posture:** Critically non-compliant. OFAC screening is absent or non-enforcing in the majority of disbursement flows.

**Key gaps:** No OFAC screening in any cross-border wire flow (Domains 02, 13); OFAC screening non-blocking in primary account creation API (Domain 04); OFAC screening API unauthenticated -- a fake webhook can approve a sanctioned entity (Domains 03, 05, 11); aml-name-screening_LIB does not query OFAC SDN list (Domain 05).

**Business consequence:** Criminal exposure under 31 CFR Part 501, civil money penalties up to $368,136 per violation (current OFAC maximum), reputational damage, and potential loss of banking relationships.

---

### GLBA (Gramm-Leach-Bliley Act)

**Current posture:** Multiple active violations. Cardholder non-public personal information flows through services without consistent access logging, data classification, or transmission encryption.

**Key gaps:** SSN passed as plaintext command-line argument visible in Windows process list (Domain 12 P0); cardholder PII logged at INFO level across at least eight services in Domains 01, 02, 03, 05, 07, 08, 13; StrongBox delivering cryptographic keys over plaintext HTTP (Domain 05); cardholder PII in plaintext warehouse tables accessible to all CubeReader role members (Domain 10).

**Business consequence:** FTC enforcement action, state attorney general actions, and civil liability for affected individuals.

---

### GDPR / CCPA

**Current posture:** Material gaps. Personal data is stored without observable deletion mechanisms in multiple services; PII is transmitted to third parties without confirmed Data Processing Agreements.

**Key gaps:** SMS notification queue, claim code issuance info, and notification log tables store PII without retention schedules or deletion mechanisms (Domain 01); dim.DimAccountHolder in the prepaid warehouse stores full cardholder PII in plaintext with no right-to-deletion mechanism (Domain 10); Mixpanel event tracking in oneplatform-react_WAPP may transmit PII to a third party without consent tracking (Domain 11); no confirmed DPA with Mailgun for PII processing (Domain 07); real employee PII appears in a database migration seed file (Domain 03).

**Business consequence:** GDPR fines up to 4% of global annual turnover; CCPA fines up to $7,500 per intentional violation; reputational damage in European and California markets.

---

### SOC 1 / SOC 2

**Current posture:** Multiple control deficiencies.

**Key gaps:** job-order-synchronization_LIB, the completeness control for disbursement audit trails, can fail silently leaving Order Service records permanently in PENDING state (Domain 06 P1); no CI/CD exists for any database in Domain 10 -- schema changes are manual operations with no change management evidence (Domain 10 P1); SNAPSHOT versions in production preclude build traceability required for SOC 1 change management controls (Domains 08, 11, 15).

**Business consequence:** Qualified SOC opinion, client audit findings, and potential loss of service provider contracts requiring SOC certification.

---

## 6. Operational Risk Register

| Rank | Risk | Domains Affected | Business Consequence | Likelihood |
|---|---|---|---|---|
| 1 | **Director SPOF -- unauthenticated credential registry.** Director is the startup dependency of every Gen-1/Gen-2 service. Its XML-RPC endpoint has no authentication, exposing all database credentials. It has no documented high-availability configuration. Failure cascades simultaneously to all services it serves. | 01, 04, 06, 08 and all Gen-1/Gen-2 consumers | Complete halt of all Gen-1/Gen-2 payment operations. Total exposure of all platform database credentials. | High |
| 2 | **xml-rpc_LIB -- estate-wide single-point transport failure.** A defect, CVE exploit, or availability failure in this library halts all Gen-1/Gen-2 service-to-service communication simultaneously. Replacement requires coordinated changes across the entire estate. | 02, 04, 06, 07, 08 and all XML-RPC consumers | Simultaneous failure of all cardholder-facing Gen-1/Gen-2 services. | High |
| 3 | **jobservice_SVC -- single execution gate for all batch disbursements.** Every dollar disbursed via batch flows through JobManager and JobAgent WARs with no documented DR procedure. No hot standby exists. | 04, 06 | Halt of all file-based client disbursements (insurance, auto, marketplace, gig programs). SLA penalties. | High |
| 4 | **Universal CI test-skip norm.** All 363 repositories skip automated test execution in CI pipelines (-Dmaven.test.skip=true or equivalent). Every production deployment carries unquantifiable regression risk. PCI DSS Req 6.2.4 requires security testing before release. | All 15 domains | Undetected defects including the autofile duplicate-payment bug reach production. No automated fraud or regression detection. | Confirmed (current state) |
| 5 | **SQL Server on-premises concentration.** ecountcore, cbaseapp, jobsvc, ordersvc, and all Gen-1 databases are SQL Server instances on named Windows hosts. No cloud-native equivalent exists. The warehouse ETL is bound to DPAPI keys owned by a specific named employee. | 06, 08, 09, 10 | Database server failure or key-person departure takes down ecountcore, halting all Gen-1/Gen-2 processing and the entire analytics layer. | Medium-High |
| 6 | **Wirecard infrastructure dependency.** The nam.wirecard.sys Active Directory domain remains the authority for production server names. wirecard.com DNS and wirecard.sys hostnames appear in production configuration, SFTP keys, and deployment scripts. Wirecard AG is insolvent. | 12, 13 and all Gen-2 services | If Wirecard-operated infrastructure is decommissioned, Gen-2 service discovery and deployment pipelines fail simultaneously. | Medium |
| 7 | **Windows VBScript operational layer obsolescence.** ACH control validation, SSN/DOB updates, PGP file operations, and card fulfillment integration are implemented in VBScript via the jIntegra J2COM bridge. Microsoft is actively removing VBScript from Windows. jIntegra is abandoned. Zero test coverage. | 12 | Critical batch operations stop working on the next Windows OS upgrade. No automated fallback. | High (on next OS upgrade) |
| 8 | **SNAPSHOT versions in production.** At least 12 production services carry -SNAPSHOT Maven version identifiers. Maven may resolve different artifact bytecode on different build executions, making reproducible builds and incident post-mortems impossible. PCI DSS requires immutable build traceability. | 01, 02, 04, 08, 09, 11, 15 | Undocumented behavior change in a SNAPSHOT dependency ships to production without a version increment. Audit traceability is impossible. | High |
| 9 | **StrongBox as sole cryptographic trust anchor with no HA or key separation.** The StrongBox cluster is the cryptographic trust anchor for all Gen-1/Gen-2 encrypted cardholder data. RSA private keys and ciphertext are co-located in the same database. No key separation, no HSM, no replicated standby. | 05 and all services consuming encrypted data | StrongBox outage halts all encrypted data operations. StrongBox compromise decrypts all Gen-1/Gen-2 cardholder records. | Medium |
| 10 | **Empty/stub repositories masking production gaps.** RecipientApp, stip-generated, stip-models, oneplatform-azureblobtags-function, OP_Mobile_TESTING_PT, and GP-RSM-Customization have no source code but appear in production architecture diagrams or system inventories. Security and compliance review cannot be completed for components with no source. | 03, 09, 11, 13, 14 | Unknown attack surface. Missing PCI DSS Req 6.3.2 inventory coverage. Missing pen test evidence (Req 11.4). | Medium |

---

## 7. Three-Generation Business Continuity Assessment

### Gen-1 Decommission Risks (eCount / Citi Heritage)

Gen-1 carries approximately 60% of live transaction volume and serves as the system of record for cardholder accounts, card lifecycle, and ACH transactions. Decommissioning Gen-1 without full Gen-3 parity would produce the following cascades:

- eCountCore database decommission would immediately halt card authorization, account inquiry, ACH processing, and cardholder search for all programs not yet migrated to Gen-3. Domain 08's xml-rpc_LIB and all associated client stubs would have no backend to call.
- emboss-extract_LIB decommission would halt all physical card personalization batches until a Gen-3 equivalent is built and validated with FDR/Fiserv/PSX/ARROWEYE bureaus.
- Domain 01 batch services (auto-card-batch_LIB, check-issuance_LIB, fdr-batch-reports-processing_LIB) need Gen-3 replacements before Gen-1 can be decommissioned. No such replacements exist in the current 363-repo estate.
- Director decommission is a prerequisite for Gen-1 sunset but would simultaneously break every Gen-1/Gen-2 service that has not been migrated to Azure Key Vault. A phased migration plan does not exist in any repository.
- The prepaid_warehouse ETL layer (Domain 10) pulls entirely from Gen-1 databases. Decommissioning Gen-1 databases without migrating the warehouse source would eliminate all analytical, reporting, and escheatment capabilities.

**Assessment:** Gen-1 cannot be safely decommissioned within a 12-month horizon given current Gen-3 readiness. A formal Gen-1 sunset roadmap with feature parity gates, data migration planning, and bureau re-certification should be initiated as a strategic program.

---

### Gen-2 Wind-Down Dependencies (Wirecard / Northlane)

Gen-2 carries approximately 30% of live transaction volume, primarily through the ACH, wire, check, and cross-border FX rails managed in Domains 02 and 13.

- Wirecard infrastructure dependency is the most acute risk. The nam.wirecard.sys Active Directory domain remains authoritative for production server names and authentication for all Gen-2 services. If Wirecard-era infrastructure is decommissioned or access is lost, all Gen-2 service DNS resolution fails simultaneously.
- Cambridge FX / Corpay integration (cambridge-service_LIB, cbts-client_LIB, cross-border-transfer-service_SVC) represents a dual integration with both the legacy SOAP (Axis) and newer REST (cbts-client) Cambridge APIs. The Axis SOAP layer carries critical CVEs. The REST layer has TLS disabled. Neither is safe for continued use without urgent remediation.
- Wirecard bank agents (Sunrise Bank NAM agent, CIMB Singapore agent) are the exclusive disbursement rails for their respective programs. No Gen-3 equivalent bank agent exists for Sunrise or CIMB.
- ActiveMQ EventHub in the Wirecard Gen-2 orchestration is a single point of failure for all Gen-2 disbursement events. No documented DR procedure exists for the message broker.

**Assessment:** Gen-2 wind-down must be sequenced: (a) migrate Wirecard DNS and AD dependencies to Onbe-controlled infrastructure; (b) build Gen-3 equivalents for Sunrise Bank and CIMB agent rails; (c) implement OFAC screening in the replacement cross-border stack before migrating any volume; (d) decommission AWS ECS hosting and Wirecard-era SFTP keys only after Gen-3 equivalents are certified.

---

### Gen-3 Readiness Gaps (NexPay / OnePlatform)

Gen-3 currently carries approximately 10% of transaction volume and is the primary investment platform. However, it is not production-safe at scale due to the following gaps:

- **Saga compensation is unimplemented.** Both Gen-3 orchestrators (nexpay-order-orchestrator, nexpay-recipientorchestrator-svc) have no-op compensation logic. A partial saga creates an orphaned funded card with no reversal path. This is an absolute blocker for volume scaling with real financial instruments.
- **OFAC screening is unauthenticated.** The primary OFAC gate for all Gen-3 disbursements is fully open to injection. This must be remediated before any regulatory examination of the Gen-3 platform.
- **Authorization is disabled in production payment APIs.** om-payment-api and account-management-payout have authorization disabled in production code. This is a blocker for PCI DSS certification of the Gen-3 environment.
- **STIP contract layer is empty.** stip-models and stip-generated contain only git metadata. The stand-in processing capability required by Visa/Mastercard network rules has no formal contract, making the STIP implementation unverifiable.
- **IVR BFF returns hardcoded PII.** nexpay-ivr-bff returns a placeholder SSN and fixed card number through an external APIM endpoint. If a live IVR system is pointed at this endpoint, cardholders receive fabricated data.
- **SNAPSHOT parent POM** (nexpay-parent:0.2.8-SNAPSHOT) governs all Gen-3 services, producing non-reproducible builds. PCI DSS certification requires immutable production artifacts.
- **Swagger UI with try-it-out enabled** in production for at least one orchestrator allows saga creation for arbitrary claim codes by any authenticated user.

**Assessment:** Gen-3 is architecturally sound in its design but requires a focused security remediation sprint before it can absorb Gen-1/Gen-2 volume migration safely. The minimum prerequisites are: saga compensation implementation, OFAC API authentication, om-payment-api authorization re-enabled, IVR BFF stub gated, and SNAPSHOT versions replaced with GA releases.

---

## 8. Strategic Recommendations (Top 10)

| # | What to Do | Why (Business / Regulatory Driver) | Domains | Priority |
|---|---|---|---|---|
| 1 | **Rotate all committed credentials estate-wide and implement secrets vault.** Conduct a git-history scan across all 363 repositories using gitleaks or truffleHog. Rotate every identified credential immediately -- treat production credentials in CONFIG_prod, the CIMB SFTP key, PGP private keys, Cambridge API signatures, AWS access keys, and Director-accessible database passwords as compromised. Migrate all secrets to Azure Key Vault via Managed Identity for Gen-2/Gen-3 services and parameterized vault integration for Gen-1 services as a stopgap. Enforce a pre-commit secret-scanning hook across all repositories. | 100+ distinct credential values in source control constitute a key-compromise event. A single unauthorized repository read enables fraud, identity verification spoofing, and card manufacturing interference. PCI DSS Req 8.3.2, 3.5.1; GLBA. | 01, 02, 04, 05, 06, 09, 12, 13, 14 | **Immediate (Week 1)** |
| 2 | **Implement OFAC screening as a synchronous hard-stop gate in all disbursement flows.** Add OAuth2 resource server authentication and HMAC webhook signature validation to recipient-screening-api. Make OFAC screening blocking (hard-fail, not log-and-continue) in account-management-api. Integrate a synchronous OFAC/SDN check in cross-border-transfer-service and Wirecard bank agents before any payment instruction reaches Cambridge or bank SFTP. Establish an interim manual screening process for cross-border transfers while automated remediation is in progress. Escalate immediately to Legal and Compliance for risk acceptance documentation. | Cross-border disbursement stack has no OFAC check at any point. account-management-api is non-blocking. The unauthenticated OFAC API can be injected. Criminal exposure under 31 CFR Part 501. | 02, 03, 04, 05, 11, 13 | **Immediate (Weeks 1-4)** |
| 3 | **Implement saga compensation logic in both Gen-3 orchestrators and add claim code uniqueness constraint.** Replace no-op compensateCardIssuance() stubs in nexpay-order-orchestrator and nexpay-recipientorchestrator-svc with live card reversal via nexpay-cardprocessor-svc and ACL rollback. Add a UNIQUE database constraint on saga.claim_code in both saga tables. This is a blocking prerequisite for any production volume increase on the Gen-3 platform. | Unimplemented compensation means a failed saga creates an orphaned funded card with no reversal path. Double-payment risk. Reg E error resolution obligation. | 03, 11 | **Immediate (Current Sprint)** |
| 4 | **Encrypt emboss files and fix PAN/CVV handling at the primary cardholder data egress boundaries.** Add PGP or HSM-based encryption to emboss-extract_LIB before files are written to the emboss output directory. Engage card bureaus to confirm acceptance of encrypted files. Add @XmlTransient to Cardtype.cvcode and Cardtype.cardnumber in request-file_LIB to prevent SAD/PAN serialization to batch XML. Verify and purge CVV from ecountcore fdr_card_account_detail and engage the QSA. Disable CVV logging in consumerload_API. | PAN in plaintext emboss files is the most direct PCI DSS violation at a network boundary. CVV storage post-authorization in the primary card database is a Req 3.2.1 violation requiring QSA notification. | 01, 07, 10, 15 | **Immediate (Weeks 1-4)** |
| 5 | **Re-enable all disabled authorization controls in production payment APIs.** Re-enable JWT authorization in om-payment-api (JwtSecurityValidator.java line 57). Restore program-level authorization in account-management-payout (validateAPISecurity() calls under "JIRA 476"). Re-enable the security validation in ClientZone's CreateAccountService.processWebRequest(). Define a JIRA epic tracking all "JIRA 476" commented-out code across the estate to ensure none are reactivated without security review. Assign each disabled control a remediation owner. | Three production payment APIs have authorization disabled. Any authenticated caller can retrieve CVV, disburse funds, and perform PIN operations. PCI DSS Req 7. | 04, 11 | **Immediate (Current Sprint)** |
| 6 | **Authenticate and isolate the Director service and accelerate its deprecation.** Add mutual TLS or a shared-secret header to Director's XML-RPC endpoint as an immediate stopgap. Restrict network access to Director to the minimum required application hosts via firewall rules. Audit Director access logs for unauthorized queries. Publish an explicit migration roadmap for all Gen-1/Gen-2 services to move from Director to Azure Key Vault, with a defined decommission date. Until decommissioned, deploy Director with a documented warm standby for availability. | Director is simultaneously a platform-wide SPOF and an unauthenticated platform-wide credential exposure. Any Director outage halts all Gen-1/Gen-2 services. Any host with network access can obtain all database passwords. | 01, 04, 06, 08 | **30-Day** |
| 7 | **Separate cryptographic keys from ciphertext in the StrongBox vault database.** Apply SQL Server Always Encrypted with a column master key stored in Azure Key Vault for the private_key and key_value columns in the StrongBox database, addressing PCI DSS Req 3.6.1 without requiring an immediate full vault migration. Concurrently, publish and fund a phased StrongBox decommission roadmap: (a) column-level encryption; (b) Gen-2 services migrated to Azure Key Vault individually; (c) StrongBox XML-RPC service decommissioned when all consumers migrate. Fix the default plaintext HTTP transport in strongbox-remote-client_LIB. | RSA private keys and ciphertext co-located in the same database -- a single backup decrypts all Gen-1/Gen-2 cardholder records. Plaintext HTTP key transport in production. PCI DSS Req 3.6.1, 4.2.1. | 05 | **30-Day** |
| 8 | **Establish a domain-wide mandatory CI test execution policy and retire the test-skip norm.** Remove -Dmaven.test.skip=true from all CI/CD pipelines estate-wide, beginning with the highest-risk services: autofile_SVC, ach-withdrawal-initiator_LIB, cross-border-transfer-service_SVC, clientapi_API, order_SVC, nexpay-cardprocessor-svc. Establish a minimum 60% line coverage gate for new code within 90 days. Require that all SAD and PII be replaced with synthetic equivalents in test fixtures across all testing repositories. This is the safety net required for all subsequent migration work. | Universal CI test-skip means every production deployment carries unquantified regression risk. The autofile duplicate-payment bug and other critical defects could have been caught by automated testing. PCI DSS Req 6.2.4 requires security testing before release. | All 15 domains | **30-Day** |
| 9 | **Publish and fund a formal Gen-1 sunset roadmap with Gen-3 feature parity gates.** Conduct a formal assessment of each Gen-1 service against Gen-3 feature parity. Define parity gates (capabilities, OFAC controls, Reg E evidence, Reg E disclosure) that must be met before any Gen-1 service is decommissioned. Prioritize: (a) scheduler replacement (Azure Scheduler or Quartz-on-Spring-Boot -- unblocks all batch consumers); (b) Director decommission (requires Key Vault migration); (c) emboss bureau re-certification with new encrypted file format; (d) eCountCore migration of account lifecycle, fund loading, and cardholder search. Establish decommission dates for Gen-1 EOL services running Java 5/6. | Gen-1 EOL runtimes cannot receive security patches. Java 5/6 services cannot run on any currently supported JVM. Struts 1 carries unpatched RCE CVEs. The longer Gen-1 remains in production, the larger the compliance exposure surface. | 01, 02, 04, 06, 07, 08, 15 | **90-Day (Program launch)** |
| 10 | **Extend CloudWatch log retention to 365 days, complete Java SBOM coverage, and fix non-PCI PAN masking in CSA search.** Update terraform-ecs-service_INFRA_TF default retention_in_days to 365 and apply to all existing ECS log groups. Connect all Maven CI pipelines to generate and submit CycloneDX SBOMs to Dependency-Track. Update MaskCCHelper.maskThisCC() in xsearch_LIB and xsearch-new_SVC simultaneously to expose BIN (first 6) + last 4 digits, meeting PCI DSS Req 3.3.1. Update CS API v1, v2, and singlewar masking accordingly. These three actions together close persistent PCI DSS audit gaps with manageable implementation effort. | 14-day log retention violates PCI DSS Req 10.7 (12-month requirement). Java SBOM gap means the majority of the estate has no supply chain vulnerability visibility. Non-PCI PAN masking in CSA search exposes 8 unmasked digits to agent staff, exceeding the PCI DSS-permitted maximum of first 6 + last 4. | 08, 12, 15 | **90-Day** |

---

*Document prepared for internal Onbe use. All findings are grounded in source code analysis of the 363-repository estate performed May 2026. Cross-references use domain numbers (e.g., Domain 05 -- Authentication & Identity) for direct traceability to the 15 underlying BA_domain synthesis documents. All cardholder data values referenced in findings are values found in committed source code; they must be treated as potentially compromised and handled under Onbe's data breach response procedures.*
