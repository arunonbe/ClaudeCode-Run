# Solution Architect — ieft-cp2e_LIB

## Technical Debt Register

### Critical Severity

| ID | Location | Issue | Regulatory Impact |
|----|----------|-------|-------------------|
| TD-001 | `pom.xml` lines 70–71 | Java 1.6 target — EOL 2013, hundreds of unpatched CVEs | PCI DSS Req 6.3.3 |
| TD-002 | `Cp2eExtractFile.java` line 153 | SQL concatenation: `"exec ieft_cfx_process_batch_extract " + request_file_id + ", '" + autoClaimExtractCutoff + "'"` | PCI DSS Req 6.2.4 (injection prevention) |
| TD-003 | `Cp2eMigrateData.java` line 71 | SQL concatenation with unvalidated string variables in update statement | PCI DSS Req 6.2.4 |
| TD-004 | `cp2eExtract.properties` line 1 | Director service URL `http://ppamwdcddcor1:80` uses plaintext HTTP — DB credentials and connection metadata transmitted unencrypted | PCI DSS Req 4.2.1 |

### High Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-005 | `StrongBoxLookupHelper.java` line 105 | `log.debug()` emits full key-value pairs from StrongBox including `bank.accountNumber` and `bank.routingNumber` | PCI DSS Req 3.3.1 — account data in logs |
| TD-006 | `pom.xml` line 59 | `strong-box-client:1.1.1-SNAPSHOT` — SNAPSHOT dependency produces non-deterministic builds | Build integrity / supply chain |
| TD-007 | `StrongBoxLookupHelper.java` lines 40–44 | Race condition: `sbClient` static field initialized in constructor without synchronization | Thread safety; potential NullPointerException under concurrent start |
| TD-008 | `pom.xml` line 37 | JUnit 3.8.1 — effectively no unit test framework capability | Testability / quality gate |

### Medium Severity

| ID | Location | Issue | Impact |
|----|----------|-------|--------|
| TD-009 | `cp2eExtract.properties` line 2 | Agent ID `b2ctest` — "test" suffix in value suggests QA value committed to repo | Operational configuration risk |
| TD-010 | `cp2eExtract.properties` line 4 | Path `cititest` in XMLFilePath — suggests QA/test environment path | Production deployment risk |
| TD-011 | `Cp2eWriter.java` line 174 | `threadPool.awaitTermination(Long.MAX_VALUE, TimeUnit.NANOSECONDS)` — effectively infinite wait; no operational timeout | Hung process risk |
| TD-012 | No CI build-on-push | No automated test execution on pull requests | Code quality regression risk |

## Security Vulnerabilities

### Flagged Items (PCI DSS Critical)

**1. Plaintext HTTP for Director Service (TD-004)**
- File: `cp2eExtract.properties`, line 1
- Value: `director.address=http://ppamwdcddcor1:80/service/dispatch.asp`
- Risk: Database connection parameters and agent credentials transmitted over unencrypted HTTP, satisfying the definition of a PCI DSS Requirement 4.2.1 violation.
- Remediation: Switch Director service endpoint to HTTPS (`https://ppamwdcddcor1:443/…`) and validate the server certificate.

**2. Bank Account Numbers Logged at DEBUG Level (TD-005)**
- File: `StrongBoxLookupHelper.java`, line 105
- Code: `log.debug("Putting " + prefix + (String)a.getKey() + " = " + a.getValue() + " into map")`
- Risk: When DEBUG logging is active, full bank account numbers and routing numbers from the StrongBox response will appear in log files. Log files are frequently captured by SIEMs, log aggregators, and developers with broad file access, creating unauthorized cardholder data exposure.
- Remediation: Remove the debug log statement or replace with field-name-only logging (omit the value entirely for sensitive fields).

**3. SQL Injection in Stored Procedure Invocation (TD-002, TD-003)**
- Files: `Cp2eExtractFile.java` line 153; `Cp2eMigrateData.java` line 71
- Remediation: Use `PreparedStatement` or Spring's `SimpleJdbcCall` with named parameter binding.

**4. SNAPSHOT Dependency on StrongBox Client (TD-006)**
- A SNAPSHOT dependency allows the upstream author to silently change the artifact between builds. For a cryptographic vault client handling bank account data, this is a supply chain integrity risk.
- Remediation: Pin to a specific release version; configure repository policy to block SNAPSHOT resolution in production build profiles.

## Remediation Priority Matrix

| Priority | Item | Estimated Effort |
|----------|------|-----------------|
| 1 — Immediate | Disable DEBUG-level value logging (TD-005) | 0.5 day |
| 2 — Immediate | Enforce HTTPS for Director service (TD-004) | 1 day (infra + code) |
| 3 — Sprint 1 | Replace SQL concatenation with parameterized calls (TD-002, TD-003) | 2 days |
| 4 — Sprint 1 | Pin `strong-box-client` to a release version (TD-006) | 0.5 day |
| 5 — Sprint 2 | Upgrade Java from 1.6 to 21 (TD-001) | 3–5 days |
| 6 — Sprint 2 | Fix StrongBox client static initialization race condition (TD-007) | 1 day |
| 7 — Sprint 3 | Implement build-on-push CI with test coverage (TD-012) | 2 days |
| 8 — Sprint 3 | Add operational timeout to thread pool await (TD-011) | 0.5 day |
| 9 — Quarter 2 | Upgrade Spring 2.x to Spring Boot 3.x | 5–10 days |
| 10 — Quarter 2 | Validate production property values (TD-009, TD-010) | 0.5 day |

## Positive Observations

- The two-mode (AutoClaim / OTT) design with explicit OTT failure recovery (exit codes 777/888) shows mature operational thinking for a payment file generation system.
- `Cp2eWriter.writeRecord()` is properly `synchronized`, preventing concurrent write corruption.
- The CP2E file template (`cp2eTemplate.xml`) externalizes record structure from code, enabling format changes without recompilation.
- `PaymentPurposeCodes` enum comprehensively covers RBI cross-border purpose codes — evidence of thorough regulatory implementation for the India corridor.
- The `ieft_cfx_process_check_last_OTT_status` guard prevents double-spend on OTT retry, a sound payment integrity control.
