# Enterprise Architect — profile_SVC

## Platform Generation
**Gen-2 (legacy ecount/Core2 platform).** Key indicators:
- Package namespace `com.ecount.Core2`, `com.ecount.service.core.Profile`
- Parent POM `com.parents:prepaid-parent` — legacy Onbe platform parent
- XML-RPC transport protocol
- Apache Commons HttpClient 3.x (EOL 2011)
- Director service for service discovery (not Kubernetes/service mesh)
- Windows `.bat` build scripts
- Java 21 compiler target (recent JDK but on a Gen-2 codebase)

## Business Domain
**Cardholder and Program Configuration** — Manages program-level and member-level configuration settings (profile classes). This is a foundational data service that other Gen-2 services depend on to resolve per-program business rules.

## Role in the Architecture
Profile SVC is a **shared configuration/settings data service** in the Gen-2 platform:
- Acts as a centralised key-value store for program configuration
- Exposes an XML-RPC interface consumed by other Gen-2 services
- Also acts as a shared library (`profile-client` JAR) — callers can embed the XML-RPC client or call the service remotely
- Published to GitHub Packages as a client library

## Module Responsibilities

| Module | Role |
|---|---|
| `profile-common` | Shared interface (`IProfile`) and domain model (keys, topics, values, outputs) |
| `profile-client` | Thread-safe XML-RPC client (Director-aware, 1-hour service location cache) |
| `profile-impl` | Business logic and DAO layer against FDR/Core2 databases |
| `profile-xmlrpc` | XML-RPC servlet (`ProfileXmlRPCServlet`) — the deployed endpoint |
| `profile-monitor` | Standalone health monitoring utility |

## Integration Patterns

| Pattern | Implementation |
|---|---|
| XML-RPC | `ProfileXmlRPCServlet` exposes `ECountCore.Profile.*` methods; `ProfileXMLRPCClient` consumes them |
| Service discovery via Director | `SimpleProfileServiceLocationResolvingCache` calls Director to resolve profile service URL, cached 1 hour |
| Shared client library | `profile-client` JAR allows Java services to call ProfileSVC without writing their own XML-RPC client |
| APIM publication | WSDL published to Azure API Management for service catalogue |

## Key External Dependencies

| System | Relationship |
|---|---|
| Director service | Service location registry — mandatory for XML-RPC client operation |
| FDR RDBMS | Profile class and scope data store |
| Core2 RDBMS | Member transaction context |
| `prepaid-parent:6.0.13` | Platform-wide dependency management |
| `ecount-system:4.0.3` | Core platform DAL framework |
| `ecountcore.common:3.1.6` | Core platform utilities |
| `director-client:2.0.2` | Director service client |
| `xplatform:6.5.8` | Platform extension library |

## Strategic Status
**Active but targeted for Gen-3 migration.** The service is:
- Actively deployed (GitHub Actions deployment workflow present)
- Published as a library to GitHub Packages
- Still on Gen-2 patterns (XML-RPC, Director, ecount packages)
- Java 21 compiler target suggests partial modernisation effort

## Migration Blockers (to Gen-3)

| Blocker | Impact |
|---|---|
| XML-RPC protocol has no equivalent in REST/gRPC without full redesign | High — all consumers must be updated simultaneously |
| Director service dependency — no Kubernetes-native equivalent | High — service discovery pattern must change |
| Apache HttpClient 3.x deeply embedded in XML-RPC transport | High — must upgrade to httpclient5 or replace entire transport |
| Gen-2 `ecount-system`, `ecountcore.common`, `xplatform` dependencies | High — these libraries are not available in Gen-3 Spring Boot context |
| FDR/Core2 RDBMS schema — not documented in this repo | High — schema migration is a separate programme of work |
| PACT verification disabled — consumers unknown | Medium — cannot identify all consumers without manual audit |
| `prepaid-parent` version management — no equivalent Gen-3 BOM yet (platform-dependencies-bom serves this role in Gen-3) | Medium |
