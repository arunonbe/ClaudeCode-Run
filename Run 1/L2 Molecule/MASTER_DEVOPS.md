# MASTER DEVOPS & OPERATIONS VIEW — Onbe 363-Repo Estate
*(Generated: 2026-05-08 | Source: 363 repositories across 15 business domains)*

---

## 1. Executive Summary

The Onbe 363-repo estate is a three-generation platform in simultaneous production operation, and the DevOps/operations posture reflects every year of that accumulated history. The clearest single statement that can be made about the estate's CI/CD maturity is this: **tests are skipped in CI pipelines across all 15 domains, in every generation of service, without exception as the dominant pattern**. This is not an isolated lapse — it is an estate-wide operational decision whose practical consequence is that production deployments at a PCI DSS Level 1 payment processor proceed with zero automated regression coverage across the overwhelming majority of repos.

Beyond the test-skip norm, the estate presents three additional systemic risks that cut across every domain:

**Committed secrets at scale.** Plaintext credentials, private keys, PGP passphrases, Android release keystores, AWS access keys, and Visa payment credentials are committed directly to Git repositories across Domains 1, 2, 4, 7, 9, 12, and 13. The scale of exposure is not a few stray development credentials — it includes production Visa keys in `dapr-secrets.json` (Domain 04), a CIMB Bank SFTP RSA private key in `application.yml` (Domain 13), a full Mailgun API key in `application.properties` (Domain 07), four database passwords in `.env` files (Domain 04 `scheduler_WAPP`), and an Azure App Configuration connection key committed to `stand-in-processing-api` (Domain 09). All must be treated as compromised until rotated.

**Three-generation deployment topology without a retirement timeline.** Gen-1 Windows batch/Tomcat on-premises, Gen-2 AWS ECS containerised, and Gen-3 Azure AKS/Azure Container Apps operate simultaneously with no documented cutover schedule. This forces the operations team to maintain three incompatible toolchains, three observability stacks, and three secrets-management models. The Wirecard-era AWS account and `nam.wirecard.sys` DNS namespace remain in active production use, and no decommission plan is visible in any repository.

**JDWP and debug-mode exposure in production.** `recipient-screening-api` (Domain 03) exposes port 50505 (probable JDWP) in its production Dockerfile. `cross-border-transfer-service_SVC` (Domain 02) exposes JVM debug port 8000 in docker-compose. `issuing-classic-selfservice_WAPP` (Domain 03) hard-codes `DEBUG = True` in Django `settings.py` with a manual-deletion comment that is trivially overlooked. Any of these exposures in a network-reachable environment is a remote code execution vector in a PCI DSS Cardholder Data Environment.

**Observability is largely absent across the Gen-1/Gen-2 estate.** The Gen-3 NexPay platform has OpenTelemetry traces shipping to Dynatrace, Micrometer metrics, and structured JSON logging. The other 200+ repos have Log4j 1.x file appenders, no distributed tracing, no health probes, and no metrics endpoints. The centralised log-archive pipeline (Logstash-ship ECS service) is currently scaled to zero — meaning the primary PCI DSS Req 10 log archive is not receiving data.

The CI/CD maturity across the estate ranges from Level 1 (no pipeline, manual deployment) in Domain 10's entire database layer to Level 3–4 in Domain 09's Gen-3 services. No domain achieves Level 5 maturity (full automated gates, container scanning, secrets scanning, signed artifacts, IaC-managed production). The single most dangerous operational pattern is the test-skip CI norm: when a PCI DSS Level 1 processor's deployment gate executes no tests, every code change and every automated Dependabot dependency bump ships to production as an untested artifact.

---

## 2. CI/CD Maturity Assessment by Domain

Maturity levels: **1** = No pipeline / fully manual; **2** = Build-only, no tests; **3** = Build + some security scanning, tests skipped; **4** = Build + tests + SAST/SCA; **5** = Full pipeline with container scan, secrets scan, coverage gate, staging gate, IaC.

| Domain | Pipeline System | Test Execution | SAST/SCA | Secrets Scanning | Container Scanning | Maturity |
|--------|----------------|---------------|----------|------------------|--------------------|---------|
| D01 Card Program Mgmt | GitLab CI + GitHub Actions (dual) | **Skipped** (all 22 repos; `-Dmaven.test.skip=true`) | CodeQL (Gen-3 only) | None | Trivy (Gen-3; 15 CVEs suppressed) | **2** |
| D02 Disbursements & Rails | Jenkins + GitLab CI + GitHub Actions + **None** (3 repos) | **Skipped** all 17 repos | OWASP Dep-Check (some) | None | None | **1–2** |
| D03 Recipient/Cardholder | GitHub Actions (Gen-3) + Jenkins + GitLab (Gen-2) + **None** (4 repos) | **Skipped** (Gen-2/Gen-1); Tests present (Gen-3) | CodeQL (Gen-3) | None | **CONTAINER_SCAN: false** (all Gen-3) | **2–3** |
| D04 Client Admin Portal | GitHub Actions + GitLab CI (12 dual-pipeline repos) | **Skipped** (scheduler, banker, clientzone, csa, contact-center-agent); `testFailureIgnore=true` (csa) | CodeQL | None | None | **2** |
| D05 Auth & Identity | GitHub Actions + GitLab CI + **None** (Gen-1 libs) | **Skipped** (api-security, strongbox, xsecurity, xsso); Tests present (nexpay-auth, recipient-screening) | CodeQL (Gen-3) | None | Suppressed CVEs (xsso, api-security) | **2** |
| D06 Order/Workflow | GitHub Actions + Jenkinsfile (dual, mismatched Java 8/21) + GitLab CI + **None** | **Skipped** all 18 repos | None observed | None | None | **1–2** |
| D07 Content/Notification | GitHub Actions (Gen-3) + **None** (batch, templates) | **Skipped** all pipelines that exist | None | None | **CONTAINER_SCAN: false** (om-content-management-api) | **2** |
| D08 Search/Platform Core | GitHub Actions + **None** (xplatform_LIB, xfire-utils_LIB) | **Skipped** all repos; floating `@main` shared workflow | None | None | None | **1–2** |
| D09 STIP/Card Processing | GitHub Actions (Gen-3) + GitLab CI (dual on crypto-svc) | Skipped (crypto-svc, stand-in-recovery); Tests run (stand-in-processing-api, nexpay-cardprocessor) | CodeQL (some) | None | **CONTAINER_SCAN: false** (nexpay-cardprocessor); Trivy (stand-in services) | **3** |
| D10 Data/Analytics | **None across all ~80 DS_ repos** | **No pipeline exists** | None | None | None | **1** |
| D11 NexPay Greenfield | GitHub Actions (nexpay-iac shared workflow) | Tests present (nexpay-parent); skipped elsewhere | CodeQL (Dependabot PRs) | None | **CONTAINER_SCAN: false** (all 11 Container Apps) | **3** |
| D12 Infra/DevOps | GitHub Actions (Gen-3) + GitLab CI (Gen-2) | Unit tests commented out in CI template | CodeQL (api-config-repo) | **None** — root cause of estate-wide secret commits | None | **2** |
| D13 Cobrand/Wirecard | GitHub Actions + Jenkins + Ansible + **None** (ERP repos) | **Skipped** (CBTS, cbts-client); Run 90% JaCoCo (Wirecard Gen-2 Jenkins) | CodeQL weekly (CBTS) | None | None | **2** |
| D14 Testing/QA Automation | GitHub Actions (Gen-3 suites); GitLab CI (SAST only, Gen-1 suites) | **Gen-1 SOAP suites: never CI-executed**; Gen-3: Playwright/Newman in CI | CodeQL + Pynt DAST (qa-api) | None | Container scan enabled (qa-test-automation only) | **2–3** |
| D15 Dev Tooling/Libraries | GitHub Actions (most repos) | **Skipped** in publish pipelines (api-logging-lib, webapp-parent-pom) | CodeQL (all repos with GHA) | None | None | **2** |

