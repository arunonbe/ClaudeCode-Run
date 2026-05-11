# Enterprise Architect View — nexpay-parent

## Position in the NexPay Gen-3 Architecture

The nexpay-parent is the **platform foundation layer** — the invisible governance artifact that ensures all NexPay Gen-3 microservices are built from a consistent base. It is not a runtime component but it is a critical architectural control that determines the security posture, operational consistency, and compliance certification scope of the entire NexPay platform.

```
nexpay-parent (POM artifact — GitHub Packages)
     │ inherits
     ├─ nexpay-order-orchestrator
     ├─ nexpay-ordervalidator-svc
     ├─ nexpay-recipientorchestrator-svc
     ├─ nexpay-recipient-profile-svc
     ├─ nexpay-recipientweb-bff
     └─ [other NexPay services]
```

## Platform Decisions Embedded in the Parent POM

### Spring Boot 4 Mandate

The decision to build on Spring Boot 4.0.5 is a significant platform commitment. Spring Boot 4:
- Requires Java 17+ (here 25 is mandated)
- Uses Jakarta EE 11 namespaces (`jakarta.*` not `javax.*`)
- Uses Jackson 3.x by default
- Has a smaller ecosystem than Spring Boot 3 (Boot 4 is relatively new at the time of NexPay Gen-3 inception)

The POM comment explicitly states: "This POM is NOT backwards compatible with previous Spring Boot 3." This means all NexPay Gen-3 services are on a new technology baseline that is distinct from Onbe's legacy services (which likely use Spring Boot 2.x or 3.x). The enterprise implication is that Gen-3 and legacy services cannot share library artifacts without careful version management.

### Java 25 Mandate

Java 25 is a long-term support (LTS) release. Virtual threads (Project Loom) in Java 25 are a stable feature, enabling the synchronous-blocking programming model adopted by the NexPay orchestration services without the concurrency limitations of thread-pool-based servers. This is a deliberate architectural choice enabling readable synchronous code at cloud-native scale.

### OpenTelemetry as a Platform Standard

Including `spring-boot-starter-opentelemetry` as a universal, non-optional dependency makes distributed observability a platform standard rather than an opt-in feature. Every NexPay service emits traces, metrics, and logs in OpenTelemetry format from day one. This is an architectural decision that enables:
- End-to-end trace correlation across the disbursement flow.
- Centralised performance monitoring.
- Audit-quality evidence of service interactions for compliance purposes.

## Platform Governance

### Who Controls the Parent POM

The two listed developers (Andrew Smirnoff, Rubens Gomes) are the current owners. For a PCI DSS-regulated platform, the parent POM must have:
1. A formal change management process (PR + review requirement)
2. An approval gate before version publication
3. A communication mechanism to notify all consuming teams of changes

These governance processes are not encoded in the repository but should be documented in Onbe's change management procedures.

### Dependency Version Governance Risk

If the parent POM maintainers upgrade a dependency (e.g., Spring Boot minor version), all consuming services must be rebuilt and redeployed. This creates a coordinated deployment requirement across the entire NexPay platform. For a payments platform, this coordination must be managed carefully to avoid service availability impacts.

### SNAPSHOT Version in Production

The use of SNAPSHOT versions (`0.2.8-SNAPSHOT`) means the parent POM is consumed from a mutable artifact. This is acceptable in development but is a compliance risk for production certification. PCI DSS Requirement 6.2.4 requires that all application components are protected from known vulnerabilities — non-reproducible builds undermine the ability to verify exactly which library versions are in production.

## Technology Strategy Alignment

| Technology Decision | Alignment with Onbe Standards | Risk |
|---|---|---|
| Spring Boot 4 | New platform, requires ecosystem readiness | Medium — limited Boot 4 ecosystem maturity |
| Java 25 | Modern LTS | Low |
| Virtual threads | Enables high concurrency | Low |
| GitHub Packages as Maven registry | Reasonable for enterprise GitHub | Low |
| Azure Cloud-native integrations (Spring Cloud Azure 7.1.0) | Aligned with Azure deployment | Low |
| OpenTelemetry | Industry standard | Low |
| SNAPSHOT parent in production | Non-reproducible builds | High |

## Enterprise Risk Register

| Risk | Severity | Mitigation |
|---|---|---|
| SNAPSHOT parent POM in production | High | Release to stable version before production go-live |
| Spring Boot 4 ecosystem immaturity | Medium | Monitor Spring Boot 4 issue tracker; pin known-good versions |
| Jackson 2.x/3.x dual version coexistence | Medium | Standardise on Jackson 3.x; migrate OpenAPI generated code |
| No coverage thresholds in parent | Medium | Define minimum coverage standards for PCI DSS compliance |
| Parent POM change coordination risk | Medium | Document deployment coordination procedure |
| Two-developer ownership concentration | Low | Expand ownership or document succession |

## NIST CSF 2.0 Alignment

The parent POM directly supports:
- **Identify (ID.AM)**: Dependency inventory is encoded in the POM; Dependabot provides automated vulnerability discovery.
- **Protect (PR.DS)**: MapStruct type-safe mapping prevents accidental PII field exposure through reflection.
- **Protect (PR.IP)**: Enforcer plugin prevents insecure toolchain versions.
- **Detect (DE.CM)**: OpenTelemetry makes all services observable by default.
- **Recover (RC.IM)**: Consistent test infrastructure (Testcontainers, JaCoCo) enables confident re-testing after patches.
