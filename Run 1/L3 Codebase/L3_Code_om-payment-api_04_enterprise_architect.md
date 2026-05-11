# om-payment-api — Enterprise Architect View

## Strategic Context

`om-payment-api` is the modern REST API facade over Onbe's legacy eCount Core payment platform. It represents the **strangler fig modernization pattern**: a new API layer wraps the legacy `com.citi.prepaid.accountmanagementapi` and `com.ecount.xplatform` libraries, exposing a clean REST interface while preserving backward compatibility with the existing account management logic. The `om` prefix (Onboarding Manager) positions this service within a broader onboarding workflow platform.

## Architectural Layers

### 1. REST Interface Layer
Spring Boot 3.4.4 with SpringDoc OpenAPI 2.8.6 provides the REST contract. The API is versioned at `/v1/`. The OpenAPI spec is generated at integration-test time via `springdoc-openapi-maven-plugin` and published to `http://localhost:8080/v3/api-docs` — enabling contract-first integration with other OM services.

### 2. Request Validation Layer
A rich custom validation framework in `src/main/java/.../validation/`:
- `@StringParameterConstraint` — regex-based string validation with optional/required flag
- `@EmailParameterConstraint` — email format validation
- `@PhoneParameterConstraint` — phone number validation
- `@DateParameterConstraint` — date format validation
- `@LongParameterConstraint` — numeric range validation
- `@ChoiceParameterConstraint` — enumerated value validation
- `@ConditionalValidator` — cross-field conditional validation

This layer ensures invalid requests are rejected at the HTTP boundary before any business logic executes. The `@Validated` annotation on `AccountManagementRestController` (line 29) activates Spring's constraint processing.

### 3. Handler Layer
`AccountManagementRestHandler` and `DebitServiceRestHandler` act as orchestrators between the controller and service beans. They aggregate multiple service calls, handle cross-cutting error translation, and insulate the controller from service implementation details.

### 4. Service/Domain Layer
Business logic lives in:
- `CardService` — card reissue, plastic request, express shipping validation (PO Box detection)
- `CheckService` — check issuance and voiding
- `DebitTransactionServiceImpl` — two-phase debit with explicit audit trail

The service layer wraps Citi Prepaid API services (`CreateAccountService`, `AddFundsService`, `WithdrawService`, etc.) that are Spring beans configured in `AccountManagementBeanConfig.java`.

### 5. Legacy Integration Layer
`ECountCoreBeanConfig.java` wires up the eCount Core business objects (`ECoreDevice`, `ECoreMember`, `ECoreTransfer`, `ECoreEManage`) using `ThreadLocalRequestContextHolder` for request context propagation. This is a thread-local state pattern — the calling thread's request context is used for authentication/authorization in the eCount Core RPC layer. This pattern is not compatible with reactive/non-blocking frameworks.

## Technology Stack Assessment

| Component | Technology | Version | Assessment |
|---|---|---|---|
| Runtime | Spring Boot | 3.4.4 | Current; supported until Nov 2027 |
| Java | OpenJDK 21 (LTS) | 21 | Current LTS; good |
| Build | Maven | (wrapper) | Standard |
| Testing | Spock Framework | 2.4-M6-groovy-4.0 | Milestone release — should use GA |
| HTTP logging | Zalando Logbook | 3.11.0 | Current |
| API docs | SpringDoc OpenAPI | 2.8.6 | Current |
| Mapping | MapStruct | 1.6.3 | Current |
| Database | SQL Server | (mssql-jdbc bundled with Boot) | Standard |
| Sidecar | Dapr | `latest` | Unpinned — operational risk |
| Serialization | XStream | 1.4.21 | Legacy XML serialization; known CVE history |
| Legacy integration | xplatform (eCount) | 6.3.2 | Legacy library |
| Legacy integration | accountmanagementapi | 3.0.3-SNAPSHOT | SNAPSHOT — unstable |

