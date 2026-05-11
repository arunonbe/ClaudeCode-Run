# actimize-kyc_LIB — Solution Architect View

## Technical Architecture

`actimize-kyc_LIB` is a **schema-compiled SOAP client library**. It has no runtime application logic, no HTTP client of its own, and no framework dependencies beyond what XmlBeans provides. The architecture is:

```
KycCheckService.xsd (XML Schema)
        │
        │  Apache XmlBeans 2.5.0 scomp tool
        ▼
KycCheckServiceXmlBeans.jar
  └── Generated Java classes (XMLBeans typed document/element types)
       matching all complex types in KycCheckService.xsd:
       - initiateCheck / initiateCheckResponse
       - scoreCheck / scoreCheckResponse
       - completeCheck / completeCheckResponse
       - ... (12 operations total)

KycCheckServiceSIT.wsdl
  └── Describes service binding (KycCheckServicePortBinding)
      and single SOAP endpoint per environment
      (consumed by JAX-WS RI to generate dynamic proxy stubs)

kyc_profile (DB table in ecountcore)
  └── Runtime configuration: endpoint URL + credentials
```

The consuming application is responsible for:
1. Reading `webservice_url`, `secure_id`, `secure_code` from `kyc_profile`.
2. Creating a JAX-WS service proxy pointing to `webservice_url`.
3. Constructing XmlBeans request objects from the generated types in the JAR.
4. Invoking the SOAP operation and deserialising the XmlBeans response types.

This library is not a Spring component, not a microservice, and not a standalone runnable — it is a pure Java library (JAR) providing typed XML bindings.

## API Surface

The full API surface is defined by `KycCheckService.xsd` (740 lines) and bound by `KycCheckServiceSIT.wsdl`. All operations belong to the `KnowYourCustomerCheck` port type at namespace `http://webservices.kyc.fortent.com/`.

### Operations Summary

| Operation | Request Type | Response Type | Key Fields |
|---|---|---|---|
| `initiateCheck` | `initiateRequest` | `initiateResponse` | `details` (PII), `performCDD`, `performCIP` → `checkReference`, `cipResult`, `possibleRisk` |
| `initiateBatch` | `batchInitiateRequest` | `batchInitiateResponse` | `inputFileContents`, `inputFileName`, `parametersMap` → `batchID` |
| `updateCheck` | `updateRequest` | `updateResponse` | `checkReference`, `details` → `checkUpdated` (boolean) |
| `scoreCheck` | `scoreRequest` | `scoreResponse` | `checkReference`, match decisions → `riskScore` (int), `riskCategory`, `verboseScoreData` |
| `completeCheck` | `completeRequest` | `completeResponse` | `checkReference`, `recommendation`, `screeningStatus` → `checkComplete`, `nextReviewDate`, `riskCategory` |
| `escalateCheck` | `escalateRequest` | `escalateResponse` | `checkReference`, `manager` → `success` (boolean) |
| `reassignCheck` | `reassignRequest` | `reassignResponse` | `checkReference`, `newAnalystId` → `reassigned` (boolean) |
| `getCheckSummaries` | `checkSummariesRequest` | `checkSummariesResponse` | `customerId`, `offset`, `windowSize` → `checkSummariesAttributes[]`, `totalCount` |
| `getRiskCategory` | `riskCategoryRequest` | `riskCategoryResponse` | `customerIds[]` → `riskCategoryAttributes[]` (customerId + category) |
| `getRiskCategoryChanges` | `riskCategoryChangesRequest` | `riskCategoryChangesResponse` | `since`, `until` → `riskCategoryAttributes[]` |
| `retrieveCheckReport` | `retrieveReportRequest` | `retrieveReportResponse` | `checkReference` → `report` (string — likely HTML/XML document) |
| `retrieveCheckCDDSearchWatchlistResults` | `retrieveCDDSearchWatchlistResultsRequest` | `retrieveCDDSearchWatchlistResultsResponse` | `checkReference`, `count`, `offset`, `retrievePrimarySearch`, `sortingCriteria` → `cddMatches[]`, `nameVariations[]` |

### Type Hierarchy
All request types extend the abstract `request` type (XSD line 68–72), which carries `keyValues[]` (kvPair) for extensibility metadata. All response types extend the abstract `response` type (XSD lines 97–102), which carries `errors[]` (error: description + errorType) and an echo of the original `request`.

Requests referencing a specific check extend `requestReferencesCheck` → `request` and add `checkReference` (XSD lines 140–148).

### Error Handling Contract
18 enumerated `errorType` values (`KycCheckService.xsd` lines 692–713):
- `AUTHENTICATION_FAILURE`
- `PERMISSION_DENIED`
- `CHECK_NOT_ACTIVE`
- `CHECK_NOT_COMPLETED`
- `INVALID_CHECK_ID`
- `INTERNAL_SERVER_ERROR`
- `NEW_ANALYST_INVALID`, `NEW_ANALYST_NOT_AUTHORIZED`
- `INVALID_MANAGER_ID`, `MANAGER_NOT_AUTH`
- `INPUT_FORMATTING_ERROR`, `REQUIRED_FIELD_MISSING`, `DISABLED_FIELD_ACCESS`, `INVALID_FIELD`, `PREPOPULATED_FIELD_UPDATED`
- `RESULTS_NOT_AVAILABLE`
- `INVALID_INPUT_FILE`
- `INVALID_WORKLOAD_ANALYST`, `INVALID_WORKLOAD_GROUP`

