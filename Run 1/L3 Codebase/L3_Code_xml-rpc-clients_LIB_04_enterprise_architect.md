# Enterprise Architect View — xml-rpc-clients_LIB

## Platform Generation Classification

**Generation**: Gen-1 (eCount/Citi era) — canonical Gen-1 artifact

xml-rpc-clients_LIB is the most representative Gen-1 artifact in the Onbe platform portfolio. The version identifier `2016.1.1`, the parent POM `service-parent:7`, the Apache Commons HttpClient 3.x transport, JUnit 4.4, and the XML-RPC protocol itself all date to the eCount/Citi era. The library predates Wirecard's acquisition, predates Spring Boot, and predates REST/JSON as a service communication standard. Its continued presence in production is a direct measure of how deeply Gen-1 architectural patterns remain embedded in the Onbe platform.

## Strategic Role in the Enterprise

This library is **the Gen-1 service integration fabric**. Every Gen-1 application that needs to perform cardholder operations — enrollment, card issuance, fund loading, transfer processing, order creation, profile management, security credential update — does so through this library's XML-RPC client stubs. The seven sub-modules represent the complete surface of eCountCore's external API as it existed in 2016.

The library's strategic importance is inverse to its technical quality: it encapsulates the only programmatic path to eCountCore backend services for Gen-1 consumers. Retiring it requires either:
1. Replacing the eCountCore XML-RPC services with modern REST/message-based APIs, or
2. Wrapping eCountCore behind a modern API gateway that translates REST/gRPC calls to XML-RPC internally

Until either path is completed, this library cannot be retired without breaking all Gen-1 consumer applications.

## Integration Patterns

**Protocol**: XML-RPC over HTTP (Apache Commons HttpClient 3.x). XML-RPC uses HTTP POST with XML bodies — a synchronous, blocking, request-response pattern with no built-in streaming, no backpressure, no retry logic, no circuit-breaker, and no distributed tracing support.

**Service discovery pattern**: Director-mediated service location — before invoking any backend service, consumers must query the Director service to resolve the target service's URL. This is a Gen-1 service mesh: centralized registry, synchronous resolution, per-agent routing. The Director is a single point of failure; if Director is unavailable, no XML-RPC service can be located.

**Consumer applications**: All Gen-1 web applications (`oneplatform_WAPP`, `csa_WAPP`, `bmcwizard_WAPP`), Gen-1 batch jobs, and any application that has not yet migrated to Gen-3 REST APIs for the operations covered by these client stubs.

**Coupling characteristics**:
- **Binary coupling**: Consumers depend on compiled JAR artifacts at specific versions (`2016.1.1`)
- **Protocol coupling**: Consumers are coupled to XML-RPC semantics; migration to REST requires updating consumers, not just the library
- **Schema coupling**: Value objects (`Member`, `ExtendedRegistration`, `SecureUserProfile`, `Transfer`) are shared types from `ecountcore:common:2014.1.1`; schema changes require coordinated releases

## Architecture Debt Assessment

| Concern | Severity | Detail |
|---|---|---|
| XML-RPC protocol (no TLS enforcement) | Critical | Transport security depends entirely on Director-resolved URLs being HTTPS; no code-level enforcement; PCI DSS Req 4.2.1 |
| Apache Commons HttpClient 3.x (EOL 2011) | Critical | Multiple CVEs; unsupported; PCI DSS Req 6.3.3 requires patching or replacement |
| Director as single point of failure | High | All service lookups fail if Director is unavailable; no fallback mechanism |
| No retry or circuit-breaker | High | First transient failure results in call failure propagated to cardholder-facing operations |
| PII logging in `puidMemberSearch()` | High | `lookupPartnerUserID` logged at INFO; potential GLBA/CCPA/PCI DSS violation |
| `Testing.java` in production source | Medium | Test code compiled into production JARs; not appropriate for a PCI-regulated environment |
| Exception swallowing returning null | Medium | Director call failures return null silently; callers may propagate NullPointerException |
| JUnit 4.4 (released 2007) | Low | Test-only risk; no runtime impact |
| Frozen version `2016.1.1` | Informational | Signals no active version evolution; consumers are permanently bound to 2016-era artifacts |

## Migration and Modernization Posture

**Current trajectory**: This library is in passive maintenance — changes are minimal if any. The GitHub Actions CodeQL scan and Dependabot configuration indicate some CI hygiene, but the absence of a publish workflow and the frozen version suggest it is treated as a stable artifact that is not actively evolved.

**Strategic recommendation**: **Retire, do not modernize in-place**

The correct migration path is not to upgrade Apache Commons HttpClient or modernize the XML-RPC transport within this library. The correct path is to replace the XML-RPC protocol boundary entirely:

1. **Near-term (0–6 months)**: Audit all consumers of each sub-module to establish which XML-RPC operations are still invoked by active production code paths. Identify which operations have equivalent Gen-3 REST API endpoints already available (order_SVC with IBM MQ is the Gen-3 replacement for `orderXMLRPCClient`). Document the migration delta.

2. **Medium-term (6–18 months)**: Build or extend a Gen-3 API facade (Spring Boot 3.x, Java 21, Azure API Management) that exposes REST endpoints for each eCountCore operation, backed by either:
   - Direct database access replacing the eCountCore intermediary, or
   - An internal XML-RPC proxy that calls eCountCore — allowing consumer migration to REST without requiring simultaneous eCountCore replacement

3. **Long-term**: Retire eCountCore XML-RPC services and this library simultaneously once all consumers have migrated to the Gen-3 REST API facade. The `MemberXMLRPCClient` operations are the highest-volume target because they cover the full cardholder lifecycle.

**Priority order for migration** (by business criticality):
1. `TransferXMLRPCClient` (QuickLoad, Begin/Commit/Cancel) — fund loading; financial risk
2. `MemberXMLRPCClient` (AddBasic, AddExtended) — enrollment; cardholder impact
3. `DeviceXMLRPCClient` (CreateDevice) — card issuance; cardholder impact
4. `OrderXMLRPCClient` — Gen-3 `order_SVC` exists; migration path most advanced
5. `ProfileXMLRPCClient`, `EventXMLRPCClient` — lower volume; migrate after core operations

## Cross-Cutting Concerns

- **PCI DSS Requirement 4.2.1**: The XML-RPC over HTTP transport pattern is the most significant PCI DSS risk in this library. A formal assessment of whether Director-resolved URLs in production environments are HTTPS is a required compliance verification action
- **PCI DSS Requirement 6.3.3**: Apache Commons HttpClient 3.x (EOL) must be tracked in the organization's software inventory and scheduled for replacement in the system lifecycle plan
- **GLBA Safeguards Rule**: PII data (name, address, email, phone) traversing XML-RPC calls must be protected in transit; TLS verification per environment is required
- **Reg E**: The three-phase transfer protocol (Begin/Commit/Cancel) means incomplete transactions are possible; any monitoring gap around uncommitted transfers creates Reg E dispute exposure
- **Vendor-provided code note**: The `MemberXMLRPCClient` carries `@author OFSS` (Oracle Financial Services Software) attribution, confirming this library was developed under a vendor contract during the Citi/eCount era. Ownership and maintenance responsibility transferred to Onbe post-acquisition
