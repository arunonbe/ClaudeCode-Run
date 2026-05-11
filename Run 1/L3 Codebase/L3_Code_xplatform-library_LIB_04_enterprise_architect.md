# Enterprise Architect View — xplatform-library_LIB

## Platform Generation
**Gen-1** — Foundational infrastructure library. The oldest layer of the eCount platform stack. Many components (DES cipher, ORO regex, custom RPC, Jsafe SDK) date to early-2000s Java programming patterns.

## Business Domain
Infrastructure / Cross-cutting concerns. No specific business domain — this library underpins all domains by providing cryptography, caching, configuration, logging, networking, and SQL access primitives.

## Role in the Platform
**Platform foundation.** This is the lowest layer in the dependency stack:
```
xplatform-library_LIB  (this repo — infrastructure)
        |
        v
xplatform_LIB  (business logic)
        |
        v
xsearch_LIB, xsso_SVC, and all other services
```
Every service that uses xplatform_LIB transitively depends on this library.

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| request-context (`com.citi.prepaid.module`) | Upstream | Citi-branded request context |
| SwarmCache / JGroups | External | Distributed cache transport |
| ORO | External | Legacy dormant regex library |
| regexp | External | Legacy regex library |
| Jsafe | External | RSA Data Security commercial crypto SDK |
| Spring Context | Framework | IoC container |
| Commons Text / Commons Pool2 | Framework | String utilities, object pooling |

## Consumers
- `xplatform_LIB` (direct)
- All services that depend on `xplatform_LIB` (transitive)

## Integration Patterns
- **Library pattern** — compiled JAR, no network surface
- **Factory pattern** — `CryptoFactory`, `CacheManager` for creating/managing instances
- **SPI (Service Provider Interface)** — `StrongBox` data store and key store; pluggable implementations
- **Custom RPC** — `ECount.System.RPC.*` implements a proprietary HTTP-based RPC mechanism (not REST, not SOAP, not gRPC)
- **JGroups multicast** — distributed cache synchronisation

## Strategic Status
**Stabilise, then replace components incrementally.** Key observations:
- Version `4.2.0` released (not SNAPSHOT) — stability is improving
- The RPC framework (`ECount.System.RPC`) is proprietary — services using it cannot be independently scaled or monitored
- Multiple broken cryptographic algorithms (DES, RC4, MD5, SHA1) must be formally deprecated and removed
- SwarmCache / JGroups must be replaced with a cloud-native cache (Redis, Hazelcast, Azure Cache)
- The Jsafe SDK must be replaced with a standard JCA provider or HSM integration
- `request-context` from `com.citi.prepaid.module` should be re-evaluated for Onbe ownership

## Migration Blockers
- Pervasive transitive dependency — replacing this library requires coordinated changes across all consuming services
- Custom RPC framework — any service using `ECount.System.RPC` must be migrated to a standard protocol (REST/gRPC) before the RPC classes can be removed
- JGroups multicast — SwarmCache replacement requires deploying a new cache infrastructure and coordinating cache population across all services
- `Windows-1252` encoding — if any class files contain non-ASCII characters, changing the source encoding requires careful validation
- Jsafe SDK — replacing proprietary crypto with JCA requires verification that all encrypted data can be re-read after migration (key migration plan needed)
- ORO and `regexp` — removing these requires identifying all call sites in xplatform_LIB and replacing with `java.util.regex`