**Key estate-wide patterns:**
- **Mutable branch CI references** (`@main`, `@feature/CRUS-0000-skip`, `@feature/IN-9108-inverse-aks`): Domains 06, 07, 08, 11, 14, 15. A force-push or deletion of any referenced branch silently breaks all downstream pipelines simultaneously.
- **`secrets: inherit` propagation**: Repos delegating to `om-ci-setup` shared workflow propagate full secrets scope to every pipeline execution, violating least-privilege for CI secrets.
- **SNAPSHOT in production**: Present in Domains 01–09, 11, 13, 15. Makes rollback and CVE attribution impossible.
- **Zero pipeline domains**: Domain 10 (all database repos), and individual repos in Domains 02, 03, 06, 07, 13.

---

## 3. Deployment Topology Map

The estate operates three irreconcilable deployment generations simultaneously. No retirement timeline for Gen-1 or Gen-2 is documented in any repository.

### Generation 1 — Windows On-Premises (Active)

Physical and virtual Windows Server hosts running IIS (atlys_WAPP with Silverlight 4.0), Tomcat 8.5 (clientzone_WAPP, csa_WAPP — EOL March 2024), Tomcat 10.x (director-svc_SVC legacy WAR path), and JBoss (rebate-inquiry_WAPP, spring-refer-a-friend_WAPP). Batch processes invoked by Windows Task Scheduler, Control-M, or Active Batch scheduler. Configuration via `D:\c-base\config\` filesystem paths hardcoded in source code across 50+ repos in Domains 01, 02, 03, 04, 05, 06, 07, 08.

Production server hostnames confirmed in source (all on `nam.wirecard.sys` DNS): `d-na-app01`, `d-na-app02`, `q-na-app01/02`, `p-az-app01`, `d-app02.nam.wirecard.sys`, `d-phl-db01.wirecard.lan`, `PPAMWDCUDSQL1C1` (SSIS execution server), `p-db06\db06`, `p-db07\db07` (production SQL Server instances). The `nam.wirecard.sys` DNS zone is the Wirecard-era corporate namespace: Onbe's production payments infrastructure is still partly managed under a bankrupt company's DNS zone.

**Exposed ports of concern (Gen-1):**
- JMX RMI unauthenticated on `api-security_SVC` (domain 05, `DistributedCacheManager`, null JMX environment map)
- Tomcat Manager default paths not confirmed removed across Windows Tomcat fleet
- H2 in-memory console enabled by default in multiple Gen-2 application configs (Domains 04, 13)

### Generation 2 — AWS ECS Fargate (Active, Wirecard-era Account)

AWS infrastructure managed by Terraform repos in Domain 12: `nlroot-aws_INFRA_TF` (Route 53, 29 hosted zones, state S3 bucket `wc-root-state`), `nlutil-aws_INFRA_TF` (VPC `10.10.0.0/16`, ECS cluster, ALB/NLB, ECR, IAM, SQS). Spring Cloud Config Server runs on ECS but its source repository contains only a README — the actual running image's provenance is unknown.

The `logstash-ship` ECS service is confirmed scaled to zero in `nlutil-aws_INFRA_TF` (`ecs_count = "0"`). Logs from all ECS services accumulate in SQS but are not shipped to S3 or ChaosSearch. The PCI DSS Req 10 log archive pipeline is currently non-functional.

CloudWatch log retention: all services deployed via `terraform-ecs-service_INFRA_TF` get `retention_in_days = 14`. PCI DSS Req 10.7 requires 12 months retention with 3 months immediately available.

Single NAT Gateway (`single_nat_gateway = true`) is a single point of failure for all private-subnet egress in the AWS VPC.

The AWS account holding this infrastructure is the Wirecard-era account (`wc-root-state` S3 bucket naming, Wirecard-prefixed IAM paths). No formal account separation between QA and Production is documented, and no retirement timeline for this account is visible.

### Generation 3 — Azure Container Apps / AKS (Active, NexPay)

NexPay greenfield (Domain 11): Azure Container Apps Environment `cae-nexpay-qa` with 11 Container Apps (config-svc, order-orchestrator, ordervalidator, auth, profile, recipientweb-bff, claim-code, card-proc, ivr-bff, clientadminweb-bff, config-test). Azure PostgreSQL Flexible Server (PostgreSQL 18, pre-GA at analysis time). VNet `10.60.0.0/20` with peering to legacy eCount spoke (`vnet-az1-qa-ecount-spoke-001` at `10.x.x.x`).

**Critical gap: no production IaC.** `nexpay-iac` contains `qa.tfvars` but no `prod.tfvars` or production Terraform workspace definition. Production NexPay infrastructure is provisioned outside IaC governance.

Azure App Configuration (`appcg-nexpay-qa`) has `app_config_public_network_access = "Enabled"` — the config store holding all NexPay runtime configuration including Key Vault references is publicly internet-reachable. Key Vault `kv-nexpay-qa` has purge protection disabled.

Gen-3 health endpoints: all services expose `/actuator/health` (NexPay) or `/hc` (OM platform). Domain 04 Gen-3 services expose `show-details: always` unauthenticated — database connectivity state visible to any caller.

---

## 4. Secrets Management: Estate-Wide Inventory

This section represents the most critical DevOps finding across the estate. The absence of secrets scanning in any CI pipeline (Domain 12, Finding P0-1) is the systemic root cause. The following table captures all confirmed committed secrets grounded in domain synthesis findings.

| Domain | Repo | Secret Type | Location | Impact | Priority |
|--------|------|-------------|----------|--------|----------|
| D01 | chargeback-engine_LIB | ODS DB credentials (CBASEAPP/ECOUNT) | `ChargebackProcess.properties` lines 13–14; `settings.xml` lines 37–50 | Direct DB access to ODS | P0 |
| D01 | auto-card-batch_LIB | Nexus passwords (dwil15?, d3v0nly, acmng) | `settings.xml` lines 37–54 | Nexus artifact poisoning | P0 |
| D01 | accept-prechecks_API | Azure App Config secret + DB passwords | `.env_bkp` lines 4, 14–19 | Azure config + DB access | P0 |
| D02 | cross-border-transfer-service_SVC | Spring Cloud Config Server password | `bootstrap.yml` (literal `s3cr3t`) | All config-server secrets compromised | P0 |
| D04 | scheduler_WAPP | 4 SQL Server DB passwords (`b2cstage`) | `scheduler-service/.env` lines 7–14; `.env-dev` lines 8–15 | Direct access to 4 production-adjacent DBs | P0 |
| D04 | manage-payment-rest-api | Live Visa payment credentials | `dapr-components/dapr-secrets.json` | Payment rail compromise | P0 |
| D07 | mailgun-event-tracker | Mailgun API key (`[REDACTED — rotate immediately]`) | `application.properties` line 18 | Send email as Onbe; read all events | P0 |
| D07 | mailgun-event-tracker | DB credentials (`b2ctest`/`b2ctest`) | `application.properties` lines 5–6 | NotificationSvc DB access | P0 |
| D09 | stand-in-processing-api | Azure App Configuration full connection key | `.env` file | All SASI runtime config compromised | P0 |
| D12 | docker-logstash_INFRA_CONT | Logstash TLS server private key | `pki/server.key` (committed + baked into Docker image) | Decrypt all mTLS Filebeat sessions; MITM log pipeline | P0 |
| D13 | wirecard_sg-bank-agent_LIB | CIMB Bank SFTP RSA private key | `application.yml` lines 34–61 | Unauthorized SFTP access to CIMB Bank SG | P0 |
| D13 | wirecard_sg-bank-agent_LIB | PGP passphrase (`wirecard`) | `application.yml` line 154 | Decrypt/sign PGP-protected payment files | P0 |
| D13 | wirecard_sg-bank-agent_LIB | AWS access key + secret (`[REDACTED — rotate immediately]`) | `gradle.properties` lines 31–32 | Full AWS API access under this key | P0 |
| D13 | cross-border-transfer-service_SVC | PGP private key (0x6392B27D-sec.asc) | `pgp/` directory in repo | Decrypt all PGP-protected transfer files | P0 |
| D13 | cross-border-transfer-service_SVC | DB password, Cambridge API signatures, SMTP key | `application-qa.yml` lines 26–385 | Cambridge API + SMTP access | P0 |
| D13 | cross-border-transfer-service_SVC | JKS keystore | `config/server.jks` | TLS private key exposure | P1 |
| D13 | wirecard_mobile-payout-citi_LIB | Android release keystore | `android/app/keystore/payoutnam_release.keystore` | Sign malicious APKs as Onbe "PayoutNAM" | P0 |
| D13 | wirecard_test-utilities_LIB | PGP private key (0x6392B27D-sec.asc) | `src/main/resources/pgp/` (in published JAR) | Key distributed to all Maven consumers | P0 |
| D13 | wirecard_funds-transfer-coordinator_LIB | CCP password (`aaaa1111`) | `application.yml` line 143 | CCP payment system access | P1 |
| D13 | wirecard_check-agent_LIB | CCP password (`aaaa1111`) | `application.yml` | CCP payment system access | P1 |
| D05 | actimize-kyc_LIB | Hardcoded `secure_code='Prepaid1'` | Three SQL files | KYC/CIP authentication bypass | P1 |
| D05 | strongbox-remote-client_LIB | Plaintext HTTP transport for RSA/AES/PGP key delivery | `service.default.properties` (`http://ecappdev:8080/...`) | In-transit key interception | P1 |
| D05 | xsso_SVC | Keystore passwords in properties files | repo properties files | SSO keystore compromise | P1 |
| D09 | crypto-service_SVC | JRE keystore default password (`changeit`) | `Dockerfile` line 20 | Keystore compromise | P2 |
| D07 | message-center_SVC | Default JVM keystore password (`changeit`) | `Dockerfile` (production) | Keystore compromise | P2 |
| D07 | xcontent_SVC | Default keystore password (`changeit`) | `Dockerfile` | Keystore compromise | P2 |
| D10 | DS_ETL_warehouse | All ETL credentials DPAPI-encrypted to NAM\nick.doan Windows account | SSIS packages (EncryptSensitiveWithUserKey) | Single person/machine controls all warehouse ETL credentials | P0 |
| D06 | batch_LIB | Office 365 EWS `clientSecret` in plaintext properties file | `ReturnedEmailBatch.properties` | O365 email account access | P1 |
| D15 | EstimationChatApp-_MISC | `.env` file committed | repo root | Team code exposure (low sensitivity) | P2 |

