# Solution Architect — wirecard_funds-transfer-coordinator_LIB

## Technical Architecture
- **Framework**: Spring Boot 2.0.7.RELEASE, Spring Cloud Finchley, Java 8
- **Modules**: 9 Gradle subprojects (config, data, service, batch, rest-controller, qa, db-scripts, db-app, check-agent-client, documentation)
- **Persistence**: JPA/Hibernate 5.3.7 with Envers auditing; Liquibase 3.6.3 managed schema; HikariCP connection pool (min 10, max 50)
- **Messaging**: Wirecard EventHub client (ActiveMQ transport) for inbound/outbound events
- **REST clients**: Spring Cloud OpenFeign 2.1.1 with Resilience4j 1.2.0 circuit-breaker
- **Scheduling**: Spring Quartz 2.3.0, JDBC job store, clustered, 5 threads
- **Email**: Spring Integration JMS gateway; SMTP via Spring Mail
- **Expression evaluation**: Apache Commons JEXL3 for configurable amount calculation logic
- **API documentation**: Springfox Swagger 2.8.0

## API Surface
| Endpoint | Method | Description |
|---|---|---|
| `/funds-transfer-coordinator/v1/trigger-configurations` | POST/GET/PUT | Create/retrieve/update trigger rules |
| `/funds-transfer-coordinator/v1/trigger-configurations/{id}` | GET/PUT/DELETE | Individual trigger CRUD |
| `/funds-transfer-coordinator/v1/quartz/...` | GET/POST | Quartz job management (pause, resume, status) |
| `/funds-transfer-coordinator/monitoring/*` | GET | Spring Boot Actuator (health, info, metrics, etc.) |

Auth: OAuth2 Bearer token validated against ISS Auth Server JWT key-set; `resource-id: callcenter-api`

## Security Posture

### Authentication / Authorisation
- OAuth2 resource server (`iss-resource-server:1.0.5.RELEASE`) validates JWT tokens
- `SecurityAutoConfiguration` excluded; custom OAuth2 filter chain applied
- REST endpoints require valid JWT; no fine-grained role mapping observed in source

### Cryptography
- TLS for Oracle DB connection: JKS truststore loaded from Base64 content at startup (`DataSourceConfiguration.java:33`)
- No column-level encryption
- Transport security for CCP/check-agent calls depends on Feign/OkHttp defaults — not explicitly configured in source

### Secrets Management
- Credentials in `application.yml` are development placeholders; production injection mechanism not visible in this repo (likely Puppet/Ansible `application.conf` overlay)
- **Risk**: `password: [REDACTED — rotate immediately]`, `callcenter_QA` visible in source YAML — must confirm these do not reach production

### Known CVEs (library-level risk)
| Library | Version | Known Risk |
|---|---|---|
| Spring Boot | 2.0.7.RELEASE | EOL since Oct 2019; numerous CVEs including RCE via Actuator if misconfigured |
| Spring Security OAuth2 | 2.3.3.RELEASE | CVE-2019-3778 (open redirect); EOL |
| spring-security-jwt | 1.0.9.RELEASE | Dependency of OAuth2; EOL |
| commons-collections | 3.2.2 | Historic RCE vector; safe if not deserialising untrusted data |
| Hibernate | 5.3.7.Final | Multiple CVEs in later minor versions; 5.3.x is maintenance only |
| H2 Database | 1.4.199 | CVE-2021-42392 (RCE via JNDI in H2 console) — h2-console enabled in base YAML |
| Logstash-logback-encoder | 5.0 | Old; no direct CVE but unsupported |

## Technical Debt
1. `gradle:4.8-jdk8` CI image — Java 8 and Gradle 4.8 are both end-of-life
2. Deprecated Gradle `compile` configuration used throughout (removed in Gradle 7)
3. `bootRepackage` used (Spring Boot 1.x Gradle plugin syntax) despite Spring Boot 2.x — indicates mixed migration state
4. TODO comments in production config: `checkagent.client.username: callcenter_QA //TODO`
5. Commented-out code in `PerformanceTracingConfiguration.java`-style pattern exists in FTC context classes
6. JmsAutoConfiguration excluded with comment "conflicts with EventHub library" — library-level conflict indicating tech debt
7. Swagger 2.8.0 (Springfox) — not maintained; OpenAPI 3 not adopted
8. `commons-io:2.4` — outdated; current is 2.15+
9. Application.yml has `transaction.default-timeout` with empty value — not explicitly set

## Gen-3 Migration Requirements
1. Replace Spring Boot 2.0.7 with Spring Boot 3.x (Java 17+)
2. Replace EventHub/ActiveMQ with cloud-native messaging (Kafka or Azure Service Bus)
3. Replace Feign + Resilience4j 1.x with Spring WebFlux / WebClient + Resilience4j 2.x
4. Replace Oracle + Liquibase with cloud-managed PostgreSQL or Azure SQL; review synonym/two-schema approach
5. Replace Quartz JDBC cluster with managed scheduler (Azure Scheduler, AWS EventBridge, or Quartz on managed DB)
6. Replace ISS Auth Server with Onbe cloud identity provider
7. Containerise: Dockerfile + Helm chart / ECS task definition; remove RPM/Ansible
8. Externalise all secrets to Azure Key Vault / AWS Secrets Manager
9. Replace Springfox with springdoc-openapi (OpenAPI 3)
10. Remove H2 console from all non-local profiles

## Code-Level Risks
| File | Line | Risk |
|---|---|---|
| `funds-transfer-coordinator-config/src/main/resources/application.yml` | 143 | Hardcoded CCP password `[REDACTED — rotate immediately]` |
| `funds-transfer-coordinator-config/src/main/resources/application.yml` | 157-159 | Check-agent TODO credentials |
| `funds-transfer-coordinator-config/src/main/resources/application.yml` | 43-44 | H2 console enabled with path exposed |
| `funds-transfer-coordinator-config/src/main/resources/application.yml` | 130-131 | ActiveMQ credentials `local/local` |
| `DataSourceConfiguration.java` | 33 | TLS truststore content decoded from property; if property is empty, TLS silently disabled |
| `FundsTransferCoordinatorApplication.java` | 27 | `SecurityAutoConfiguration.class` excluded — security misconfiguration risk if wrong profile applied |
| `build.gradle` | 17-20 | Nexus repo uses HTTP not HTTPS (`http://d-issrepo-app01`) — artifact integrity at risk |
