# om-payment-api — Solution Architect View

## Solution Overview

`om-payment-api` is a Spring Boot 3.4.4 microservice that serves as the internal REST implementation of the `manage-payment-rest-api` OpenAPI contract. It bridges the modern REST API surface demanded by Onboarding Manager orchestration workflows with the established Citi prepaid account management and eCount Core platform. The solution is designed for containerized deployment with Dapr sidecar integration while also supporting legacy Tomcat WAR deployment.

## Request Processing Pipeline

```
HTTP Request
  → Spring Security Filter Chain (ApiSecurityConfiguration — currently excluded)
  → Logbook Request Logging Filter (obfuscates ssn, cardNumber, cvv in body)
  → RequestAwareGlobalRequestFilter (RequestContextFilter — populates ThreadLocalRequestContextHolder)
  → DispatcherServlet
    → AccountManagementRestController / DebitRestController
      → Bean Validation (@Valid, @Validated, custom constraints)
        → AccountManagementRestHandler / DebitServiceRestHandler
          → Service Layer (CreateAccountService, CardService, CheckService, etc.)
            → eCount Core / Citi API RPCs
              → SQL Server databases
  → Logbook Response Logging Filter
  → HTTP Response (MapStruct-mapped DTO)
```

## Handler Architecture

`AccountManagementRestHandler` and `DebitServiceRestHandler` are thin orchestrator beans. Each handler method:
1. Maps the REST request DTO to the service-specific input object (via injected MapStruct mappers).
2. Calls the appropriate `*Service` bean.
3. Maps the service output back to the REST response DTO.
4. Handles exceptions from service layer and translates to appropriate HTTP status codes via `RestControllerAdvice`.

## Error Handling Architecture

`RestControllerAdvice.java` (`src/main/java/.../exception/`) provides centralized exception translation:

| Exception Type | HTTP Status | Source |
|---|---|---|
| `InputValidationException` | 400 Bad Request | Citi API input validation failures |
| `BusinessValidationException` | 422 Unprocessable | Business rule violations (insufficient funds, etc.) |
| `ApiSecurityException` | 403 Forbidden | Authorization failures (when security is enabled) |
| `ApiTimeoutException` | 504 Gateway Timeout | Downstream service timeouts |
| `ApiSystemFailureException` | 500 Internal Server Error | Unexpected system failures |
| `NotFoundException` | 404 Not Found | Resource not found |

The Problem Detail pattern (`BusinessValidationProblem`, `SecurityExceptionProblem`, `InvalidParametersProblem`, `InternalErrorProblem`) provides RFC 7807-compliant error responses. This is an enterprise-grade error response standard that enables API consumers to programmatically handle errors.

## Debit Transaction State Machine

`DebitTransactionServiceImpl` implements a precise state machine for debit operations:

```
State Transitions (stored in audit table via AuditHelper):
BEGIN_PENDING → BEGIN_SUCCESS | BEGIN_FAILED
                             ↓
                    COMMIT_SUCCESS | COMMIT_FAILED
                    CANCEL_SUCCESS | CANCEL_FAILED
```

Critical design details:
- `UUID.randomUUID()` generates the `transfer_id` for new transactions (line 68).
- Previously cancelled transactions (`CANCEL_SUCCESS`) are treated as new starts when the same `transaction_id` is reused (line 73 `isExistingTxn.set`).
- The audit update is in the `finally` block — guaranteed execution even on exception.
- The `isExistingTxn` flag prevents duplicate processing for already-committed transactions.

## Card Reissue Business Logic (CardService.java)

The `reissueCard` operation is a compound two-step process:
1. `iDeviceManager.reIssueECard(account, blockCode)` — marks old card as LOST (or SUSPENDED if status was SUSPENDED), creates new account.
2. `accountDetailDao.updateBlockCode(ddaNumber)` — resets DDA block code to 0 before plastic request.
3. `iDeviceManager.issuePlastic(account, deliveryCode, funds, isRenewal)` — emboss request.

Delivery code mapping (`getDeliveryCode` method):
| Input | Delivery Code | Meaning |
|---|---|---|
| "0" | "000" | Standard domestic |
| "1" | "069" | Express domestic |
| "2" | "008" | Standard international |
| "3" | "010" | Express international |

PO Box validation is enforced for express delivery (codes 1 and 3) — a correct business rule since express shipping carriers cannot deliver to PO Boxes. The detection logic (`isAddressPOBox`) normalizes whitespace before matching against known PO Box patterns, handling variations like "P.O.Box", "PO Box", "Post Office Box".