**Estate-wide systemic cause:** No secrets scanning pre-commit hook, no GitHub Secret Scanning push protection, and no Trufflehog/GitLeaks in any CI pipeline across all 363 repos. Domain 12 identified this as its top finding. Until secrets scanning is enforced at push time, new credentials will continue to be committed.

---

## 5. Top 20 DevOps/Operational Findings (P0/P1)

| Rank | Domain(s) | Finding | Operational Risk | PCI DSS Reference | Priority |
|------|-----------|---------|-----------------|-------------------|----------|
| 1 | D04, D07, D09, D12, D13 | Production Visa keys, CIMB SFTP RSA private key, Android release keystore, Logstash TLS private key, and 15+ additional secrets committed to Git repositories in active use | Payment rail compromise; unauthorized SFTP; fraudulent APK signing; log pipeline MITM | Req 3.5, Req 8.3 | **P0** |
| 2 | All 15 domains | Tests universally skipped in CI/CD pipelines (`-Dmaven.test.skip=true`, `-DskipTests`) — the single most pervasive operational quality risk across the estate | Undetected regressions ship to production on every deployment; payment logic defects reach cardholders | Req 6.2.4, Req 6.4 | **P0** |
| 3 | D02, D03 | JVM debug port 8000 exposed in `cross-border-transfer-service_SVC` docker-compose; port 50505 (probable JDWP) exposed in `recipient-screening-api` production Dockerfile | Remote code execution via JDWP attach on a network-reachable container | Req 6.3, Req 2.2 | **P0** |
| 4 | D03 | `DEBUG = True` hard-coded in `issuing-classic-selfservice_WAPP settings.py` line 27; Django debug-toolbar as first middleware | SQL queries, stack traces, session tokens, DB credentials exposed via Django error pages in production | Req 6.3, Req 2.2 | **P0** |
| 5 | D05 | `xsecurity_SVC` (operator credential authority) deployed with `EXCLUDE_STAGE: true` — every change goes directly to production with no staging gate | Zero integration test window for the service managing all operator credentials | Req 6.4 | **P0** |
| 6 | D05 | `strongbox-xmlrpc_SVC CryptoService.java:173` logs `input.getText()` (PGP plaintext) at INFO level — ongoing cardholder data leakage into log aggregators | PAN/cardholder data in logs shipped to Splunk/Azure Monitor with broad read access | Req 3.3, Req 10.5 | **P0** |
| 7 | D10 | All DS_ETL_warehouse SSIS packages encrypted with `EncryptSensitiveWithUserKey` bound to NAM\nick.doan's Windows account on P-NA-DB11; `.dtsConfig` production configuration not version-controlled | Single person/machine SPOF for 100+ ETL packages; total DR failure on account deactivation | Req 12.3 (BCP), FFIEC IT | **P0** |
| 8 | D12 | `logstash-ship` ECS service scaled to zero (`ecs_count = "0"`) — logs accumulate in SQS but are NOT shipped to S3 or ChaosSearch | PCI DSS Req 10 log archive is currently inactive; audit trail non-functional | Req 10.3, Req 10.7 | **P0** |
| 9 | D11 | No `prod.tfvars` or production Terraform workspace exists in `nexpay-iac` — NexPay Gen-3 production infrastructure is not managed by IaC | Unauditable production infrastructure changes; untested DR; PCI DSS change-management gap | Req 10, Req 6.4 | **P0** |
| 10 | D02 | Spring Cloud Config Server bootstrap password is literal `s3cr3t` in `cross-border-transfer-service_SVC bootstrap.yml` — all secrets delivered via this server must be treated as compromised | Config server credential compromise; all downstream service secrets at risk | Req 8.3, Req 3.5 | **P0** |
| 11 | D11, D03, D09 | `CONTAINER_SCAN: false` set in deployment workflows across all 11 NexPay Gen-3 Container Apps and across Gen-3 services in Domains 03 and 09 | OS-layer CVEs in container base images not detected before production promotion | Req 6.3.3 | **P1** |
| 12 | D12 | CloudWatch log retention hardcoded at 14 days in `terraform-ecs-service_INFRA_TF` for all ECS services | PCI DSS requires 12-month retention (3 months immediately available); 14 days satisfies neither | Req 10.7 | **P1** |
| 13 | D01 | `chargeback-engine_LIB` targets Java 6 / JDBC-ODBC bridge (`sun.jdbc.odbc.JdbcOdbcDriver` removed in JDK 8); requires JDK 7 or earlier (EOL April 2015) to execute | Service cannot run on any supported JVM; if in production, represents a critical unpatched runtime | Req 6.3.3, Req 12.3.4 | **P0** |
| 14 | D04, D12 | No secrets scanning (Trufflehog, GitLeaks, GitHub Secret Scanning) in any CI pipeline across all CONFIG repos, `api-config-repo`, or any other pipeline in the estate | Root-cause of estate-wide credential-in-Git posture; new secrets continue to be committed undetected | Req 8.3, Req 3.5 | **P0** |
| 15 | D04, D05, D06 | Director service (`director-svc_SVC`) is a pre-startup hard dependency for all Gen-1 and Gen-2 services with no circuit breaker, no cached fallback, and 1,000 max concurrent TCP connections with 60-second timeouts | Director outage cascades to simultaneous failure of all Gen-1/Gen-2 services estate-wide; thread pool exhaustion | Req 12.3 (availability) | **P1** |
| 16 | D12 | No CI/CD pipeline for any Terraform repository — all `terraform apply` operations are manual with no plan review, approval gate, or independent audit trail | Infrastructure changes to AWS CDE-adjacent resources cannot be change-controlled per PCI DSS Req 6.4 | Req 6.4, Req 6.5 | **P1** |
| 17 | D06 | `notification-framework_SVC` deployment workflows pinned to mutable `feature/CRUS-0000-skip` branch in `om-ci-setup` — branch deletion or force-push silently breaks all four notification delivery pipelines simultaneously | All regulatory notification delivery (Reg E disclosures) halted with no alerting | Req 10.7 (log failures), Reg E | **P1** |
| 18 | D13 | `wirecard_mobile-payout-citi_LIB` certificate pins for production (`webservice.wirecard.com`) and QA targets expired December 2021 and July 2021 respectively | All app API communications broken or breaking at next certificate rotation; no automated expiry monitoring | Req 4.2, Req 12.3 | **P1** |
| 19 | D04 | `manage-payment-rest-api` and `om-payment-api` Dockerfiles have no `USER` instruction — JVM runs as Linux root; `daprio/daprd:latest` Dapr sidecar on `om-payment-api` is unpinned | Container escape grants attacker root on node; unpinned sidecar changes security surface without decision | Req 7, Req 2.2 | **P1** |
| 20 | D08 | `xsearch-xmlrpc_SVC` combines `EXCLUDE_STAGE: true` + `-Dmaven.test.skip` + `UPDATE_DEPENDENCIES: true` — every automated Dependabot PR on the cardholder PAN search service is promoted to production without regression testing or staging validation | Dependabot-generated dependency change could break PAN search contract, reaching production with no detection | Req 6.3.2, Req 6.3.3 | **P1** |

