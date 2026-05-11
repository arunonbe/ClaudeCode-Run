# Enterprise Architect — ieft-cp2e_LIB

## Platform Generation

`ieft-cp2e_LIB` is a **Generation 1 / legacy** component. Evidence:

- Maven artifact version `2019.4.5` — last formally versioned in April 2019 with no subsequent releases in the repo.
- Java 1.6 target (EOL February 2013, per pom.xml lines 70–71).
- Spring 2.x XML-driven context (DTD `spring-beans`), a configuration model that predates Spring Boot by many years.
- JUnit 3.8.1 test dependency (pom.xml line 37) — JUnit 3 has not had a release since 2003.
- XML-RPC based StrongBox client — a protocol style that predates RESTful and gRPC service communication.
- No container/orchestration artifact (no Dockerfile, no Kubernetes manifest).

## Position in Onbe Architecture

```
eCount Core Database (SQL Server)
        │
        │  JDBC (Spring JdbcTemplate)
        ▼
┌─────────────────────────────┐
│  ieft-cp2e_LIB (batch JAR)  │   ◄── Scheduled batch invocation
│  Cp2eExtractFile.main()      │
└─────────────────────────────┘
        │                  │
  StrongBox              CP2E Flat File
  XML-RPC Vault          (128-char/line)
  (bank acct/routing)         │
                              ▼
                     NDM / MFT Transfer
                              │
                              ▼
                     Citibank Payment Platform
                     (Wire / Cross-border ACH)
```

The library sits in the **outbound payment disbursement path** for international and domestic wire transfers. It is critical-path infrastructure; failure to generate the CP2E file on schedule delays or blocks wire disbursements for Onbe clients.

## Dependencies

### Upstream (what this component depends on)

| Dependency | Version | Risk |
|-----------|---------|------|
| eCount Core SQL Server | Unknown | Single point of failure for payment data |
| Director service (`ppamwdcddcor1:80`) | Internal service | Plain HTTP; potential SPOF |
| StrongBox XML-RPC vault | `strongboxClient:1.0.2`, `strong-box-client:1.1.1-SNAPSHOT` | SNAPSHOT in production — non-deterministic build |
| `ecount-system:1.0.10` | Internal library | Frozen version |
| `DAO-Util:1.0.2` | Internal library | Frozen version |

### Downstream (what depends on this component)

| Consumer | Dependency |
|---------|-----------|
| NDM/MFT file transfer service | Reads CP2E output file from `D:/c-base/runtime/ndmroot/…` |
| Citibank wire processing | Receives CP2E file for payment execution |
| eCount Core DB | Procedure `ieft_cfx_process_upd_file_gen_flag` called on success to update state |

## Cross-cutting Concerns

### PCI DSS Relevance

This component is **within PCI DSS scope** because:
- It processes full bank account numbers and routing numbers from StrongBox.
- It writes those values unmasked to CP2E output files that traverse the network.
- The file path resides on what appears to be a production server (`p-az-` naming convention from the infrastructure repo).

Applicable PCI DSS v4.0.1 requirements:
- **Req 3.4**: Render PAN/account data unreadable anywhere it is stored (output files must be encrypted or access-controlled).
- **Req 4.2.1**: Strong cryptography for data in transit — Director HTTP call violates this.
- **Req 6.3.3**: All software protected from known vulnerabilities — Java 1.6 has hundreds of known CVEs.
- **Req 6.2.4**: Prevent common software attacks including injection — SQL concatenation risk.

### Architectural Maturity Assessment

| Dimension | Score (1=poor, 5=excellent) | Notes |
|-----------|---------------------------|-------|
| Modularity | 2 | Monolithic JAR; no API layer |
| Testability | 2 | JUnit 3, no integration test harness |
| Operability | 2 | No metrics, no health check, exit codes only |
| Security | 2 | HTTP transport, DEBUG log exposure, stale deps |
| Maintainability | 2 | Java 6, frozen Spring 2.x, XML-RPC |
| Compliance readiness | 2 | PCI scope data in plaintext logs/files |

## Modernization Roadmap Considerations

1. **Short-term (0–6 months)**: Upgrade Java to LTS 21; replace JUnit 3 with JUnit 5; fix SQL injection patterns; disable DEBUG-level account logging.
2. **Medium-term (6–18 months)**: Refactor to Spring Boot; containerize; add a CI artifact publish pipeline; migrate StrongBox client to REST/HTTPS.
3. **Long-term (18–36 months)**: Replace the CP2E flat-file batch pattern with an event-driven payment instruction service that integrates with Onbe's multi-rail orchestration layer. Consider whether the Citibank CP2E wire rail should be replaced by the modern push-to-card or ACH API channels already in the Onbe platform.
