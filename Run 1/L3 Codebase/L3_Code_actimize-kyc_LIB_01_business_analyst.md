# actimize-kyc_LIB — Business Analyst View

## Business Purpose

`actimize-kyc_LIB` is a shared Java library that provides a pre-compiled, schema-bound client interface to the **NICE Actimize KYC (Know Your Customer) web service** operated by Fortent (the legacy Actimize/Fortent platform, endpoint namespace `http://webservices.kyc.fortent.com/`). The library encapsulates the XML/SOAP data types required to call the remote KYC Check Service and is distributed as a Maven artifact (`com.ecount.actimizekyc:actimizekyc:1.0`) for consumption by other Onbe/eCount platform services (formerly operating under the "eCount" brand). It does not contain business logic itself; it is a typed API stub and compiled schema binding.

## Business Capabilities

The library exposes — via the compiled `KycCheckServiceXmlBeans.jar` and the governing `KycCheckService.xsd` schema — the following remote KYC service operations (defined in `KycCheckServiceSIT.wsdl`):

| Operation | Business Function |
|---|---|
| `initiateCheck` | Submit a new KYC check for an individual or organisation; triggers CIP and/or CDD screening |
| `initiateBatch` | Submit a bulk KYC screening file (file name + base-64 contents + parameters map) |
| `updateCheck` | Amend customer details on an in-progress check |
| `scoreCheck` | Request a risk score calculation with primary/secondary watchlist match indication |
| `completeCheck` | Finalise a check with analyst recommendation, screening status, and optional rescreening override |
| `getCheckSummaries` | Retrieve paginated historical check summaries for a customer |
| `getRiskCategory` | Look up current risk category for one or more customer IDs |
| `getRiskCategoryChanges` | Poll for risk category changes within a date-time range |
| `retrieveCheckReport` | Retrieve the full check report document for a completed check |
| `retrieveCheckCDDSearchWatchlistResults` | Retrieve paginated CDD watchlist match results, sortable by relevance or name |
| `escalateCheck` | Escalate an in-progress check to a named manager |
| `reassignCheck` | Reassign an in-progress check to a different analyst |

## Business Entities

All entities are derived from the XML Schema (`KycCheckService.xsd`):

- **`details`** (XSD line 462–483): Core customer profile carrying `customerId`, `personName` (first/middle/last), `dateOfBirth`, `idType` + `idNumber`, `address`, phone numbers, `nationality`, `lineOfBusiness`, `kycRationale`, `individual` flag, `accountNumbers[]`, and `otherGeographies[]`.
- **`address`**: `streetAddress`, `city`, `state`, `postalCode`, `country`.
- **`personName`**: `firstName`, `middleName`, `lastName`.
- **`cipResult`** (XSD line 526–540): CIP (Customer Identification Program) verification outcome covering `verifiedFields`, `notVerifiedFields`, `failedFields`, SSN-specific flags (`isSsnInDeathRecord`, `isSsnIssuedBeforeDOB`), and address-risk flags (`isHighRiskAddress`, `isMailDropAddress`).
- **`cddSearchWatchlistMatch`** (XSD line 328–351): Watchlist hit record containing entity name variants (first/middle/last/org), `dateOfBirth`, `placeOfBirth`, `country`, `countryOfNationality`, `pep` (Politically Exposed Person flag), `listNames[]`, `aliases[]`, `addresses[]`, `role[]`, `idTypeValues[]`, and `category`.
- **`riskCategoryAttributes`**: `customerId` + `category` (risk rating string).
- **`checkSummariesAttributes`** (XSD line 578–592): Historical check record with `checkId`, `customerId`, `customerName`, `finalRiskRating`, `finalRiskScore`, `dateCompleted`, `completedBy`, `nextReviewDate`, `nextReviewInterval`, `kycRationale`.
- **`verboseScoreData`**: Detailed scoring breakdown by group (`riskScoreGroup` → `riskScoreLineItem`) plus primary/secondary CDD match attribute structures.
- **`kvPair`**: Generic key-value extensibility pair used throughout for custom attributes and request metadata.

## Business Rules & Validations

Evidence from `KycCheckService.xsd` and sample message files:

1. **CIP vs CDD flags are mandatory and mutually-selectable**: `initiateCheck` requires explicit `performCDD` (boolean) and `performCIP` (boolean) flags on every call (XSD line 455–457). The sample request (`artifacts/checkapi_request`) shows `performCDD=false`, `performCIP=true` as a valid combination.
2. **Identity document type is restricted to a single profile entry**: The `kyc_profile` SQL inserts in all three environments hard-code `id_type = 'Social Security No.'`, constraining identity verification to US SSN only within the current profile configuration.
3. **Recommendation values are profile-driven**: `kyc_profile.recommendation_check = 'Approve'` and `recommendation_reason = 'ID Verification Passed'` are pre-configured per environment — the platform auto-applies these for passing checks.
4. **Rescreening override requires justification**: `completeRequest` enforces `reasonForRescreeningOverride` and `reasonForRecommendation` alongside the optional `overrideRescreeningInterval` and `overrideNextReviewDate` (XSD line 261–266).
5. **Name variation search scope is controlled**: `nameVariationOption` enum restricts fuzzy-name search to `broad`, `medium`, or `narrow` — a compliance tuning parameter.
6. **Error taxonomy is strictly enumerated** (`errorType` enum, XSD line 692–713): 18 defined error codes including `AUTHENTICATION_FAILURE`, `PERMISSION_DENIED`, `CHECK_NOT_ACTIVE`, `CHECK_NOT_COMPLETED`, and `RESULTS_NOT_AVAILABLE`. Any integration must handle all 18.
7. **Analyst authorisation is enforced by the remote service**: `reassignCheck` can fail with `NEW_ANALYST_INVALID` or `NEW_ANALYST_NOT_AUTHORIZED`; `escalateCheck` can fail with `INVALID_MANAGER_ID` or `MANAGER_NOT_AUTH`.
8. **CIP result for taxID failure is explicit**: The sample response (`artifacts/checkapi_response`) shows `failedFields/key=taxID` and `cipFailed=1` — the SSN did not match, resulting in `possibleRisk=true`.