---

## 6. EOL Runtime & Dependency Inventory

The estate carries an exceptional volume of end-of-life frameworks. These cannot be patched in place — migration is required. Their presence directly violates PCI DSS Req 6.3.3 (all software components protected from known vulnerabilities).

| Technology | Version(s) | EOL Date | Key CVE(s) | Repos / Domains Affected | Risk Level |
|------------|-----------|----------|-----------|-------------------------|------------|
| Java (JDK) | 1.5 / 1.6 | Feb 2013 | JVM-level unpatched vulnerabilities | D08 `ecore-batch_LIB` (Java 5); D01 `chargeback-engine_LIB`, D05 `actimize-kyc_LIB`, D05 `aml-name-screening_LIB`, D14 4 SOAP test repos (Java 7); D15 `webapp-parent-pom_PARENT` (Java 6 source/target) | Critical |
| Apache Struts | 1.3.8 | 2013 | S2-045, S2-052 (RCE) | D15 `webapp-parent-pom_PARENT` + all inheriting web apps (D04 `csa_WAPP` Struts 1.x runtime) | Critical |
| Log4j | 1.2.14–1.2.17 | 2015 | CVE-2019-17571 (RCE via SocketServer) | D01 (auto-card-batch, pos-connector, card-notification); D02 (check-issuance, ach-withdrawal-initiator); D04 (clientzone, csa via Tomcat); D06 (batch_LIB, notification-requests-generator); D08 (ecore-batch); D15 `onbe-log4j1-utils` | Critical |
| Spring Framework / Boot | 2.x (Spring 2.0.x–2.5.x) | ~2007 | Multiple deserialization / SSRF CVEs | D08 `xfire-utils_LIB`, `xsearch-new_SVC`; D13 `cambridge-service_LIB`, `cambridge-auth-service_LIB`; D02 (multiple Gen-1 batch) | Critical |
| Spring Boot | 1.5.x / 2.0.x | Aug 2019 / Oct 2019 | Actuator RCE misuse | D13 `wirecard_sg-bank-agent_LIB` (1.5.13), `wirecard_funds-transfer-coordinator_LIB` (2.0.7) | Critical |
| Apache Axis | 1.4 / Axis2 1.7.5 | ~2006 / 2018 | CVE-2019-0227 (SSRF via malicious WSDL) | D02 `cambridge-auth-service_LIB` (Axis 1.4), `cambridge-service_LIB` (Axis2 1.7.5); D15 `api-logging-lib` | High |
| Commons HttpClient | 3.x | 2011 | CVE-2012-5783 (SSL bypass) | D08 `xml-rpc_LIB`, `xml-rpc-clients_LIB` + all Gen-1/Gen-2 consumers | High |
| XStream | 1.3.x / suppressed CVEs | Ongoing CVEs | CVE-2021-39144, CVE-2024-47072 (RCE) | D01 `clientapi_API` (suppressed); D05 `api-security_SVC` (suppressed); D15 `request-file_LIB` | High |
| Quartz Scheduler | 1.6.x | EOL | CVE-2019-13990 (XML injection via job store) | D13 `wirecard_funds-transfer-coordinator_LIB` Oracle JDBC + Quartz 1.6 | High |
| sqljdbc | 1.1 | 2005 | TLS 1.0 only; no TLS 1.2/1.3 support | D08 `ecore-batch_LIB` | Critical (PCI DSS Req 4.2.1 — early TLS prohibited) |
| SSIS / SQL Server | 2012 (11.x toolchain) | July 2022 | No security patches since EOL | D10 all `DS_ETL_warehouse` packages | High |
| Oracle Client | 12c | 2022 | Oracle support ended | D10 `DS_CCP_ccp-export` (blocks server OS upgrades) | High |
| Silverlight | 4.0 | 2021 (browser support lost ~2016) | No patches; SQL injection in `atlys_WAPP wsAtlys.svc.cs:847` | D04 `atlys_WAPP` | Critical (functionally inaccessible; active attack surface on IIS) |
| Tomcat | 8.5 | March 2024 | CVE-2024-52316 (auth bypass), CVE-2024-50379 (RCE race) | D04 `clientzone_WAPP`, `csa_WAPP`; CVEs suppressed in D05 `xsso_SVC`, D09 `crypto-service_SVC` | Critical |
| Node.js | 15 | June 2021 | JVM-level unpatched vulnerabilities | D15 `EstimationChatApp-_MISC` | Medium |
| Filebeat / Logstash | 7.9.2 / 7.9.3 | End of Elastic 7.x support (~2024) | 5 years of unpatched security issues | D12 logging pipeline (all Gen-1/Gen-2 hosts) | High |
| OpenAI Python SDK | 0.27.7 (v0 API) | Deprecated; replaced by v1.x | API may stop functioning | D15 `InternalOnbeAI` | Medium |
| SwarmCache / JGroups multicast | JGroups 2.x era | EOL | Incompatible with Kubernetes CNI (Calico, Cilium, Flannel) | D08 `xplatform-library_LIB` — blocks containerisation of all Gen-1 services | High |
| BouncyCastle | 1.48 (2012) | EOL | Multiple cryptographic implementation CVEs | D13 `wirecard_sg-bank-agent_LIB`, `wirecard_utilities_LIB` | High |

