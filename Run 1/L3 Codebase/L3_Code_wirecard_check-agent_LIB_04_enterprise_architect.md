# Enterprise Architect — wirecard_check-agent_LIB

## Platform Generation
**Gen-2** (Wirecard/Northlane issuing platform). Indicators:
- Spring Boot 1.5.13 (released 2018) — Gen-2 Wirecard platform baseline.
- Gradle 4.8 with JDK 8.
- GitLab CI pipeline (Wirecard-era CI/CD platform).
- RPM packaging + Ansible rolling-update deployment pattern (Wirecard infrastructure model).
- Wirecard internal Nexus and `.wirecard.sys` DNS hostnames for all dependencies.
- Oracle Database as primary persistence.

## Business Domain
**Payment Disbursements — Check Issuance**. Core business domain: issuing physical paper checks to beneficiaries as a form of payment disbursement. Part of the broader Northlane (formerly Wirecard North America) prepaid card and disbursement platform.

## Role in the Architecture
- **Core disbursement microservice** for the check payment rail.
- **Upstream dependencies**: Wirecard CCP (fund reservation), ISS Auth Server (JWT validation), Brand Server (check templates).
- **Downstream dependencies**: Check printing/mailing system (consumes `NewCheckEvent` / `VoidCheckEvent` from EventHub); monitoring/alerting via email.
- **Shared library**: Despite the `_LIB` suffix, this is a full microservice (Spring Boot application, REST controllers, database, EventHub). The suffix likely refers to its internal Gradle multi-module library structure rather than being a compile-time library only.

## Dependencies
| Dependency | Type | Direction |
|---|---|---|
| Wirecard CCP (Horus) | HTTP REST API | Outbound — fund reservation |
| Wirecard Brand Server | HTTP REST API | Outbound — check template config |
| Wirecard ISS Auth Server | HTTP (JWK Set) | Outbound — JWT public key retrieval |
| Oracle Database | JDBC | Outbound |
| ActiveMQ EventHub | JMS/messaging | Bidirectional (produce + consume) |
| SMTP server | Email | Outbound — operational alerts |

## Integration Patterns
- **REST S2S/S2C**: Synchronous REST API for check creation/management.
- **Event-driven (EventHub)**: Asynchronous publication of `NewCheckEvent` and `VoidCheckEvent`; asynchronous consumption of `CheckStatusUpdatedEvent`.
- **Idempotent consumer**: `@IdempotentSubscriber` AOP pattern ensures exactly-once processing of inbound events.
- **Retry batch**: Spring Batch job to retry failed EventHub publications.
- **OAuth2 Resource Server**: JWT token validation against ISS Auth Server's JWK Set.

## Strategic Status
- **Active Gen-2 service requiring urgent migration planning**: Spring Boot 1.5.13 is 6+ years past EOL. This service handles payment disbursements and is PCI-scope relevant.
- **High migration priority**: Given check payment volumes and PCI scope, this service should be on the Gen-3 migration roadmap.
- **Wirecard infrastructure dependencies are a blocker**: CCP, Brand Server, ISS Auth Server are Wirecard/Northlane-internal services with `.wirecard.sys` DNS names. Migration requires either migrating these upstream services first or implementing adapter patterns.

## Migration Blockers
1. **Spring Boot 1.5.13 (EOL)**: Requires upgrade through 2.x to 3.x. Breaking changes include removal of `spring-security-oauth2` in favour of Spring Authorization Server, removal of `javax.*` in favour of `jakarta.*`, Hibernate 6.x JPA changes.
2. **`spring-security-oauth2`**: Used for OAuth2 resource server (JWT validation). This library is deprecated and removed in Spring Security 5.8+. Must migrate to `spring-security-oauth2-resource-server`.
3. **JDK 8 → JDK 21**: Likely straightforward but requires testing of Oracle JDBC driver compatibility, JMX/management endpoint behaviour, and JVM flag changes.
4. **ActiveMQ EventHub**: If the Gen-3 platform uses Azure Event Hub, AWS SQS/SNS, or Kafka instead of ActiveMQ, the event consumer/producer must be re-implemented.
5. **`.wirecard.sys` DNS**: Internal hostnames for CCP, Brand Server, and Auth Server. Migration requires updated service endpoint configuration and potentially API contract changes.
6. **Oracle DB**: If Gen-3 targets a different database (e.g., Azure SQL, PostgreSQL), Liquibase changelogs contain Oracle-specific DDL and synonyms that must be ported.
7. **RPM packaging**: Gen-3 likely targets container/Kubernetes deployment. RPM packaging and `nebula.rpm` plugin must be replaced with Docker/OCI image builds.
