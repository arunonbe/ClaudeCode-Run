# MASTER ENTERPRISE ARCHITECT VIEW — Onbe 363-Repo Estate

*(Generated: 2026-05-08 | Source: 363 repositories across 15 business domains)*

---

## 1. Executive Summary

Onbe operates a three-generation prepaid payments estate that has accumulated approximately twenty years of compounding technical and compliance debt across three corporate acquisitions (eCount, Citi Prepaid, Wirecard/Northlane). The estate currently carries all three generations in simultaneous production: Gen-1 eCount/Citi-era services handle the majority of transaction volume (estimated 55–65%), Gen-2 Wirecard/Northlane services handle 25–35%, and Gen-3 NexPay/Onbe services handle 5–15% and growing.

The strategic architecture problem is not that legacy systems exist — it is that the three generations are not cleanly separated. Gen-3 NexPay services depend on Gen-1 SQL Server databases (stand-in-processing-api reads from ecountcore at runtime), Gen-3 orchestrators depend on Gen-2 notification services over XML-RPC (the MPV portal calls message-center_SVC), and Gen-2 services depend on a Gen-1 credential broker (Director) for every startup. These cross-generation dependencies mean no generation can be decommissioned independently — the estate must be migrated in orchestrated phases with explicit dependency severance at each boundary.

**Three critical blockers prevent Gen-3 completion and Gen-1 decommission:**

1. **Director as credential broker**: 90–110 repositories retrieve database passwords, API keys, and SMTP credentials from director-svc_SVC at startup via an unauthenticated HTTP endpoint. Director failure is a platform-wide cascade. Director's existence is the primary constraint preventing any Gen-1 or Gen-2 service from becoming cloud-native.

2. **XML-RPC as the universal internal bus**: xml-rpc_LIB's proprietary `application/x-mapxml` wire format, unauthenticated at every endpoint, is embedded in every consuming service WAR. It has no equivalent in any cloud-native service mesh, API gateway, or observability toolchain. Replacing it requires either a simultaneous coordinated change across the entire Gen-1/Gen-2 fleet or a protocol bridge layer.

3. **EcountCore stored-procedure DAL**: The DS_DB_ecountcore database — a 20-year-old SQL Server monolith with 300+ stored procedures containing embedded business logic — is the system of record for all prepaid card accounts. Every analytical, reporting, and card-lifecycle capability downstream of this database cannot be modernised until the stored-procedure business logic is extracted into service-layer code and the database schema is decomposed.

**Estate-wide single points of failure (SPOFs) requiring immediate architectural attention:**

- director-svc_SVC: credential broker for 90–110 services; no HA configuration confirmed
- xml-rpc_LIB: transport for every Gen-1/Gen-2 service call; single CVE = estate-wide outage
- jobservice_SVC / job-scheduler_SVC: no Gen-3 equivalent; all batch disbursement routes through this
- Great Plains (banker_API): sole financial data integration; 120-second SERIALIZABLE transactions cascade to all consumers
- IBM MQ / TIBCO JMS brokers: on-premises messaging with no cloud-native failover
- ecountcore SQL Server: system of record with no read replica and no decomposition plan
- StrongBox (strongbox-xmlrpc_SVC): cryptographic trust anchor for all Gen-1/Gen-2 encrypted data

**The architectural debt that must be resolved before Gen-1 can be decommissioned** falls into five categories: unauthenticated protocol surfaces (Director, XML-RPC, Spring HTTP Invoker); EOL runtimes on critical payment paths (Java 1.5/1.6 on ACH, chargeback, and IVR services); broken cryptographic implementations (MD5/DES in xplatform-library_LIB, DESede with fixed IV in xsso_SVC, co-located keys and ciphertext in StrongBox); financial data in plaintext (PAN in emboss-extract files, CVV in ecountcore and request-file_LIB XML output, PAN as stored procedure parameter); and Windows-native deployment dependencies (NDM, VBScript, BCP.exe, hardcoded Windows filesystem paths) that prevent containerisation of 40+ services.

---

## 2. Three-Generation Platform Architecture

### Gen-1 (eCount/Citi, pre-2015): ~150 repos, 55–65% production traffic

The Gen-1 estate is the operational foundation of Onbe's business. It comprises the cardholder account management system (ecount-core_SVC, EcountCore SQL Server), the card program management stack (director-svc_SVC, xplatform_LIB, xplatform-library_LIB), the batch disbursement pipeline (jobservice_SVC, batch_LIB, autoclaim-split-svc_LIB), the client administration portals (clientzone_WAPP, csa_WAPP), and the cryptographic infrastructure (strongbox-xmlrpc_SVC, xsecurity_SVC).

**Technology profile:** Java 1.5–1.8 targets; Spring 1.x–2.5.x XML configuration; Apache Axis 1.4 SOAP (RPC-encoded, WS-I non-compliant); XML-RPC via xml-rpc_LIB as the universal service bus; Struts 1.3.x for web applications; Log4j 1.2.x (CVE-2019-17571 RCE present in auto-card-batch_LIB and emboss-extract_LIB); Windows-only deployment (D:\c-base, NDM file transfer, Windows Task Scheduler, VBScript operations); stored-procedure-centric data access across ecountcore, cbaseapp, jobsvc, and ordersvc databases; Director credential brokering for all service startups; Spring HTTP Invoker (deprecated Spring 5.3, removed Spring 6) for inter-service RPC.

**Notable Gen-0 outliers** within this tier — auto-card-batch_LIB (Spring Batch 2.1.1, Java 1.5, EOL since 2010), emboss-extract_LIB (Spring 2.0, Log4j 1.2.8, plaintext PAN XML output), pos-connector_LIB (Spring 1.2.7), spring-refer-a-friend_WAPP (Spring 2.0.2, Java 1.5) — represent services so aged they have no viable upgrade path without full replacement.

### Gen-2 (Wirecard/Northlane, 2015–2021): ~140 repos, 25–35% traffic

The Gen-2 estate represents Onbe's first containerisation attempt. It introduced Spring Boot 1.5–2.5, Java 8–21, AWS ECS deployment, Docker containerisation, and structured logging. However, it did not break the fundamental Gen-1 architectural patterns: Gen-2 services still depend on Director for credentials, still consume xml-rpc_LIB for eCountCore access via xml-rpc-clients_LIB, still use IBM MQ and TIBCO JMS for messaging, and still write to the same SQL Server databases through direct JDBC rather than service APIs.

**Key Gen-2 architectural sub-estates:** The Wirecard issuing platform (11 wirecard_* repositories) operates an Oracle-based, ActiveMQ-driven, Ansible-RPM-deployed platform entirely self-contained but dependent on the same Director credential brokering. It carries BouncyCastle 1.48 (2012, multiple CVEs) as its cryptographic foundation. The Cambridge FX dual-stack (cambridge-auth-service_LIB / cambridge-service_LIB on Axis SOAP, plus cbts-client_LIB / cross-border-transfer-service_SVC on REST) operates two parallel implementations for the same external vendor without a documented migration plan. The AWS infrastructure (nlroot-aws_INFRA_TF, nlutil-aws_INFRA_TF) runs QA and production in the same AWS account without environment isolation.

**Wirecard infrastructure dependency:** A significant subset of Gen-2 and Gen-3 services (recipient-screening-api, stand-in-recovery-service, Automation_ClientZone test suites) retain DNS references to `nam.wirecard.sys` and `wirecard.sys` infrastructure. These represent a corporate governance risk — Wirecard went insolvent in 2020, and ownership/maintenance responsibility for this Active Directory domain post-acquisition is unresolved.

### Gen-3 (NexPay/Onbe, 2021+): ~60 repos, 5–15% traffic

The Gen-3 estate represents the target architecture: Java 21–25, Spring Boot 3.x–4.x, Azure Container Apps (ACA) / AKS, Dapr sidecar for secrets and pub/sub, Azure Key Vault with Managed Identity, OpenAPI-first contracts, Flyway-managed schemas on Azure PostgreSQL, OpenTelemetry with Dynatrace OTLP, and CycloneDX SBOM generation.

