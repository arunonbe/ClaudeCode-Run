# actimize-kyc_LIB — Data Architect View

## Data Stores

### Remote Service (Actimize/Fortent KYC Platform)
The library is a client-side stub. All authoritative KYC data is stored in the remote Actimize/Fortent application server, accessed via SOAP over HTTPS. The library itself contains no local data store. The remote endpoint hostnames per environment are:

| Environment | Endpoint |
|---|---|
| SIT | `https://isgswcse46i.nam.nsroot.net:8181/kycapp/KycCheckService` |
| UAT | `https://icgmwcos1u.nam.nsroot.net:8181/kycapp/KycCheckService` |
| PROD | `https://icgmwcos1p.nam.nsroot.net:8181/kycapp/KycCheckService` |

All three are internal `.nam.nsroot.net` hostnames on port 8181 (HTTPS), suggesting a private corporate network or VPN-accessible environment.

### Local Relational Database: `ecountcore.kyc_profile`
Evidence: `artifacts/PROD certificate/kyc_profile_PROD_NA.sql`, `artifacts/SIT certificate/kyc_profile_SIT_NA.sql`, `artifacts/UAT certificate/kyc_profile_UAT_NA.sql`

This is the only explicit table definition in the repository. The INSERT statements reveal the schema:

```sql
-- Table: ecountcore.kyc_profile
INSERT INTO kyc_profile (
  country_code,        -- VARCHAR, e.g. 'US'
  country,             -- VARCHAR, e.g. 'United States'
  id_type,             -- VARCHAR, e.g. 'Social Security No.'
  recommendation_check,-- VARCHAR, e.g. 'Approve'
  recommendation_reason,-- VARCHAR, e.g. 'ID Verification Passed'
  webservice_url,      -- VARCHAR, HTTPS endpoint URL
  secure_id,           -- VARCHAR, e.g. 'PREPAID' (service username/client ID)
  secure_code          -- VARCHAR, plaintext password/secret ('Prepaid1' in all envs)
)
```

Database: `ecountcore` (Microsoft SQL Server — `use ecountcore; go` syntax, file: `kyc_profile_PROD_NA.sql` line 1–2).

### Artifact Storage
- `KycCheckServiceXmlBeans.jar` — compiled XmlBeans JAR, checked into the repository root and into `artifacts/`.
- Maven repository: `http://ecsvn.office.ecount.com:8080/mvn/release` — internal Nexus/Maven repo; referenced in `deploy kycbean jar to repository.txt`.
- Java KeyStore (JKS): `cacerts` file on the deployment JVM (`D:\c-base\opt\jdk1.6.0_16\jre\lib\security\cacerts`) — contains 72 CA trust entries (documented in `artifacts/cacertslist.txt`). Per-environment server certificates (`artifacts/*/servercert.bin`) are imported into this truststore via `keytool`.

## Schema & Tables

### `ecountcore.kyc_profile`
Full column inventory derived from SQL INSERT statements (all three environment files):

| Column | Observed Value (PROD) | Purpose |
|---|---|---|
| `country_code` | `US` | ISO country code for profile selection |
| `country` | `United States` | Human-readable country name |
| `id_type` | `Social Security No.` | Identity document type used for CIP |
| `recommendation_check` | `Approve` | Default recommendation applied on pass |
| `recommendation_reason` | `ID Verification Passed` | Default reason text |
| `webservice_url` | `https://icgmwcos1p.nam.nsroot.net:8181/kycapp/KycCheckService` | Remote KYC service endpoint |
| `secure_id` | `PREPAID` | Service authentication identifier/client ID |
| `secure_code` | `Prepaid1` | **Plaintext service credential/password** |

No DDL (CREATE TABLE) is present in the repository — only INSERT statements. Table structure is inferred from the column list in the INSERT.

### XSD-Defined Message Schema (`KycCheckService.xsd`)
The XSD defines the full wire-format schema. Key complex types and their data fields:

**`details`** (XSD lines 462–483) — Customer PII payload:
- `customerId` (xs:string) — internal Onbe customer GUID
- `personName` → `firstName`, `middleName`, `lastName`
- `dateOfBirth` (xs:dateTime)
- `idNumber` (xs:string) — SSN or other government ID
- `idType` (xs:string) — matches `kyc_profile.id_type`
- `address` → `streetAddress`, `city`, `state`, `postalCode`, `country`
- `homePhone`, `businessPhone`
- `nationality`
- `organizationName` (for non-individual entities)
- `lineOfBusiness`, `kycRationale`
- `accountNumbers[]` (unbounded)
- `otherGeographies[]` (unbounded)

**`cipResult`** (XSD lines 526–540):
- `verifiedFields[]`, `notVerifiedFields[]`, `failedFields[]` (kvPair)
- `isSsnInDeathRecord` (cipResultValue enum: yes/no/data_unavailable)
- `isSsnIssuedBeforeDOB` (cipResultValue enum)
- `isHighRiskAddress`, `isMailDropAddress`, `isBusinessAddress`, `isCurrentAddress`, `isDeliverableAddress`, `isPropertyOwnerOfAddress`

**`cddSearchWatchlistMatch`** (XSD lines 328–351):
- `entityId`, `firstName`, `middleName`, `lastName`, `orgnaizationName` [sic — typo in XSD]
- `dateOfBirth`, `placeOfBirth`, `country`, `countryOfNationality`
- `pep` (xs:boolean)
- `category`, `listNames[]`, `aliases[]`, `addresses[]`, `role[]`
- `idTypeValues[]` (idTypeValue: type + value)
- `additionalInformation`, `title`, `nameVariations[]`

