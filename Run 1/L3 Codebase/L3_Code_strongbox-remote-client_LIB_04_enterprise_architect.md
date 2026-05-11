# Enterprise Architect Report: strongbox-remote-client_LIB

## Platform Generation

**Gen-2 (Wirecard/Northlane)**. The groupId `com.northlane` and the SCM URL (`gitlab.com/northlane/...`) confirm this library was developed during the Wirecard/Northlane era. Its Java 8 compile target and Spring 4.x dependency place it at the lower end of Gen-2 vintage — earlier than the Spring Boot 2.x services that form the core of Gen-2. It appears to be an adapter library created by the Northlane team to allow their Spring-based services to communicate with the inherited eCount/Citi Gen-1 StrongBox XML-RPC service.

## Integration Patterns

- **XML-RPC over HTTP**: The library wraps the Apache XML-RPC protocol used by the Gen-1 StrongBox service. XML-RPC is a predecessor to SOAP and REST, using HTTP POST with XML payloads
- **Strategy pattern for transport**: The `ReadMapXmlRemoteCall` and `WriteMapXmlRemoteCall` lambda interfaces allow callers to inject the specific HTTP transport implementation (connection parameters, retry logic, authentication) without changing the library's serialisation logic
- **Spring `@Component`**: `StrongBoxRemoteServiceImpl` is Spring-managed, enabling autowiring into any Gen-2 Spring service
- **XmlRPC serialisation**: Uses the internal Citi XML-RPC utilities (`XmlRPCFromObjectMapper`, `XmlRPCToObjectMapper`) for object-to-XML-RPC and back — these are proprietary formats tied to the Gen-1 platform

## External Dependencies

- `com.citi.prepaid.service.core:xmlrpc:2.0.0-SNAPSHOT` — internal Citi-era XML-RPC utilities; SNAPSHOT version; hosted on the old Wirecard Nexus
- `com.ecount.service.core.ecountcore:common:2.0.1` — eCount core common library
- `org.springframework:spring-core:4.3.27.RELEASE` — EOL Spring Framework
- StrongBox XML-RPC service at a network-reachable HTTP endpoint (connection details configured by callers via lambda)

## Position in the Broader Platform

This library sits at the intersection of the Gen-1 and Gen-2 platform layers. Its role:

- **Gen-1 StrongBox service** (XML-RPC, Java servlet, eCount-era) provides the actual key vault functionality
- **This library** adapts the Gen-1 XML-RPC interface for use by Gen-2 Spring services
- **Gen-2 services** autowire `IStrongboxRemoteService` and use it to read/write secrets from the Gen-1 vault

The library is a **glue layer** — it exists because Gen-1 (StrongBox XML-RPC) and Gen-2 (Spring REST/component-based) were never replaced by a unified key management solution. The continued existence of this library is an indicator that the StrongBox Gen-1 service has not been replaced by a modern HSM or cloud-native key management system (Azure Key Vault, AWS KMS, HashiCorp Vault).

Gen-3 services use Azure Key Vault directly and do not use this library. The split creates a two-tier key management architecture:
- Gen-1/Gen-2: StrongBox (XML-RPC, SQL Server-backed, RSA keys co-located with ciphertext in DB)
- Gen-3: Azure Key Vault (cloud-native, HSM-backed, keys separate from data)

## Migration Blockers

1. **Proprietary XML-RPC format**: The serialisation format used by StrongBox is the internal Citi XML-RPC format, not a public standard; migrating to a different vault requires re-encrypting all secrets stored in StrongBox format
2. **Gen-1 StrongBox dependency**: This library is useful only as long as the Gen-1 StrongBox XML-RPC service is running; decomissioning StrongBox requires all consumers to migrate to an alternative before this library can be retired
3. **Secret format coupling**: Secrets stored via this library are in StrongBox reference format; any migration requires reading all secrets via this library, re-encrypting with the new vault, and updating all references in every consuming service's configuration
4. **Consumer inventory unknown**: There is no visibility from this repository into which Gen-2 services consume it; a dependency graph analysis of the Maven artifact is required before migration planning

## Strategic Status

**Decommission target — but blocked on StrongBox migration**. This library should not be used for new development. Gen-3 services must use Azure Key Vault directly. The Gen-2 consumer services that use this library should migrate to Azure Key Vault as part of their Gen-3 upgrade. The StrongBox service and this library can then be decommissioned together.

The migration path is: Gen-2 service → Azure Key Vault (with Managed Identity) → retire StrongBox reference for that service → when all services migrated, decommission StrongBox service and this library.

Immediate risk mitigation: upgrade Spring to 5.3.x or 6.x, upgrade Java target to 17 or 21, and fix the placeholder logger name. These changes can be made without affecting the API surface.
