# Enterprise Architect View — xplatform_LIB

## Platform Generation
**Gen-1** — Core platform library. Foundational to the entire eCount/Onbe prepaid platform. Despite Java 21 compiler targeting (a modernisation effort), the domain model, patterns, and dependencies are Gen-1 in heritage.

## Business Domain
Cross-cutting platform core. Spans all business domains:
- Cardholder lifecycle (member registration, account management)
- Affiliate / partner management
- Payment processing support (job account mapping, pre-check definitions)
- Cross-border transfer (CBTS integration)
- CSA / customer support (ticket management)
- Notification (email)

## Role in the Platform
**Load-bearing platform library.** This is the shared kernel consumed by every major downstream service. It defines the canonical domain objects (Affiliate, Member, ECard, Device) and the authoritative business logic for the eCount platform. No service can operate without it.

## Dependencies
| Dependency | Direction | Notes |
|---|---|---|
| xplatform-library_LIB (`xplatformlibrary 4.2.0`) | Upstream | Low-level infrastructure: crypto, cache, config, logging, networking |
| cbtsclient 2.1.5 (Wirecard CBTS) | External | Cross-border transfer service client — Wirecard-heritage |
| eCount Core Database (SQL Server) | External | Primary data store; JNDI-injected |
| JobSvc Database (SQL Server) | External | Job processing data; JNDI-injected |
| msal4j (Microsoft Azure) | External | Azure AD token acquisition |
| Hibernate Core | Framework | ORM for entity persistence |
| XStream | Framework | XML serialisation |
| spring-jdbc | Framework | JDBC template for non-Hibernate queries |

## Consumers (known from this analysis)
| Consumer | Version Pinned |
|---|---|
| xsso_SVC | 6.1.8 |
| xsearch_LIB | 6.0.1 |

## Integration Patterns
- **Shared library pattern** — compiled JAR consumed by all platform services
- **Factory + Cache pattern** — `AffiliateFactory` / `CacheableObjectFactoryImpl` for affiliate objects
- **Manager pattern** — `MemberManagerImpl`, `EManageManagerImpl` as orchestrators over DAOs
- **RPC (CBTS)** — synchronous RPC calls to Wirecard cross-border transfer service
- **JNDI DataSource injection** — database connections resolved via container JNDI

## Strategic Status
**Maintain with modernisation path.** Key observations:
- Java 21 compiler adoption is positive
- SNAPSHOT versioning (`6.5.9-SNAPSHOT`) indicates active development
- The Wirecard CBTS dependency (`cbtsclient 2.1.5`) must be replaced or migrated to a supported vendor
- `msal4j` inclusion suggests partial Azure modernisation is underway
- The library is architecturally monolithic — all domains are bundled together, creating high coupling
- Long-term target should be domain decomposition (break into affiliate-service, member-service, etc.)

## Migration Blockers
- Pervasive coupling: every downstream service imports this library — any breaking API change requires coordinated release across all consumers
- CBTS client (`cbtsclient`) — if this vendor relationship is active, replacing it requires negotiation with the payment network
- Hibernate ORM entity mappings — migrating to a different persistence strategy requires rewriting all entity mappings
- `CacheableObjectFactoryImpl` / SwarmCache — cache eviction and consistency behaviour must be replicated in any replacement architecture
- No API versioning strategy — consumers depend on the exact method signatures of business managers