---

## 7. Observability Assessment

### Gen-3 (NexPay, Domain 11 / Domain 03 / Domain 09)

The NexPay platform and Gen-3 services are the only part of the estate with end-to-end observability. OpenTelemetry OTLP exports to Dynatrace for traces, logs, and metrics. Spring Boot Actuator exposes `/actuator/health` (liveness/readiness probes), `/actuator/metrics`, and `/actuator/prometheus` on port 8081 (internal only). `AuditFilter` propagates `actor.id`, `source`, `reason`, and `Idempotency-Key` as OTel baggage across ACA service boundaries. The `saga`, `saga_step`, and `outbox_event` PostgreSQL tables provide a persistent, queryable audit trail for every disbursement saga.

**Gen-3 observability gaps:**
- OTLP metrics disabled in QA profiles for `nexpay-claim-code-svc` — performance regressions in QA are invisible
- Domain 04 Gen-3 services expose `show-details: always` on health endpoints — unauthenticated callers can observe database connectivity status
- Domain 12 `logstash-ship` scaled to zero — the centralised log archive receiving Gen-1/Gen-2 log data is inactive

### Gen-1 / Gen-2 (All Other Domains)

**Structured logging:** Absent. All Gen-1/Gen-2 services use Log4j 1.x or Log4j 2.x file appenders with unstructured text output. `auto-card-batch_LIB` log4j.properties line 1 sets `rootLogger=DEBUG` globally — all packages including PII-containing classes log at DEBUG in production. Log file named `autocardtest.log` in production configuration (Domain 01).

**Distributed tracing:** Absent across Domains 01, 02, 04, 05, 06, 07, 08, 10, 12, 13. Domain 08's `xsearch_LIB` has 30+ debug log calls commented out. The only correlation mechanism across Gen-1/Gen-2 is a per-call UUID generated in some services that is not propagated through service boundaries. MTTR for multi-service payment failures requires manual log file correlation across Windows filesystem paths.

**Metrics:** No Micrometer or Prometheus metrics endpoint configured in any Gen-1 or Gen-2 service. No counters for authorization grants/denials (Domain 05 `api-security_SVC`), vault read/write operations (Domain 05 `strongbox-xmlrpc_SVC`), MFA outcomes (Domain 05 `rsa-mfa_LIB`), or batch job completion counts (any batch service in Domains 01, 02, 06).

