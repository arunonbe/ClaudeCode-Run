# Data Architect Report — OP_Mobile_TESTING_PT

## Source Availability Note

No source files are present in this repository clone. Analysis is based on the repository name and inferred purpose within Onbe's OnePlatform mobile testing estate. All observations are inferred and must be validated against actual source code when access is restored.

## Data Models (Inferred)

Testing repositories typically contain the following data artifacts, depending on test type:

### If Performance Testing:
- **Test scenario definitions:** HTTP request templates, think times, virtual user counts, ramp-up/ramp-down profiles
- **Test data files:** CSV or JSON files containing synthetic test accounts, synthetic card numbers (e.g., BIN 411111 test range, last 4 "0000"), synthetic disbursement amounts
- **Baseline results:** Historical performance metrics (p50, p95, p99 latencies, throughput) used for regression comparison
- **Environment configurations:** Target API base URLs, authentication headers (test tokens), load test worker configurations

### If Penetration Testing:
- **Test case specifications:** OWASP Mobile Top 10 coverage matrix, specific test steps for authentication bypass, session management, insecure data storage
- **Findings reports:** Identified vulnerabilities with CVE references, CVSS scores, affected components, and remediation recommendations
- **Exploit scripts:** Proof-of-concept code demonstrating identified vulnerabilities
- **Scan results:** Burp Suite exports, MobSF (Mobile Security Framework) reports, network capture files

## Sensitive Data Handling — Critical Risk Areas

Testing repositories for payment applications represent one of the highest-risk categories for accidental sensitive data exposure:

### Risk 1 — Real Payment Credentials in Test Data
If performance or pen test scripts were developed using real cardholder accounts, real PANs, or real API credentials (even for test environments), these would constitute a PCI DSS violation if committed to source control. Even "test environment" credentials are PCI DSS in-scope if the test environment mirrors production data.

**Mitigation:** All test data must use synthetic values. PANs should use BIN 411111 test ranges or Luhn-valid synthetic numbers. Account credentials should be test-specific, rotated after each test cycle, and never reused from production.

### Risk 2 — API Tokens / Authentication Headers in Scripts
Load test tools (JMeter, k6, Gatling) commonly store HTTP headers, including `Authorization: Bearer <token>` or `X-API-Key: <key>` in script files. These credentials must be externalized to environment variables or secrets managers, never committed as literals.

### Risk 3 — Penetration Testing Findings Containing CHD References
Pen test reports often include request/response examples demonstrating vulnerabilities. These examples must use synthetic data. If a pen tester captured a real API response containing cardholder data during testing, that response must not be included in repository files.

## Data Flows (Inferred)

### Performance Testing Data Flow:
```
[Load Test Tool (JMeter/k6/Gatling)]
    --> [OnePlatform Mobile API (test/QA environment)]
        --> [OnePlatform Backend Services]
            --> [Test Database]
    --> [Performance metrics collection (InfluxDB/Grafana or similar)]
```

### Penetration Testing Data Flow:
```
[Security tester workstation]
    --> [OWASP ZAP / Burp Suite proxy]
        --> [OnePlatform Mobile App (test environment)]
            --> [OnePlatform Mobile API]
    --> [Findings documentation] --> [Jira / this repository]
```

## Encryption and Data Protection

Without source files, encryption posture cannot be assessed. Key questions for when source code is available:
- Are API authentication tokens externalized from test scripts?
- Do performance test HTTP requests use HTTPS (TLS) endpoints only?
- Are test result files containing any response data (which could include CHD) excluded from git via `.gitignore`?

## PCI DSS Compliance Assessment

- Req 11.3/11.4: This repository, if populated, would be a key PCI DSS testing artifact. Its absence of content is a compliance documentation gap.
- Req 6.3.3 / 6.5 (Test data): PCI DSS explicitly requires that production data not be used in testing and that test data containing CHD be removed before test completion.
- Gap: Empty repository means no evidence of testing activities. PCI DSS requires documentation that pen testing was performed, findings tracked, and remediation validated.
- **Recommended action:** Ensure all test scripts use synthetic data, externalize credentials, and commit testing artifacts (excluding any captures of real data) to this repository for audit trail purposes.