**Architectural patterns established:** Orchestration Saga with PostgreSQL state persistence (SagaState, SagaStateTransitions, outbox_event); SPI adapter pattern for processor extensibility (nexpay-cardprocessor-svc with Thredd and FIS adapters); BFF pattern (nexpay-recipientweb-bff, nexpay-clientadminweb-bff, nexpay-ivr-bff); OpenAPI-first with generated client libraries published as Maven artifacts; virtual threads (Project Loom) as the concurrency model across all Gen-3 services.

**Critical Gen-3 gaps:** Three P0 findings prevent Gen-3 from being considered production-ready at scale. recipient-screening-api has `anyRequest().permitAll()` with no authentication on the OFAC screening endpoint. Both nexpay-order-orchestrator and nexpay-recipientorchestrator-svc have compensation logic that is stubbed (log-only, no rollback). om-payment-api's JwtSecurityValidator unconditionally returns `true`, disabling all authorization. Additionally, no production Terraform definitions exist in nexpay-iac — production infrastructure is provisioned outside IaC governance.

---

## 3. Estate-Wide Architecture Patterns (Cross-Domain)

The following ten integration and architectural patterns recur across multiple domains and collectively define the migration challenge facing Onbe's engineering organisation.

**Pattern 1: Director hub-and-spoke credential brokering**
director-svc_SVC functions as a credentials registry and service registry for all Gen-1 and Gen-2 services. Its /dispatch.asp endpoint returns database passwords, API keys, and SMTP credentials as plaintext `Map<String,String>` over HTTP with no authentication. The director-client_LIB is embedded in every consuming service, making Director a startup prerequisite for 90–110 services across all 15 domains. This pattern appears in Domains 1, 2, 4, 6, 7, 8, 9, 12, and 13.

**Pattern 2: XML-RPC dispatch without authentication**
xml-rpc_LIB's XmlRPCServlet dispatches to any Spring bean in the application context by constructing bean names directly from HTTP headers (RPC-Interface, RPC-Method) with no authentication, no allowlist, and no authorization. Any internal network actor can invoke any registered bean method — including financial transaction operations, card blocking, SSN update, and account closure. This pattern appears in Domains 1, 2, 4, 6, 7, 8, and 15.

**Pattern 3: Axis 1.4 / JAX-RPC RPC-encoded SOAP**
Apache Axis 1.4 (EOL 2006) with RPC-encoded style (explicitly prohibited by WS-I Basic Profile 1.1 and removed from JAX-WS) is used for both external API exposure (clientapi_API, account-management-api_API, banker_API) and internal SOAP service consumption (cambridge-auth-service_LIB, rsa-mfa_LIB, ivrintegration_API). Axis 1.4 carries CVE-2019-0227 with no patch path. This pattern appears in Domains 1, 2, 3, 4, 5, 9, and 13.

**Pattern 4: Spring HTTP Invoker (Java serialization RPC)**
Spring HTTP Invoker was deprecated in Spring 5.3 and removed in Spring 6.0. It is used for inter-service calls between account-management-api_API, manage-payment-rest-api, om-payment-api, scheduler_WAPP, and the Order/Banker/JobService backend services. Java deserialization without a class allowlist is a documented RCE vector. scheduler_WAPP's unauthenticated Spring HTTP Invoker endpoint accepts inbound deserialized requests from any internal caller. No service in this communication graph can upgrade to Spring 6 while it participates in Spring HTTP Invoker communication. Affects Domains 4, 6, 9, and 15.

**Pattern 5: Stored-procedure data access layer**
Every Gen-0/Gen-1/Gen-2 service performs all write operations and most read operations through T-SQL stored procedures. The EcountCore database alone has 300+ stored procedures containing fee calculations, velocity checks, escheatment rules, and NACHA date logic that have never been extracted into service-layer code. Schema changes are high-risk cross-team events with no automated migration tooling. This pattern appears across all operational domains.

**Pattern 6: NDM / Sterling Connect:Direct file-based messaging**
Batch operations across check issuance, card emboss file delivery, ACH file exchange, and Citibank wire instructions all use NDM (Network Data Mover) file transfer agents. Files are generated in proprietary fixed-length formats, deposited to Windows filesystem directories, and picked up by file-transfer-service for SFTP transmission. These services cannot be containerised without replacing the NDM dependency. This pattern appears in Domains 1, 2, and 6.

**Pattern 7: Dual-database non-atomic financial writes**
Multiple services (branded-currency_LIB, chargeback-engine_LIB, account-service_LIB, drawdown-data-manager_LIB, ieft-cp2e_LIB) perform financial state changes across two databases without a distributed transaction coordinator. The pattern is: commit to database A, then commit to database B in a separate transaction. Failure between the two commits leaves balances, status flags, or journal entries in irreconcilable split state with no compensating transaction or saga. This pattern appears in Domains 1, 2, and 4.

**Pattern 8: Test-skip CI anti-pattern**
All 22 repositories in Domain 01 and the majority of the Gen-1/Gen-2 estate suppress test execution in CI via `-DskipTests`, `<skip>true</skip>`, or equivalent Maven/Gradle configuration. Domain 14's Gen-1 SOAP regression suites also lack a CI execution path. Four of the most critical API suites (account-management, cs-api, client-api-v4, debit-api) are manually triggered only. The platform accumulates changes without any automated verification gate across all 15 domains.

**Pattern 9: Binary JAR dependency coupling without service contracts**
Core platform libraries (ecount-system_LIB, account-service_LIB, branded-currency_LIB, xaffiliate-service_LIB, xplatform_LIB, services-common_LIB, xml-rpc_LIB) are delivered as compiled JARs consumed through Maven dependencies. There are no REST, gRPC, or messaging contracts. SNAPSHOT artifact consumption (xml-rpc_LIB 3.1.3-SNAPSHOT, ecount-system_LIB 4.0.4-SNAPSHOT, services-common_LIB 3.0.2-SNAPSHOT) makes production builds non-reproducible and violates PCI DSS Req 6.3.2. This pattern spans Domains 1, 2, 4, 6, 7, 8, and 15.

