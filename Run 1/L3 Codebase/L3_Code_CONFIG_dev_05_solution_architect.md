# Solution Architect View — CONFIG_dev

## Technical Architecture
The DEV configuration repository externalises configuration for two generations of service architecture:

**Gen-2 (Legacy Tomcat)**: `.properties` files and Spring XML context files read from `D:\c-base\config\{service}\` at Tomcat startup. Services on `d-na-app01`, `d-na-app02`, `d-na-app03`, `d-na-bat02`.

**Gen-3 (Spring Boot)**: `application.yml` with Spring Boot auto-configuration, resilience4j, HikariCP connection pool, Spring JPA. Service: CBTS on `d-na-app04:9443`.

### Config File Taxonomy
- `*-ds.properties` — JDBC datasource (driver, URL, user, password)
- `applicationContext-*.properties` — Spring XML context property placeholders
- `*.xml` (Spring beans, log4j, web.xml) — XML-based configuration
- `application.yml` — Spring Boot YAML configuration (CBTS only)
- `{SERVICE}.yml` under `filebeat_application.yml/` — Filebeat log input definitions

## API Surface
No APIs are defined in this repository — it is configuration only. The services configured here expose APIs defined in their respective application code repositories.

## Security Posture

### Hardcoded Secrets Found (locations noted, values not reproduced)

1. **`config/d-na-app01/config/cbaseapp-ds.properties`** — SQL Server credentials (username + password in plaintext)
2. **`config/d-na-app01/config/jobsvc-ds.properties`** — SQL Server credentials (username + password in plaintext)
3. **`config/d-na-app04/config/service/cbts/application.yml`**:
   - SQL Server credentials for CBTS database
   - Mailgun SMTP password
   - Cambridge FX partner signature (API signing key)
   - Cambridge FX RCCL client API credentials (ID, code, signature, settlement account ID)
   - Cambridge FX Disney client API credentials (ID, code, signature, settlement account ID)
   - CBTS internal service username and password (used for HTTP basic auth)
4. **`config/d-na-app01/config/oneplatform/applicationContext-oneplatform.properties`**:
   - CBTS service username and password
   - Google reCAPTCHA site key and secret key
   - KYC Microsoft Azure AD OAuth client secret
   - Western Union static key
5. **`config/d-na-app01/config/dfapiclient/jms.properties`** — IBM MQ connection credentials (principal name, blank password field)
6. **`config/d-na-app01/config/csa/applicationContext-csa.properties`** — CBTS username and password; KYC Azure AD client secret

### Other Security Observations
- `mfaSwitch=OFF` in `cz/clientzone.properties` — MFA disabled in DEV for ClientZone
- `mfa.required=N` in enrollment config — MFA disabled in DEV enrollment
- JMX remote management enabled with SSL disabled (`jmxremote.ssl=false`) in JAVA_OPTIONS (UAT repo pattern — same expected in DEV)
- Keystore password present in JAVA_OPTIONS files: `javax.net.ssl.keyStorePassword` and `javax.net.ssl.trustStorePassword` — committed to source control in UAT repo (likely same in DEV)

## Technical Debt
- **JDK 1.7.0.65 binary committed** — Java 7 is EOL since April 2015; severely outdated
- **JDK 1.8 binary committed** — Java 8 extended support ends 2030 for commercial; open source EOL
- **Large binary JDK artifacts in Git** — JDK binaries inflate repository size and complicate cloning
- **Plaintext credentials throughout** — no secret management integration; all secrets in plaintext `.properties` files
- **Commented-out production URLs** in DEV config files — maintenance hazard
- **`ecount-config.xml` referenced but not present** in config repo — externalised config file managed outside this repo
- **Duplicate credential values** across multiple files — DRY violation, creates maintenance inconsistency risk
- **IBM MQ in DEV points to UAT** — data isolation boundary violation
- **Spring XML context config** (`.xml` Spring bean files) — legacy Spring 2.x/3.x pattern; should migrate to annotation/YAML-based configuration

## Gen-3 Migration Requirements
1. **Remove all credentials from config files** — migrate to Azure Key Vault or HashiCorp Vault with Spring Cloud Config or environment variable injection
2. **Remove JDK binaries from Git** — use package manager or Docker base images
3. **Upgrade to JDK 17/21** — required for modern Spring Boot, TLS 1.3, and security patches
4. **Containerise services** — replace `D:\c-base\config\` filesystem dependency with ConfigMaps/Secrets in Kubernetes
5. **Replace IBM MQ** — migrate DFAPI remittance to cloud-native messaging
6. **Replace Strongbox XML-RPC** — migrate to Azure Key Vault or AWS KMS
7. **Replace Director dispatch** — re-architect routing for microservices
8. **Migrate SQL Server to cloud** — Azure SQL or equivalent
9. **Fix DEV/UAT environment boundary** — DEV should not connect to UAT MQ or KYC QA endpoints
10. **Consolidate Spring XML configs to Spring Boot YAML** across all services

## Code-Level Risks
- `df.mq.credentials=` (blank password) in jms.properties — unclear if this is a deliberate empty credential or a config management gap
- `westernUnion.statickey` committed in plaintext — Western Union signing key in source control
- `cbtsClient.Password` appears identically in multiple files — any rotation requires changes in all files simultaneously
- `kyc.ms.client.secret` appears in multiple files — same rotation problem
- CBTS `application.yml` has `show-sql: true` — SQL queries logged to application logs; potential data exposure in log files
