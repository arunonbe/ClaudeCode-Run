# Solution Architect — payment-service_SVC

## Technical Architecture
- **Framework**: Spring Framework (XML context, Spring MVC) — NOT Spring Boot.
- **Java**: 21 (compiler); Gen-1 patterns throughout.
- **Deployment**: WAR on Apache Tomcat 10.1.28.
- **Multi-module**: `payment-client` (XMLRPC input/output DTOs), `Payment-Common` (domain + exceptions + service interface), `Payment-Service` (implementation + DAO), `Payment-War` (WAR assembly + servlet config).
- **Protocol**: XML-RPC (`XmlRPCServlet` at `/dispatch.asp`); Spring MVC `DispatcherServlet` at `/hc`.
- **Data access**: Spring `StoredProcedure` subclasses (JDBC); no ORM/JPA.
- **Logging**: Log4j2 (external config file); Log4j refresh every 300 seconds.
- **Serialization**: Jackson `ObjectMapper` in DAO layer (FAIL_ON_UNKNOWN_PROPERTIES=false).

## API Surface

### XML-RPC Handlers (via EPaymentProxy)
| Operation | Input Type | Output Type |
|-----------|-----------|------------|
| `StopPayment(paymentId, agent)` | int, String | `StopPaymentOutput` |
| `CreateCertificate(input, agent)` | `CreateCertificateInput` | `CreateCertificateOutput` |
| `CreateEmailNotifications(input, agent)` | `CreateEmailInput` | `CreateEmailOutput` |
| `CreateBulkUser(agent, affiliateId, programId, name)` | String, int, String, String | `CreateBulkUserOutput` |

### HTTP Endpoints
| Method | Path | Handler |
|--------|------|---------|
| GET | `/hc` | `HealthCheck.java` (Spring MVC) |
| POST | `/dispatch.asp` | `XmlRPCServlet` (all XMLRPC operations) |

## Security Posture

### Authentication and Authorization
- **No application-layer authentication** on the XMLRPC endpoint. The `web.xml` defines no security constraints, login config, or security roles.
- All access control is enforced at the network/VPN layer (internal `wirecard.sys` DNS names confirm VPN-only accessibility).
- The `agent` parameter in all service calls is a string identifier used for audit/logging purposes — it is not cryptographically verified.
- `CheckUserPermissions` stored procedure provides permission check at the data layer for some operations.

### Transport Security
- SQL Server: TLS 1.2 via xplatform data source config.
- Tomcat connector: `config/server.xml` controls connector TLS — specific settings not read in full detail; SSL configuration is present for the WAR.
- XMLRPC calls from clients: HTTP within VNet; TLS at the load balancer boundary.

### Dependency / CVE Risks
- **Tomcat downloaded at build time** from archive.apache.org: No SHA checksum verification in Dockerfile — supply chain risk. [Payment-War/Dockerfile:8-10]
- `com.parents:prepaid-parent:6.0.13` — parent POM carries older plugin and dependency versions; requires SCA scan.
- `xplatform:6.4.27` — large internal library; CVE status unknown without SCA scan.
- `xmlrpc:3.1.0` — Apache XML-RPC; check CVE database for known vulnerabilities.
- **`jakarta/servlet/http/HttpUtils.java`** manually placed in WAR source — this is a recreation of the deprecated `HttpUtils` class; it bypasses normal Jakarta EE library management and may introduce subtle incompatibilities. [Payment-War/src/main/java/jakarta/servlet/http/HttpUtils.java]

### Sensitive Data
- `CreateBulkUser` hardcodes `partner@ecount.com` as the email and a physical address — these appear in payment records. [PaymentServiceImpl.java:161-166]
- XMLRPC requests/responses are XML; if logged at DEBUG level, they may expose sensitive payment data.

## Technical Debt
- **Raw types throughout**: `Map context = new Hashtable()` — unchecked types in `PaymentServiceImpl` (lines 90, 112, 153).
- **ThreadLocal logger**: `private static ThreadLocal<Logger> log = new ThreadLocal<Logger>() {...}` — unusual and unnecessary; standard static SLF4J logger should be used. [PaymentServiceImpl.java:29-34]
- **Hardcoded bulk user profile**: Physical address, email, phone hardcoded in business logic. [PaymentServiceImpl.java:161-171]
- **SNAPSHOT version** (`4.1.2-SNAPSHOT`).
- **Tests skipped**: All test execution disabled in CI.
- **Two exception hierarchies**: Both `com.ecount.paymentsvc.domain.ChainedException` and `com.ecount.paymentsvc.exception.ChainedException` exist — duplicate class in different packages.
- **Domain / exception duplication**: Several classes appear in both `domain/` and `exception/` packages (e.g., `ChainedException`, `ProfileException`).
- **`ObjectMapper.FAIL_ON_UNKNOWN_PROPERTIES=false`** in DAO: Silent field dropping. [PaymentServiceDAOJDBCImpl.java:50-51]
- **Dockerfile downloads Tomcat without checksum**: Supply chain risk. [Dockerfile:8-10]
- **`certfile_qa.crt` in image**: QA cert should not be in production image; needs build-time parameterization.

## Gen-3 Migration Requirements
1. **Expose REST API**: Add Spring Boot REST controllers wrapping the payment operations; deprecate XMLRPC over time.
2. **Remove XML Spring context**: Migrate to Spring Boot auto-configuration and `@Configuration` classes.
3. **Add authentication**: JWT or mTLS on all endpoints.
4. **Enable tests**: Remove `maven.test.skip=true` from CI; write unit and integration tests.
5. **Fix raw types**: Replace `Hashtable`/raw `Map` with typed context objects.
6. **Replace ThreadLocal logger**: Use standard `private static final Logger log`.
7. **Externalize bulk user defaults**: Move hardcoded address/email/phone to configuration.
8. **Fix Jakarta servlet shim**: Remove manual `jakarta/servlet/http/HttpUtils.java`; resolve Jakarta EE dependency properly.
9. **Add OpenTelemetry**: Integrate `otel-grpc_LIB` (when Spring Boot 4 ready) or add Spring Boot Actuator + Micrometer.
10. **Resolve duplicate classes**: Remove duplicated `ChainedException`, `ProfileException` across packages.
11. **Dockerfile hardening**: Add Tomcat download checksum verification; parameterize certificate inclusion.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| Hardcoded bulk user address/email/phone | `Payment-Service/src/main/java/.../service/PaymentServiceImpl.java` | 161-171 |
| `ThreadLocal<Logger>` anti-pattern | `Payment-Service/src/main/java/.../service/PaymentServiceImpl.java` | 29-34 |
| Raw `Hashtable`/`Map` context | `Payment-Service/src/main/java/.../service/PaymentServiceImpl.java` | 64, 90, 112, 153 |
| No authentication on XMLRPC endpoint | `Payment-War/src/main/webapp/WEB-INF/web.xml` | entire |
| Tomcat downloaded without checksum | `Payment-War/Dockerfile` | 8-10 |
| QA cert hardcoded in Docker image | `Payment-War/Dockerfile` | 19-20 |
| Manual Jakarta servlet shim | `Payment-War/src/main/java/jakarta/servlet/http/HttpUtils.java` | entire |
| `FAIL_ON_UNKNOWN_PROPERTIES=false` | `Payment-Service/src/main/java/.../dao/jdbc/PaymentServiceDAOJDBCImpl.java` | 50-51 |
| Tests skipped in CI | `.gitlab-ci.yml` | 7, 9, 10 |
| Duplicate exception classes | `domain/ChainedException.java` and `exception/ChainedException.java` | N/A |