**Pattern 10: Feature-flag-less dual-stack deployment**
The migration switch from Gen-1 to Gen-3 for the cardholder portal (Domain 3) is a single affiliate feature flag (`display_recipient_web = Y` in xaffiliate-service_LIB's `findAccessLevelFeatureMap()`). This flag has no audit log, no automated rollback capability, and is the load-bearing architectural control for the entire Gen-1-to-Gen-3 cardholder migration. A misconfiguration of this flag could expose Gen-3 services — some of which have unauthenticated endpoints — to production cardholder traffic at scale. No equivalent feature flag governance or canary deployment mechanism exists for any other cross-generation migration boundary.

---

## 4. Critical Architectural Dependencies (Migration Blockers)

The following eight components must be addressed as a precondition to Gen-1 decommission, listed in dependency order.

**1. Director (director-svc_SVC / director-client_LIB) — Estate-wide SPOF, 90–110 repos dependent**
Director is the operational keystone of the entire Gen-1 and Gen-2 platform. Its /dispatch.asp endpoint returns production credentials over unauthenticated HTTP. Without Director running, every dependent service fails to initialise. No HA configuration, circuit breaker, credential cache, or fallback credential source exists in any consumer. Director must be replaced with Azure Key Vault (Managed Identity) and Kubernetes service DNS before any dependent service can achieve cloud-native autonomous deployment. The replacement must be executed as a fleet-wide coordinated cutover — there is no incremental path because all consumers call Director before they can serve any traffic. Affected domains: 1, 2, 3, 4, 5, 6, 7, 8, 9, 12, 13.

**2. xplatform / cBase XML-RPC bus — Core messaging fabric for Gen-1**
xml-rpc_LIB is the transport for every Gen-1 and Gen-2 service-to-service call. It is embedded as a JAR in every consuming service WAR, meaning a critical defect affects all services simultaneously. The proprietary `application/x-mapxml` wire format has no compatible alternative client or server — replacement requires either simultaneous fleet-wide change or a protocol bridge layer (REST/gRPC gateway forwarding to internal XML-RPC). The agent/affiliate HTTP header scoping that provides Gen-1's multitenancy isolation is cryptographically unenforced — any XML-RPC caller can forge any agent identity. Affected domains: 1, 2, 4, 6, 7, 8, and all domains whose services consume xml-rpc-clients_LIB.

**3. JobService distributed scheduler (jobservice_SVC, job-scheduler_SVC) — All batch jobs**
The JobService platform (JobManager, WorkflowManager, JobAgent via TIBCO JMS) has no Gen-3 equivalent. All client batch disbursement jobs — insurance claims, automotive rebates, gig payouts, incentive programs — route through this platform. job-scheduler_SVC is the single scheduling gate; its failure blocks all batch job execution across all programs. scheduler_WAPP (Domain 4) compounds this with an unauthenticated Spring HTTP Invoker endpoint accepting Java-deserialized requests. No decommission plan or Gen-3 replacement specification exists for any of these components. Affected domains: 4, 6, and every domain with batch payment operations.

**4. EcountCore stored-procedure DAL — Financial transaction core**
DS_DB_ecountcore is the system of record for all prepaid card accounts. Its 300+ stored procedures contain embedded business logic (fee calculations, velocity checks, escheatment rules, NACHA timing, FDR/Fiserv/Citi NAOT card management table sets) that has never been extracted into service-layer code. ecount-core_SVC maintains both a Gen-3 REST endpoint layer (Azure AD OAuth2) and a Gen-1 XML-RPC endpoint layer simultaneously — meaning the REST authentication does not protect the same data and operations accessible via XML-RPC. Zero-downtime migration of a live 20-year-old financial database with 300+ stored procedures and active cardholder accounts is a multi-year programme requiring dedicated programme-level governance. Affected domains: 1, 2, 3, 4, 6, 8, 9, 10.

**5. SQL Server on-premises estate (50+ databases)**
Beyond ecountcore, the platform operates cbaseapp, jobsvc, ordersvc, riskdb, strongbox, notificationsvc, repositorysvc, banker, and 15 per-server instance scripts (DS_DP_db01 through DS_DP_db15). Gen-3 services (stand-in-processing-api, stand-in-recovery-service, recipient-screening-api) connect directly to these on-premises databases via VNet peering, creating a hybrid CDE network topology that must be formally documented for PCI DSS network segmentation. The DPAPI machine-bound ETL encryption in DS_ETL_warehouse means the entire analytical layer's credentials are bound to a single Windows user account on a single server — loss of that account permanently destroys warehouse ETL access. Affected domains: 2, 3, 4, 6, 9, 10.

**6. IBM MQ / TIBCO JMS — Async messaging for Gen-1/Gen-2 boundary**
notification-framework_SVC uses IBM MQ v9.4.0.0 between its EventHandler and Subscriber modules. The JobAgent execution queue uses TIBCO JMS. Both require on-premises or vendor-cloud infrastructure conflicting with Onbe's Azure-primary cloud strategy. The proprietary Wirecard EventHub client (com.wirecard.eventhub:eventhub-client:2.1.188) in Domain 13 is the only option for event exchange between funds-transfer-coordinator and all bank agents — replacement requires simultaneous changes to all consumers. None of these message brokers have dead-letter queuing or retry configurations documented in any repository. Affected domains: 6, 7, 13.

**7. StrongBox key management (strongbox-xmlrpc_SVC) — All cryptographic operations**
The StrongBox cluster is the cryptographic trust anchor for all Gen-1 and Gen-2 cardholder data protection. RSA private keys are co-located with ciphertext in the same SQL Server database — a single database compromise yields complete decryption of all Gen-1/Gen-2 protected cardholder data (PCI DSS Req 3.6.1 direct violation). Key material transits Gen-2 consumers over unencrypted HTTP via strongbox-remote-client_LIB's default transport configuration. Migration requires: inventorying all consuming services; designing a key export ceremony to move RSA private keys to Azure Key Vault HSM; re-encrypting all vault-stored records; updating all consumers. This is a multi-year programme; interim SQL Server Always Encrypted is the mandatory immediate step. Affected domains: 1, 2, 5, 9, 13.

**8. Director-sourced credential injection into Gen-2/Gen-3 services**
Even services that have been partially modernised (cross-border-transfer-service_SVC, card-notification-restful_API, ivr-ws_API boot module) retain director-client_LIB as a startup dependency. Until Director is replaced, these services cannot be deployed autonomously or achieve the credential-at-rest isolation required for PCI DSS Req 8 compliance. The pattern of retrieving credentials at startup via XML-RPC means that credential rotation requires coordinated service restarts across the entire fleet.

---

## 5. Domain-to-Domain Dependency Map

The table below identifies which domains are consumers or producers of critical shared services, and which domains would be directly impacted by failure of each service.

| Shared Service | D01 | D02 | D03 | D04 | D05 | D06 | D07 | D08 | D09 | D10 | D11 | D12 | D13 | D14 | D15 | Blast Radius |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| Director (credential broker) | X | X | X | X | — | X | X | X | X | — | X | X | X | — | X | 12 domains — platform-wide startup cascade |
| xml-rpc_LIB / XML-RPC bus | X | X | X | X | X | X | X | X | — | — | X | — | X | X | X | 11 domains — every Gen-1/Gen-2 service call |
| jobservice_SVC / JobScheduler | — | X | — | X | — | X | X | — | — | — | X | — | X | — | X | 7 domains — all batch disbursement halted |
| EcountCore (DB + SVC) | X | X | X | X | X | X | — | X | X | X | X | X | X | X | — | 13 domains — card account system of record |
| StrongBox (key management) | X | X | — | — | X | — | — | X | X | — | — | — | X | — | — | 6 domains — all encrypted cardholder data |
| notification-framework_SVC | X | — | X | X | — | X | X | — | — | — | X | — | — | — | X | 7 domains — all cardholder communications |
| order_SVC | X | X | — | X | — | X | — | — | — | — | X | — | — | X | — | 6 domains — all order processing |
| Great Plains (banker_API) | — | X | — | X | — | X | — | — | — | X | X | — | X | — | — | 6 domains — all financial balance queries |
| IBM MQ / TIBCO JMS | — | X | — | — | — | X | X | — | — | — | — | — | X | — | X | 5 domains — async processing halted |
| recipient-screening-api (OFAC) | — | — | X | — | X | — | — | — | — | — | X | — | — | X | — | 4 domains — all Gen-3 disbursement gated |
| Spring Config Server (Gen-2) | — | X | — | X | — | X | — | — | — | — | X | X | X | — | — | 5 domains — Gen-2 service startup |

---

## 6. Top 20 Enterprise Architecture Findings (P0/P1)

Ranked by architectural blast radius across the 363-repo estate.

| Rank | Finding | Domains Affected | Pattern | Architectural Risk | Migration Impact | Priority |
|---|---|---|---|---|---|---|
| 1 | **Director unauthenticated credential broker** — /dispatch.asp returns plaintext production credentials (DB passwords, API keys, SMTP) to any HTTP caller with network access. No mTLS, no auth token, no IP allowlist at the application layer. | 12 | Director hub-and-spoke | Platform-wide credential exfiltration via single request; Director failure = estate-wide startup cascade | Must precede all Gen-3 migration; fleet-wide coordinated replacement required | P0 — Immediate |
| 2 | **XML-RPC no-auth dispatch** — XmlRPCServlet in xml-rpc_LIB constructs Spring bean names from HTTP headers with no authentication or authorization; any internal caller can invoke financial transaction operations, card blocking, or SSN update | 11 | XML-RPC unauthenticated bus | Any compromised internal host can initiate unauthorized financial operations; agent/affiliate header forgery enables cross-program data access | Protocol bridge required before any consumer can be migrated; cannot be addressed per-service | P0 — Immediate |
| 3 | **om-payment-api authorization disabled in production** — JwtSecurityValidator.java unconditionally returns `true` (line 57), all JWT authorization logic commented out; any caller can invoke createAccount, addFunds, withdraw, cardInquiry | 4, 11 | Commented-out security control | CVV and PAN retrieval, fund addition and withdrawal exposed to any network caller; PCI DSS Req 7.2 direct violation | 3–5 days to re-enable; authorization model already designed but bypassed | P0 — Emergency (same day) |
| 4 | **OFAC screening endpoint entirely unauthenticated** — recipient-screening-api SecurityConfig uses `anyRequest().permitAll()`; the sole OFAC/sanctions screening control on the Gen-3 platform is accessible to any network actor who can inject APPROVED results or bypass screening | 3, 5, 11 | Unauthenticated critical control | Regulatory: sanctions violations, OFAC enforcement; business: fraudulent disbursements to screened parties | Add Spring Security OAuth2 resource server; wiring already partially scaffolded | P0 — Immediate |
| 5 | **StrongBox RSA keys co-located with ciphertext** — strongbox-xmlrpc_SVC stores RSA private keys in the same SQL Server database as the ciphertext they encrypt; single DB compromise = complete Gen-1/Gen-2 cardholder data decryption | 1, 2, 5, 9, 13 | Insecure key storage | PCI DSS Req 3.6.1 direct violation; blast radius covers all Gen-1/Gen-2 encrypted cardholder records across 15+ years | Multi-year programme; interim: SQL Server Always Encrypted within 60 days | P0 — Critical |
| 6 | **PANs transmitted in cleartext XML** — emboss-extract_LIB writes full PANs as `<cardnumber>` elements in plaintext XML files at `/upload/EmbossFileExtract/` before NDM transmission to card bureaus | 1 | Plaintext PAN in file pipeline | PCI DSS Req 3.5.1 direct violation; any filesystem or NDM access = full PAN exposure | File-level AES-256 encryption wrapper; key from Azure Key Vault | P0 — Within 30 days |
| 7 | **CVV stored in ecountcore fdr_card_account_detail.cv_code** — DS_DB_ecountcore analysis identifies post-authorization CVV storage in the primary card account database; QSA notification required if confirmed | 1, 10 | SAD storage violation | PCI DSS Req 3.3.1 unconditional violation; requires immediate QSA engagement and purge procedure | Verify storage lifecycle; implement purge stored procedure; disable column retention | P0 — QSA notification |
| 8 | **MD5 password hashing for operator accounts** — xsecurity_SVC uses MD5 for new operator registrations and all dormant accounts; minimum password length 6–8 characters against PCI DSS requirement of 12 | 5 | Broken cryptography in auth | PCI DSS Req 8.3.2 direct violation; offline dictionary attack on credential database | Requires parallel identity migration for all operator accounts to Entra ID | P0 — Critical |
| 9 | **TLS certificate validation disabled for all MFA traffic** — rsa-mfa_LIB uses TrustAllSSLSocketFactory, disabling certificate validation for all MFA SOAP calls to RSA Adaptive Authentication | 5 | MITM exposure on MFA path | Complete MITM exposure for every MFA transaction on OnePlatform and ClientZone portals | Replace with Microsoft Entra MFA; Axis SOAP stack cannot be safely maintained | P0 — Within 30 days |
| 10 | **chargeback-engine_LIB requires JVM class removed in JDK 8** — depends on sun.jdbc.odbc.JdbcOdbcDriver (removed JDK 8, 2013); service is non-functional on any supported JVM; Reg E dispute resolution timelines materially affected | 1 | EOL runtime dependency | Reg E breach: if not running, dispute processing timeline is violated; if running on JDK 7 (EOL), no security patches since 2015 | Assess operational status; replace with Microsoft JDBC Driver; quantify Reg E exposure | P0 — Assess immediately |
| 11 | **Dual orchestrator overlap with double-payment risk** — nexpay-order-orchestrator and nexpay-recipientorchestrator-svc implement identical saga logic with the same entry-point path, same PostgreSQL schema, same SagaState — both can be triggered for the same claim code | 3, 11 | Undefined domain boundary | Double-payment is structurally possible; no cross-orchestrator uniqueness constraint; no formal trigger routing boundary | Declare formal boundary; add cross-orchestrator Redis lock before saga creation | P0 — This sprint |
| 12 | **Saga compensation logic stubbed across both orchestrators** — compensation methods in both nexpay-order-orchestrator and nexpay-recipientorchestrator-svc log a warning and take no action; failed sagas leave card issuance, ACL write-back, and fund allocation in indeterminate state | 3, 11 | Incomplete saga implementation | Failed financial transactions leave irreconcilable state across card processor, OFAC screening, and legacy ACL; Reg E error resolution obligations | Implement card reversal, ACL rollback, and outbox notification before production traffic at scale | P0 — This quarter |
| 13 | **stip-generated and stip-models are empty repositories** — no canonical STIP schema exists; every STIP-aware service independently defines its stand-in processing data model; stand-in-processing-api has a 99.999% uptime target with no schema governance anchor | 9 | Governance gap | FFIEC Business Continuity gap; silent incompatibilities between STIP services; no version-controlled definition of a stand-in authorisation request | Assign STIP domain owner; initiate stip-models schema definition; prerequisite for all STIP Gen-3 work | P0 — Assign owner immediately |
| 14 | **No production IaC for Gen-3 platform** — nexpay-iac has no prod.tfvars; production infrastructure is provisioned outside Terraform governance; no auditable infrastructure change history; disaster recovery untested | 11, 12 | IaC governance gap | PCI DSS Req 6.5 change management gap; production infrastructure cannot be recreated from source; DR untested | Define prod.tfvars with Key Vault purge protection, per-service managed identities, private endpoints | P1 — Before next QSA |
| 15 | **Spring HTTP Invoker removal in Spring 6 blocks all Gen-3 migration** — scheduler_WAPP, order_SVC, banker_API, account-management-api_API, manage-payment-rest-api all participate in Spring HTTP Invoker RPC; Spring 6 removed this mechanism entirely; circular migration dependency prevents any single service from upgrading first | 4, 6, 9 | Deprecated RPC mechanism | All consuming services frozen at Spring 5.3 maximum; Spring 5.3 OSS EOL approaching; unauthenticated deserialization RCE risk on scheduler_WAPP | Replace scheduler_WAPP with Azure Scheduler first; REST interfaces for Order/Banker/Job | P1 — 60–90 days |
| 16 | **SASI Gen-1 database coupling undermines 99.999% availability target** — stand-in-processing-api reads directly from four Gen-1 on-premises SQL Server databases (ecountcore, cbaseapp, jobsvc, ordersvc) during stand-in operations; the standby that covers primary system outages shares dependencies with the system it replaces | 9, 10 | Availability paradox | SASI availability claim is structurally false; Gen-1 outage triggers SASI activation and simultaneously removes SASI's data source | Event-driven pre-population of SASI Azure SQL; eliminate Gen-1 runtime reads | P1 — Half-year programme |
| 17 | **Git as primary secrets store for production payment platform** — CONFIG_dev/qa/uat/prod repos, api-config-repo, and multiple application repos contain committed production credentials; all secrets accessible to any repository reader | 1, 12 | Secrets in VCS | PCI DSS Req 8.3.1 direct violation; historical Git pack files retain secrets indefinitely | Secret rotation + git filter-repo history rewrite + Azure Key Vault migration; 90-day programme | P0 — Rotate now, migrate 90 days |
| 18 | **SQL injection via string concatenation in chargeback-engine_LIB** — ChargebackHelper.java:60 constructs SQL query by string concatenation of unvalidated input in a financial dispute processing context | 1 | SQL injection | PCI DSS Req 6.2.4 direct violation; data integrity and confidentiality risk in dispute processing | Parameterised PreparedStatement; same fix cycle as chargeback JDBC driver replacement | P0 — Same fix sprint |
| 19 | **wirecard_sftp-common-utilities_LIB Java version mismatch** — compiled with maven.compiler.source/target=21 while all Gen-2 consumers run Java 8 JVMs; loading a Java 21 class in a Java 8 JVM throws UnsupportedClassVersionError; Gen-2 services consuming v2.0.0 may be failing silently | 13 | Build/runtime version mismatch | If deployed, Gen-2 Wirecard services fail at startup; NACHA and wire transfer disbursements potentially affected | Fix compiler target to Java 8; audit which services consumed v2.0.0; assess silent failure window | P0 — Audit immediately |
| 20 | **DPAPI machine-bound ETL encryption in DS_ETL_warehouse** — SSIS protection level EncryptSensitiveWithUserKey binds all warehouse ETL credentials to a single Windows user account on server P-NA-DB11; loss of that account permanently destroys all warehouse ETL credential access | 10 | Single-person key custody | Business continuity: entire analytical layer irrecoverable without that user account | Migrate to DontSaveSensitive with SSIS Catalog environment variables backed by team-accessible secrets store | P0 — Business continuity |

---

## 7. Gen-3 Readiness Assessment

### NexPay Core Services (Domains 3, 9, 11)

**nexpay-cardprocessor-svc:** Most architecturally complete Gen-3 service in the estate. SPI adapter pattern for Thredd and FIS, Flyway schema migrations, Envers audit trail, scoped routing via ScopeMap, structured OTLP observability. **Production readiness gaps:** SNAPSHOT parent POM (nexpay-parent:0.2.8-SNAPSHOT) creates non-reproducible builds; container running as root user; no circuit breaker on POST /v1/cards creation path; FIS cardNum PAN audit pending. **Gen-1/Gen-2 dependencies:** none at runtime. **Recommended cutover:** can accept increased traffic once SNAPSHOT is stabilised, circuit breaker added, and root container addressed.

**recipient-screening-api:** Architecturally Gen-3 but with a critical Gen-0 security configuration. `anyRequest().permitAll()` makes this the highest-priority individual finding in the domain. **Dependencies:** cbaseapp and EcountCore databases on `wirecard.sys` infrastructure (p-lis-db02/03.nam.wirecard.sys). **Cannot scale to full production traffic** until: (1) OAuth2 resource server authentication added; (2) HMAC webhook signature validation wired in SanctionWebhookRequestValidator; (3) wirecard.sys database dependency migrated to Azure SQL.

**nexpay-order-orchestrator and nexpay-recipientorchestrator-svc:** Both are architecturally sound (PostgreSQL saga state, transactional outbox, formal SagaStateTransitions) but have two P0 blockers: compensation stubs are no-ops, and the dual-orchestrator boundary creates double-payment risk. **Cannot be promoted to full production scale** until: (1) formal boundary declared and enforced via ADR; (2) card reversal and ACL rollback compensation implemented; (3) UNIQUE constraint on claim_code across both saga tables added; (4) cross-orchestrator Redis deduplication key in place.

**stand-in-processing-api (SASI):** Gen-3 platform but Gen-1 data dependency. The 99.999% uptime SLA is architecturally compromised by runtime reads from four Gen-1 on-premises databases. **Cutover sequence:** (1) build event-driven data sync from Gen-1 databases to SASI Azure SQL (half-year programme); (2) remove disable-security-filter bypass flag from production code; (3) replace SOAP with REST-only as Gen-1 SOAP clients migrate.

**nexpay-recipientweb-bff:** Active production, architecturally correct (JWE stateless session, APIM external boundary, virtual threads). **Gaps:** multiple TODO comments in registration flow; no circuit breaker or retry on downstream REST clients (SimpleClientHttpRequestFactory used throughout). Can accept increased traffic with circuit breaker addition and TODO resolution.

**nexpay-ivr-bff:** Must not receive real IVR traffic. The FsCustomerInquiryController returns hardcoded values including placeholder SSN `987654321` and static card account number. Deployed to external APIM. External APIM route must be disabled until stub is replaced.

**nexpay-config-svc:** No Spring Security configuration. As the authoritative source for which payment rails are active for each client program, any internal network actor can read or modify program configurations. Spring Security must be added before this service controls production program configurations.

### OnePlatform Migration Status (Domains 3, 4)

The `display_recipient_web = Y` affiliate feature flag is the operational migration switch between Gen-1 and Gen-3 cardholder portals. It is the load-bearing architectural control for the migration, yet it has no audit log, no automated rollback, and routes traffic to Gen-3 services that have the production gaps noted above. The Gen-1 fallback (oneplatform_WAPP, enrollment_WAPP) carries active Struts 1.x RCE CVEs — migration must continue forward, not pause.

### Domain 14 Testing Gap

The Gen-3 nucleus of Domain 14 (qa-ui-test-automation, qa-api-test-automation, qa-test-orchestrator) is mature and well-structured. However, four of the most critical Gen-1 API regression suites (account-management, cs-api, client-api-v4, debit-api) have no CI execution path and depend on `webservice-qa.wirecard.com` — a domain associated with an insolvent company. Loss of this QA endpoint eliminates all automated regression coverage for the Gen-1 card lifecycle API tier simultaneously.

---

## 8. Strategic Migration Roadmap (Phased)

### Phase 1 (0–90 days — Security Baseline)

These are non-negotiable security fixes that reduce the immediate blast radius of confirmed compliance exposures. They do not require architectural change — they are code-level and operational remediation actions.

- **Day 1–7:** Re-enable JwtSecurityValidator in om-payment-api (3–5 days; existing auth model fully designed). Add OAuth2 resource server to recipient-screening-api (1 week). These are the two highest-priority PCI DSS Req 7 violations in the Gen-3 estate and both can be resolved with minimal code changes.
- **Week 1–4:** Rotate all credentials committed to source control across Domains 1, 2, 5, 12, and 13. Engage git filter-repo history rewrite across all identified repositories. Rotate the SFTP private key from infrastructure repo (treat as compromised). Rotate wirecard_sg-bank-agent PGP keys and the wirecard_test-utilities_LIB PGP key distributed in production JARs.
- **Week 1–4:** Verify CVV storage in ecountcore fdr_card_account_detail.cv_code. If confirmed, notify QSA, implement purge stored procedure, and disable PAN parameter capture in all SQL monitoring tools.
- **Week 4–8:** Assess chargeback-engine_LIB operational status. If running on JDK 7 (EOL since 2015), document as critical security risk. If not running, engage Compliance to quantify Reg E exposure. Begin driver replacement (sun.jdbc.odbc.JdbcOdbcDriver → Microsoft JDBC Driver for SQL Server).
- **Week 4–12:** Add mTLS authentication to Director's /dispatch.asp for production calls as an interim hardening measure while the replacement programme is designed. Implement credential caching in director-client_LIB to reduce blast radius of Director unavailability.
- **Week 4–12:** Migrate DS_ETL_warehouse SSIS protection level from EncryptSensitiveWithUserKey to DontSaveSensitive. Store warehouse ETL credentials in a team-accessible secrets store.
- **Week 8–12:** Implement AES-256 file-level encryption in emboss-extract_LIB using an Azure Key Vault-managed key.

### Phase 2 (90–180 days — Decouple)

This phase breaks the most critical structural dependencies and introduces the foundational security infrastructure that all subsequent migration phases require.

- **Director replacement programme:** Define Azure Key Vault + Kubernetes service DNS as the target. Implement a Director-to-cloud adapter that translates existing Director key paths to Azure Key Vault, allowing services to migrate their Director calls incrementally. Target: all 90–110 dependent services migrated off Director before end of Phase 3.
- **Authenticated service mesh:** Deploy Azure API Management as the perimeter for all inter-service calls that currently traverse the XML-RPC bus, beginning with ecount-core_SVC's REST endpoints. Define an allowed operation list and OAuth2 client credentials for all new service-to-service calls.
- **Secrets vault establishment:** Migrate all CONFIG repo properties and api-config-repo secrets to Azure Key Vault with Managed Identity. Enforce no-plaintext-secret rule in CI via Trufflehog or equivalent scanning.
- **scheduler_WAPP replacement:** This is the first decommission target — an unauthenticated deserialization endpoint, a Spring 6 migration blocker, and a clear replacement by Azure Scheduler with authenticated REST-based callback registration. Catalogue all consumer callback registrations; build REST-based replacement; migrate consumers one by one.
- **om-payment-api XStream and Spring HTTP Invoker:** Remove XStream deserialization (replace with Jackson). Begin migration from Spring HTTP Invoker to REST for Order/Banker/Job service calls from om-payment-api and manage-payment-rest-api.

### Phase 3 (180–365 days — Protocol Modernisation)

This phase replaces the proprietary Gen-1 wire protocols with standards-compliant alternatives, enabling independent service deployment and cloud-native operation.

- **XML-RPC protocol bridge:** Deploy a REST/gRPC gateway that accepts authenticated inbound calls (OAuth2 client credentials, TLS 1.2+, operation allowlist) and internally forwards to eCountCore's existing XML-RPC endpoints via xml-rpc-clients_LIB. This bridge is the central Domain 8 migration action — it unblocks consumer migration from XML-RPC one service at a time without requiring a simultaneous big-bang migration.
- **Axis SOAP retirement:** Complete Cambridge SOAP-to-REST migration (cambridge-auth-service_LIB and cambridge-service_LIB to cbts-client_LIB / cross-border-transfer-service_SVC). Retire ivrintegration_API once check-cashing volume is confirmed or migrated to nexpay-ivr-bff. Retire rsa-mfa_LIB — replace with Microsoft Entra MFA.
- **StrongBox interim remediation:** Implement SQL Server Always Encrypted on key columns as interim PCI DSS Req 3.6.1 remediation. Build Azure Key Vault facade maintaining the XML-RPC interface for consumer migration transparency.
- **EOL runtime upgrades:** Migrate auto-card-batch_LIB, emboss-extract_LIB, pos-connector_LIB, and consumerload_API from Java 1.5/1.6/6 to Java 21. Replace Log4j 1.2.x with Log4j2. Upgrade ecore-batch_LIB from sqljdbc 1.1 (TLS 1.0 only) to Microsoft JDBC Driver 12.x.
- **xsecurity_SVC identity migration:** Begin operator account migration from Acegi Security / MD5 hash model to Microsoft Entra OIDC. Parallel provider operation during transition period.
- **OFAC screening domain capability:** Establish a domain-level OFAC/sanctions screening gateway callable by all disbursement rails (ach-withdrawal-initiator, cross-border-transfer-service, check-issuance, ieft-cp2e). This requires Legal and Compliance sponsorship and is an enterprise architecture decision, not a per-service fix.

### Phase 4 (1–2 years — Gen-1 Retirement)

This phase decommissions the eCount/Citi stack once Gen-3 achieves functional parity and all cross-generation dependencies have been severed.

- **EcountCore decomposition:** Execute the bounded-context decomposition (CardService, MemberService, ACHService, FeeService, NotificationService). Extract stored-procedure business logic into service-layer code. Migrate card_number_cert encryption to HSM-backed tokenisation. Establish a Gen-3 analytics pipeline from NexPay PostgreSQL to replace the ecountcore hub in DS_DB_prepaid_warehouse.
- **Windows dependency elimination:** Complete replacement of all Windows-native batch infrastructure (NDM, VBScript operations scripts, BCP.exe) with cloud-native equivalents (Azure Data Factory for ETL, Gen-3 admin API for PII operations, Azure Blob SFTP for file exchange).
- **Gen-1 portal retirement:** Complete clientzone_WAPP and csa_WAPP replacement with React SPA + Spring Boot 3.x BFF following the contact-center-agent-api pattern. Complete oneplatform_WAPP retirement by expanding the `display_recipient_web = Y` flag to all affiliate programmes.
- **AWS estate decommission:** Retire the AWS ECS estate (nlutil-aws_INFRA_TF, terraform-ecs-service_INFRA_TF) once all Gen-2 ECS services have migrated to Azure AKS/ACA. Publish and execute the AWS-to-Azure migration timeline with named owners per service.

---

## 9. Enterprise Risk Register (Top 10)

| # | Risk | Probability | Impact | Domains | Mitigation |
|---|---|---|---|---|---|
| 1 | **Director compromise = estate-wide credential breach.** An attacker with internal network access can retrieve all production database passwords, API keys, and SMTP credentials from a single unauthenticated HTTP call to /dispatch.asp. All 90–110 dependent services' credentials are exposed simultaneously. | High — unauthenticated, accessible to any internal host | Critical — complete production credential exfiltration; card issuance, disbursement, and fraud operations all compromised | 1, 2, 3, 4, 6, 7, 8, 9, 12, 13 | Immediate: mTLS on /dispatch.asp. 90-day: Azure Key Vault replacement programme |
| 2 | **StrongBox database compromise = complete Gen-1/Gen-2 cardholder data decryption.** Co-location of RSA private keys and ciphertext in the same SQL Server database means a single database breach exposes all Gen-1/Gen-2 protected cardholder data — 15+ years of prepaid card account records. | Medium — SQL Server on-premises, insider threat risk elevated in M&A environment | Critical — PCI DSS Req 3.6.1 violation; all encrypted cardholder data exposed; regulatory and reputational consequence of maximum severity | 1, 2, 5, 9, 13 | 60 days: SQL Server Always Encrypted. 18 months: full Azure Key Vault HSM migration |
| 3 | **Single SQL Server datacenter for ecountcore.** The ecountcore database has no confirmed read replica and no documented disaster recovery runbook in any repository. A datacenter-level failure takes the system of record for all prepaid card accounts offline with no automated failover. | Low-medium — datacenter failure is rare; risk is in the absence of tested DR | Critical — all card issuance, all transaction authorisation, all reporting offline; Reg E and NACHA obligations breached immediately | 1, 2, 3, 4, 6, 8, 9, 10 | Document DR plan; confirm Availability Group / mirroring status; establish and test RTO/RPO targets |
| 4 | **Empty STIP repos = no Gen-3 card processing continuity.** stip-generated and stip-models contain no code. stand-in-processing-api also reads from the same Gen-1 databases it is meant to replace during outages, creating an availability paradox for a service targeting 99.999% uptime. | High — already materialised; repos are empty today | High — Visa/Mastercard network rule compliance for stand-in processing; cardholder fund access during primary system outage compromised | 9 | Assign STIP domain owner; define stip-models schema; fund SASI data-independence programme |
| 5 | **Dual orchestrator double-payment risk.** nexpay-order-orchestrator and nexpay-recipientorchestrator-svc implement identical claim-code processing sagas with no cross-service uniqueness enforcement. Both can be triggered for the same claim code through overlapping entry points with no prevention mechanism. | Medium — boundary undefined; both services in production today | High — double-payment to recipient; direct financial loss; Reg E error resolution obligation | 3, 11 | Formal boundary ADR; cross-orchestrator Redis lock; UNIQUE constraint on claim_code |
| 6 | **No OFAC pre-screening on any disbursement rail.** Confirmed across ACH (ach-withdrawal-initiator), international wire (ieft-cp2e, cross-border-transfer-service), check issuance, and FX (Cambridge). The Gen-3 screening service is architecturally correct but entirely unauthenticated and covers Gen-3 flows only. | High — confirmed in source analysis across all rails | Critical — OFAC sanctions violations; criminal referral risk; regulator-imposed programme suspension | 2, 3, 11, 13 | Emergency: authenticate recipient-screening-api. Programme: establish domain-level OFAC gateway for all rails |
| 7 | **nam.wirecard.sys Active Directory dependency in production.** Production deployment pipelines, production server DNS, and the Wirecard issuing platform infrastructure all depend on an Active Directory domain associated with an insolvent company. Domain governance clarity is unknown post-acquisition. | Medium — dependency confirmed; governance uncertainty high | High — unplanned domain decommission would break production deployments and Wirecard Gen-2 issuing platform simultaneously | 12, 13 | Inventory all nam.wirecard.sys dependencies; establish AD ownership; publish migration timeline |
| 8 | **VBScript deprecation cliff.** Microsoft has announced VBScript removal on a published timeline. VBScript is the operational mechanism for ACH file processing triggers, PII management (1099_ssn_update.vbs, dob_update.vbs), and card fulfilment operations. No replacement programme exists. | High — Microsoft's deprecation timeline is fixed and approaching | High — operational failure of batch payment processing and PII management on a fixed, non-negotiable date | 2, 12 | Map all VBScript scripts to Gen-3 equivalents; fund audited admin API with RBAC; prioritise 1099_ssn_update.vbs |
| 9 | **Chargeback processing inoperability = Reg E breach.** chargeback-engine_LIB depends on sun.jdbc.odbc.JdbcOdbcDriver removed in JDK 8 (2013). If running on JDK 7 (EOL 2015), no security patches. If not running, Reg E §205.11 10-business-day provisional credit window is being violated. | High — confirmed code analysis shows broken dependency | Critical — confirmed Reg E breach if chargeback processing is non-operational; regulatory action; cardholder harm | 1 | Assess operational status immediately; measure Reg E exposure period; replace JDBC-ODBC bridge |
| 10 | **DPAPI machine-bound ETL = analytical layer permanent loss risk.** DS_ETL_warehouse SSIS packages encrypted with EncryptSensitiveWithUserKey (nick.doan, P-NA-DB11). If that user account is deleted, disabled, or the server is rebuilt, all warehouse ETL credential access is permanently destroyed with no recovery path. | Medium — user account lifecycle events are common in M&A organisations | High — entire analytical layer offline; no client reporting, no regulatory reporting, no BI; reconstruction requires rebuilding all SSIS package credentials from scratch | 10 | Migrate to DontSaveSensitive + SSIS Catalog environment variables immediately |

---

## 10. Strategic Enterprise Architecture Recommendations (Top 10)

### Rec-1: Declare the Director Decommission a Board-Level Infrastructure Programme

**What:** Fund and staff a formal Director Replacement Programme with executive sponsorship, dedicated engineering capacity, and a 12-month completion target. The programme encompasses: (a) completing the Azure App Configuration migration for all 90–110 dependent services; (b) rotating all credentials through Azure Key Vault; (c) establishing Kubernetes service DNS as the replacement for Director-mediated endpoint discovery; (d) removing director-client_LIB from all consuming services' dependency trees.

**Architectural Rationale:** Director is the single most important constraint in the entire 363-repo estate. Every other migration initiative — containerisation, AKS adoption, Gen-3 expansion, AWS estate decommission — is blocked or severely limited while Director remains the credential and service registry. It is the architectural keystone; removing it changes the structural possibilities for every other initiative simultaneously.

**Domains:** All 15. **Timeline:** 12 months. **Dependencies:** Azure Key Vault tenant established with RBAC; Managed Identity assigned per service; mTLS interim hardening on Director completed first.

---

### Rec-2: Establish a Domain-Level OFAC Screening Gateway as an Enterprise Architecture Control

**What:** Design and implement a synchronous OFAC/sanctions screening microservice (or integrate with an approved vendor such as LexisNexis or Refinitiv) that serves as a mandatory gateway for all outbound disbursements regardless of rail — ACH, wire, FX, check, push-to-card. Define a canonical API contract: `POST /screen/beneficiary` returns CLEAR, HOLD, or BLOCK. All disbursement orchestrators must call this gateway before releasing funds. The gateway must: (a) be authenticated via mTLS or OAuth2 client credentials; (b) log all HOLD/BLOCK decisions to a Compliance notification queue; (c) implement OFAC tipping-off protection (generic error to recipient on BLOCK).

**Architectural Rationale:** The absence of OFAC screening across all disbursement rails is not a per-service deficiency — it is an enterprise-level capability gap confirmed in Domains 2, 3, and 13. The recipient-screening-api exists as the Gen-3 screening control but is unauthenticated and only covers Gen-3 NexPay flows. An enterprise gateway applied consistently before any outbound disbursement is the only architectural pattern that satisfies OFAC compliance at platform scale.

**Domains:** 2, 3, 11, 13. **Timeline:** Quarter 1–2. **Dependencies:** Legal and Compliance sponsorship; vendor selection; recipient-screening-api authentication fix as prerequisite.

---

### Rec-3: Commission the StrongBox Migration Programme as a Strategic Initiative with Executive Sponsorship

**What:** Charter a formal StrongBox Migration Programme with a phased approach: (a) SQL Server Always Encrypted on all key columns within 60 days (interim PCI DSS Req 3.6.1 remediation); (b) Azure Key Vault facade maintaining the XML-RPC interface for consumer transparency within 9 months; (c) direct Azure Key Vault integration for all consumers within 18 months, with StrongBox decommissioned. The programme must include all three StrongBox repos (strongbox-xmlrpc_SVC, strongbox-lib_LIB, strongbox-remote-client_LIB) and their consuming services.

**Architectural Rationale:** Co-located keys and ciphertext is the most severe PCI DSS compliance violation in the estate. It is also the highest-complexity migration — keys protect 15+ years of cardholder data, key export ceremonies require HSM involvement, and re-encryption must occur under zero-downtime constraints with live cardholder accounts. No compensating control can fully mitigate this gap for a Level 1 QSA assessment; the only path to compliance is architectural key separation.

**Domains:** 1, 2, 5, 9, 13. **Timeline:** 18 months. **Dependencies:** Azure Key Vault HSM tier provisioned; key export ceremony designed with cryptographic consultant; consuming service inventory complete.

---

### Rec-4: Adopt Microsoft Entra as the Unified Identity Standard and Retire Three Legacy IAM Systems

**What:** Extend the Gen-3 pattern established by nexpay-auth-svc (Microsoft Entra External ID) across the entire platform: (a) migrate operator identity from xsecurity_SVC (Acegi Security, MD5 hashes) to Entra OIDC; (b) migrate partner SSO from xsso_SVC (JKS keystores, no token expiry) to Entra-issued JWTs; (c) retire rsa-mfa_LIB in favour of Entra MFA; (d) migrate api-security_SVC's IP/certificate access control model to Azure API Management policy enforcement or OPA sidecar.

**Architectural Rationale:** Onbe currently operates five separate IAM systems simultaneously: Acegi Security (xsecurity_SVC), RSA Adaptive Authentication (rsa-mfa_LIB), JKS/RSA SSO (xsso_SVC), IP/certificate control (api-security_SVC), and Microsoft Entra (nexpay-auth-svc). Each has independent key management, independent credential stores, and independent audit logs. Consolidating to a single identity control plane eliminates the MD5 and TrustAllSSLSocketFactory P0 findings, provides a single audit trail for PCI DSS Req 10 compliance, and removes three separate EOL security frameworks from the estate.

**Domains:** 3, 4, 5, 11. **Timeline:** 18–24 months. **Dependencies:** Operator account migration requires user-facing communication; partner SSO requires coordinated key rotation with external partners.

---

### Rec-5: Replace scheduler_WAPP with a Cloud-Native Scheduler as the First Decommission Milestone

**What:** Decommission scheduler_WAPP — the distributed job dispatch mechanism for card lifecycle events and disbursement processing — and replace it with Azure Scheduler + Azure Service Bus FIFO queues with authenticated REST-based callback registration. Execution sequence: (1) catalogue all consumer callback registrations in the QRTZ2_* Quartz schema; (2) build REST-based replacement with RBAC authentication; (3) migrate consumers one by one; (4) retire the Quartz schema and the scheduler_WAPP deployment.

**Architectural Rationale:** scheduler_WAPP is the most immediately dangerous service in Domain 4 (unauthenticated Java deserialization RCE surface, credentials in VCS, Spring HTTP Invoker migration blocker) and simultaneously the clearest candidate for cloud-native replacement. Its decommission establishes a reusable migration template — catalogue, replace, migrate, retire — applicable to banker_API, order_SVC (xmlrpc path), and jobservice_SVC. Completing this first demonstrates programme capability and reduces the Spring HTTP Invoker blast radius.

**Domains:** 4, 6, 15. **Timeline:** 12–18 months. **Dependencies:** Consumer callback catalogue; Azure Scheduler Service provisioned; REST replacement built and tested before first consumer migration.

---

### Rec-6: Establish EcountCore Decomposition as a Multi-Year Platform Programme with Formal Governance

**What:** Commission a formal EcountCore decomposition architecture study that: defines bounded contexts (CardService, MemberService, ACHService, FeeService, NotificationService); maps all 300+ stored procedures to service domains; identifies the card_number_cert key migration path; and produces a phased migration roadmap aligned with Gen-3 platform objectives. Establish a programme governance board with Engineering, Database, Compliance, and Finance representation. No decomposition work begins without the architecture study complete.

**Architectural Rationale:** EcountCore is simultaneously the most critical database in Onbe's estate and the most difficult to change. Every analytical capability, every Gen-3 cross-generation dependency (SASI, STIR, recipient-screening-api), and every card-lifecycle operation is downstream of this database. Decomposition cannot be attempted without a formal architecture study because the blast radius of a misstep is total platform failure. The study itself is a 3–6 month investment that prevents years of compounding ad-hoc debt.

**Domains:** 1, 2, 3, 4, 6, 8, 9, 10. **Timeline:** Study: 3–6 months. Decomposition execution: 3–5 years. **Dependencies:** Stored procedure business logic inventory; card_number_cert key management documentation; zero-downtime migration strategy for live cardholder accounts.

---

### Rec-7: Publish and Execute the AWS-to-Azure Migration Timeline with Named Owners per Service

**What:** Define a formal AWS-to-Azure migration timeline that identifies: (a) every Gen-2 ECS service currently running in the AWS estate (nlutil-aws_INFRA_TF); (b) its Azure target (AKS/ACA); (c) a named engineering owner; (d) a cutover date. Separate the AWS account into non-production and production accounts using AWS Organizations before migration completes. Decommission the AWS ECS estate on a published date with no extensions without CISO and CTO approval.

**Architectural Rationale:** Operating two cloud estates (AWS ECS for Gen-2, Azure ACA/AKS for Gen-3) indefinitely doubles operational overhead, security surface, cost, and compliance scope. Without a published timeline, the dual-cloud model will persist indefinitely. The dual-cloud model also complicates PCI DSS network segmentation documentation because the CDE spans two cloud providers with different control frameworks and different audit evidence requirements.

**Domains:** 2, 12, 13. **Timeline:** Timeline published within 60 days; execution 12–24 months. **Dependencies:** Gen-3 Azure capacity planning; per-service Azure target architecture defined; Director replacement complete (services cannot migrate to Azure while dependent on Director's Windows Registry path).

---

### Rec-8: Enforce an Enterprise-Wide Secrets Governance Standard with Immediate Git History Remediation

**What:** (a) Treat all identified committed credentials as compromised and rotate immediately. (b) Execute git filter-repo history rewrites across all identified repositories (6 in Domain 1, plus Domains 5, 12, 13, 14). (c) Establish Trufflehog or equivalent pre-commit hooks and CI scans across all repositories as a merge gate. (d) Prohibit SNAPSHOT artifact consumption in production build pipelines via Maven Enforcer rule. (e) Require all new secrets to use Azure Key Vault with Managed Identity or equivalent.

**Architectural Rationale:** Git as a secrets store is the root cause of the majority of credential-related compliance gaps across the estate. The scope of committed credentials — database passwords, API keys, SFTP private keys, PGP private keys, AWS IAM keys, SMTP credentials — means that any repository read access equates to a potential credential exfiltration event. The remediation is operational but must be treated as an active compliance incident with a 90-day completion deadline, not a backlog item.

**Domains:** All 15. **Timeline:** Rotation and rewrite: 30 days. CI enforcement: 60 days. Full vault migration: 90 days. **Dependencies:** Azure Key Vault provisioned; Managed Identity assigned per service or team; git filter-repo tooling approved by InfoSec.

---

### Rec-9: Resolve the Dual Orchestrator Boundary and Complete Saga Compensation Before Scaling Gen-3 Traffic

**What:** (a) Formally declare in an Architectural Decision Record (ADR) which orchestrator owns which disbursement trigger (payee-initiated web vs. system-initiated order). (b) Implement cross-orchestrator uniqueness enforcement (Redis key `claim:lock:{claimCode}` acquired before saga initiation, scoped across both orchestrators). (c) Implement complete saga compensation logic — card reversal, ACL rollback, outbox notification for DECLINED screening — in both orchestrators before routing production traffic at scale. (d) Establish a decommission timeline for the service-bus module in nexpay-order-orchestrator.

**Architectural Rationale:** The dual orchestrator overlap is a structural double-payment risk with no current compensating control. Both orchestrators are individually architecturally sound — the saga pattern, PostgreSQL state persistence, and outbox mechanism are all correct. The undefined boundary between them means the same claim code can initiate two sagas simultaneously in two separate services with no cross-service deduplication. This is a design governance gap that must be resolved before Gen-3 achieves meaningful production traffic volumes, as double-payment incidents at scale create both direct financial loss and Reg E error resolution obligations.

**Domains:** 3, 11. **Timeline:** ADR and Redis lock: this sprint. Full compensation implementation: this quarter. **Dependencies:** None — these are Gen-3 internal changes with no legacy dependencies.

---

### Rec-10: Establish a Formal Gen-1 Sunset Roadmap with Binding Retirement Dates

**What:** Convene an executive-sponsored Architecture Review Board to publish a Gen-1 Sunset Roadmap that: (a) assigns each Gen-1 repository a named owner and a retirement date, or declares it a designated long-lived legacy service with an explicit SLA and interim security controls; (b) specifies the Gen-3 replacement service for each Gen-1 service being retired; (c) establishes interim security controls (WAF, network ACLs, dependency patches via vendored forks) for Gen-1 services that cannot be decommissioned within 18 months; (d) defines migration prerequisites (Director replacement, XML-RPC bridge, StrongBox migration) as sequenced gates rather than parallel workstreams.

**Architectural Rationale:** Without a binding sunset roadmap, the dual-generation and triple-generation operating model will persist indefinitely. The estate currently has five simultaneous migration programmes (Director replacement, StrongBox migration, XML-RPC protocol bridge, clientzone rewrite, EcountCore decomposition) that share dependencies but have no formal sequencing. The roadmap does not create new work — it sequences existing work into a coherent execution plan that prevents the cross-programme blockers from compounding further. Every year that Gen-1 remains in production without a roadmap, the migration cost grows as Gen-3 services accumulate additional cross-generation dependencies on Gen-1 infrastructure.

**Domains:** All 15. **Timeline:** Roadmap published within 90 days. Roadmap execution: 2–5 years depending on programme investment level. **Dependencies:** Executive sponsorship; dedicated programme management office; engineering capacity allocation separate from feature development velocity commitments.

---

*This document synthesises findings from 363 repositories across 15 business domains analysed during the Phase 3 Enterprise Architecture review completed 2026-05-08. All findings are grounded in source code analysis of the OnbeEast estate. Specific repository and file references are detailed in the corresponding domain synthesis files at E:\OnbeEast363\analysis\domain-synthesis\.*