## Validation Framework Design

The custom constraint annotations (`src/main/java/.../validation/annotation/`) use the standard JSR-380 Bean Validation API, enabling Spring to integrate them transparently with `@Validated`. The `StringParameterConstraint(checkRequired = false)` flag allows optional parameters that are only validated when present — needed for `partnerUserId` and `accountNumber` where exactly one must be provided (enforced by `ConditionalValidator`).

The `cardInquiry` endpoint (controller lines 173-189) demonstrates the pattern:
```java
@RequestParam @StringParameterConstraint(regex = "[0-9]{8}") String programId
@RequestParam(required = false) @StringParameterConstraint(regex = "[A-Za-z0-9-]{1,40}", checkRequired = false) String partnerUserId
@RequestParam(required = false) @StringParameterConstraint(regex = "[0-9]{1,16}", checkRequired = false) String accountNumber
```
`programId` is always required (8 digits), while `partnerUserId` and `accountNumber` are optional but validated when present.

## Log Sanitization in Service Layer

`CardService` implements `LoggingUtil` (line 23: `public class CardService implements DeviceTypes, LoggingUtil`). This interface provides `sanitizeLogMessage(Object)` which strips Unicode control characters (`[\\p{C}]`). The method is called before every log statement in `CardService`:
```java
log.info("Reissue Card Request: {}", sanitizeLogMessage(reissueCardRequest));
log.info("Home Address = {}", sanitizeLogMessage(address));
log.info("Found eCard = {}", sanitizeLogMessage(eCard));
```
This prevents log injection attacks where malicious input could forge log entries or inject ANSI escape sequences. However, `sanitizeLogMessage` does not mask PAN, CVV, or SSN — it only sanitizes control characters. The address and eCard objects logged may contain PII that should be masked or excluded from INFO-level logs.

## Security Implementation Gaps (Solution Level)

### Gap 1: JwtSecurityValidator bypass (Critical)
`JwtSecurityValidator.authorize()` returns `true` unconditionally. The commented-out code shows the intended implementation pattern. To remediate:
1. Uncomment and complete the JWT validation logic.
2. Add `ApiSecurityConfiguration.class` back to the Spring Boot auto-configuration (remove it from the exclusion in `@SpringBootApplication`).
3. Implement token validation against the `jwtEntityCandidate.getAccessEntityJwt()` mechanism.
4. Test with the program-method-feature authorization matrix documented in comments (lines 21-28).

### Gap 2: trustServerCertificate=true (High)
Replace in all four datasource URLs:
```
trustServerCertificate=false;trustStore=/path/to/truststore.jks;trustStorePassword=${DB_TRUSTSTORE_PASSWORD}
```
The QA truststore is already available at `src/main/resources/keystore/truststore_qa.jks` — this should be mounted into the container and referenced in the datasource URL for QA environments.

### Gap 3: SNAPSHOT dependency (High)
`accountmanagementapi:3.0.3-SNAPSHOT` should be promoted to a release version. Work with the `account-management-api` team to cut a `3.0.3` release.

### Gap 4: Dapr `latest` tag (Medium)
Pin `daprio/daprd:latest` to a specific version in `docker-compose.yml`, e.g., `daprio/daprd:1.13.0`.

## Performance Considerations

- `connectTimeout: 5000 / readTimeout: 120000` for eCount Core (application.yml lines 85-87) — 2-minute read timeout is long for a synchronous REST API. If eCount Core is slow, client requests will hang for up to 2 minutes.
- `connectTimeout: 5000 / readTimeout: 30000` for Order Service — 30-second read timeout.
- No connection pool tuning is visible in the datasource configuration (HikariCP defaults will apply via Spring Boot auto-configuration).
- No caching layer is defined for frequently-read static data (affiliate configurations, program parameters).

## Testing Architecture

- **Unit tests**: JUnit 5 (`*Test.java`) and Spock Specs (`*Spec.groovy`) in `src/test/`.
- **Integration tests**: Spock `*IntegrationSpec.groovy` in `src/integration-test/` — run against a live Spring Boot instance started by `spring-boot:start`.
- **Coverage**: JaCoCo excludes `config/**`, `security/**`, and the main application class from coverage measurement (pom.xml lines 371-376) — ensuring coverage metrics reflect business logic only.
- **Mock profile**: `application-mock.yml` activates sandbox response files for integration testing without external dependencies.