**Health checks:** Domain 04 Gen-2 services use `GET /login.jsp` as their health check URI in GitLab CI — a full page render rather than a lightweight probe. `crypto-service_SVC` (Domain 09) returns static `"OK"` from `/cryptokeysvc/hc` with no dependency validation. Strongbox vault (`strongbox-xmlrpc_SVC`, Domain 05) has no health endpoint — a silent database connection failure causes cascading failures across all consuming services with no alertable signal.

**PII/SAD in logs:** Domain 14 Gen-1 SOAP suites use `given().log().all()` — complete SOAP request/response bodies including committed PANs, CVVs, and SSNs are written to stdout on every test execution. Domain 05 `strongbox-xmlrpc_SVC CryptoService.java:173` logs PGP plaintext at INFO. Domain 02 `xml-rpc_LIB` logs full RPC payloads at DEBUG. Domain 04 `manage-payment-rest-api` logs at TRACE including payment request bodies. These are active, ongoing cardholder data leakage pathways.

**Log retention (AWS ECS / Gen-2):** Hardcoded at 14 days in `terraform-ecs-service_INFRA_TF`. PCI DSS Req 10.7 requires 12 months with 3 months immediately available. A single Terraform variable change followed by apply across all callers would fix this.

**Alerting:** Operational awareness across Gen-1/Gen-2 is entirely reactive — external scheduler exit codes and manual log file review. `DS_ETL_warehouse` (Domain 10) sends failure notifications to `colin.treat@northlane.com`, a former Northlane employee email that may be inactive; if so, all ETL failure alerts are silently dropped. SMTP notification uses `EnableSsl=False` on relay `nl-smtp-01.nam.wirecard.sys`.

---

## 8. Infrastructure as Code Coverage

| Domain / Layer | IaC Tool | Coverage | Key Gap |
|----------------|----------|----------|---------|
| Gen-2 AWS (nlroot-aws_INFRA_TF) | Terraform | Route 53 (29 zones), S3 state | No CI/CD pipeline; manual apply; no version constraints in `terraform {}` block |
| Gen-2 AWS (nlutil-aws_INFRA_TF) | Terraform | VPC, ECS cluster, ALB, ECR, IAM, SQS | No CI/CD; IAM over-permissions (`ecr:*`, `ssm:*`, `iam:PassRole` all on `Resource: *`); single NAT GW SPOF; no VPC Flow Logs |
| Gen-2 AWS ECS (terraform-ecs-service_INFRA_TF) | Terraform reusable module | ECS task/service/CloudWatch | No `backend.tf` (local state risk); same IAM role for task execution and runtime; `retention_in_days = 14` hardcoded; `definitions` output not marked `sensitive` |
| Gen-3 Azure NexPay QA (nexpay-iac) | Terraform | Container Apps env, PostgreSQL, Key Vault, App Config, VNet | **No `prod.tfvars` or production workspace** — production not IaC-managed; App Config public access enabled; Key Vault purge protection disabled; App Config on free tier (no private endpoints) |
| Gen-3 Azure NexPay Prod | None visible | **Zero IaC coverage** | Production infrastructure governance entirely opaque |
| Gen-1/Gen-2 Windows servers | None | **Zero IaC coverage** | 29 PROD server config directories maintained by manual file copy; no drift detection |
| Gen-2 Spring Cloud Config | Unknown | README only in source repo | Actual running ECS image provenance unknown; auth status unknown |
| Data Platform (Domain 10) | None | **Zero IaC coverage** | All database, ETL, SSAS deployments manual; no CI/CD for any DS_ repo |
| Wirecard-era AWS account | Terraform (partial) | No multi-environment structure; `chaossearch_INFRA_TF` single `poc.tfvars` | No governed production promotion path; no account separation QA/PROD |

**No Terraform pipeline exists for any IaC repository.** All `terraform apply` operations in the estate are manual, with no automated plan review, approval gate, or audit trail beyond Git commit history. In a PCI DSS Level 1 environment, this means all infrastructure changes to CDE-adjacent systems are uncontrolled by the change management process that would satisfy Req 6.4 and Req 6.5.

**Wirecard-era infrastructure not decommissioned:** The `nam.wirecard.sys` private DNS zone is used by production services, QA servers, configuration repositories, CI pipelines, and SSIS ETL packages across all 15 domains. The AWS account is named and bucketed using Wirecard conventions. No decommission or migration timeline is documented in any repository.

---

## 9. Operational Risk Register (Top 10)

