# job_LIB — Solution Architect View

## Technical Architecture

- **Language**: Java (target compatibility not explicitly set in sub-module POMs; inherited from `com.citi.prepaid.service.job` parent which historically targets Java 8 or lower)
- **Framework**: Spring Framework (XML-based context, no Spring Boot)
- **Module layout**:
  - `job-common`: API interfaces, request/response DTOs, domain objects, Spring XML config for JMS client wiring
  - `job-impl`: JDBC DAO implementations, `JobManagerImpl`, Spring XML context for server-side wiring
- **Data access**: Spring `JdbcDaoSupport` + `StoredProcedure` / `MappingSqlQuery` abstractions
- **Remoting**: Spring JMS Invoker via `ConfigurableJmsInvokerProxyFactoryBean` (in `springutils-jms`)
- **Serialization**: XStream (for JMS message body)
- **AOP**: Spring AOP proxies around all DAO beans and `JobManager`
- **Caching**: `AgentCachingJobManagerClient` — name implies caching but the cache implementation is inside the xplatform library (not visible here)

## API Surface

This is a library — it exposes a Java interface, not an HTTP endpoint:

```java
// com.ecount.service.job.JobManager (job-common)
FindUserMappingResponse findUserMapping(FindUserMappingRequest)
UserMapping mapUser(MapUserRequest)
boolean clearUserMappingLock(ClearUserMappingLockRequest)
FindProgramProcessingAgentResponse findProgramProcessingAgent(FindProgramProcessingAgentRequest)
GetJobStatisticsResponse getJobStatistics(GetJobStatisticsRequest)
List<JobAccountMapEntry> getPuids(String ecountIds)
FindValidationVersionResponse findValidationVersion(FindValidationVersionRequest)
boolean updatePartnerUserId(UpdatePartnerUserIdRequest)
String getBatchIDbyEcountID(String ecountID)
int getInstantIssueCardStatus(String ecountID)
```

The JMS client path exposes the same interface over a JMS destination (`${service.job.manager.jms.destination}`).

## Security Posture

### Authentication / Authorization
- None at the library level. All callers are implicitly trusted. The JMS connection uses JNDI-configured credentials (not visible in source). No method-level security annotations.

### Cryptography
- PUID encoding is handled entirely within SQL Server stored procedures. No Java-side crypto. No TLS enforcement code. No key management in Java layer.

### Secrets
- No credentials, connection strings, or keys in source code. All resolved via Spring bean injection at runtime from `CBASE_HOME_URL` file-system config or JNDI. This is acceptable for Gen-1 patterns but not cloud-ready.

### Known CVE-relevant Dependencies
- **XStream** (`com.thoughtworks.xstream`): XStream has a long history of critical deserialization vulnerabilities (CVE-2021-39139, CVE-2021-21345, etc.). The version in use is not pinned in the visible sub-POM (inherited from parent). XStream is used for JMS message serialization; **any message that arrives on the JMS queue is deserialized with XStream** — this is a significant deserialization attack surface if the JMS broker is not isolated.
- **Commons Lang**: Older versions have had known vulnerabilities; version not pinned in visible POMs.
- **Spring Framework**: Version inherited from parent; if not kept current, Spring-related CVEs apply.

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| Raw type usage (`List`, `Map` without generics) | `JdbcJobAccountMapDao.java` lines 346, 352 | Low |
| `@SuppressWarnings("unchecked")` cast | `JdbcJobAccountMapDao.java` line 346 | Low |
| `Hashtable` usage (legacy, synchronized, not thread-safe by modern standards) | `ChryslerFileConverter.java` (integration lib) | Low |
| `StringBuffer` instead of `StringBuilder` | `BatchFile.java` throughout | Low |
| Empty constructor body `public BatchFile(String filename, String programId)` | `BatchFile.java` line 43 | Medium — silent no-op |
| Off-by-one potential in `writeRequestHeader`: `ecountId.substring(16)` instead of `substring(0, 16)` | `BatchFile.java` line 143 | Medium — data truncation bug |
| No null check on `ecountId` / `partnerUserId` length before substring | `BatchFile.java` lines 141-158 | Medium — potential `IndexOutOfBoundsException` |
| `getPuids` returns `null` instead of empty list | `JdbcJobAccountMapDao.java` line 359 | Medium — callers must null-check |
| Spring XML config — no Spring Boot, no component scan | All XML files | High — migration burden |
| `CBASE_HOME_URL` file-system config | `configuration.xml`, `configuration-jms.xml` | High — not container-ready |
| Tests skipped in CI | `github-package-publish.yml` | High — no regression safety net |

## Gen-3 Migration Requirements

To migrate the job-management domain to a Gen-3 (NexPay/Azure-native) microservice:

1. Replace the `JobManager` JMS interface with a REST or gRPC API.
2. Re-implement stored-procedure logic as JPA repositories or Spring Data queries.
3. Reverse-engineer and re-implement the PUID encoding algorithm.
4. Replace `CBASE_HOME_URL` file-system config with Azure Key Vault + Azure App Configuration.
5. Remove XStream; use Jackson or Protocol Buffers for serialization.
6. Add Spring Security for API authentication (JWT/OAuth2 via Azure Entra ID).
7. Add OpenTelemetry tracing, Micrometer metrics, and structured logging.
8. Replace the `com.citi.prepaid` namespace throughout with `com.onbe`.
9. Upgrade to Java 21+ and Spring Boot 3.x.

## Code-Level Risks (File:Line References)

| Risk | File | Line |
|---|---|---|
| XStream deserialization on JMS messages (RCE risk) | `client-JobManagerJMS.xml` | All — JMS invoker proxy uses XStream |
| `ecountId.substring(16)` — should be `substring(0, 16)` | `job-common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 143 |
| `partnerUserID.substring(50)` — should be `substring(0, 50)` | `job-common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 152 |
| `passthrough.substring(32)` — should be `substring(0, 32)` | `job-common/src/main/java/com/ecount/jobintegration/common/BatchFile.java` | 157 |
| `null` returned instead of empty list | `job-impl/src/main/java/com/ecount/service/job/dao/jdbc/JdbcJobAccountMapDao.java` | 359 |
| Raw `Map` cast without generic type | `job-impl/src/main/java/com/ecount/service/job/dao/jdbc/JdbcJobAccountMapDao.java` | 352 |
| `getPuids` bulk input is a raw string passed to SP — potential SQL injection if SP does not parameterise | `job-impl/src/main/java/com/ecount/service/job/dao/jdbc/JdbcJobAccountMapDao.java` | 334-372 |
