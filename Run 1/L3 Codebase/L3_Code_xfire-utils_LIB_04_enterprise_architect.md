# xfire-utils_LIB — Enterprise Architect View

## Platform Generation
**Gen-1** — Definitively legacy infrastructure component.

Evidence:
- XFire 1.2.4 (2007; last release before the project was donated to Apache as Apache CXF)
- Spring 2.0.2 (2006 era)
- ActiveMQ 4.1.0-incubator (pre-release, circa 2006–2007)
- `geronimo-spec-*` J2EE spec JARs (J2EE 1.4 era)
- SVN origin (`ecsvn.office.ecount.com`) — predates Git adoption at the company
- `com.ecount.xfire` groupId — ecount-era naming
- Parent POM `com.ecount:module-parent:1` — earliest generation of the ecount module hierarchy
- `1.0.0-SNAPSHOT` — never released; in perpetual draft since inception
- Apache incubating Maven repository (defunct)

## Business Domain
**Platform Infrastructure — SOAP Transport Layer**

This library is pure infrastructure: it provides the transport mechanism for SOAP-based inter-service communication in the Gen-1 platform. It has no business domain by itself.

## Role in Platform
- **Foundational transport library**: Used by any Gen-1 service that needs to consume or produce SOAP web services via XFire
- **Spring integration bridge**: Bridges XFire SOAP with Spring IoC — allows SOAP clients to be declared as Spring beans
- **JMS/SOAP bridge**: Enables SOAP message routing over JMS queues — critical pattern in the Gen-1 asynchronous messaging architecture
- **Likely transitive dependency**: Many Gen-1 services in the estate may depend on this library indirectly through other libraries (e.g., `xsecurity_SVC`, `xsearch_LIB`, `xplatform_LIB`)

## Dependencies
**Inbound consumers (known/inferred):**
- Any Gen-1 service in the `xfire-utils`, `xplatform`, or `xsecurity` dependency chain

**Outbound:**
- XFire 1.2.4 framework
- Spring 2.0.2
- JMS providers (runtime: TIBCO, WebLogic, ActiveMQ)
- WSDL-described SOAP endpoints (dynamic, resolved at runtime)

## Integration Patterns
- **SOAP/WSDL**: XML-based service contract; WSDL-first or interface-first service creation
- **Spring FactoryBean pattern**: `XFireClientFactoryBean` implements Spring's `FactoryBean<T>` — transparent proxy injection into any Spring-managed consumer
- **Proxy pattern**: `ProxyInterceptor` for lazy initialization of client proxies
- **JMS transport substitution**: XFire's pluggable transport architecture used to route SOAP over JMS — advanced pattern for the era, but completely superseded by REST/message-based microservices today

## Strategic Status
**Retire — High Priority**

- XFire has been EOL since 2007; Apache CXF is the successor
- All services depending on this library are Gen-1 candidates for migration/replacement
- The SOAP-over-JMS pattern is superseded by modern event-driven architectures
- No active consumers should remain after Gen-1 platform retirement
- This library should be retired as part of the Gen-1 → Gen-3 migration wave, not upgraded or maintained

## Migration Blockers
1. **Unknown consumer surface**: Without a full dependency audit across all repos, it is not known how many services depend on this library directly or transitively
2. **XFire service contracts**: All services that use this library expose or consume XFire-generated WSDL contracts; migration requires replacing all endpoints and updating all consumers simultaneously
3. **JMS-over-SOAP pattern**: The `xfire-utils-springjms` module enables an unusual SOAP-over-JMS transport; identifying all consumers and their JMS queue dependencies is required before retirement
4. **`module-parent:1` parent POM**: The root parent POM (`com.ecount:module-parent:1`) may version-constrain other Gen-1 libraries; changing the xfire-utils parent chain could have cascading effects
5. **Defunct Maven artifacts**: `activemq-core:4.1.0-incubator` from `people.apache.org/repo/m2-incubating-repository` — may only be available from local Nexus/Artifactory cache; if that cache is cleared, the library cannot be built