| Rank | Risk | Domains Affected | Likelihood | Impact | Recommended Mitigation |
|------|------|-----------------|------------|--------|------------------------|
| 1 | **Director service SPOF** — Director is a pre-startup hard dependency for all Gen-1/Gen-2 services. The `DirectorXMLRPCClient` in `xml-rpc-clients_LIB` has 1,000 max connections with 60-second TCP timeout; a Director outage causes cascading thread pool exhaustion across all consuming services simultaneously. No circuit breaker, no cached fallback. | D01, D04, D06, D08 | High | Critical — estate-wide Gen-1/Gen-2 outage | Implement circuit breaker (Resilience4j); add Director health check to all consumer startup probes; cache last-known-good Director response; define Director DR runbook |
| 2 | **`job-scheduler_SVC` SPOF** — Single instance, no HA configuration, no warm standby, no DR runbook. An outage means no new batch jobs can be scheduled, authorised jobs are stuck, and blackout windows cannot start or end. | D06 | Medium | High — all batch job scheduling halted | Deploy at minimum two instances; implement leader election via DB lock; document recovery procedure |
| 3 | **`logstash-ship` ECS service scaled to zero** — Logs from all Gen-1/Gen-2 ECS services accumulate in SQS but are not shipped to S3 or ChaosSearch. The PCI DSS Req 10 centralised log archive is currently inactive. This is a confirmed production state in `nlutil-aws_INFRA_TF`. | D12 (all Gen-2) | Confirmed / Active | Critical — compliance gap; security event loss | Set `ecs_count = "1"` in `nlutil-aws_INFRA_TF`; verify S3 receive; create monitoring alert for SQS queue depth growth |
| 4 | **DPAPI key-man risk (DS_ETL_warehouse)** — All 100+ SSIS packages encrypted with `EncryptSensitiveWithUserKey` bound to NAM\nick.doan's Windows account on P-NA-DB11. Disabling, locking, or deleting this account destroys access to all warehouse ETL credentials permanently. `.dtsConfig` production configuration files exist only on the SSIS execution server — not version-controlled. | D10 | Medium | Catastrophic — total warehouse ETL failure with no recovery path | Emergency: migrate to `DontSaveSensitive` + SSIS Catalog environment variables backed by Azure Key Vault; document all `.dtsConfig` values in a secure secrets store |
| 5 | **Dual-cloud estate with no retirement timeline** — Gen-1 Windows on-premises, Gen-2 AWS ECS, and Gen-3 Azure ACA/AKS all in simultaneous production. The Wirecard-era AWS account (`wc-root-state`) and `nam.wirecard.sys` DNS namespace remain active. Operations requires three incompatible toolchains and three secrets management models. | All 15 | Ongoing | High — operational complexity multiplies incident MTTR; DNS zone controlled by defunct company | Define and publish a domain-by-domain migration timeline; establish a Wirecard infrastructure decommission workstream with a named programme owner |
| 6 | **No container scanning estate-wide** — `CONTAINER_SCAN: false` is set in deployment workflows for all 11 NexPay ACA services (Domain 11) and Gen-3 services in Domains 03 and 09. OS-layer CVEs in base images are never detected before production. `bellsoft/liberica-openjre-alpine:21` is used without SHA256 pinning across Domain 04 and others. | D03, D09, D11 | High | High — critical CVEs in base images reach production undetected | Enable `CONTAINER_SCAN: true`; configure `allowedlist.yaml` for documented suppressions; add scan gate blocking promotion on CRITICAL CVEs |
| 7 | **SSIS ETL bound to personal DPAPI key** (see Risk 4) combined with **`DS_ETL_warehouse` failure notifications routing to a former employee** (`colin.treat@northlane.com`) — ETL failures may go undetected for hours or days | D10 | High | Medium — operational blind spot for data warehouse | Update notification to active team distribution list; enable TLS on SMTP relay; add ETL SLA monitoring |
| 8 | **Swagger/Spring Cloud Config password `s3cr3t`** in `cross-border-transfer-service_SVC bootstrap.yml` — all credentials delivered via this Config Server must be treated as compromised until rotated; the service handles live international wire transfers | D02 | Confirmed / Active | Critical — all Cambridge FX credentials at risk | Immediately rotate Config Server password to an Azure Key Vault-managed value; audit all secrets the Config Server has delivered |
| 9 | **`xsearch-xmlrpc_SVC` Dependabot-to-production without testing** — `EXCLUDE_STAGE: true`, `-Dmaven.test.skip`, and `UPDATE_DEPENDENCIES: true` combine to create a path where every automated dependency bump on the cardholder PAN search service is promoted to production without any human review of runtime behavior | D08 | High | High — broken PAN search ships to production automatically | Set `EXCLUDE_STAGE: false`; remove `-Dmaven.test.skip`; set `UPDATE_DEPENDENCIES: false` until staging gate is operational |
| 10 | **SwarmCache/JGroups multicast incompatible with Kubernetes network overlays** — `xplatform-library_LIB` uses JGroups multicast for distributed cache synchronisation. JGroups multicast is blocked by Calico, Cilium, Flannel, and most cloud VPC configurations. This is a hard blocker for containerising any Gen-1 service that depends on `xplatform_LIB` — which is every Gen-1 service. Silent cache failures would degrade search and session performance without detection. | D08 (all Gen-1 consumers) | High | High — blocks entire cloud migration for Gen-1 services | Replace SwarmCache with Redis/Azure Cache for Redis behind `ICache` interface; dual-write validation before cutover |

---

## 10. Strategic DevOps Recommendations (Top 10)