Errors are returned in-band in the response body (not as SOAP Faults). Callers must check `response.errors[]` on every call.

## Security Posture

### Strengths
- All three production endpoint URLs use HTTPS (port 8181), enforcing TLS for data in transit.
- Server certificate validation is enforced via JVM truststore (per-environment `servercert.bin` imports).
- The `kyc_profile` table separates credentials from code — credentials are stored in the database rather than hardcoded in Java source.

### Weaknesses and Vulnerabilities

| Finding | Location | Severity |
|---|---|---|
| **Plaintext `secure_code = 'Prepaid1'` committed to Git** | `artifacts/*/kyc_profile_*.sql` line 5 (all 3 envs) | CRITICAL — credential exposure in version history |
| **JDK 1.6 — TLS 1.0/1.1 likely in use** | `artifacts/keytool security cer add.txt` line 3 | HIGH — PCI DSS v4.0 Req 4.2.1 prohibits TLS < 1.2 |
| **SSN (`idNumber`) transmitted without field-level encryption** | `KycCheckService.xsd` line 473; `artifacts/checkapi_request` line 23 | HIGH — SSN in SOAP body; any logging captures full SSN |
| **SSN + full PII in Git artifacts** | `artifacts/checkapi_request`, `artifacts/checkapi_response` | HIGH — possible real PII (SSN `405415342`, name "Richard Ammar Chichakli") stored in repo |
| **Maven repo on plain HTTP** | `deploy kycbean jar to repository.txt` lines 3–9 | MEDIUM — artifact substitution attack possible |
| **Default JKS truststore password `changeit`** | `artifacts/keytool security cer add.txt` line 5 | MEDIUM — well-known default; if truststore file is accessible, it is trivially unlocked |
| **No WS-Security header** | `KycCheckServiceSIT.wsdl` — no `wsp:Policy` or WS-Security binding | MEDIUM — authentication is HTTP-header-based only; no message-level security |
| **Binary JARs in Git** | `KycCheckServiceXmlBeans.jar` (root and `artifacts/`) | MEDIUM — cannot audit compiled code; supply chain risk |
| **`nameVariationOption` controls watchlist fuzzy matching** | `KycCheckService.xsd` lines 725–731 | LOW — if set to `narrow`, potential OFAC matches may be missed |
| **Expired CA certificate in truststore** | `artifacts/cacertslist.txt` — TC TrustCenter Class 2 CA II expired Dec 31, 2025 | LOW — may cause TLS handshake failures for chains signed by this CA |

### Authentication Model
The library uses service-level authentication: `secure_id` (likely HTTP Basic username or a proprietary header) and `secure_code` (password) stored in `kyc_profile`. There is no OAuth2, no JWT, no client certificate mutual TLS (mTLS), and no WS-Security UsernameToken or SAML assertion. The WSDL contains no `wsp:Policy` element, confirming no WS-Security binding is in place.

## Technical Debt

