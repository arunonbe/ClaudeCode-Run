# Enterprise Architect — onbe-log4j-utils

## Platform Generation
**Gen-2 / Gen-3 Support Library** — targets services on Log4j 2.x, which includes both older Spring MVC apps migrated from Log4j 1 and newer Spring Boot 2/3 services. It is the recommended replacement for onbe-log4j1-utils.

## Business Domain
Cross-cutting: Security / Observability Infrastructure.

## Role in the Platform
Standard log-sanitization filter for all services that have not yet adopted Spring Boot 3.4.0 structured logging. Published as a shared library consumed via GitHub Packages.

## Known Consumers
Any Onbe service that includes `onbe-log4j-utils` in its POM and references `onbe-common-log4j2-spring.xml` or inlines the `<SanitizingFilter/>` in its log4j2 config.

## Dependencies
- Upstream: `org.apache.logging.log4j:log4j-core:2.24.3` and `log4j-api:2.24.3`.
- Test: JUnit Jupiter 5.11.4.
- Build: shared CI workflow.

## Integration Patterns
- Maven dependency injection.
- Log4j 2 plugin mechanism (`@Plugin(name = "SanitizingFilter")`): auto-discovered when the JAR is on the classpath.

## Strategic Status
**Active but transitional** — actively maintained for Gen-2/Gen-3 services on Log4j 2. The README (updated December 2024) recommends Spring Boot 3.4.0 structured logging as the terminal state, suggesting this library is also temporary but on a longer horizon than onbe-log4j1-utils.

## Migration Blockers
1. Services on Spring Boot < 3.4.0 need this library or an equivalent sanitization approach.
2. No automated policy preventing Log4j 2 services from staying on this dependency indefinitely.
3. Dual Java 8 / Java 21 support increases maintenance burden during the migration window.
