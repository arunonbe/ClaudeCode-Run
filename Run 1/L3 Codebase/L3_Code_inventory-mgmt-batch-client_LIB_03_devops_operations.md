# DevOps / Operations View — inventory-mgmt-batch-client_LIB

## Build
- **Build system**: Maven, single-module JAR.
- **Maven wrapper**: `mvnw` / `mvnw.cmd` present.
- **Parent POM**: `com.citi.prepaid.service:service-parent:8`.
- **Java compiler**: source/target 1.6 — Java 6.
- **Assembly plugin**: `maven-assembly-plugin` produces a distribution ZIP/directory (`inventory-mgmt-batch-client-<version>-dir`) with all JARs assembled.
- **Output**: `inventory-mgmt-batch-client-2.0.1-SNAPSHOT.jar` plus assembly.
- **GitLab CI**: `.gitlab-ci.yml` present.
- **SCM**: `gitlab.com/northlane/development/application-development/libraries/inventory-mgmt-batch-client.git`.

## Deployment
- **Deployment model**: Assembled JAR distribution deployed to a server with the C-Base directory structure.
- **Execution**: Direct JVM invocation (e.g., `java -cp ... CardExpiryAlertNotificatonClient`) triggered by OS scheduler (cron, Windows Task Scheduler).
- Requires `D:/c-base/config/inventoryMgmt/` directory with `inventoryMgmtBatchClient.properties` and `CardExpiryClientLog4j.properties`.
- Requires `D:/c-base/config/director-client.properties`.
- Not containerised; no Docker or Kubernetes deployment.

## Configuration Management
- Configuration via plaintext `.properties` files at fixed filesystem paths:
  - `D:/c-base/config/director-client.properties`
  - `D:/c-base/config/inventoryMgmt/inventoryMgmtBatchClient.properties`
  - `D:/c-base/config/inventoryMgmt/CardExpiryClientLog4j.properties`
- Spring XML context files on classpath configure bean wiring.
- No secrets manager, Azure Key Vault, or Spring Cloud Config.

## Observability
- Log4j 1.x with `PropertyConfigurator` — log level and file path from properties file.
- ELF (Enterprise Logging Framework) via TIBCO JMS SSL (configured in consuming `applicationContext` if ELF appender is included).
- No metrics endpoint or health check.
- `System.exit(0)` on normal completion; `System.exit(-1)` on failure — batch completion detected via process exit code.

## Infrastructure Dependencies
| Dependency | Type | Notes |
|-----------|------|-------|
| ecountCore SQL Server | Database | DDA card sync |
| JobSvc SQL Server | Database | Inventory, email queue |
| cbaseapp SQL Server | Database | C-Base app data |
| Director service registry | Service discovery | Resolves DB connections |
| TIBCO JMS | Messaging | ELF logging (optional) |
| Filesystem (`D:/c-base/config/`) | Configuration | Properties files |
| Filesystem (filePath) | Staging | XML reorder files |

## Operational Risks
1. Java 6 compiler target — severely EOL; JVM runtime must be Java 6 or compatible, limiting security patching options.
2. Fixed hardcoded Windows-style paths (`D:/c-base/config/`) — non-portable; incompatible with Linux or containerised deployment.
3. `System.exit()` calls make the batch non-embeddable and untestable in unit test contexts.
4. No retry logic or idempotency for batch runs — duplicate runs may produce duplicate notifications or orders.
5. log4j 1.2.14 — EOL library; while not affected by log4shell (CVE-2021-44228) in v1.x, it has other unpatched CVEs (CVE-2019-17571 — SocketServer gadget chain).

## CI/CD
- **GitLab CI**: `.gitlab-ci.yml` present (content not read; likely Maven build/deploy stages).
- **GitHub Actions**: `.github/workflows/codeql.yml` — CodeQL analysis.
- **Dependabot**: `.github/dependabot.yml`.
- Default branch: `master`.
- Maven release plugin version 3.0.0-M1 configured for releases.
