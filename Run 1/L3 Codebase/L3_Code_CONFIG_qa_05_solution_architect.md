# Solution Architect View — CONFIG_qa

## Technical Architecture
Same Gen-2 Tomcat externalized-configuration pattern as DEV. Key technical differentiator: automated GitLab CI config deployment pipeline (`.gitlab-ci.yml`). QA also has more complete datasource configuration than DEV, including Great Plains, eCount, and WebCert/Omaha datasources.

### Additional QA-specific Patterns
- **BioCatch fraud scoring**: Active in QA (`biocatch.switch=Y`); REST API call to BioCatch test endpoint per login/enrollment
- **MFA variant config**: Two enrollment config files (`applicationContext-enrollment.properties` and `applicationContext-enrollment.mfaOn.properties`) — supports toggling MFA for test scenarios
- **Client backup config**: `cz/clientzonebackup.properties` — manual backup config file suggesting rollback practices

## API Surface
None — configuration repo only.

## Security Posture

### Hardcoded Secrets Found (locations noted, values not reproduced)

1. **`config/q-na-app01/config/cbaseapp-ds.properties`** — SQL Server username and password (same username/password pattern as DEV)
2. **`config/q-na-app01/config/oneplatform/applicationContext-oneplatform.properties`**:
   - CBTS service username and password (same values as DEV — shared credential)
   - Google reCAPTCHA site key and secret (same values as DEV — shared credential)
   - KYC Microsoft Azure AD OAuth client secret (same values as DEV — shared credential)
   - Western Union static key (same value as DEV — shared credential)
   - BioCatch customer ID (test value)
3. **`config/q-na-app01/config/dfapiclient/jms.properties`** — IBM MQ principal (`df.mq.principal=prepaid`); blank password field
4. **`config/q-na-app01/config/cardnotification/CardNotification.properties`** — SAP Mobile Services username and password for SMS gateway
5. **`config/q-na-app01/config/csa/applicationContext-csa.properties`** — CBTS username/password, KYC client secret

### Security Observations
- `mfaSwitch=ON` in ClientZone (QA has better MFA posture than DEV)
- `mfa.required=N` in OnePlatform — MFA disabled for automation convenience
- CBTS accessed via HTTP (`http://q-na-app08:9443`) in some configs — should be HTTPS
- Multiple secrets shared between DEV and QA (same values) — violates environment isolation principle

## Technical Debt
- Feature branch (`SQ-4057-deploy-configuration-files`) referenced in `.gitlab-ci.yml` — using a non-master branch for production-path automation is a stability risk
- JDK binaries in Git (large binary artifacts)
- Same credential values across DEV and QA for CBTS, reCAPTCHA, KYC — no environment-specific rotation
- `clientzonebackup.properties` — ad hoc backup file in source control
- Blank MQ password field (`df.mq.credentials=`) — ambiguous configuration state
- No Filebeat input YAML files found in QA config repo — log visibility gap if not managed separately

## Gen-3 Migration Requirements
Same as DEV, plus:
1. Resolve feature-branch ci-templates reference to master/tag before Gen-3 pipeline work
2. Migrate BioCatch integration to cloud-native secrets and configuration
3. Create distinct credentials per environment (DEV, QA, UAT, PROD should have unique CBTS/reCAPTCHA/KYC credentials)
4. Add Filebeat (or replacement) input configuration if QA log shipping is not managed elsewhere
5. Implement automated config deploy with secrets injection from vault (replacing plaintext file approach)

## Code-Level Risks
- `westernUnion.statickey=cy*$s19kup` — same value as DEV; Western Union signing key should be environment-specific
- Multiple `#backup` and commented-out URL blocks in config files increase maintenance error risk
- `contactus.recipientEmail=gaurav.sharma@onbe.com` — employee email in committed config; PII in source control; should use a team alias