**XStream concern**: `com.thoughtworks.xstream:xstream:1.4.21` (pom.xml line 40) has a history of critical deserialization CVEs (CVE-2021-21344, CVE-2021-21350, etc.). Version 1.4.21 addressed many known CVEs, but XStream deserialization of untrusted data remains a risk. Its specific usage in this codebase should be reviewed.

## Service Mesh and Sidecar Architecture

The presence of `dapr-components/` directory and Dapr configuration in `docker-compose.yml` indicates this service is being migrated toward a Dapr-based service mesh. Dapr provides:
- Service-to-service invocation with mTLS
- State management
- Pub/sub messaging
- Secret management (integrating with Azure Key Vault, Vault, etc.)

The Dapr integration is currently in development (components directory appears empty, some Dapr config is commented out in docker-compose). When operational, Dapr would replace direct HTTP/RPC calls to eCount backends with Dapr service invocation, enabling mTLS between services without application-level TLS management.

## Security Architecture Assessment

### Critical Finding: Authorization Bypass
`JwtSecurityValidator.java` (lines 31-57): The entire JWT authorization logic is commented out:
```java
// audit.accessRequested(candidate, requestedDomain);
// if(candidate instanceof JwtEntityCandidate jwtEntityCandidate) {
// ...
return true; // Line 57 — unconditionally authorize all requests
```
The comment on lines 21-28 describes the intended behavior:
```
{METHOD=createAccount, API=AccountManagement, PROGRAM=04016113}
{FEATURE=Return-Card-Number, METHOD=createAccount, API=AccountManagement, PROGRAM=04016113}
```
This indicates a token-based, program-scoped authorization model was designed but not yet implemented. Until this is enabled, all callers are authorized for all payment operations, which is a **critical PCI DSS violation** (Requirement 7 — access controls) for any environment that processes real payment data.

The `@SpringBootApplication` annotation on `ManagePaymentRestApiApplication.java` also comments out `ApiSecurityConfiguration.class` in the exclusion list (line 9), suggesting the security configuration class exists but is excluded from auto-configuration.

### Security Control Inventory

| Control | Status | Notes |
|---|---|---|
| TLS on REST endpoints | Active (inferred from QA cert import in Dockerfile) | Must verify TLS termination point |
| JWT Authorization | Disabled | Critical gap — line 57 returns true unconditionally |
| Request validation | Active | Custom constraint annotations on all controller parameters |
| Log obfuscation (SSN, PAN, CVV) | Active | Logbook `json-body-fields` configuration |
| Database TLS | Active but incomplete | `sslProtocol=TLSv1.2` enabled; `trustServerCertificate=true` disables cert validation |
| Audit trail for debits | Active | `DebitTransactionServiceImpl` maintains explicit audit state |
| Security audit logging | Active | `LoggingSecurityAudit` bean instantiated even though authorization is bypassed |

## PCI DSS Architecture Alignment

| Requirement | Status | Gap |
|---|---|---|
| Req 6.2 — Bespoke software security | Partial | Custom validation layer exists; authorization disabled |
| Req 6.3.2 — Software inventory | Not implemented | No SBOM generation in this repo |
| Req 7.2 — Access control | Violated | JwtSecurityValidator returns true for all requests |
| Req 8.6 — Service account credentials | Partial | Env var injection correct; `trustServerCertificate=true` weakens transport |
| Req 10.2 — Audit log | Partial | Debit audit trail; logbook HTTP logging; no structured SIEM export |
| Req 10.3 — Audit log protection | Not assessed | Log destination not visible in this repo |

## Enterprise Integration Patterns Used

1. **Facade Pattern**: REST controller layer wraps complex multi-service eCount operations.
2. **Mapper/Translator Pattern**: MapStruct mappers between REST DTOs and service input/output objects.
3. **Two-Phase Commit**: Begin/Commit/Cancel debit pattern for atomic financial transactions.
4. **Strangler Fig**: New Spring Boot API wrapping legacy `com.citi.prepaid` libraries.
5. **Request Context Propagation**: `ThreadLocalRequestContextHolder` propagates caller identity through eCount Core calls.
6. **Health Aggregation**: Spring Boot Actuator aggregates multiple health indicators (databases, RPC connections).
