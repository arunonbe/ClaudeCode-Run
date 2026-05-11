# Solution Architect Report: scheduler_WAPP

## API Surface

| Endpoint | Protocol | Method | Auth | Notes |
|---|---|---|---|---|
| `/scheduler.service` | HTTP Invoker | POST (binary) | None | Full CRUD for schedules |
| `/hc` | HTTP | GET | None | Health check, returns "OK" |
| `index.jsp` | HTTP | GET | None | Default welcome page |

URL pattern in `web.xml`: `*.service` routes to the Spring DispatcherServlet. `/hc` also mapped. All other paths are unauthenticated.

## Security Posture

**Overall: High-risk for an infrastructure service handling financial scheduling.**

- **No authentication on the RPC endpoint**: `scheduler-webapp.xml` defines no security interceptors; `web.xml` has no `<security-constraint>`. Any process on the internal network can create, modify, or delete schedules
- **No input validation on `callbackPath`**: The `callbackPath` field is stored and used verbatim for HTTP callbacks. No allowlist check is visible in `SchedulerInputValidatorImpl` or `QuartzServiceProviderImpl`, creating server-side request forgery risk
- **Spring HTTP Invoker uses Java deserialisation**: Inbound requests are deserialised Java objects. Java deserialisation of untrusted data is a well-known attack vector (CVE-2015-4852 class of vulnerabilities); the service has no whitelisting or filtering of deserialised classes visible
- **PGP passphrase logging**: In the `CryptoService` in the related strongbox service (not in scheduler directly), but the scheduler's log statements include `log.info("PGP Encrypt Input ==> " + input.getText())` patterns in other Gen-1 services, suggesting a platform-wide risk of sensitive data logged at INFO level

## Critical Vulnerabilities

1. **Credentials committed to VCS** (`scheduler-service/.env`, lines 7–14 and `scheduler-service/.env-dev`, lines 8–15):
   - `SCHDULERWAAP_CBASEAPPDB_PASSWORD=b2cstage`
   - `SCHDULERWAAP_JOBSVCDB_PASSWORD=b2cstage`
   - `SCHDULERWAAP_REQUESTDB_PASSWORD=b2cstage`
   - `SCHDULERWAAP_ECOUNTDB_PASSWORD=b2cstage`
   - These are PCI DSS Requirement 8.3 violations (shared, default-like credentials committed to source control)

2. **Unauthenticated schedule management endpoint** (`scheduler-service/src/main/webapp/WEB-INF/web.xml`, line 31–43):
   - Spring DispatcherServlet mapped with no authentication; `*.service` pattern exposes full scheduler management to any internal caller

3. **`trustServerCertificate=true` in JDBC URLs** (`scheduler-service/.env-dev`, lines 1–4):
   - TLS certificate validation disabled for all four database connections in development environment; if this configuration propagates to non-production environments that share network access with production, it enables MITM attacks

4. **Java deserialisation attack surface**: Spring HTTP Invoker (`HttpInvokerServiceExporter`) deserialises all inbound requests without a class filter; exploitable if the scheduler is reachable by an attacker with internal network access

5. **Tests skipped in deployment pipeline** (`deployment.yml`, line 33): `MAVEN_ARGS: -Dmaven.test.skip` means no regression guard exists before production pushes

## Technical Debt

- Spring HTTP Invoker: deprecated since Spring 5.3, removed in Spring 6. The service cannot upgrade to Spring 6 without replacing this RPC mechanism
- XML-only Spring configuration: no annotation-driven beans, no Spring Boot autoconfiguration; all wiring is in XML files requiring manual maintenance
- WAR + JNDI: The deployment model requires a servlet container with JNDI resources; incompatible with Spring Boot embedded server pattern and adds operational complexity
- No dependency injection for `SchedulerServiceProvider` in some paths: `schedulerServiceProvider` is checked for null in `SchedulerServiceImpl` (lines 65–80) rather than guaranteed non-null via constructor injection, indicating legacy setter-injection patterns
- Log4j2 configuration at external file path: the logging framework reads from `${CBASE_HOME_URL}/config/service/scheduler/log4j2.xml`; if this path is unavailable at startup the service may use default logging or fail to initialise properly
- `--add-opens` JVM flags in Dockerfile (line 25): six module opens required for legacy reflection-heavy code; this is a maintainability warning signal that deep Spring XML internals are being accessed in ways incompatible with the Java module system