## Business Flows

### Individual KYC Onboarding (CIP)
1. Caller populates `details` (customer PII, SSN, address) and submits `initiateCheck` with `performCIP=true`.
2. Remote service returns `checkReference` + `cipResult` (verified/notVerified/failed fields, SSN death-record flags, address-risk flags) and `possibleRisk` boolean.
3. If `cipFailed > 0` or `possibleRisk=true`, analyst reviews in the Actimize platform.
4. Analyst calls `scoreCheck` (supplying watchlist match decisions) to generate `riskScore` + `riskCategory`.
5. Analyst finalises via `completeCheck` supplying recommendation, optional rescreening override, and screening status.
6. Calling system polls `getRiskCategoryChanges` or calls `getRiskCategory` to retrieve the final risk classification.

### CDD (Customer Due Diligence) Watchlist Screening
1. `initiateCheck` with `performCDD=true` triggers watchlist search.
2. Response includes `cddPrimarySearchListMatches` / `cddSecondarySearchListMatches` counts.
3. Analyst reviews matches via `retrieveCheckCDDSearchWatchlistResults` (paginated, sortable).
4. Analyst scores via `scoreCheck` indicating primary/secondary match decisions and reasons.
5. Check completed via `completeCheck`.

### Batch Screening
1. `initiateBatch` accepts a file name, base-64 `inputFileContents`, and a `parametersMap`. Returns a `batchID`.
2. Downstream process monitors batch completion and handles individual check results.

### Management Workflows
- `escalateCheck` → manager review (escalation tracked by `manager` string field).
- `reassignCheck` → workload rebalancing to `newAnalystId`.
- `getCheckSummaries` → audit trail retrieval with pagination (`offset` + `windowSize`).

## Compliance & Regulatory Concerns

This library is the primary integration point for Onbe's compliance with the following frameworks:

- **BSA/AML — CIP (31 CFR 1020.220)**: The `initiateCheck` + `cipResult` flow is the mechanism by which Onbe verifies the identity of customers under the Customer Identification Program. The SSN verification result fields (`isSsnInDeathRecord`, `isSsnIssuedBeforeDOB`, `taxID` failedFields) directly support CIP documentary and non-documentary verification requirements.
- **BSA/AML — CDD Rule (31 CFR 1010.230)**: The `performCDD` flag and `retrieveCheckCDDSearchWatchlistResults` operation support Customer Due Diligence screening against internal and third-party watchlists.
- **OFAC / Sanctions Screening**: The `cddSearchWatchlistMatch.listNames[]` field carries the names of the watchlists matched (e.g., OFAC SDN, EU consolidated, UN). The `pep` boolean flag on each match explicitly identifies Politically Exposed Persons.
- **FINRA / FinCEN — Risk Rating**: `riskCategory` and `riskScore` outputs, plus `nextReviewDate` and `nextReviewInterval`, directly support periodic risk-based review obligations under BSA.
- **Reg E (12 CFR Part 1005)**: KYC gating is a pre-condition for prepaid account issuance; `kyc_profile.id_type = 'Social Security No.'` confirms US-only SSN-based identity verification.
- **GLBA / Privacy**: PII fields transmitted in requests (SSN in `idNumber`, `dateOfBirth`, full name, address) are sent over TLS (HTTPS endpoints in all three `kyc_profile` SQL inserts). However, see Compliance Gaps below.

## Business Risks

1. **Hardcoded credentials in SQL scripts**: All three environment SQL inserts (`kyc_profile_PROD_NA.sql`, `kyc_profile_SIT_NA.sql`, `kyc_profile_UAT_NA.sql`) store `secure_code = 'Prepaid1'` in plaintext inside the repository. If this value is an active service password, it represents a material credential exposure risk.
2. **US-only identity verification**: The `kyc_profile` is configured exclusively for `country_code = 'US'` with `id_type = 'Social Security No.'`. Non-US customers or alternative ID types (passport, ITIN) are not covered by the current profile configuration.
3. **Static version (1.0) with no upgrade path**: The Maven artifact is pinned at version `1.0` with no evidence of versioning strategy. Changes to the Actimize service contract (XSD/WSDL) would require full rebuild and manual re-deployment.
4. **SSN transmitted in plaintext request body**: The sample request (`artifacts/checkapi_request`) shows `idNumber` (SSN `405415342`) and full PII transmitted in SOAP XML. While transport is HTTPS, there is no field-level encryption or masking applied at the library layer.
5. **Test data using real-looking SSN**: The sample request/response pair uses what appears to be a 9-digit SSN value (`405415342`) and the real-looking name "Richard Ammar Chichakli" — a name that appears on OFAC lists. This should be validated as truly synthetic/test data and not live PII.
6. **Single-country, single-profile risk**: The library and its profile scripts support only the US market, creating a migration/expansion gap for any EMEA or LATAM onboarding requirements.
