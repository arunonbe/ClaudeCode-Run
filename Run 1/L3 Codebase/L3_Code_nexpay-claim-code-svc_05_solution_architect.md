# nexpay-claim-code-svc — Solution Architect View

## Technical Architecture

- **Language**: Java 25 (early-access)
- **Framework**: Spring Boot (from `nexpay-parent`; exact Spring Boot version inherited)
- **Web layer**: Spring MVC (Spring Boot Starter Web)
- **Data layer**: Spring Data JPA + Hibernate 6.x over SQL Server (MSSQL JDBC 13.4.0.jre11)
- **Schema migration**: Flyway with SQL Server dialect (`flyway-sqlserver:12.1.0`)
- **Audit**: Hibernate Envers (revision entity `CustomRevisionEntity` + `CustomRevisionListener`)
- **Config**: Azure App Configuration (Spring Cloud Azure 4.x) + Azure Key Vault
- **Observability**: Spring Boot Actuator + OpenTelemetry (OTLP gRPC) + Micrometer
- **API contract**: OpenAPI-generated via `nexpay-claimcode-api` module
- **Testing**: Testcontainers with `testcontainers-mssqlserver` for integration tests

## Module Layout

```
nexpay-claim-code-svc/
├── nexpay-claimcode-api/          # OpenAPI-generated models and API interfaces
├── nexpay-claimcode-boot/         # Spring Boot app, Dockerfile, integration tests
│   ├── config/                    # DatabaseConfigProperties, DockerDatabaseInitConfig, JpaConfig
│   ├── exception/                 # ErrorExceptionHandlers (global error handler)
│   └── NexpayConfigApplication.java
├── nexpay-claimcode-data/
│   ├── nexpay-claimcode-data-entity/   # JPA entities + Flyway migrations
│   └── nexpay-claimcode-data-repository/ # Spring Data JPA repositories
└── nexpay-claimcode-impl/
    ├── config/                    # AsyncConfig, ImplementationConfig
    ├── health/                    # ApplicationHealthIndicator
    ├── mapper/                    # ClaimablePaymentMapper, RecipientRegistrationMapper
    └── service/                   # ClaimableControllerApiDelegateImpl
```

## API Surface

### REST Endpoints (port 8080)

| Method | Path | Description |
|---|---|---|
| `GET` | `/claimable/{claimCode}` | Returns `ClaimablePaymentDetail` or HTTP 404 |
| `GET` | `/recipient-registrations/{id}` | Returns `RecipientRegistrationDetail` (UUID path param) or HTTP 404 |
| `POST` | `/validateCodes` | Accepts list of claim codes; returns list of `ClaimCodeValidationResult` |

### Management Endpoints (port 8081)
`health`, `info`, `metrics`, `prometheus`, `startup`, `env`

### API Registration
- Published to **internal APIM** (`INTERNAL_APIM: true`)
- Not on external APIM (`EXTERNAL_APIM: false`)
- OpenAPI spec: `client-api/v1/client-api.yaml` (path in nexpay-iac)

## Security Posture

### Authentication / Authorization
- **No explicit security configuration visible** in the scanned source files. No `@EnableWebSecurity`, no `SecurityFilterChain` bean, no JWT validation.
- The service relies on network-level security (Azure Container Apps internal VNet, APIM) for access control. All callers must go through internal APIM.
- Actuator endpoints are on a separate port (8081) — not routable through public APIM.

### Cryptography
- No application-layer encryption. Database encryption relies on Azure SQL TDE.
- Claim codes stored as plain NVARCHAR — not hashed. This is standard for single-use voucher codes but means the DB is the single authoritative store with no hash-based verification.

### Secrets
- Database connection string: Azure Key Vault → Azure App Configuration → Spring property injection at startup. Not present in source. Correct pattern.
- Azure Managed Identity (`credential.managed-identity-enabled: true`) — no service principal credentials in source. Correct.
- `AZURE_CLIENT_ID` environment variable injected by ACA infrastructure.

