# Enterprise Architect View — strongbox-lib_LIB

## Platform Generation
**Gen-1** — Legacy J2EE / Spring XML heritage. Characteristics:
- Spring XML bean configuration (no annotations-based configuration).
- XML-RPC for remote communication (pre-REST era).
- Apache HttpClient 3.x (EOL since ~2011).
- JTDS JDBC driver (not Microsoft's official JDBC driver).
- DESede (3DES) still present as V1 cipher.
- Original group ID `com.citi.prepaid` — predates Onbe brand; indicates lineage from Citi Prepaid era.
- Java 21 compiler target added as a recent uplift, but the architecture pattern remains Gen-1.

## Business Domain
**Security / Credential Vault** — Cross-cutting security infrastructure. Used by:
- ECount Core
- Job Service
- Repository Service

This is a foundational security capability, not a business-domain service.

## Role in Ecosystem
- Acts as the encryption-at-rest vault for regulated PII (SSN, DOB) and financial account data (bank account numbers).
- Consumed by multiple internal services as a shared library.
- The `strongbox-client` module abstracts remote access to the StrongBox service via XML-RPC; `strongbox-impl` provides the full server-side stack.

## Dependencies
| Artifact | Version | Notes |
|----------|---------|-------|
| `com.parents:prepaid-parent:6.0.12` | Parent POM | External to this repo |
| `com.citi.prepaid.service.core:xmlrpc:3.0.1` | Internal | XML-RPC transport |
| `com.ecount.service.core.ecountcore:common:3.0.1` | Internal | ECount Core commons |
| `com.ecount.daoutil:dao-util:2.0.0` | Internal | JDBC utilities |
| `com.citi.prepaid.service.core.client:director-client:2.0.0` | Internal | Service discovery |
| `net.sourceforge.jtds:jtds` (test scope) | Third-party | SQL Server JDBC driver (JTDS, EOL) |
| `commons-dbcp` / `commons-pool` (test scope) | Third-party | Connection pooling |

## Integration Patterns
| Pattern | Details |
|---------|---------|
| Library (direct) | `strongbox-impl` consumed as a JAR dependency by server-side services |
| XML-RPC | `strongbox-client` communicates with the StrongBox service over HTTP XML-RPC |
| Service Discovery | Director service resolves StrongBox URL (analogous to a service registry) |
| In-process Key Cache | RSA keys cached in static `HashMap` — no distributed cache |

## Strategic Status
**Maintain with security uplift required.** This component:
- Is security-critical and cannot simply be decommissioned without migrating all dependent services.
- Requires cipher modernisation (3DES → AES-256-GCM) before PCI DSS v4.0 compliance deadline.
- Should be evaluated for replacement with a modern secrets manager (e.g., HashiCorp Vault, AWS Secrets Manager, Azure Key Vault) as part of Gen-3 migration.
- The `com.citi` group IDs and artifact names must be renamed (noted as TODO in README).

## Migration Blockers
| Blocker | Description |
|---------|-------------|
| 3DES V1 cipher | Existing encrypted data stored with DESede cannot be migrated to AES without a bulk re-encryption operation. Requires a migration plan and potential downtime. |
| XML-RPC transport | Apache XML-RPC and HttpClient 3.x are both EOL. Migration to REST/gRPC requires client-side changes in all consumers. |
| Director service coupling | All consumers depend on Director service for URL resolution. Must be replaced or emulated in a Gen-3 architecture. |
| Static key cache | The in-process `HashMap` key cache does not survive restarts or work across multiple instances. A distributed or JVM-scoped cache must be designed before horizontal scaling. |
| Non-self-contained tests | Tests require live SQL Server. A test-doubles strategy must be introduced before the library can be safely refactored. |
