# Enterprise Architect View — jakarta-migrator

## Platform Generation

`jakarta-migrator` is a **platform migration enabler**, not an application or service in its own right. It spans generations:
- It exists because of **Gen-1/Gen-2 technical debt**: legacy libraries compiled against `javax.*` (Java EE) that cannot run on the Jakarta EE 10 runtime required by Spring Boot 3.x (the Gen-3 framework baseline).
- It directly enables **Gen-3 adoption**: without the migrated `jakarta-acegi-security` JAR, any Gen-3 service that transitively depends on Acegi Security would fail at startup with `NoClassDefFoundError` or namespace resolution failures.

## Business Domain

Not aligned to a payment or product domain. This is a **platform infrastructure artifact** in the Architecture domain. Its stakeholders are development teams and the platform/architecture governance function.

## Role in the Portfolio

```
Legacy prepaid platform (javax.* runtime: Tomcat 8.5, Spring 4.x)
    │
    │  Jakarta EE 10 runtime gap (javax → jakarta)
    │
    ▼
jakarta-migrator (build-time bytecode transformer)
    │  produces migrated JARs:
    │    jakarta-acegi-security:1.0.3
    │    jakarta-axis:1.4              (completed, module commented out)
    │    jakarta-spring-remoting:2.0.8 (completed, module commented out)
    │    ...
    ▼
Gen-3 services (Spring Boot 3.x, Jakarta EE 10, Java 21+)
    e.g., ivr-ws_API, manage-payment-rest-api
```

The manage-payment-rest-api's `pom.xml` directly lists `jakarta-spring-remoting`, `jakarta-axis-jaxrpc`, `jakarta-axis-saaj`, and `jakarta-axis-wsdl4j` as dependencies — confirming that `jakarta-migrator`'s outputs are consumed by production Gen-3 payment services.

## Dependencies

| Dependency | Direction | Artifact |
|---|---|---|
| `prepaid-parent:6.0.10` | Upstream (build parent) | POM inheritance |
| `org.acegisecurity:acegi-security:1.0.3` | Upstream (source) | Input JAR to transform |
| Maven Central / Nexus | Upstream (repository) | Source JAR resolution |
| GitHub Packages | Downstream (registry) | Publish target |
| Nexus | Downstream (registry) | Publish target |
| `manage-payment-rest-api` | Downstream (consumer) | Consumes `jakarta-axis-*`, `jakarta-spring-remoting` |
| `ivr-ws_API` | Downstream (consumer) | Consumes `jakarta-axis-*` |

## Integration Patterns

- **Build-time transformation**: Eclipse Transformer Maven Plugin intercepts the package phase and re-signs the bytecode. No runtime integration patterns apply.
- **Maven artifact registry**: Follows standard Maven artifact publish/consume pattern.
- **Shared library distribution**: Migrated JARs are transitive dependencies consumed via Maven; consuming teams do not directly interact with this repository.

## Strategic Status

**Transitional / Planned Obsolescence**

The correct long-term trajectory for every module in `jakarta-migrator` is removal:
1. `jakarta-axis-*` modules — Replace with Apache CXF 4.x (native Jakarta EE 10 support). Apache Axis 1.4 is end-of-life and has known CVEs.
2. `jakarta-spring-remoting` — Spring Remoting was removed from Spring Framework 6.x. Its use indicates RMI or HTTP invoker patterns that should be replaced with REST/gRPC.
3. `jakarta-acegi-security` — Replace with Spring Security 6.x (native Jakarta EE 10). Acegi Security 1.0.3 is ~2007 vintage, unsupported, and has known vulnerabilities.

The presence of the active `acegi-security` module signals that at least one production service still depends on Acegi Security rather than Spring Security 6. This is a migration blocker that should be tracked in the architecture backlog.

## Migration Blockers

| Blocker | Affected Service(s) | Resolution Path |
|---|---|---|
| Acegi Security dependency | Unknown (service not identified in repo scan) | Migrate to Spring Security 6.x; retire `jakarta-acegi-security` |
| Spring Remoting usage | `manage-payment-rest-api`, `ivr-ws_API` | Replace Spring Remoting with REST/OpenFeign; retire `jakarta-spring-remoting` |
| Apache Axis SOAP | `manage-payment-rest-api`, `ivr-ws_API` | Replace Apache Axis with Apache CXF 4.x or Spring WS; retire `jakarta-axis-*` |

## Enterprise Risk

The continued existence of this project in its current form (active module count: 1) suggests the Axis and spring-remoting migrations are completed for Gen-3 but consuming services have not yet fully migrated away from the legacy patterns. The architecture team should validate that no new services are introduced that take transitive dependencies on `jakarta-axis-*` or `jakarta-spring-remoting` as a permanent solution rather than a migration step.

**Key architecture governance recommendation**: Establish a migration completion date for the remaining `acegi-security` consumer and sunset the `jakarta-migrator` project entirely once all consuming services have migrated to Spring Security 6.
