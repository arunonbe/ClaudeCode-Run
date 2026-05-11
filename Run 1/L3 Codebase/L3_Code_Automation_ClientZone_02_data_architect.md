# Automation_ClientZone — Data Architect View

## Data Stores

### 1. Microsoft SQL Server — EcountCore (QA)
- **Connection string** (hardcoded in `framework/DatabaseConnection.java` line 21):
  `jdbc:sqlserver://Q-LIS-DB02:2231;instanceName=q-db02\db02;databaseName=EcountCore;sslProtocol=TLSv1.2;sendStringParametersAsUnicode=false;trustServerCertificate=true`
- **Credentials** (hardcoded, plaintext): username `b2cstage`, password `b2cstage`.
- **Driver**: `com.microsoft.sqlserver.jdbc.SQLServerDriver` via `mssql-jdbc 12.8.1.jre11`.
- **Access pattern**: Read-only `ResultSet.TYPE_SCROLL_INSENSITIVE` / `CONCUR_READ_ONLY` via JDBC `Statement`. Direct SQL string concatenation — no prepared statements used anywhere in this codebase.

### 2. JSON Test Data Files (File System)
Located at `src/test/resources/data/`:
- `clientzone.json` — ClientZone QA credentials and email addresses.
- `mypaymentvault.json` — MPV QA credentials, card numbers, CVV values, account numbers, routing numbers, SSN, DOB.
- `wizard.json` — Wizard/Onbe admin credentials, MPV URL, existing program ID.
- `idpassme.json` — Base URL only (no credential data).

These files are read at runtime by `framework/TestData.java` using Jackson `ObjectMapper`, deserialized into `framework/DataMapper.java` POJOs. No encryption or masking is applied.

### 3. Web Application State (Browser)
The Playwright browser session holds session cookies and tokens for authenticated ClientZone, MPV, Wizard, and IdPassMe sessions. Sessions are created fresh per scenario (via `framework/Hook.java` `@Before` → `PlaywrightManager.startPlaywright()`) and destroyed after each scenario (`@After` → `stopPlaywright()`). No session state persists between scenarios.

## Schema & Tables

All database interaction is concentrated in `clientzone/steps/SearchableAddendaSteps.java` and `clientzone/steps/LoginSteps.java`. The following tables in the `EcountCore` database are queried:

| Table | Schema | Purpose in Tests |
|---|---|---|
| `core_device_dda` | `EcountCore.dbo` | DDA account records; joined on `owner_id` to `core_member_addenda`; `dda.number` used as program-prefixed account identifier |
| `core_member_addenda` | `EcountCore.dbo` | Addenda/memo values per account; `field_type`, `value`, `owner_id` columns referenced |
| `fdr_profile_transaction_field_type` | `EcountCore.dbo` | Addenda field type definitions; `id` joined to `core_member_addenda.field_type`; `display_label`, `searchable` columns referenced |
| `fdr_card_account` | `EcountCore.dbo` | Card-to-DDA mapping; `dda_number`, `card_id` columns |
| `fdr_card_account_detail` | `EcountCore.dbo` | Card account detail; `card_id`, `block_code` columns |
| `core_device_eCard_extended` | `EcountCore.dbo` | Card role metadata; `card.card_id`, `role` (0=primary, 1=secondary, 2=temporary) |
| `fdr_profile_block_code` | `EcountCore.dbo` | Block code lookup; `id`, `name` columns |
| `app_profile_addenda` | (implied EcountCore) | Program-level addenda profile; `program_id`, `searchable`, `display_label` columns |
| `core_device` | `EcountCore.dbo` | Device type filter; `type_id LIKE '47%'` used to exclude certain account types |
| `user_validation_information` | (implied EcountCore) | Login audit table; queried by `iaffiliate_id = '104010929'` in `LoginSteps.java` line 25 (commented out in runtime but query is defined) |

Key SQL queries constructed in `SearchableAddendaSteps.java`:
- **Addenda dropdown validation query** (line 126): `select display_label from app_profile_addenda where program_id = '04014978' and searchable = 1`
- **Primary count query** (lines 198–208): Multi-join across `core_device_dda`, `core_member_addenda`, `fdr_profile_transaction_field_type`, `fdr_card_account`, `fdr_card_account_detail`, `core_device_eCard_extended`, `fdr_profile_block_code` — WHERE `addenda.value IN (?)` AND `dda.number LIKE ?%`
- **Secondary card role query** (lines 215–226): Same multi-join with additional `cde.role = 1` filter.
- **DDA-only accounts query** (lines 235–242): `core_device_dda` JOIN `core_member_addenda` WHERE `dda.owner_id NOT IN (select owner_id from core_device where type_id LIKE '47%')`.
- **Distinct DDA count query** (lines 247–257): DISTINCT `dda.number` variant.

## Sensitive Data Handling

### Hardcoded Credentials (Critical Risk)
1. **Database credentials** hardcoded in `framework/DatabaseConnection.java` line 25:
   - Username: `b2cstage`
   - Password: `b2cstage`
   - Server: `Q-LIS-DB02:2231` (internal QA SQL Server)
   - These are committed to source control in plain text.

2. **Application credentials** in `src/test/resources/data/mypaymentvault.json`:
   - Card numbers: 16-digit values (BIN 544544x) — e.g., `"5445446588231925"`, `"5445446583086258"`, and 12 more.
   - CVV values: `"944"`, `"930"`, `"109"`, `"447"`, `"210"`, `"568"`, `"974"`, `"637"`, `"283"`, `"126"`, `"018"`, `"314"`.
   - SSN: `"987654321"`.
   - DOB: `"06-04-1985"`, `"06041985"`.
   - Account number: `"7835676345435"`.
   - Routing number: `"021000021"`.
   - PIN: `"1247"`, `"1234"`.