| Rank | Recommendation | Why | Domain(s) | Priority |
|------|---------------|-----|-----------|----------|
| 1 | **Rotate all committed secrets and purge Git history.** Execute `git filter-repo` (not `git filter-branch`) across all affected repositories to remove committed credentials from all branches and tags. Rotate: Visa credentials (Domain 04 `dapr-secrets.json`), CIMB SFTP RSA key (Domain 13), PGP private keys (Domains 05, 13), AWS access key `[REDACTED — rotate immediately]` (Domain 13 — audit CloudTrail immediately), Mailgun API key (Domain 07), `scheduler_WAPP` four DB passwords (Domain 04), `stand-in-processing-api` App Configuration key (Domain 09), Logstash TLS private key (Domain 12), Config Server `s3cr3t` password (Domain 02), `b2ctest` DB credentials (Domain 07), Android release keystore (Domain 13). Coordinate credential rotation with affected counterparties (CIMB Bank SG, Cambridge, Visa, Mailgun, app stores). **This is the single most urgent action in the estate.** | Every committed secret is an active compromise until rotated. PCI DSS Req 3.5 and Req 8.3. | D02, D04, D07, D09, D12, D13 | **P0 — Week 1** |
| 2 | **Implement secrets scanning with push protection across all repos.** Enable GitHub Secret Scanning with push protection (blocks push on detected secrets) for all 363 repositories. Configure `gitleaks` as a required pre-commit hook across all developer workstations. Add Trufflehog as a mandatory CI step in all GitHub Actions workflows. Without this, new secrets will continue to be committed regardless of any other remediation effort. | Root cause of estate-wide credential exposure identified in Domain 12 as the highest-priority gap. | All (D12 as root cause) | **P0 — Week 1** |
| 3 | **Re-enable automated tests in CI pipelines; establish a no-deploy-without-tests policy.** Remove `-Dmaven.test.skip=true` and `-DskipTests` flags from all CI/CD deployment pipelines estate-wide. Phase 1 (30 days): enable existing test classes in the 10 most business-critical repos (clientapi_API, account-management-api, scheduler_WAPP, banker_API, autofile_SVC, cross-border-transfer-service_SVC, xsecurity_SVC, api-security_SVC, strongbox-xmlrpc_SVC, stand-in-recovery-service). Phase 2 (90 days): add minimum JaCoCo coverage thresholds (40% instruction coverage as initial floor). For repos with zero tests, add at minimum CodeQL SAST and OWASP Dependency-Check with CVSS >= 7.0 as a build-failure threshold. | Undetected regressions shipping to production is the most pervasive quality risk across all 15 domains. PCI DSS Req 6.2.4 explicitly requires testing of changes. | All 15 | **P0 — 30 days** |
| 4 | **Deploy Azure Key Vault or HashiCorp Vault as the estate-wide secrets management standard; migrate all runtime secrets from files and properties into the vault.** Gen-3 (NexPay) already uses Azure Key Vault — extend this pattern to Gen-2 services via Managed Identity or service principal. Priority order: scheduler_WAPP, manage-payment-rest-api, mailgun-event-tracker, cross-border-transfer-service_SVC, strongbox-remote-client_LIB, api-security_SVC. For Gen-1 Windows batch services, use Windows DPAPI group service account (replacing individual user binding) as an interim measure until containerisation is feasible. | Secrets in source code and properties files on filesystem are exploitable by anyone with repo read access or server filesystem access. | D01–D07, D09, D12, D13 | **P0 — 60 days** |
| 5 | **Enable container scanning on all Gen-3 services and mandate it as a deployment gate.** Set `CONTAINER_SCAN: true` in all NexPay service deployment workflows, Domain 03 Gen-3 services, and Domain 09 services. Configure `allowedlist.yaml` with documented suppressions (each suppression must have: CVE ID, justification, compensating control, and remediation deadline). Add a CI gate that blocks promotion to production if any CRITICAL-severity unwaivered CVE is detected. Pin base images by SHA256 digest rather than mutable tags. | CONTAINER_SCAN: false across all 11 NexPay ACA services means OS-layer critical CVEs ship to a PCI DSS CDE without detection. PCI DSS Req 6.3.3. | D03, D09, D11 | **P1 — 30 days** |
| 6 | **Fix the CloudWatch log retention to 365 days and restore the `logstash-ship` ECS service.** In `terraform-ecs-service_INFRA_TF`, change `retention_in_days = 14` to `retention_in_days = 365`. Scale `logstash-ship` from `ecs_count = "0"` to `ecs_count = "1"` in `nlutil-aws_INFRA_TF` and verify S3 log delivery to `nl-chaossearch-ingest-us-east-1`. Add a CloudWatch alarm on SQS queue depth growth that alerts when log messages are accumulating without being consumed. These are trivial Terraform one-line changes with a `terraform apply`; the compliance cost of the current state is a PCI DSS Req 10.7 finding. | PCI DSS Req 10.7 requires 12-month log retention with 3 months immediately available; 14 days fails both thresholds. Log archive is currently inactive. | D12 | **P0 — Week 2** |
| 7 | **Implement Terraform CI/CD pipelines with plan-approval gates for all IaC repositories.** Add GitHub Actions workflows to `nlroot-aws_INFRA_TF`, `nlutil-aws_INFRA_TF`, `terraform-ecs-service_INFRA_TF`, and `nexpay-iac`: PR triggers `terraform plan` with output as artifact; production apply requires a named approver. Add `terraform {}` version constraints (`required_version = "~> 1.7"`) and provider version pins. Create `prod.tfvars` for NexPay in `nexpay-iac` with production-grade settings: Key Vault purge protection enabled, App Configuration private endpoint, Standard App Config tier, production PostgreSQL SKU. | Manual Terraform apply with no approval gate means infrastructure changes to the CDE are uncontrolled under PCI DSS Req 6.4. Production NexPay infrastructure is not IaC-managed at all. | D11, D12 | **P1 — 60 days** |
| 8 | **Resolve the EOL runtime upgrade backlog using a risk-prioritised roadmap.** Immediate (P0): Replace `sqljdbc 1.1` (TLS 1.0 only) in `ecore-batch_LIB` — PCI DSS Req 4.2.1 prohibits early TLS in CDE. Decommission `atlys_WAPP` (Silverlight 4.0, SQL injection) and `chargeback-engine_LIB` (requires JDK 7). Quarter 1: Replace Log4j 1.x with Log4j2/Logback in all Gen-1 batch repos (Domains 01, 02, 04, 06) — CVE-2019-17571 RCE. Upgrade Tomcat 8.5 (EOL) in clientzone_WAPP and csa_WAPP to Tomcat 10.1. Quarter 2: Migrate from Apache Axis 1.4/Axis2 1.7.5 to maintained REST clients. Upgrade Spring 2.x and Spring Boot 1.5.x to Spring Boot 3.x. Year 1: Replace SwarmCache/JGroups with Redis in `xplatform-library_LIB` to unblock Gen-1 containerisation. Migrate DS_ETL_warehouse from SSIS 2012 to Azure Data Factory. | EOL frameworks cannot be patched; each represents an accepted CVE that will never be remediated without migration. PCI DSS Req 6.3.3 and Req 12.3.4. | D01, D02, D04, D08, D10, D13 | **P0–P1 — Phased** |
| 9 | **Consolidate to single CI pipeline per repo; decommission all legacy GitLab/Jenkins pipelines.** For every repo with both a GitLab CI (or Jenkinsfile) and GitHub Actions workflow: (a) verify the GitHub Actions workflow is the authoritative build; (b) archive or delete the legacy CI file; (c) decommission the legacy Tomcat/WinRM deployment targets in GitLab. Document which pipeline is authoritative in each repo's CLAUDE.md or README. Priority: `director-svc_SVC` (simultaneous WAR + AKS deployment ambiguity), `crypto-service_SVC` (GitLab still targeting Windows VMs), `enrollment_WAPP` and `oneplatform_WAPP` (Jenkins + GitLab dual with different artifact versions). Dual pipelines can deploy different versions to different targets simultaneously with no operator visibility. | Dual CI creates deployment ambiguity, possible version overwrites, and prevents clear incident attribution. | D01, D02, D03, D04, D05, D09, D13 | **P1 — 90 days** |
| 10 | **Implement OpenTelemetry distributed tracing across the client-facing payment path.** Add OpenTelemetry SDK to the top-10 business-critical Gen-1/Gen-2 services: `clientapi_API`, `order_SVC`, `account-service_LIB`, `autofile_SVC`, `director-svc_SVC`, `api-security_SVC`, `strongbox-xmlrpc_SVC`, `notification-framework_SVC`, `jobservice_SVC`, `xsecurity_SVC`. Configure W3C Trace Context header propagation across SOAP and XML-RPC boundaries. Export to Azure Monitor Application Insights or the existing Dynatrace OTLP sink already used by Gen-3 services. Simultaneously: add Micrometer counters for authorisation grants/denials, vault operations, MFA outcomes, and batch job completions. Without distributed tracing, MTTR for multi-service payment failures is measured in hours of manual log correlation rather than minutes of trace waterfall analysis. | No distributed tracing across Gen-1/Gen-2 estate. MTTR for payment failures is unacceptably high. PCI DSS Req 10.2 (log all access to cardholder data). | D01, D04, D05, D06, D08 | **P1 — Quarter** |

---

*Document end — MASTER_DEVOPS.md | Generated 2026-05-08 | Onbe 363-Repo Estate | Internal — Restricted*
*Source files: DO_domain01.md through DO_domain15.md | 15 domain synthesis documents | Phase 3 Master Synthesis*
