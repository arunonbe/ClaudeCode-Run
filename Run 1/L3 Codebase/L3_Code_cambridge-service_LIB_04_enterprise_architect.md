# cambridge-service_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-1**

Evidence:
- Spring Framework 2.0.3 (released 2007) — pre-Spring 3 annotations, pure XML IoC
- Apache Axis2 1.7.5 (released 2017, generated from WSDL in May 2017) — SOAP/WS-* integration pattern, no REST
- No Spring Boot, no microservice framework, no containerisation
- Hardcoded Windows filesystem paths, manual proxy configuration via JVM system properties
- JUnit 3.8.1 (released 2004) — pre-annotations test harness
- Package namespace `com.citi.prepaid` — indicates Citi-era origin, predating or coinciding with the Onbe/Citi prepaid program transition
- Version `1.0-SNAPSHOT` — never formally released; remains in prototype/integration state
- All WSDL-generated code dated May 06, 2017 per Axis2 code generation comment headers

This library exhibits all hallmarks of first-generation enterprise integration code: XML-configured Spring, SOAP stubs auto-generated from vendor WSDL, localhost filesystem dependencies, and no cloud-native or containerisation affordances.

---

## Business Domain

**Domain: Cross-Border Payment Rail / FX Integration**

Sub-domains:
- **FX Rate and Deal Management** — spot and forward rate retrieval, deal booking and cancellation (`TradeServiceImpl`)
- **Payment Instruction** — wire payment initiation tied to a booked FX deal (`instructPayment`, `instructPaymentSettlement`)
- **Beneficiary Management** — CRUD for payment recipients including bank details and compliance classification (`BeneficiaryServiceImpl`)
- **Bank Directory** — lookup and search of correspondent banks by name and country (`BankServiceImpl`)
- **Authentication** — token-based SSO with HMAC digital signature (`SSOServiceImpl`)
- **Regulatory Disclosure** — Reg E disclosure retrieval for US international remittance (`RegEDisclosureServiceAPIStub`)

Within Onbe's product context, this library enables the **cross-border disbursement** capability — sending funds internationally via FX wire to a named beneficiary with a bank account in a foreign currency. This is a non-card, non-prepaid rail used when the recipient requires international bank transfer rather than a Visa/Mastercard prepaid card or ACH.

---

## Role in Platform

This is a **shared integration library** (JAR) — it has no runtime process of its own. Its role in the platform is:

1. **FX rail adapter**: Provides a Java API surface over the Cambridge FX Online SOAP web services, abstracting SOAP complexity from consuming services.
2. **Cross-border payment enablement**: Enables Onbe's disbursement platform to send international wire payments (e.g., global payouts, cross-border rebates, international contractor payments) through the Cambridge/Corpay network.
3. **Beneficiary registry client**: Allows the platform to register and manage payment recipients on the Cambridge side, including compliance classification and dynamic validation.

The library does not contain business logic beyond the Cambridge API contract. It is a translation layer: it converts Java method calls and POJOs into SOAP XML and inverts Cambridge XML responses back to Java objects.

---

## Dependencies

### Outbound (this library depends on)
| Dependency | Type | Version | Status |
|---|---|---|---|
| Cambridge FX Online API | External SOAP service | WSDL generated 2017 | Beta endpoint hardcoded; production URL unknown from code |
| Spring Framework | Library | 2.0.3 (2007) | EOL — severely outdated |
| Apache Axis2 (kernel, adb, transport-http, transport-local, saaj) | Library | 1.7.5 (2017) | EOL — outdated, known CVEs |
| Apache Axiom | Library | 1.2.20 | Outdated |
| Apache Neethi | Library | 3.0.1 | Outdated |
| JUnit | Library (test) | 3.8.1 (2004) | EOL |

### Inbound (what depends on this library)
Not determinable from this repository alone. The library must be consumed by one or more Onbe internal services (likely a disbursement or payment orchestration service) that instantiate `CambridgeServiceImpl` via Spring or direct instantiation.

### External Service Contract
The library is bound to the Cambridge FX Online WCF service WSDL generated May 2017. Any change to Cambridge's API contract (new fields, deprecated operations, endpoint URL changes — e.g., Corpay rebrand) requires regenerating the stubs and updating the library.

---

## Integration Patterns

### Pattern: SOAP Client with Auto-Generated Stubs
All integration uses Apache Axis2-generated stub classes (`BankServiceAPIStub`, `BeneficiaryServiceAPIStub`, `TradeServiceAPIStub`, `RegEDisclosureServiceAPIStub`, `SSOServiceStub`). Each stub:
- Extends `org.apache.axis2.client.Stub`
- Implements WS-Policy `TransportBinding` with HTTPS + Basic256 per operation
- Uses `OutInAxisOperation` (request-response) for all operations
- Engages the `addressing` WS-Addressing module per call