**`checkSummariesAttributes`** (XSD lines 578–592):
- `checkId`, `displayCheckId`, `customerId`, `customerName`
- `finalRiskRating`, `finalRiskScore` (xs:int)
- `dateCompleted` (xs:dateTime), `completedBy`
- `nextReviewDate` (xs:dateTime), `nextReviewInterval` (xs:int)
- `kycRationale`

**`scoreResponse`** (XSD lines 156–166):
- `riskCategory` (xs:string), `riskScore` (xs:int)
- `verboseScoreData` → `riskScoreDetail` → `riskScoreGroups[]` → `riskScoreLineItems[]`

## Sensitive Data Handling

Data classified as sensitive by PCI DSS, GLBA, and BSA/CIP rules present in this library:

| Data Element | Location | Sensitivity |
|---|---|---|
| SSN (`idNumber`) | `details` complex type (XSD line 473); sample request `artifacts/checkapi_request` line 23 | PII — government ID; regulated under GLBA, BSA CIP |
| Date of birth | `details.dateOfBirth` (XSD line 468) | PII — GLBA, CCPA |
| Full name | `personName` (XSD lines 495–501) | PII |
| Home/business address | `address` (XSD lines 485–493) | PII — GLBA, CCPA |
| Phone numbers | `details.homePhone`, `details.businessPhone` | PII |
| `secure_code` ('Prepaid1') | `kyc_profile_*.sql` line 5 (all three environments) | **Credential — active service secret; HIGH RISK** |
| `checkReference` (GUID) | `initiateResponse.checkReference`; sample response line 33 | Internal reference; low sensitivity alone |
| Customer GUID | `details.customerId`; sample files | Internal identifier; links to PII records |

The SSN value `405415342` present in `artifacts/checkapi_request` (line 23) and echoed in `artifacts/checkapi_response` (line 19) must be confirmed as a synthetic test SSN. The name "Richard Ammar Chichakli" associated with it is publicly known as an OFAC-listed individual — the test data appears to have been deliberately constructed against a known watchlist hit.

## Encryption & Protection

**Transport security**: All three `kyc_profile` SQL scripts specify HTTPS endpoints on port 8181 — TLS is enforced at the network layer for data in transit.

**Certificate management**: Per-environment server certificates (`servercert.bin`) are manually imported into the JVM `cacerts` truststore using `keytool` commands documented in `artifacts/keytool security cer add.txt` (lines 3–11). The instructions reference JDK 1.6.0_16, indicating a very old TLS stack. The default keystore password is the well-known default `changeit` (line 5 of the keytool instructions).

**At-rest encryption**: No evidence of encryption for the `kyc_profile` database table. `secure_code` is stored as plaintext in the database and in Git.

**Field-level encryption**: None. The XmlBeans-compiled types transmit `idNumber` (SSN), `dateOfBirth`, and other PII as unmasked xs:string/xs:dateTime values.

**Credential storage**: `secure_id = 'PREPAID'` and `secure_code = 'Prepaid1'` are hardcoded in all three SQL files committed to the Git repository — no secrets manager, environment variable injection, or vault reference is used.

## Data Flow

```
Onbe Application
    │
    ├── reads kyc_profile from ecountcore DB
    │       (webservice_url, secure_id, secure_code)
    │
    ├── constructs SOAP request using KycCheckServiceXmlBeans.jar
    │       (customer PII: name, SSN, DOB, address → details object)
    │
    └── HTTPS POST → Actimize KYC remote endpoint
            │
            └── returns checkReference, cipResult, riskScore, watchlist matches
                    │
                    └── Onbe Application processes result, stores
                        check outcomes (riskCategory, nextReviewDate)
```

The library provides the Java types for steps 2–3 only. Persistence of results is handled by the consuming application (not in this repo).

## Data Quality & Retention

- **No retention policy**: The repository contains no retention logic, data lifecycle rules, or archival configuration.
- **No schema versioning**: Single version (1.0) of the XmlBeans JAR with no migration path.
- **Pagination is supported but not enforced**: `getCheckSummaries` and `retrieveCheckCDDSearchWatchlistResults` support `offset`/`windowSize`/`count` parameters, but callers are responsible for correct pagination to avoid incomplete result sets.
- **Date-time precision risk**: `riskCategoryChangesRequest` uses `xs:dateTime` for `since`/`until` ranges — timezone handling must be consistent between caller and service (the sample response shows timezone offset inconsistency: request sent `1959-03-29T00:00:00.000-04:00`, echoed back as `1959-03-28T23:00:00-05:00`).
- **Typo in XSD**: `cddSearchWatchlistMatch.orgnaizationName` (XSD line 345) is misspelled — should be `organizationName`. This is a data quality defect in the canonical schema.

## Compliance Gaps

1. **Plaintext credential in Git**: `secure_code = 'Prepaid1'` committed across all three environment SQL files. Violates secrets management best practices and potentially PCI DSS Requirement 8.6.3 (protection of passwords).
2. **No field-level masking for SSN at rest or in logs**: The library does not mask or truncate `idNumber` before transmission or logging. Any application-layer logging of the SOAP envelope would expose full SSN.
3. **JDK 1.6 TLS stack**: The keytool instructions reference JDK 1.6.0_16 (circa 2009). TLS 1.0/1.1 may be in use, which is prohibited by PCI DSS v4.0 Requirement 4.2.1 for cardholder data environments. This needs validation.
4. **No data masking in sample artifacts**: `artifacts/checkapi_request` and `artifacts/checkapi_response` contain a 9-digit SSN and full PII stored in Git — a potential privacy violation if these are real data.
5. **No audit logging at the library layer**: No logging framework integration; consuming applications must implement their own audit trails for BSA/SAR reporting obligations.
6. **Single-country profile**: Only `country_code = 'US'` is configured. GDPR/PIPEDA/Quebec Law 25 requirements for non-US customers are not addressed.
