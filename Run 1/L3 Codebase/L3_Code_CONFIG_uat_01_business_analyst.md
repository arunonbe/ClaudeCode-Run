# Business Analyst View — CONFIG_uat

## Business Purpose
This repository holds all environment-specific configuration files for the **UAT (User Acceptance Testing)** environment of Onbe's legacy Java prepaid card and payments platform. UAT is the final pre-production environment where business stakeholders and clients validate functionality before promotion to PROD. It runs on the `u-na-app01` and `u-na-app02` server pair.

## Business Capabilities Configured
UAT hosts a focused subset of the platform, covering the externally-facing and API-layer services required for client UAT sign-off:

**Card Management APIs**
- Account Management API — card lifecycle (create, activate, link, account status, payout)
- Account Management Payout — payout-specific account management variant
- Client API — B2B API for card operations (with validation regex for all input fields)
- Card Management CSAPI / CardManagementCSAPIPayout — card management web service variants
- Debit API — debit card transaction processing (programs `04014096`, `04019215`)

**Notifications**
- Card Notification SMS Pull — transaction SMS alerting (extensive program list across hundreds of program IDs; SAP Mobile Services UAT endpoint active)
- IVR Web Service — IVR integration (`agent=B2C`)

**Security / Web Services**
- Accept Prechecks — Certegy precheck (`agent=B2CTEST` — note: still using TEST agent in UAT)
- CSWS (Card Services Web Service) — V1 and CSWS contexts (CMS via `login-uat.northlane.com`)

## Key Differences from QA
- Agent: `B2C` for most services (same as PROD), except AcceptPrechecks uses `B2CTEST`
- CMS: `login-uat.northlane.com` (HTTPS, port 443)
- Director: referenced in `applicationContext-CSWS.properties` as `ppnau.nam.wirecard.sys`
- Region: `NA` (North America, same as PROD)
- `accountstatus=CLOSED|ACTIVE|Activate|activate|ACTIVATE` — full status set, same as PROD
- CardNotification has the full production-equivalent program ID list (hundreds of programs) — UAT mirrors PROD program list
- SMS active with SAP Mobile Services UAT endpoint (same endpoint as QA CardNotification)
- JAVA_OPTIONS files (Tomcat registry) present for all services — UAT is the only lower environment with committed JVM tuning configs
- Truststore/keystore passwords present in committed JAVA_OPTIONS files
- JMX remote management enabled with authentication (password/access files referenced)

## Business Entities
Same as DEV/QA: Programs, Agents, Members, Cardholders, Clients. UAT uses `B2C` agent (production agent code) for most services.

## Business Rules
- `region=NA` — North America only (UAT is NA-region UAT)
- `memberId=5FCFFE5C-D07B-490C-82DD-00003311D26D` — same member ID as QA and PROD environments
- CardNotification SMS program list is effectively the production list — UAT validates the full production program scope
- `dfiNA=553`, `routingNA=011001234` — ACH routing details for card account funding in UAT (ClientAPI)
- AcceptPrechecks uses `B2CTEST` agent — suggests Certegy UAT endpoint is still test-facing

## Business Flows
UAT flows mirror PROD:
1. Client team deploys and tests new release in UAT
2. Business stakeholders validate card operations via Account Management API and Client API
3. SMS notifications validated via CardNotification with production-representative program IDs
4. Sign-off obtained → promotion to PROD

## Compliance Concerns
- Truststore and keystore passwords committed to source control in JAVA_OPTIONS files (committed text files in `tomcat/registry/`)
- JMX remote authentication enabled but SSL disabled (`jmxremote.ssl=false`) — JMX exposed without TLS in UAT
- CardNotification SMS gateway credentials (SAP Mobile Services) committed in CardNotification.properties
- AcceptPrechecks uses `B2CTEST` agent in UAT — inconsistency with production agent; may indicate Certegy UAT credentials are test credentials

## Business Risks
- `B2C` agent used in UAT for most services — UAT mistakes could interact with production-adjacent systems
- Full production program ID list in CardNotification — any misconfiguration could affect real programs
- Only 2 app servers in UAT — limited capacity for full-scale testing; may not catch concurrency issues