| Item | Impact | Effort to Resolve |
|---|---|---|
| EOL Java 6 (JDK 1.6.0_16) | Blocks TLS 1.2+, no vendor security patches | HIGH — requires recompile with Java 11+; test all consumers |
| EOL XmlBeans 2.5.0 | Blocks modern Java compatibility; no security patches | HIGH — replace with JAXB 2.x or `wsimport`-generated stubs |
| Hardcoded `D:\c-base\` paths in `build.xml` | Unrepeatable build; blocks CI/CD | HIGH — parameterise build; remove absolute paths |
| Compiled JAR in Git (no Java source in repo) | Cannot audit, patch, or understand library internals | HIGH — locate source project; separate source from binary |
| Static version `1.0` forever | No upgrade path; all consumers tightly coupled | MEDIUM — introduce proper semver; deprecate 1.0 |
| `orgnaizationName` typo in XSD (line 345) | Data mapping errors in downstream consumers | LOW — XSD fix requires recompile and re-deployment of library |
| GroupId inconsistency (`actimizekyc` vs `com.ecount.actimizekyc`) | Consumers may reference wrong artifact | MEDIUM — standardise groupId; republish with correct coordinates |
| Manual SQL scripts for environment config | Error-prone; no validation; no secret management | MEDIUM — migrate to Flyway/Liquibase with secrets vault integration |
| Manual keytool certificate management | Cert expiry not monitored; manual rotation | MEDIUM — automate via cert management tooling |
| Plain HTTP Maven repo | Supply chain attack surface | MEDIUM — migrate to HTTPS-enabled artifact repository |
| No unit tests | Zero confidence in schema binding correctness | MEDIUM — add integration/contract tests |
| No logging instrumentation | Cannot audit KYC check activity at library layer | LOW — library-layer, but consuming services must compensate |

**Total technical debt assessment**: This library has accumulated approximately 15+ years of deferred maintenance. It is functional but operationally fragile. Any change to the upstream Actimize service contract or the underlying JVM environment could break it without warning.

## Gen-3 Migration Requirements

To migrate this library's functionality into a Gen-3 platform the following must be addressed:

### 1. Language / Runtime Modernisation
- Replace Java 6 + XmlBeans 2.5.0 + JAX-WS RI 2.1.2 with Java 17+ or Java 21 LTS.
- Replace XmlBeans compilation with `wsimport` (JAX-WS), `wsdl2java` (Apache CXF), or a modern SOAP client framework (Spring WS, Apache CXF 3.x+).
- If the Actimize platform supports a REST/JSON API (NICE Actimize has newer REST APIs), replace the SOAP client entirely with a REST client.

### 2. Build Pipeline
- Replace `build.xml` with a Maven POM (`pom.xml`) or Gradle build script.
- Remove all hardcoded absolute filesystem paths.
- Implement a proper CI/CD pipeline (GitHub Actions, Azure DevOps, Jenkins) that compiles, tests, and publishes the library automatically on push.

### 3. Secrets Management
- Remove `secure_code` from SQL scripts and Git history entirely (Git history scrub required).
- Inject `secure_id` and `secure_code` at runtime from a secrets vault (HashiCorp Vault, AWS Secrets Manager, Azure Key Vault).
- Rotate the `Prepaid1` credential immediately.

### 4. Certificate Management
- Replace manual `keytool` import with automated certificate provisioning (cert-manager, AWS ACM, or programmatic truststore construction from vault-managed certs).
- Upgrade TLS to 1.2/1.3 minimum.
- Remove expired CA entries from truststore.

### 5. Configuration Externalisation
- Migrate `ecountcore.kyc_profile` content to a Gen-3-compatible config store (Kubernetes ConfigMap + Secret, AWS Parameter Store, or Spring Cloud Config).
- Implement per-environment configuration injection at container startup.

### 6. Test Coverage
- Implement SOAP contract tests using a WireMock or similar stub of the Actimize endpoint.
- Validate all 12 operations and all 18 error types against the XSD.

### 7. Data & Compliance
- Implement SSN masking (first 5 digits masked: `XXX-XX-####`) in any logging pipeline before Gen-3 migration.
- Confirm whether `artifacts/checkapi_request` and `artifacts/checkapi_response` contain real PII and, if so, purge from Git history.
- Obtain a Gen-3 data classification for all fields in `details` and `cipResult` and apply field-level protection appropriate to GLBA/PCI DSS requirements.

### 8. API Adapter (if SOAP must be preserved)
- If the Actimize service remains SOAP-only, build a thin REST-to-SOAP adapter service (using Spring WS or Apache CXF) that exposes a REST/JSON API to Gen-3 consumers while handling SOAP translation internally.
- This adapter should own: credential management, TLS configuration, retry logic, circuit breaking, and audit logging.

## Code-Level Risks

1. **`artifacts/checkapi_request` line 23 — `<idNumber>405415342</idNumber>`**: A 9-digit value formatted as an SSN is stored unmasked in a Git repository artifact. Whether this is real or synthetic test data must be confirmed with the original developers. The associated name "Richard Ammar Chichakli" is publicly known to appear on OFAC sanctions lists — if this is a real submission that produced `possibleRisk=true` (as shown in the response file), this represents a historical KYC transaction record stored in source control.

2. **`KycCheckService.xsd` line 345 — `<xs:element name="orgnaizationName">`**: Typo (`orgnaization` instead of `organization`) in the canonical XSD. The compiled XmlBeans JAR will generate a getter method named `getOrgnaizationName()`. Any consuming code that attempts to access `getOrganizationName()` would get a compilation error or be silently receiving null. This has likely caused silent data loss for organization-type CDD watchlist matches.

3. **`build.xml` line 8 — `GENERATED_SOURCE_DIR` property defined but never used**: The property `GENERATED_SOURCE_DIR` is set to `D:\c-base\src\services\core\actimizeKYC\` but is not referenced anywhere in the build targets. Dead code; likely a copy-paste artefact.

4. **`KycCheckService.xsd` lines 130–134 — `primarySearchNoMatch`/`secondarySearchNoMatch` are `xs:boolean` without `minOccurs="0"`**: These fields are required (no `minOccurs="0"` default means required in XSD). If a caller does not explicitly set these to `false`, the XmlBeans default (false) will be transmitted, potentially causing incorrect "no match" assertions.

5. **`cddSearchWatchlistMatch.pep` (XSD line 346) — required boolean**: The `pep` (Politically Exposed Person) field has no `minOccurs="0"`, making it a required field. If the remote service omits it for non-PEP matches, XmlBeans will default to `false` — which is semantically correct but opaque. No explicit handling for `data_unavailable` equivalent exists for PEP (unlike `cipResultValue` which has a three-value enum).

6. **`batchInitiateRequest.inputFileContents` (XSD line 377) — untyped `xs:string`**: Batch file content is transmitted as a plain xs:string with no defined encoding (base-64 vs raw text). The consuming application must ensure consistent encoding with the Actimize service expectation — this is not enforced by the schema.