### CVE Assessment
- **Java 25 (early-access)**: Not a GA release as of August 2025 (GA expected September 2025). Using pre-release Java in production is a supportability risk; security patches may be irregular.
- **`nexpay-parent:0.2.7-SNAPSHOT`**: Snapshot parent means transitive dependency versions are not fixed. A snapshot resolution change could introduce a vulnerable library version without a code change.
- **MSSQL JDBC 13.4.0.jre11**: Relatively recent; should be monitored for CVEs.
- **Nimbus JOSE JWT** (`nimbus-jose-jwt:10.9`): Declared in parent but its usage in this service is not visible in scanned source.

## Technical Debt

| Item | File | Severity |
|---|---|---|
| Claim code logged at INFO level | `nexpay-claimcode-impl/.../ClaimableControllerApiDelegateImpl.java` line 58 | High — financial token in logs |
| Employee PII in migration seed | `db/migration/V5__create_recipient_registration.sql` line 40 | High — PII in version-controlled file |
| Java 25 (non-LTS / early-access) | Root `pom.xml` | High — production supportability risk |
| `nexpay-parent:0.2.7-SNAPSHOT` | Root `pom.xml` | High — non-reproducible build |
| No authentication/authorization config visible | Boot module | Medium — depends on network-layer security |
| Container scan disabled | `.github/workflows/deployment.yml` | Medium — CVE blind spot |
| Flyway disabled in QA | `application-qa.yaml` | Medium — schema drift risk |
| OTLP metrics disabled in QA | `application-qa.yaml` | Medium — monitoring gap |
| `RecipientRegistration` lacks timestamps | `RecipientRegistration.java` | Medium — GDPR audit trail gap |
| Artifact ID `nexpay-config` ≠ service name `nexpay-claim-code-svc` | Root `pom.xml` line 14 | Low — naming confusion |
| SQL logging at DEBUG in QA config | `application-qa.yaml` | Low — verbose SQL logs in QA may expose query data |
| No null-safety on `claimCodes` validation | `ClaimableControllerApiDelegateImpl.java` lines 101–105 | Low — `IllegalArgumentException` not mapped to HTTP 400 |

## Gen-3 Migration Requirements

This service is already Gen-3. Items to address for production hardening:

1. **Mask claim codes in logs**: Replace `log.info("...claimCode={}", claimCode)` with masked value (first 4/last 4).
2. **Remove employee PII from V5 migration seed**: Replace with synthetic test data.
3. **Upgrade to Java 21 LTS**: Replace Java 25 with 21 in POM and Dockerfile.
4. **Stabilise nexpay-parent**: Cut a release version.
5. **Add Spring Security**: Add JWT validation (Azure Entra ID) for API callers even behind APIM (defence in depth).
6. **Enable container scanning**: Fix the container scan configuration.
7. **Enable Flyway in QA**: Use a migration-only elevated-credential job or grant DDL permissions.
8. **Map `IllegalArgumentException` to HTTP 400** in `ErrorExceptionHandlers`.
9. **Add `created`/`updated` timestamps** to `RecipientRegistration`.

## Code-Level Risks (File:Line References)

| Risk | File | Line |
|---|---|---|
| Claim code logged at INFO (token leakage) | `nexpay-claimcode-impl/src/main/java/com/onbe/nexpay/claimcode/impl/service/ClaimableControllerApiDelegateImpl.java` | 58 |
| Employee email PII in migration seed | `nexpay-claimcode-data/nexpay-claimcode-data-entity/src/main/resources/db/migration/V5__create_recipient_registration.sql` | 40 |
| `IllegalArgumentException` not mapped to HTTP response | `nexpay-claimcode-impl/src/main/java/com/onbe/nexpay/claimcode/impl/service/ClaimableControllerApiDelegateImpl.java` | 103 |
| Java 25 in Dockerfile | `nexpay-claimcode-boot/Dockerfile` | 1 |
| `--enable-native-access=ALL-UNNAMED` (broad native access) | `nexpay-claimcode-boot/Dockerfile` | 16 |
| SQL debug logging in QA may expose query parameters | `nexpay-claimcode-boot/src/main/resources/application-qa.yaml` | 69 |
