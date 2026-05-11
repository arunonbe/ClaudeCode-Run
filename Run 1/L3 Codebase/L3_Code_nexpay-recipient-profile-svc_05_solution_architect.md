# Solution Architecture — nexpay-recipient-profile-svc

## Technical Architecture
- **Framework**: Spring Boot (via `nexpay-parent:1.0.2`), Java 25.
- **Architecture style**: Layered multi-module Maven: api → data-entity → data-repository → impl → boot.
- **Package root**: `com.onbe.nexpay`.
- **Persistence**: Spring Data JPA + Hibernate Envers + Flyway; PostgreSQL dialect.
- **Virtual threads**: `spring.threads.virtual.enabled: true` — Project Loom enabled.
- **API generation**: OpenAPI-first; generated `*ApiDelegate` interfaces implemented by `*ApiDelegateImpl` classes.
- **Mapping**: Manual mapper classes (`RecipientProfileMapper`, `ProfileAddressMapper`, etc.) — no MapStruct observed.
- **Audit**: Hibernate Envers with `CustomRevisionEntity` capturing `actorId`, `traceId`, `source`, `reason`.
- **Config**: Azure Spring Cloud App Configuration starter with Key Vault secret provider.
- **Telemetry**: OpenTelemetry Java agent auto-configure; OTLP export to Dynatrace.

## API Surface
| Method | Path | Description |
|--------|------|-------------|
| POST | `/recipient-profiles` | Create profile |
| GET | `/recipient-profiles/{profileId}` | Get profile |
| PATCH | `/recipient-profiles/{profileId}` | Update profile |
| DELETE | `/recipient-profiles/{profileId}` | Delete profile |
| GET | `/recipient-profiles` | List profiles (paginated, status filter) |
| GET | `/recipient-profiles/{profileId}/revisions` | Get revision history |
| GET | `/recipient-profiles/{profileId}/revisions/{revisionNumber}` | Get specific revision |
| GET/POST | `/profile-addresses/*` | Address CRUD |
| GET/POST | `/profile-attributes/*` | Attribute CRUD |
| GET/POST | `/external-profile-mappings/*` | External mapping CRUD |
| GET | `/actuator/health` | Liveness/readiness |
| GET | `/actuator/metrics`, `/actuator/prometheus` | Metrics |

## Security Posture
- **Authentication**: Not visible in this repo — expected to be enforced by Azure API Management or a Spring Security configuration in the boot module (boot module has no security config file observed in source scan).
- **Transport**: HTTPS assumed via ACA ingress/APIM; no explicit TLS config in application code.
- **Secrets**: Managed via Azure Key Vault / Managed Identity — no static passwords in production YAML.
- **PII at rest**: `date_of_birth`, `primary_email`, `primary_phone`, `first_name`, `last_name` stored in plain text in PostgreSQL — no field-level encryption.
- **Audit**: Envers captures actorId and traceId per revision; `CustomRevisionListener` reads from MDC/context (`CustomRevisionEntity.java`).
- **Log injection**: No explicit log sanitisation found in application code (unlike the mock-processor service); Logstash structured format partially mitigates free-text injection risk.

## Technical Debt
- No `@NotNull`, `@Size`, or Bean Validation constraints on most entity fields except the `profile_status` regex pattern — incomplete input validation.
- Swagger UI enabled in qa/prod profiles — API discoverable.
- No `-Xmx` heap limit set in Dockerfile.
- `RecipientProfileMapper`, `ProfileAddressMapper` etc. are handwritten — no code-generation framework (MapStruct), increasing maintenance surface.
- `RevisionService` uses raw Hibernate Envers `AuditQuery` — not type-safe; breaking changes in Envers API would require manual updates.
- `CONTAINER_SCAN: false` in deployment workflow.
- Coverage thresholds not enforced (no JaCoCo config in pom).

## Code-Level Risks
| File | Line | Risk |
|------|------|------|
| `RecipientProfilesApiDelegateImpl.java` | 72-73 | `offset % limit != 0` check throws 400 — correct business rule but undocumented in OpenAPI spec |
| `RecipientProfileService.java` | 34 | `"Recipient profile not found: " + profileId` — UUID concatenated into exception message; acceptable but consider structured error body |
| `application.yaml` | 93-94 | `com.zaxxer.hikari: TRACE` and `org.postgresql: TRACE` in qa/prod profiles — overly verbose; may expose connection metadata in logs |
| `nexpay-recipient-profile-boot/src/main` | — | No Spring Security configuration observed — auth enforcement not visible in this repo |
| `V1__initial_schema.sql` | 18 | `date_of_birth VARCHAR(10)` — date stored as string; no format enforcement at DB level |

## Gen-3 Migration Requirements
- Service is already Gen-3 native.
- Pre-go-live: re-enable container scan, add field-level encryption for PII columns or implement transparent encryption at the PostgreSQL column level, disable Swagger UI in prod, add Spring Security configuration.
