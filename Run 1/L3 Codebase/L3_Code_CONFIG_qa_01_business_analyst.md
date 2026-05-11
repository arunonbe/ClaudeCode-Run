# Business Analyst View — CONFIG_qa

## Business Purpose
This repository holds all environment-specific configuration files for the **QA (Quality Assurance / Staging)** environment of Onbe's legacy Java prepaid card and payments platform. It provides configuration for the QA server fleet (`q-na-app01` through `q-na-app12`, plus `q-na-bat02` and `q-na-bat03`), enabling full functional and regression testing against production-like configuration.

## Business Capabilities Configured
The QA environment mirrors the full production capability set, configured for staging/testing:

**Card Management & Account Services**: AccountManagementAPI, ClientAPI, DebitAPI, AcceptPrechecks, FDVS Precheck, CSWS

**Cardholder Portals**: ClientZone (with MFA ON, agent B2CSTAGE), Enrollment, OnePlatform, OP508

**Payment Services**: Payment, DFAPI/Remittance (IBM MQ, different queue to DEV), CBTS cross-border transfer

**Notifications**: CardNotification SMS (SAP Mobile Services UAT endpoint), IVRWS

**Back-Office & Batch**: InventoryMgmt, Scheduler, RebateCardInquiry, IEFTRules

**Client-Specific Programs**: SubaruRewards, various client batch programs, xContent

**Security**: Strongbox (crypto key service), eCount core, CSA

**Biometrics/Fraud**: BioCatch fraud scoring (`biocatch.switch=Y`) — QA/test BioCatch endpoint configured in QA (not present in DEV config)

## Key Differences from DEV
- Agent code: `B2CSTAGE` (not `B2CTEST`)
- MFA: `mfaSwitch=ON` in ClientZone; `mfa.required=N` in OnePlatform (relaxed for test automation)
- CMS URL: `login-qa.northlane.com` (branded Northlane QA hostname)
- Director: `ppnaut.nam.wirecard.sys:8080` (dedicated QA Director server)
- CBTS points to `q-na-app08.nam.wirecard.sys:9443`
- IBM MQ: Different queue manager `WLDF_UAT_QMGRS` on `dflnxswmqu.nam.wirecard.sys:1414`
- CardNotification SMS uses UAT SAP endpoint (same as UAT repo)
- BioCatch fraud scoring enabled (QA/test BioCatch API)
- Contact us email routed to `gaurav.sharma@onbe.com` (Onbe employee — test environment)
- KYC Portal: same Azure QA endpoint as DEV
- Multiple datasources present in QA that are absent from DEV (ecount-db, ecountcore-ds, greatplains-ds, webcertomaha-ds)
- QA has 12 app servers vs DEV's 4 — larger fleet reflecting production-like scale testing

## Business Entities
Same as DEV: Programs, Agents, Members, Cardholders, Clients, Orders. QA uses staging-tier client identifiers and program IDs.

## Business Rules
- QA uses agent `B2CSTAGE` across all services
- MFA is ON in ClientZone but OFF in OnePlatform — mixed MFA posture
- RCCL programs use different QA-specific program IDs (`04015612`, `06015613`)
- Biometrics fraud scoring is active in QA (BioCatch `riskScoreToDeny=1000`)
- Sanctions screening domains restricted: `.cu,.ir,.kp,.sy,.ua`

## Business Flows
Identical to PROD flows but using QA infrastructure endpoints and test program IDs. QA is the final pre-production verification environment.

## Compliance Concerns
- Committed credentials (SQL Server passwords, IBM MQ credentials, CBTS passwords, KYC client secret, Western Union static key, Google reCAPTCHA secret) — same pattern as DEV
- QA has GitLab CI pipeline (`.gitlab-ci.yml`) that deploys config changes automatically via ci-templates — config deployment is automated for QA
- BioCatch test credentials committed
- IBM MQ credentials (`df.mq.principal=prepaid`, blank password) committed
- `contactus.recipientEmail=gaurav.sharma@onbe.com` — internal employee email in source control

## Business Risks
- Credentials committed to source control across multiple files (see Data Architect view)
- QA environment has a larger server fleet (12+ app servers) with more attack surface than DEV
- SMS notification uses production-adjacent SAP Mobile Services test endpoint — misconfiguration could reach real SMS gateway
- BioCatch fraud scoring in QA uses test credentials; must not use production BioCatch API keys
