# api-logging-lib — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Gen-1 / Legacy.**

Evidence:
- Package namespace `com.ecount.axis.soap.logging` — `ecount` is the legacy platform brand predating the Onbe rebrand.
- Core dependency is **Apache Axis 1.4** (`axis:jakarta-axis:1.4`), a SOAP stack whose 1.x line has been end-of-life for over a decade. Modern platforms use JAX-WS, Spring-WS, or REST/gRPC.
- The library's `README.md` references `csapi-axis-soap-logging` as the former module name, indicating origin in the CS API / ecount legacy service layer.
- Windows service / Tomcat deployment model documented in `README.md` (lines 83-109) is characteristic of Gen-1 on-premise deployments.
- No cloud-native patterns (service mesh, sidecar, structured JSON logging, OpenTelemetry) are present.

## Business Domain

**Cross-Cutting Infrastructure / Observability** — not specific to a single business domain. The library provides logging middleware for any SOAP-based service within the ecount/Onbe platform. Based on the sensitive field list (`card_number`, `ssn`, `new_pin`, `cvv`, `account_number`, `routing_number`, `dda_number`, `dda`, `application_id`), the consuming services operate in the **payments and financial services** domain, handling:
- Prepaid card operations (PAN, CVV, PIN)
- ACH/bank account transactions (account number, routing number, DDA)
- Identity (SSN, application ID)

## Role in Platform

`api-logging-lib` is a **shared library / cross-cutting concern** within the Gen-1 SOAP service tier. Its role is:

1. **Observability middleware**: Provides uniform SOAP request/response/fault trace logging across all consuming services without per-service implementation.
2. **PCI DSS compliance enabler**: Centralises the sensitive-field scrubbing logic so individual services do not need to independently implement PAN/CVV/PIN redaction in logs.
3. **Operational tooling**: Supports incident investigation and service behaviour auditing by capturing full (scrubbed) SOAP payloads.

The library is a **dependency** of other services — it has no standalone runtime or deployment footprint of its own.

## Dependencies

### Inbound (consumers of this library)
- Any Apache Axis-based SOAP service within the Onbe/ecount platform that includes `com.ecount.webservices:api-logging-lib:1.0.0` in its `pom.xml`. Specific consumers are not identifiable from this repository alone — they are upstream dependants.

### Outbound (this library depends on)
| Dependency | Version | Scope | Notes |
|------------|---------|-------|-------|
| `axis:jakarta-axis` | 1.4 | compile | Core SOAP engine — EOL |
| `axis:jakarta-axis-jaxrpc` | 1.4 | compile | JAX-RPC API — EOL |
| `axis:jakarta-axis-saaj` | 1.4 | compile | SAAJ API |
| `org.slf4j:slf4j-api` | 2.0.16 | compile | SLF4J 2.x — current |
| `Onbe/om-ci-setup` | `@main` | CI | Shared CI/CD reusable workflows |
| `onbe/onbe_maven_releases` | — | registry | GitHub Packages Maven registry |

**Notable**: The Axis dependency is sourced from a custom Maven repository (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) rather than Maven Central, indicating Onbe maintains its own fork or repackaging of the Axis 1.4 libraries under the `axis:jakarta-axis` coordinates.

## Integration Patterns

1. **Apache Axis Handler Chain (WSDD)**: The library integrates via the Axis Web Service Deployment Descriptor handler mechanism. Consumers add `SoapLoggingHandler` to the `requestFlow` and `responseFlow` in their WSDD configuration (`README.md`, lines 43-54). This is a classic **interceptor/pipeline** pattern.
2. **Shared Library / JAR dependency**: Distributed as a Maven JAR artifact published to GitHub Packages. Consumers declare it as a compile-scope dependency.
3. **Configuration via JVM/OS**: No service registry, no config server, no Kubernetes ConfigMap — configuration is entirely via JVM system properties and OS environment variables, typical of Gen-1 Tomcat deployments.
4. **SLF4J logging bridge**: The library acts as a **provider** to the SLF4J API, with the consuming service acting as the **binder** (providing the SLF4J implementation). This decouples the library from any specific logging backend.

## Strategic Status

**Maintenance mode — migration target.**

- The library is actively maintained (Java 21 compiler target, SLF4J 2.0.16, JUnit 5.10.2) and has CodeQL SAST scanning, indicating it is not abandoned.
- However, its core dependency on Apache Axis 1.4 is an architectural liability. The Axis 1.x SOAP stack is EOL and cannot receive security patches through the open-source supply chain.
- The `com.ecount` namespace and the described Tomcat/Windows service deployment model place this firmly in Gen-1 territory.
- Gen-3 migration would typically replace Axis-based SOAP services with REST/gRPC microservices, at which point this library would be superseded by a modern structured logging approach (e.g., OpenTelemetry spans, Micrometer, structured JSON log appenders).
- Until SOAP services are retired or migrated, this library remains essential to PCI DSS log compliance for those services.

## Migration Blockers

1. **Apache Axis 1.4 hard dependency**: `SoapLoggingHandler` extends `org.apache.axis.handlers.BasicHandler` and operates on `org.apache.axis.MessageContext` and `org.apache.axis.Message`. The entire library is tightly coupled to the Axis 1.x API — it cannot function without it. Migration of consuming services to JAX-WS or REST would require a replacement logging solution.
2. **WSDD handler registration**: The integration point (`handler name="SoapLogger" type="java:com.ecount.axis.soap.logging.SoapLoggingHandler"`) is Axis-specific. There is no equivalent mechanism in JAX-WS, Spring-WS, or REST frameworks — migration requires re-implementing the interceptor pattern in the target framework.
3. **`com.ecount` package namespace**: Not directly a migration blocker, but indicates the library has not been refactored to the Onbe namespace, which may cause confusion in mixed-generation environments.
4. **Static version `1.0.0`**: No semantic versioning or SNAPSHOT mechanism is visible in `pom.xml`. Consumers pinned to `1.0.0` will not automatically receive updates, creating drift risk.
5. **Windows/Tomcat deployment assumptions**: The `README.md` documents Windows service registry configuration — these operational procedures must be re-documented and re-tested for any Linux container or cloud-native target deployment.
