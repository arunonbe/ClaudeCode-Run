# Enterprise Architect Report: spring-dbctx_LIB

## Platform Generation

**Gen-1 / Gen-2 shared infrastructure library**. The library's groupId `com.citi.prepaid.spring-dbctx` places its origin in the Citi/eCount era (Gen-1). Its database inventory (`greatplains`, `webcertomaha`, `ecountcore`, `strongbox`) maps exactly to the Gen-1 eCount/Citi platform schema partitions. It has been carried forward into the Gen-2 (Wirecard/Northlane) era as-is, with the compiler target updated to Java 21 but the fundamental design (Spring XML beans, JNDI DataSources) unchanged.

## Integration Patterns

- **Library-as-configuration**: Rather than copy-pasting Spring XML beans, services declare a Maven dependency on `spring-dbctx` and import the relevant classpath XML resource. This is a Gen-1 idiom for DRY configuration management
- **JNDI-based credential injection**: Credentials are not in the library; they are injected through the application server JNDI namespace — a correct separation of concerns for its era
- **TransactionAwareDataSourceProxy pattern**: Every DataSource is wrapped to participate in Spring's `PlatformTransactionManager` ecosystem — compatible with `@Transactional` annotations even in XML-configured contexts

## External Dependencies

- Spring Framework (spring-jdbc, spring-context): version managed by `prepaid-parent:6.0.12`
- Internal Nexus/GitHub Packages Maven repository for publishing
- All consuming services: `spring-dbctx` is a transitive dependency for most Gen-1/Gen-2 services; removing or changing it affects the entire fleet

## Position in the Broader Platform

`spring-dbctx_LIB` is the **data access foundation layer** for the Gen-1/Gen-2 platform. It establishes the canonical database partition names and JNDI naming conventions used across the fleet. Its database inventory is the definitive map of the logical data tier:

- **Core cardholder data tier**: ecountcore, cbaseapp
- **Financial/GL tier**: greatplains
- **Operational services tier**: jobsvc, ordersvc, request, repositorysvc
- **Security/cryptography tier**: strongbox
- **Network certification tier**: webcertomaha

The library's nine-database inventory reveals the complete domain decomposition of the Gen-1 platform's data — a valuable artefact for understanding data ownership boundaries.

Gen-3 services (NexPay/Onbe, Azure, Spring Boot 3.x) do not use this library; they use Azure SQL with Spring Data JPA and Azure Key Vault for credentials. Gen-3 introduces its own database naming conventions, creating a parallel data layer that must eventually be reconciled or unified.

## Migration Blockers

1. **Fleet-wide JNDI dependency**: Every Gen-1/Gen-2 service that uses `spring-dbctx` depends on JNDI, which requires a servlet container. Migrating these services to Spring Boot embedded server means replacing all JNDI DataSource imports with `spring.datasource.*` properties or `@Bean DataSource` definitions
2. **XML-only configuration**: The library provides only XML bean definitions; there are no Java-config equivalents or Spring Boot autoconfiguration starters. Creating Spring Boot-compatible equivalents requires writing a new library
3. **Shared versioning**: Because one library version serves the entire fleet, any migration must be done library-version by library-version, with consuming services opting into the new version — a coordinated upgrade challenge at fleet scale
4. **StrongBox DataSource coupling**: The `strongbox` DataSource is bundled with all operational DataSources in the same library; separating cryptographic key management access into a distinct, more strictly controlled library would improve security but requires a cross-fleet change

## Strategic Status

**Freeze and gradually sunset**. This library should not receive feature additions; the current 2.0.1 release should be declared stable-and-frozen. As Gen-2 services migrate to Gen-3, their dependency on this library should be removed. The library should be archived when no Gen-2 consumers remain.

Immediate action: audit all consumers of `com.citi.prepaid.spring-dbctx:spring-dbctx` in the Maven dependency graph (or GitHub Packages downloads) to establish the consumer list and prioritise migration planning. The `strongbox` DataSource consumer list is particularly important for PCI DSS access control review.
