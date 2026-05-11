# Business Analyst View — CONFIG_prod

## Business Purpose
This repository holds all environment-specific configuration files for the **PRODUCTION** environment of Onbe's legacy Java prepaid card and payments platform. It configures the full production server fleet (`p-az-app01` through `p-az-app21`, plus batch servers `p-az-bat02` and `p-az-bat03`), enabling live cardholder-facing services and client B2B operations. This is the most sensitive configuration repository in the organisation.

## Business Capabilities Configured
The PROD configuration covers the full live platform:

**Card Management & Account Services**
- Account Management API — live card lifecycle management (`region=NA`, `agent=B2C`, `ecount.agent=B2C`)
- Client API — live B2B API for card operations
- Debit API — live debit card transaction processing
- Card Notification SMS Pull — live SMS alerts to cardholders (production SAP endpoint: `sms-pp.sapmobileservices.com/citi/citi_prepa31535/`)
- Accept Prechecks / FDVS Precheck — production Certegy/FDVS checks
- CSWS — production card management web service

**Customer-Facing Portals**
- ClientZone — production cardholder portal at `clientzone.mypaymentadmin.com`
- Enrollment / OnePlatform — production enrollment and account hub at `login.northlane.com`
- CSA — production customer service agent portal

**Payment Services**
- Payment — production payment processing
- DFAPI/Remittance — production IBM MQ (`dofrmwpmq.nam.wirecard.sys`, QM=`DF_QM`) — live remittance
- CBTS — production cross-border transfer service (Cambridge FX production client)

**Security & Fraud**
- BioCatch fraud scoring — **production BioCatch endpoint** (`api-9a7a72ec.us.v2.we-stats.com`, `customerID=osiris`)
- KYC — **production Azure KYC portal** (`app-activationportalapi-prod-westus2-001.azurewebsites.net`)
- Strongbox — production crypto key service

**Notifications**
- IVR Web Service — live IVR (same `appKey` as UAT — see risks)
- eDelivery — electronic statement delivery

**Back-Office & Batch**
- Inventory Management, Scheduler, Rebate Card Inquiry, IEFTRules, SubaruRewards, DailyReport
- Multiple batch servers: `p-az-bat02`, `p-az-bat03`

## Key Production Identifiers
- Agent: `B2C` (production agent code)
- MFA: `mfaSwitch=ON`, `mfa.required=Y`, `otpRequired=Y` — **MFA fully enforced in PROD**
- CMS: `https://login.northlane.com:443`
- Director: `http://ppazp.nam.wirecard.sys:8080/service/dispatch.asp`
- Production member IDs are different from lower environments
- RCCL programs: `04014347` (main), `04019420` (PHP) — production RCCL program IDs
- Comcast program IDs and cardholder domain restrictions active

## Business Entities
Live Cardholders, active Programs, production Clients (RCCL, Disney, Comcast, Subaru, Verizon, Western Union, etc.), live ACH/wire transactions, production BioCatch fraud sessions, production KYC validations.

## Business Rules
- MFA fully enforced (ON) in PROD for all portals
- OFAC/sanctions domains blocked: `.cu,.ir,.kp,.sy,.ua`
- Western Union integration active (with static signing key in config)
- DFAPI remittance routes directly to production MQ (`DF_QM`)
- BioCatch production endpoint with `riskScoreToDeny=1000`

## Compliance Concerns (HIGH SEVERITY)
**PRODUCTION credentials are committed to source control.** This is the most critical finding across all 7 repos:

1. **Production CBTS service username and password** committed in `applicationContext-oneplatform.properties` and `applicationContext-csa.properties`
2. **Production KYC Azure AD OAuth client secret** committed — grants access to production identity verification service
3. **Production BioCatch customer credentials** committed — `customerID=osiris` with production endpoint
4. **Production Western Union static signing key** committed
5. **Production IBM MQ connection details** (hostname, port, channel, QM, queue names) committed — production remittance infrastructure topology exposed
6. **Production SMS gateway credentials** (SAP Mobile Services production endpoint credentials in CardNotification.properties)
7. **Production IVR `appKey`** committed — same value as UAT (key reuse)
8. **Google reCAPTCHA production keys** committed
9. **Production DFAPI client ID and configuration** committed

These credentials, if compromised via a Git repository breach, could allow attackers to:
- Initiate fraudulent remittance transactions via DFAPI
- Spoof KYC identity verification decisions
- Bypass or manipulate fraud scoring via BioCatch
- Send unauthorised SMS notifications to cardholders
- Access production cross-border transfer operations

## Business Risks
- Entire production credential set is in a Git repository — a single Git breach compromises the production platform
- 21+ production app servers means a configuration error affects live cardholders immediately
- Production and lower-environment configs share some credential values (CBTS credentials identical to DEV/QA)
