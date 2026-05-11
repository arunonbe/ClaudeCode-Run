# client-api-v4_TESTING_AUTO — Data Architect View

## Data Stores

This repository is a test automation client — it has **no server-side data stores** of its own. It does not implement a database, cache, message queue, or file storage layer.

Data persistence occurs entirely within the remote **Client API v4** service at `webservice-qa.wirecard.com:4005`. The test suite interacts with that service via SOAP over HTTPS and reads response payloads in-memory only; no response data is persisted locally.

The repository contains **static SOAP XML fixture files** (`SoapRequest/*.xml`) which constitute the only local data artifacts. These files are read at test runtime and sent as HTTP request bodies.

## Schema & Tables

No database schema is defined or referenced within this repository.

The SOAP request structures imply the following logical data model on the server side (inferred from XML namespaces and field names):

**Namespace**: `http://ws.clientapi.one.ecount.com/v4` / `http://request.clientapi.one.ecount.com/v4`

| Logical Entity | Key Fields Observed in Fixtures |
|---|---|
| Fund Load Request | region_id, package_id, program_id, promotion_id, transaction_id, amount, comment, reference_1..4 |
| Request Status Query | region_id, package_id, program_id, promotion_id, transaction_id |
| Account Status Update | region_id, package_id, program_id, transaction_id, reference_1, status (e.g., CLOSED) |
| Registration Update | region_id, package_id, program_id, transaction_id, address (4 lines, city, state, country, postal), name (first/middle/last), home/business/mobile phone, ssn, date_of_birth, e_mail |

## Sensitive Data Handling

### CRITICAL FINDING — SSN in Version Control

**File**: `SoapRequest/UpdateRegV4.xml`, element `<v41:ssn>`
A 9-digit numeric value consistent with a Social Security Number format is committed in plaintext to this Git repository. SSNs are classified as sensitive PII under GLBA, CCPA, and multiple state laws. This value must be:
1. Immediately assessed to determine if it is real or synthetic.
2. Removed from the Git history (not merely deleted from HEAD) using `git filter-repo` or equivalent.
3. If real: treated as a PII breach and reported per Onbe incident response procedures.

**Note**: The actual SSN value is not reproduced in this report.

### HIGH FINDING — Personal Email Address in Test Fixture

**File**: `SoapRequest/UpdateRegV4.xml`, element `<v41:e_mail>`
A named Onbe employee's corporate email address is committed as test data. Under GDPR Article 5(1)(c) (data minimisation) and CCPA, identifiable personal data should not be committed to source repositories. Replace with a synthetic address (e.g., `test.user@example.com`).

### HIGH FINDING — Personal Email Address in Source Code

**File**: `src/JsonFiles/XmltoJson.java`, within an inline string literal
A named external Wirecard employee's email address (`himanshu.goyal@external.wirecard.com`) is hard-coded in a SOAP template string. This should be replaced with a synthetic address and the named individual should be notified per GDPR/CCPA obligations if applicable.

### HIGH FINDING — Plaintext Credentials in Maven settings.xml

**File**: `.mvn/wrapper/settings.xml`
Three sets of server credentials (username/password pairs) for Nexus Maven repository servers are committed in plaintext:
- Server ID `wirecard-mavenproxy-repository` — plaintext username and password present
- Server ID `nexus-qa` — plaintext username and password present
- Server ID `ecount.release` and `ecount.snapshot` — plaintext username and password present

Passwords are not reproduced here. These must be rotated immediately and removed from Git history. Credential storage in source control violates PCI DSS Requirement 8.2.1 and Onbe security policy.

### OBSERVATION — Package IDs in Fixture Files

`package_id` values (e.g., `0401500700051334`, `0401500700051335`) are committed in the SOAP fixtures. These appear to be test account identifiers. If these correspond to real card accounts (even in QA), they constitute account reference data and should be evaluated for sensitivity.

## Encryption & Protection

- The SOAP endpoint uses HTTPS (`https://webservice-qa.wirecard.com:4005/`), so data is encrypted in transit during test execution.
- There is no encryption of data at rest within this repository. All fixture data is plaintext.
- No tokenization, masking, or pseudonymization is applied to any values in the fixture files.
- The `settings.xml` credential handling uses no secrets management integration (e.g., no HashiCorp Vault, AWS Secrets Manager, or environment variable substitution) for the three plaintext passwords. The GitHub token is correctly sourced from `${env.GITHUB_TOKEN}`.

## Data Flow

```
Test Runner (local/CI)
  |
  +--> Reads SoapRequest/*.xml (fixture files, plaintext, from local filesystem)
  |
  +--> Constructs HTTP POST request with XML body
  |         HTTPS (TLS) in transit
  +--> webservice-qa.wirecard.com:4005/clientapiws/services/ClientApiWebServices/v4
  |
  +--> Receives XML SOAP response
  |
  +--> Extracts ns2:description string in-memory
  |
  +--> Asserts PROCESSED_SUCCESSFULLY (no data persisted locally)
```

No data is written to disk by the test code. RestAssured logs request/response to stdout (`.log().all()`), which may expose sensitive values in CI pipeline logs.

## Data Quality & Retention

- **No data quality controls**: Test fixtures use hardcoded transaction IDs that are not regenerated between runs. Duplicate transaction IDs will cause test failures unless the API supports idempotent re-submission.
- **No data retention policy**: As a test automation repository, no formal retention policy is defined. The committed PII/sensitive data (SSN, email) in fixture files effectively has the retention lifetime of the Git repository and all its clones.
- **Git history retention**: Even if sensitive values are deleted from the current HEAD, they remain in Git history until the history is rewritten.

## Compliance Gaps

| Gap | Regulation | Severity |
|---|---|---|
| SSN committed to source control | GLBA, CCPA, state PII laws | Critical |
| Employee PII (email) in fixture | GDPR Art. 5, CCPA | High |
| Employee PII (email) in source code | GDPR Art. 5, CCPA | High |
| Plaintext credentials in settings.xml | PCI DSS Req 8.2, security policy | High |
| No masking of account identifiers in fixtures | PCI DSS (if PANs present), internal policy | Medium |
| CI logs expose full SOAP request/response (`.log().all()`) | PCI DSS Req 10, internal log management | Medium |
| No test data lifecycle / anonymization strategy | GDPR Art. 25 (Privacy by Design) | Medium |
