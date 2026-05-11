# Business Analyst View — CONFIG_dev

## Business Purpose
This repository holds all environment-specific configuration files for the **DEV (development)** environment of Onbe's legacy Java prepaid card and payments platform. It provides externalized configuration for every application service and batch job running across the DEV application server fleet (`d-na-app01` through `d-na-app04`, plus `d-na-bat02`), allowing service behaviour to be changed without code deployments.

## Business Capabilities Configured
The DEV environment hosts configuration for the full stack of Onbe's legacy prepaid payment capabilities:

**Card Management & Account Services**
- Account Management API — card account lifecycle (create, activate, link, status update, card issuance)
- Client API — B2B API for client-side card operations (issuance, enrollment, account query)
- Debit API — debit card transaction processing
- Card Notification (SMS Pull) — transaction SMS alerting to cardholders
- Accept Prechecks / FDVS Precheck — pre-authorization acceptance checks (Certegy integration)
- CSWS (Card Services Web Service) — card management web service

**Customer-Facing Web Applications**
- ClientZone / ClientZone5 / ClientZoneHub — cardholder web portal (multi-region: NA, EMEA, LATAM, APAC)
- CSA (Client Service Application) — customer service agent portal
- Enrollment — cardholder enrollment application
- OnePlatform / OnePlatform Hub / OP508 — multi-program enrollment and account management hub
- Workbench / Wizard — internal tooling portals

**Payment Services**
- Payment — payment processing service
- DFAPI Client — Deutsche Financial/Direct Funds API integration (IBM MQ)
- CBTS (Cross-Border Transfer Service) — international wire transfer (Cambridge FX integration)
- IVR Web Service — Interactive Voice Response integration

**Back-Office / Batch Services**
- Inventory Management — card inventory lifecycle (auto-reorder, expiry, shipping)
- Scheduler — job scheduling service
- Rebate Card Inquiry — rebate program card inquiry
- Request File Bulk Card Generation — bulk card request file processing
- DailyReport, IEFT Rules — reporting and electronic funds transfer rules
- Strongbox — cryptographic key/secret service
- eCount Core — core account management
- AutoFile — automated file processing
- ConsumerLoad, HartfordFilesProcessor, SubaruRewards, SprintRAF, Hyundai, W3C, ThankyouCard — client-specific batch programs

**Microservices (Spring Boot)**
- CBTS (cross-border-transfer-service) — Spring Boot service on port 9443

**Observability**
- Filebeat input configs — log shipping configuration for all services on all DEV servers

## Business Entities
- **Program** — a branded prepaid card product (identified by 8-digit program ID, e.g., `04011161`)
- **Agent** — environment identifier (`B2CTEST` in DEV)
- **Member ID** — unique platform membership identifier (GUID format)
- **Cardholder** — end consumer holding a prepaid card
- **Client** — business entity (e.g., RCCL, Disney, Subaru, Comcast, Verizon) sponsoring a card program
- **Order** — a card issuance or account request processed through the Order service
- **CMS (Content Management System)** — `d-na-app03`; serves xContent and cardholder-facing content
- **Director** — internal routing/dispatch service at `d-na-app01:8080/service/dispatch.asp`

## Business Rules
- DEV environment uses agent code `B2CTEST` (vs `B2C` in PROD, `B2CSTAGE` in QA)
- MFA is configured `OFF` for ClientZone in DEV (relaxed for development convenience)
- `mfa.required=N` in enrollment DEV config
- Database names are identical to PROD (`cbaseapp`, `jobsvc`, `CBTS`) but on DEV database servers (`d-na-db01`)
- CBTS configures brand-client relationships (Disney, RCCL) with specific payment program IDs
- Western Union, Cambridge FX, KYC portal integrations point to UAT/beta endpoints from DEV

## Business Flows
1. Developer deploys updated WAR → config files on server drive (`D:\c-base\config\`) configure service at startup
2. Tomcat reads config files externally (not bundled in WAR) for environment-specific behaviour
3. Application connects to DEV databases, DEV Director service, and DEV CMS
4. SMS notifications use UAT/test SMS gateway endpoints
5. Cross-border transfers use Cambridge beta environment

## Compliance Concerns
- DEV environment contains actual IBM MQ credentials for a REMIT UAT queue (`jms.properties`) — credentials are committed to source control (see Data Architect view)
- CBTS `application.yml` contains database passwords, mail server credentials, and third-party API signatures in source control
- Oneplatform config contains hardcoded credentials for CBTS service and Google reCAPTCHA keys
- KYC Microsoft OAuth credentials (client secret) committed in multiple properties files
- DEV environment connects to Cambridge FX beta and KYC QA endpoints — cross-environment dependency
- MFA disabled in DEV config — expected for development but should be documented as deviation from PROD posture

## Business Risks
- Credentials committed to source control expose DEV service accounts and third-party API keys
- DEV uses the same eCount agent code format (`B2CTEST`) across many files — if DEV config is accidentally deployed to PROD, data could be corrupted
- Multiple commented-out PROD URLs remain in DEV config files, increasing the risk of accidental PROD connection from DEV
