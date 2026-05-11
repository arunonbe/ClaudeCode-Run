# Enterprise Architect Analysis — notification-requests-generator_LIB

## Position in Onbe Platform Architecture

This library is a **batch data pipeline** component sitting between the operational database and the notification framework. It is the "feeder" for reminder and scheduled notifications:

```
Onbe Operational Database (notification_queue table)
       ↓ Spring Batch JDBC reader (stored procedure)
notification-requests-generator_LIB (batch job)
       ↓ Spring Batch ItemWriter → XML-RPC or DB write
notification-framework_SVC EventHandler
       ↓
Cardholder receives notification
```

## Architectural Pattern Analysis

### Spring Batch Architecture
The library follows the standard Spring Batch chunk-oriented processing pattern:
```
Reader → [Processor] → Writer (in chunks, with transaction support)
```

The `generateNotificationRequestsBatchJob.xml` defines the job steps. The `NotificationRequestDetailsLimitDecider` adds a flow-control decision step — processing stops when a count limit is reached, preventing runaway batch execution.

**Resilience design:** Spring Batch provides restart-from-checkpoint capabilities. If the job fails mid-run, it can resume from the last committed chunk. The `NotificationRequestHistoryDAO` tracks job history to support idempotent re-processing.

### Legacy Technology Stack

**Java 1.5-era patterns:**
- `ClassPathXmlApplicationContext` (Spring XML configuration — pre-annotation era)
- `Log4j 1.x` (EOL since 2015)
- `commons-logging` (`LogFactory.getLog()`)
- Spring Batch XML job definitions (current Spring Batch prefers Java-based configuration)
- `.bat` and `.vbs` deployment scripts

This codebase was written circa 2011 and has received minimal architectural updates. The technology stack is significantly out of date relative to the modern microservices stack used by `notification-service-client_SVC` (Spring Boot, Feign, Resilience4j).

## Integration Architecture

### Database Integration
The batch reads from the Onbe operational database via stored procedures. This tight coupling to specific stored procedure signatures means:
1. Database schema changes require coordinated batch code changes.
2. The batch holds a database connection for potentially extended periods during chunk processing.
3. No database failover strategy is visible.

### Notification Framework Integration
After processing records from the database, the batch writes to a Spring Batch `ItemWriter` (`NotificationRequestDetailsItemWriter`). How this writer submits to the notification framework is not directly visible in the reviewed code — it likely either writes back to a database table for the notification framework's subscriber to pick up, or makes a direct service call.

## Architectural Debt

| Issue | Impact | Notes |
|---|---|---|
| Windows-only deployment | High | Cannot containerise without rewrite |
| Log4j 1.x | High | EOL, security vulnerabilities |
| Spring XML configuration | Medium | Migration effort, not blocking |
| Pre-built JARs in repository | Medium | Audit and reproducibility concern |
| No CI/CD deployment pipeline | High | Quality risk |
| `commons-logging` | Low | Should be replaced with SLF4J |
| Hardcoded log file path (`d:/c-base/logs`) | Medium | Not portable |

## Multi-Environment Architecture Gap

The batch job configuration is stored in XML files embedded in the JAR. There is no visible externalisation of environment-specific configuration (database connection strings, processing parameters) via environment variables or an external config server. This means deploying to different environments (dev, QA, prod) requires either separate JARs or configuration injection at runtime via the command-line properties file mechanism.

The `NotificationRequestConstants.propFileName` field (referenced in `NotificationRequestGenerator.java` line 135) points to an external properties file that is loaded at runtime — this is the likely mechanism for environment-specific configuration. However, the path and contents of this file are not visible in the repository.

## Scalability Architecture

**Horizontal scaling limitations:** Spring Batch job instances are not designed for distributed execution without the Spring Batch integration module. Multiple simultaneous instances of this batch job would need coordination to avoid processing the same records. The `NotificationRequestHistoryDAO` and status-tracking stored procedures may serve this purpose, but the locking mechanism needs to be verified.

**Chunking:** The `notification_request_details_gridsize` property controls parallelism. Without knowing the value in production, it is unclear whether multi-threaded step processing is being used.

## Recommended Architectural Evolution

1. **Containerise**: Migrate from Windows batch to a Linux-compatible Docker container with environment variables replacing hardcoded paths.
2. **Replace Log4j 1.x with SLF4J/Logback**: Enables JSON-structured logging compatible with modern log aggregation.
3. **Migrate Spring Batch configuration to Java-based**: Improves type safety and IDE support.
4. **Add CI/CD pipeline**: GitHub Actions workflow for build, test, and deployment.
5. **Remove JARs from repository**: Use GitHub Packages or Nexus for artifact distribution.
6. **Implement PII masking**: Remove PII from log statements before any other changes.
