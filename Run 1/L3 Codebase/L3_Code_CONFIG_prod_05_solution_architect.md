# Solution Architect View — CONFIG_prod

## Technical Architecture
Production runs Gen-2 Tomcat externalized-configuration on Azure IaaS (Windows VMs). Same file-based config pattern as DEV/QA/UAT. Unique production characteristics:
- Azure VMs (`p-az-*`) with `wirecard.sys` internal DNS still active
- 21 primary app servers + 6 sub-instances + 2 batch = 29 server config sets
- `ecount-config.xml.erb` ERB template (historical CM tooling artefact)
- `CardNotification-UAT.properties` committed alongside production `CardNotification.properties` (vestige file)
- Java 7 binary (`Java/Java/`) present alongside Java 8 (`Java/JDK-AWS-8/`) — two JDK generations in production repo

### Production-Specific Config Differences from Lower Environments
- `mfa.required=Y`, `otpRequired=Y`, `display.Jcaptcha.flag=Y` — full security enforcement
- `mfaSwitch=ON` — MFA active
- `initial.profile=prod` — Spring profile set to production
- DFAPI connects to production MQ server `dofrmwpmq.nam.wirecard.sys` with `QM=DF_QM`
- BioCatch uses production endpoint and `customerID=osiris` (not test)
- KYC uses `app-activationportalapi-prod-westus2-001.azurewebsites.net`
- CBTS credentials are production-specific values (different from DEV/QA — at least partially isolated)
- SAP SMS uses production gateway path (`citi_prepa31535`) vs UAT (`citi_uat_487792`)

## API Surface
No APIs defined here. Production services expose APIs defined in application code repos.

## Security Posture — CRITICAL

### Production Secrets in Source Control (file locations, values NOT reproduced)

**CRITICAL SEVERITY — IMMEDIATE ACTION REQUIRED:**

1. **`config/p-az-app01/config/oneplatform/applicationContext-oneplatform.properties`**:
   - Production CBTS service password (plaintext) — controls production cross-border transfer authorisation
   - Production KYC Azure AD OAuth2 client secret — controls production identity verification
   - Production BioCatch customer credentials — controls production fraud scoring
   - Production Western Union static key — controls WU transfer signing
   - Google reCAPTCHA production secret key

2. **`config/p-az-app01/config/dfapiclient/jms.properties`**:
   - Production IBM MQ server hostname, port, channel, QM name, send/receive queue names
   - `df.mq.principal=prepaid` with blank credential field — MQ authentication state unclear
   - **Production remittance infrastructure fully enumerated** in this file

3. **`config/p-az-app01/config/cardnotification/CardNotification.properties`**:
   - Production SAP Mobile Services SMS gateway username and password
   - Access to this credential allows sending SMS to all production program cardholders

4. **`config/p-az-app01/config/ivrws/ivrws.properties`**:
   - Production IVR `appKey` — SAME VALUE as UAT; no environment isolation

5. **`config/p-az-app01/config/accountmanagementapi/accountmanagementapi.properties`**:
   - Production KYC Azure AD OAuth2 client secret (same value repeated in multiple files)

All the above are duplicated across all 21+ production server config directories.

### Other Security Observations
- CBTS production service accessed via HTTP (`http://ppazp.nam.wirecard.sys:9443`) — **production financial service without TLS encryption on internal network**
- `debug.session.output=false` — explicitly disabled (correct for production)
- `addFund.bcc.email=addfundsdisclosures@citi.com` — Citi email domain used in production Onbe config (legacy Citi/Wirecard relationship artifact)
- `disclaimer.filter.text.list` contains `citiprepaid`, `citibank`, `citiprepaid` — confirms legacy Citi branding still filtered in production

## Technical Debt
- **Production credentials in plaintext properties files** — most critical technical debt item
- **Java 7 binary in production repo** — EOL since April 2015; any service running JDK 7 is critically vulnerable
- **JDK 8 in production** — Java 8 extended support only; TLS 1.3 not natively supported
- **Tomcat 8.5.57 EOL** (August 2024)
- **CMS GC and PermGen JVM flags** (expected in JAVA_OPTIONS, not visible in this repo but inferred from UAT pattern)
- **`wirecard.sys` DNS in production Azure** — internal infrastructure DNS not yet migrated to post-Wirecard naming
- **ERB template alongside raw config** — mixed CM approaches
- **29 server config directories** — no templating or dynamic generation; all maintained manually
- **`CardNotification-UAT.properties` in PROD folder** — UAT config file committed to production
- **IVR `appKey` shared with UAT** — no secret rotation or environment isolation

## Gen-3 Migration Requirements (Priority Order)

**IMMEDIATE (before any migration work):**
1. **Rotate all production credentials** that are committed to this repository
2. **Move all production secrets to Azure Key Vault** — use Spring Cloud Azure Key Vault integration for properties injection
3. **Remove secrets from Git history** (git-filter-repo or BFG Repo Cleaner)

**Short-term:**
4. Upgrade JDK to 17 or 21 (critical security — remove Java 7 entirely)
5. Upgrade Tomcat to 10.x or migrate to Spring Boot embedded
6. Enable TLS for CBTS internal traffic
7. Isolate IVR appKey per environment (generate unique keys per env)

**Medium-term:**
8. Containerise services (Docker → AKS or Azure Container Apps)
9. Replace externalized `.properties` files with Kubernetes ConfigMaps/Secrets or Azure App Configuration
10. Replace IBM MQ with Azure Service Bus
11. Automate config deployment (eliminate 29-server manual updates)
12. Migrate from `wirecard.sys` internal DNS to cloud-native service discovery

## Code-Level Risks
- Multiple config properties files contain the same credential values (CBTS credentials appear in `oneplatform/`, `csa/`, and potentially `cz/`) — rotation requires finding and updating all occurrences across 29 server directories = 29 × N files
- `df.mq.credentials=` blank in production — if MQ authentication is actually disabled in production, this is a critical financial infrastructure exposure
- `addfundsdisclosures@citi.com` email in production config — legacy Citi email address; any Citi decommission of this address would silently break add-funds disclosure notifications
- Biocatch `riskScoreToDeny=1000` — maximum risk score; if BioCatch API is unavailable and fails open (no deny), fraud scoring is bypassed entirely; failover policy not visible in this config
