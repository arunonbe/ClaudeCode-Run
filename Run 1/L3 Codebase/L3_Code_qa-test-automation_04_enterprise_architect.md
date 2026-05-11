# Enterprise Architect View — qa-test-automation

## Platform Generation

This repository is firmly Gen-1 (eCount/Citi). All tested services are in the `com.ecount.*`, `com.citi.prepaid.*`, and `com.citi.prepaid.service.*` namespaces. The dependency list confirms integration with Gen-1 services:
- `director-client:2.0.0-beta` — eCount Director routing service
- `repository-common/client/svc:3.0.0-SNAPSHOT` — eCount Repository service
- `strong-box-common/client:4.0.0-SNAPSHOT` — eCount StrongBox key vault
- `xsecurity-client:4.0.0-SNAPSHOT` — eCount security service
- `ecount-core-client:2.0.0-SNAPSHOT` — eCount Core service
- `orderxmlrpcclient:2.0.0-SNAPSHOT` — Order service XML-RPC client

The runtime container uses Java 21 (modern), but the application dependencies are legacy Gen-1 SNAPSHOT artifacts that depend on XML-RPC as the transport protocol.

## Integration Patterns

The dominant pattern is **client-side service virtualization testing** — the test framework acts as a direct consumer of Gen-1 services over XML-RPC, verifying that the service contracts remain intact. This is black-box integration testing at the transport layer, not unit or component testing.

Each test specification wires a Spring `@ContextConfiguration` from an XML configuration file in `src/test/resources/cbase/config/`, which mirrors the configuration used by production clients. This tight coupling to Spring XML application contexts is characteristic of the Gen-1 eCount architecture.

The XML-RPC transport (`xmlrpc-*` dependencies from the eCount order service) places this repository in the same lineage as other eCount XML-RPC consumers. XML-RPC is a Gen-1 protocol with no Gen-2 or Gen-3 analog.

## External Dependencies

- **QA environment endpoint**: `http://ppnaut.nam.wirecard.sys:8080` — an internal Wirecard/Northlane DNS name in the `.wirecard.sys` domain. This indicates Gen-2 (Wirecard) infrastructure hosting the QA environment for Gen-1 services, which is a cross-generation dependency.
- **GitHub Package Registry**: Onbe's internal Maven package registry (authenticated via PAT).
- **Azure Container Registry**: Docker image publishing destination.
- **Onbe/om-ci-setup**: Shared composite GitHub Actions CI library.

## Position in the Broader Platform

`qa-test-automation` occupies the cross-cutting QA tooling layer, sitting above the Gen-1 service layer. Its architectural position:

```
[qa-test-automation Docker container]
    → XML-RPC → [Director, Repository, StrongBox, Notification, OrderService, CryptoService]
                       (Gen-1 eCount platform services)
                                → [Fiserv processor, DDA backends]
                                → [qa-mocking-service] (when Fiserv is mocked)
```

There is no direct dependency on Gen-3 services (Azure Service Bus, AKS workloads, NexPay APIs).

## Migration Blockers

The primary migration blocker is the XML-RPC transport. XML-RPC clients generated from the eCount codebase cannot be retargeted to REST/gRPC without replacing the underlying service client libraries. Migration to Gen-3 test automation would require:

1. Replacement of all XML-RPC client beans (`director-client`, `orderxmlrpcclient`, etc.) with REST API clients for the successor services.
2. Re-expression of all Spock specifications against new REST contracts.
3. Replacement of Spring XML `ContextConfiguration` with Spring Boot test slice annotations.

These are non-trivial changes requiring coordination with service teams.

## Strategic Status

**Active but legacy; medium-term sunset candidate.** As Gen-1 eCount services are decommissioned or replaced by Gen-3 equivalents, this test automation repository will progressively lose coverage targets. The recommended strategic path:

1. Maintain as-is for Gen-1 services still in production.
2. Do not invest in extending XML-RPC test coverage for new features.
3. Create a parallel Gen-3 test automation framework (Spring Boot, REST Assured or Spock+RestTemplate) for new services.
4. Archive this repository once the last XML-RPC service it covers is decommissioned.
