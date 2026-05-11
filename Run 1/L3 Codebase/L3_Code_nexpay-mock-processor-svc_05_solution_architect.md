# Solution Architecture — nexpay-mock-processor-svc

## Technical Architecture
- **Framework**: Spring Boot 4.0.2, Java 25.
- **Structure**: Single Maven module; no sub-modules.
- **Package root**: `com.onbe.nexpay.mock`.
- **Layers**: `controllers` → `services` → `repositories` → `entities`.
- **Persistence**: Spring Data JPA with SQLite via Xerial JDBC driver and Hibernate Community Dialects (`org.hibernate.community.dialect.SQLiteDialect`).
- **API documentation**: springdoc-openapi 2.8.5, Swagger UI at `/swagger-ui.html`.

## API Surface
| Method | Path | Tag | Description |
|--------|------|-----|-------------|
| POST | `/a2a/CO_CreatePerson.asp` | FIS | Create FIS person |
| POST | `/a2a/CO_AssignCard_LoadValue.asp` | FIS | Assign card and load value |
| POST | `/a2a/CO_OTB_ByProxy.asp` | FIS | Get balance by proxy |
| POST | `/a2a/CO_StatusAcct.asp` | FIS | Update card status |
| POST | `/sandbox/api/v1/cards` | Thredd | Create Thredd card |
| POST | `/sandbox/api/v1/cards/{cardId}/transactions` | Thredd | Load funds |
| GET | `/sandbox/api/v1/cards/{cardId}/balance` | Thredd | Get card balance |
| PUT | `/sandbox/api/v1/cards/{publicToken}/status` | Thredd | Update card status |
| POST | `/connect/token` | Thredd OAuth | OAuth2 token |
| GET | `/actuator/health` | Actuator | Health check |
| GET | `/actuator/info` | Actuator | Info |

## Security Posture
- **Authentication**: None — all endpoints are unauthenticated.
- **Authorization**: None.
- **Transport**: Plain HTTP (no TLS configured).
- **Log injection**: Mitigated — `sanitizeForLog()` in both controllers strips `\r`, `\n`, `\t` from user-supplied values before logging (`FisMockController.java:37-46`, `ThreddMockController.java:37-47`).
- **Secret management**: No secrets required; no credentials stored.
- **Cryptography**: None.
- **CVE exposure**: Spring Boot 4.0.2 and Java 25 are pre-release; CVE tracking from official release channels has not yet matured for these versions.

## Technical Debt
- `ddl-auto: update` in application.yaml — schema management is undisciplined; no Flyway/Liquibase.
- No test sources in the repository — zero automated test coverage.
- No `-Xmx` JVM memory limit.
- `MockDataGenerator.java` uses `(SECURE_RANDOM.nextLong() & Long.MAX_VALUE) % (range)` — the modulo of a Long introduces slight bias, though acceptable for test data.
- Spring Boot 4.0.2 is not a GA release at time of analysis — dependency stability risk.
- The `ThreddMockController` log at line 103 is missing the argument for `{}` in `"Thredd PUT /cards/{}/status called"` — the `publicToken` is not interpolated into the log message.

## Code-Level Risks
| File | Line | Risk |
|------|------|------|
| `ThreddMockController.java` | 103 | Missing log argument for `{}` placeholder — `publicToken` not logged, potential confusion during debugging |
| `application.yaml` | 13 | `ddl-auto: update` — not safe for any shared environment |
| `Dockerfile` | 9 | `JAVA_TOOL_OPTIONS="-Xms256m"` — no `-Xmx` ceiling; container OOM risk |
| `MockDataGenerator.java` | 37 | `generatePersonId()` uses `SECURE_RANDOM.nextLong() & Long.MAX_VALUE` modulo pattern — minor bias, acceptable for test use only |

## Gen-3 Migration Requirements
This service is already Gen-3 tooling. No migration is required. When stable Spring Boot 3.x/4.x GA and Java LTS (21 or 25) versions align, dependency versions should be pinned to GA releases.