### Pattern: Service Facade over Stubs
Each `*ServiceImpl` class is a thin facade that:
- Accepts simple Java types (String token, BigDecimal amount, etc.)
- Constructs the appropriate SOAP request type
- Calls the stub
- Extracts and returns the result field

This pattern decouples consuming code from Axis2 types.

### Pattern: Spring XML IoC Assembly
All wiring is via `appContext-CambridgeService.xml` using classic Spring 2 `<bean>` XML. There are no annotations. The `CambridgeServiceImpl` aggregates all four service implementations.

### Pattern: Token-Based SSO (Shared Secret HMAC)
Authentication uses a compute-and-submit pattern: compute HMAC digest of (sharedSecret + returnURL + userName + timestamp), submit to Cambridge SSO, receive a short-lived bearer token, use token in all subsequent requests.

### Pattern: Quote-then-Book (Two-Phase Commit for FX)
FX deals follow a two-phase pattern: `getRate` → `bookDeal`. This is a common financial transaction pattern where rates are volatile and must be locked before commitment. Cancel follows: `getCancelRate` → `cancelDeal`.

### Anti-Pattern: No Abstraction Interface
None of the `*ServiceImpl` classes implement a Java interface. `CambridgeServiceImpl` holds concrete references to all four service implementations. This makes unit testing and mocking difficult and creates tight coupling.

### Anti-Pattern: No Connection Pooling or Client Lifecycle Management
Each stub is instantiated as a Spring singleton but the underlying HTTP connection management is left to Axis2 defaults. There is no explicit connection pool configuration, timeout setting, or keep-alive control.

---

## Strategic Status

**Status: Legacy / Maintenance-Only**

Assessment:
- No active development evident (snapshot version, outdated dependencies, no unit tests, hardcoded paths)
- The library was generated from a 2017 WSDL snapshot and has not been updated to reflect any Cambridge API changes since
- Cambridge FX Online has been rebranded as Corpay Cross-Border; API endpoint changes may have occurred
- Spring 2 and Axis2 1.7.5 are both end-of-life. Continued use exposes the platform to unpatched CVEs
- The library serves a real business need (cross-border wire payments) but in its current form cannot be:
  - Containerised (Windows filesystem paths)
  - Migrated to microservices (no REST, no health endpoints, no metrics)
  - Tested in isolation (no interfaces, no unit tests)
  - Operated with confidence (no logging, no error handling)

**Recommended strategic disposition**: Replace with a modern REST client to the Cambridge/Corpay API (or evaluate a different FX rail provider offering a REST/JSON API), migrating to a Gen-3 pattern. If replacement is not immediately feasible, a Gen-2 wrapper service should be built around this library to add logging, error handling, endpoint management, and metrics.

---

## Migration Blockers

| Blocker | Severity | Detail |
|---|---|---|
| Windows-only filesystem paths | HIGH | `D:\c-base\runtime\axis\repository` and `d:/c-base/config/...` prevent containerisation on Linux. Must be externalised before Docker/Kubernetes deployment. |
| Hardcoded beta endpoints | HIGH | All five default stub constructors resolve to `isbeta.cambridgefxonline.com`. Production endpoints are not present in the codebase. |
| Spring 2.0.3 (EOL) | HIGH | Spring 2 is incompatible with Spring Boot 2/3. Migration requires rewriting IoC configuration (XML → annotations/Java config). |
| Axis2 1.7.5 (EOL, CVEs) | HIGH | Axis2 1.7.x has published CVEs including XXE and deserialization vulnerabilities. Replacement with a modern HTTP client (e.g., Apache CXF, Spring WS, or REST via OpenFeign) is needed. |
| No unit tests | MEDIUM | Zero test coverage means any refactoring carries high regression risk. Test coverage must be established before migration. |
| No interfaces on service classes | MEDIUM | `BankServiceImpl`, `BeneficiaryServiceImpl`, etc. are concrete classes with no interfaces. Mocking requires Mockito `spy` or subclass mocking. |
| Shared secret in local file | MEDIUM | The `sharedSec` property must be migrated to a secrets vault before cloud deployment. |
| No version release history | LOW | `1.0-SNAPSHOT` forever — no way to audit what version is deployed in any environment. |
| No Reg E implementation | MEDIUM | `RegEDisclosureServiceAPIStub` exists without an `Impl` class. If Gen-3 requires Reg E compliance for international remittance, this must be implemented. |
| Unknown production endpoints | MEDIUM | Cambridge/Corpay production URLs are not in the codebase. Migration requires obtaining current production API credentials and endpoints. |