3. **Application credentials** in `src/test/resources/data/clientzone.json`:
   - `uname: "bhagyashree.bijagarni@onbe.com"`, `pwd: "Bhagy@nandache131"` — a named Onbe employee's actual email and what appears to be a real password.

4. **Application credentials** in `src/test/resources/data/wizard.json`:
   - Internal app URL `q-na-app05.nam.wirecard.sys:8090` and MPV URL `mypaymentvault.qa.onbe.dev` with credentials.

5. **Hardcoded in SSLoginSteps.java** (lines 148, 170–171): Username `"Bhagyashree"` and password `"Passcode2"` hardcoded directly in step definitions.

6. **Hardcoded address in RegistrationPage.java** (line 78): `input[value='1300 fayette street']`, city `Conshohocken`, zip `19428`, email `rashmi1dhandar@gmail.com`, phones `6106057162/6106057163` — PII hardcoded in page object locators.

## Encryption & Protection

- **TLS on DB connection**: `sslProtocol=TLSv1.2` specified but `trustServerCertificate=true` disables certificate validation — man-in-the-middle risk on the DB connection.
- **HTTPS on Playwright**: `setIgnoreHTTPSErrors(true)` in `PlaywrightManager.java` line 38 — SSL certificate errors are silently ignored for all browser connections. This means invalid or self-signed certificates on test environments do not fail the tests.
- **No credential encryption**: All test data JSON files are unencrypted plaintext. No secrets manager (Vault, AWS SSM, etc.) is used. No `.env` or environment-injection pattern for sensitive values.
- **No data masking in reports**: ExtentReports (`target/TestResults.html`) will capture any text printed via `System.out.println()`, which includes query results and addenda values from DB calls. Screenshots in `target/SparkReport/screenshots/` may capture card numbers or account details visible in the browser.

## Data Flow

```
Test Execution
    |
    ├── TestData.get("mypaymentvault.json")
    │       → ObjectMapper reads src/test/resources/data/*.json
    │       → DataMapper POJO (credentials, card numbers, CVV, SSN, DOB)
    │
    ├── PlaywrightManager (browser session)
    │       → HTTP/HTTPS to MPV / CZ / Wizard / IdPassMe
    │       → Fills credentials, card numbers, PII into browser forms
    │       → Assertions on UI responses
    │
    └── DatabaseConnection.jdbcconnection(query)
            → JDBC to Q-LIS-DB02:2231 / EcountCore
            → Reads: core_device_dda, fdr_card_account, core_member_addenda,
                     fdr_profile_transaction_field_type, core_device_eCard_extended,
                     fdr_profile_block_code, app_profile_addenda
            → ResultSet compared against UI record counts
```

## Data Quality & Retention

- **Test data environment**: All `baseUrl` values point to QA environments (`qa.idpassme.com`, `mypaymentvault.qa.onbe.dev`, internal `.wirecard.sys` hosts). No production URLs are referenced.
- **Card number BIN analysis**: BIN `544544` (Mastercard prepaid) — these are Onbe QA test cards. BIN `419` (Visa) and `522480` (Mastercard) also appear in IdPassMe test data.
- **Static test data**: No dynamic test data generation; all values are static in JSON. This creates dependencies on specific QA accounts existing in the database (e.g., `RPautomation6`, `2531ww`, `RPauto1221`).
- **No cleanup/teardown**: No `@After` hook deletes created data. Registration tests that create accounts will accumulate test accounts in QA.
- **Test output**: HTML report at `target/TestResults.html`; screenshots at `target/SparkReport/screenshots/`. These directories are in the project root and should be excluded from version control (`.gitignore` should cover `target/`).
- **Retention**: No explicit retention policy for test reports or screenshots. If stored in a CI artifact store, screenshots containing card numbers or PII should be governed by a retention policy.

## Compliance Gaps

1. **PCI DSS Req 3.3 — SAD Storage**: CVV/CVC values (`944`, `930`, `109`, etc.) are stored in `mypaymentvault.json`. Even if these are test cards, the practice of storing CVV in source control is a violation pattern that should be remediated with synthetic values or a secrets manager.
2. **PCI DSS Req 6.2 / 6.3 — SQL Injection**: All SQL queries in `SearchableAddendaSteps.java` are constructed via string concatenation with test-data-supplied values (e.g., `AddendaValue`, `ProgramId`). No parameterized queries or prepared statements are used. Although test data is controlled, this pattern is a code-quality risk and teaches an unsafe pattern.
3. **PCI DSS Req 2.2 / Credential Management**: Database credentials (`b2cstage`/`b2cstage`) and application credentials are stored in source code. Should be externalized to environment variables or a secrets manager.
4. **CCPA/GDPR — PII in Source Control**: SSN, DOB, real name, address, email (`rashmi1dhandar@gmail.com`), phone numbers are present in source-controlled files. These constitute personal data and should not be stored in version-controlled repositories without proper data governance.
5. **GLBA — Financial Data**: Bank account number (`7835676345435`) and routing number (`021000021`) are stored in `mypaymentvault.json`. These constitute non-public personal financial information (NPPI) under GLBA.
6. **Trust Server Certificate**: `trustServerCertificate=true` on the JDBC connection bypasses SQL Server certificate validation — this should be replaced with a properly trusted certificate in QA environments.
7. **Ignore HTTPS Errors**: `setIgnoreHTTPSErrors(true)` in Playwright prevents detection of certificate misconfiguration on application under test.
