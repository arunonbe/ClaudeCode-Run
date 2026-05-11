# Enterprise Architect View — j-integra-j2com_LIB

## Platform Generation
**Gen-1** — Java 6, Spring 2.5.6, jintegra 2.12, log4j 1.2.15, Windows NT service, TIBCO JMS, hardcoded filesystem paths, COM bridge pattern. This is the oldest and most Windows-specific component in the Onbe estate. It represents a bridge from the VBScript/COM scripting world into the Java ecount platform.

## Business Domain
**Platform Integration / Legacy Script Bridge** — Infrastructure bridge enabling Windows COM/script-based automation to call ecount Java services. Used historically by legacy Windows batch scripts, automations, and VBScript tools that predated REST APIs.

## Role
- **Primary role**: Java-COM bridge service exposing ecount platform XML-RPC services as COM-callable objects to Windows VBScript/automation scripts.
- **Consumer pattern**: Legacy Windows scripts and automation tools that cannot call Java/HTTP directly.
- **Services proxied**: Crypto (PGP), StrongBox, Repository, Profile, Member, Transfer, Device, Order, Workflow, Job, Security, Events.

## Dependencies
### Inbound (consumers)
- Windows VBScript / legacy automation tools via COM / jintegra.
- Potentially legacy batch processes and scheduled scripts on Windows servers.

### Outbound (runtime)
| Dependency | Type |
|-----------|------|
| Director service registry | Service discovery (all ecount service endpoints) |
| All ecount XML-RPC services | Platform services (12 service clients) |
| ecount DirectorConfiguredDBCPdatasourceCreator | DB connection factory |
| TIBCO JMS ELF | Transaction logging |
| jintegra 2.12 | COM bridge runtime (commercial) |

## Integration Patterns
- **Java-COM Bridge**: jintegra library exposes Java objects as COM Automation servers.
- **XML-RPC**: All ecount service calls use XML-RPC over HTTP.
- **Director service discovery**: `DirectorServiceLocator` with 40-second cache for service endpoint resolution.
- **Windows NT Service**: Java process hosted as a Windows service for always-on availability.

## Strategic Status
**End-of-Life / Retire** — This library is Gen-1 and has no viable upgrade path:
- jintegra is a commercial Java-COM bridge library; the product has had no significant development since the early 2010s.
- COM-based scripting is incompatible with containerised, cloud-native, or Linux-based infrastructure.
- All the services it proxies now have or should have REST API alternatives.
- The Windows NT service hosting model is incompatible with Kubernetes or Azure App Service.

**Recommended disposition**: Identify all active COM/VBScript consumers; replace each with direct REST API calls or new-platform automation; retire the service once no active consumers remain.

If any consumers are still active, this service presents a significant security risk due to its broad surface area (cryptography, security hierarchy, profile management) exposed via an unaudited COM interface on a Windows host.

## Migration Blockers
1. **Consumer identification**: All VBScript/COM callers must be catalogued. This may require Windows server audit logs or script inventory.
2. **jintegra licensing**: The commercial jintegra library may require vendor engagement to confirm license status; the binary is committed to source.
3. **Crypto operations**: PGP encrypt/decrypt via CryptoService must be migrated to a modern cryptographic API before retiring this bridge.
4. **Windows-only hosting**: No path to containerisation without eliminating the jintegra COM bridge.
5. **ELF logging**: TIBCO JMS ELF logging configuration references Citi-era infrastructure; migration to Azure Monitor required.
6. **Director dependency**: Director service registry dependency shared across many Gen-1 services — retirement of this service must be coordinated with Director decommission timeline.
