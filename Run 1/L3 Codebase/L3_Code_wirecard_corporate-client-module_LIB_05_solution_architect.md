# Solution Architect — wirecard_corporate-client-module_LIB

## Technical Architecture

### Module Structure
| Module | Role |
|---|---|
| `corporate-client-module-config` | Spring Boot application entry; datasource TLS config; app context wiring; Swagger properties |
| `corporate-client-module-service` | Business logic services (corporate client, card, virtual client management) |
| `corporate-client-module-data` | DTOs, request/response models, events, exceptions |
| `corporate-client-module-persistence` | JPA entities, Spring Data repositories |
| `corporate-client-module-db-scripts` | Liquibase changelogs (Oracle + H2) |
| `corporate-client-module-db-app` | Standalone DB migration application |
| `corporate-client-module-rest-controller` | REST controllers (v1), Swagger config, OAuth2 resource server, RPM packaging |
| `corporate-client-module-event-consumer` | EventHub `AccountStateEvent` consumer |
| `corporate-client-module-auth-server-client` | HTTP client for ISS Auth Server (technical user management) |
| `corporate-client-module-cmm-client` | HTTP client for CMM (Card Management Module) |
| `corporate-client-module-documentation` | API doc generation |
| `corporate-client-module-qa` | QA test utilities |

### Runtime Stack
- Spring Boot 1.5.13.RELEASE
- Spring Security OAuth2 (resource server — JWT, brand-aware)
- Spring Data JPA + Hibernate
- HikariCP
- Liquibase
- ActiveMQ EventHub
- EhCache 3 (JCache)
- Springfox Swagger 2 + Swagger UI
- Logstash Logback encoder
- `correlation-web` (Wirecard correlation ID library)

## API Surface

### REST Endpoints (v1, base `/corporate-client-module`)
All require JWT authentication. Brand-aware authorisation enforced.

| Method | Path | Auth Role | Description |
|---|---|---|---|
| POST | `/callcenter-api/corporate-clients` | `CorporateClientCreate` + brand permission | Create corporate client |
| PUT | `/callcenter-api/corporate-clients/{key}` | `CorporateClientUpdate` + brand auth | Update corporate client |
| GET | `/callcenter-api/corporate-clients/{key}` | `CorporateClientRead` | Retrieve corporate client |
| POST | `/callcenter-api/corporate-clients/{key}` | `CorporateClientUpdate` + brand auth | Update status |
| POST | `/callcenter-api/corporate-clients/searches` | `CorporateClientRead` | Search (brand-filtered) |
| POST | `/callcenter-api/corporate-clients/history` | `CorporateClientRead` | Retrieve history |
| POST | `/callcenter-api/corporate-clients/cards` | `CardCreate` | Create card (via CMM) |
| POST | `/callcenter-api/corporate-clients/products` | `ProductCreate` | Create product |
| (Additional card/product/virtual-client endpoints inferred from handler classes) | | | |

Content types: `application/vnd.wirecard.issuing+json;version=1` and XML variant (from `ApiVersion.java` constants).

### EventHub
- **Consumes**: `AccountStateEvent` (inbound from EventHub)

## Security Posture

### Authentication / Authorisation
- OAuth2 Resource Server (`spring-security-oauth2`): validates JWTs against ISS Auth Server JWK Set.
- Brand-aware authorisation: `@PreAuthorize("hasRole('CorporateClientCreate') and hasPermission(#client.brands, 'brand')")` — enforces that the authenticated user's JWT includes the brand being operated on.
- `AuthorizationHandler` / `AuthorizationHandlerImpl` — additional runtime authorisation checks (e.g., `authorizeUpdateCorporateClient`, `authorizeExistingClientForBrandsByKey`).
- Technical user authority list hardcoded in `application.yml`: `CorporateClientRead`, `CardProgramDetailsRead`, `CardCreate`, `CardLoadUnload`, `CardClose`, `ProductCreate`, `ProductRead`, `ProductUpdate`, `VirtualClientCreate`, `VirtualClientRead`, `VirtualClientUpdate`, `AccountFundTransfer`, `AccountFundTransferFaceValueDiscount`.

### Cryptography
- JDBC TLS: same pattern as `check-agent` (`DataSourceConfiguration` + `DataSourceTruststoreProperties`).
- No application-layer encryption for PII or `T_PIN` column.
- `T_PIN VARCHAR2(16)`: if this is a PIN value, it must be encrypted per PCI DSS Req 3.5. **Storing a cleartext PIN is prohibited.**

### Secrets
- `application.yml` QA credentials (must not reach production):
  - `ccp.client.password: aaaa1111`
  - `cmm.client.password: aaaa1111`
  - `iss-auth.client.password: aaaa1111`
- Truststore content: Base64-encoded in environment config — same risk as `check-agent`.

### Known CVEs / EOL
- **Spring Boot 1.5.13 (EOL)**: Same critical EOL status as `check-agent`.
- **`spring-security-oauth2`**: EOL, unpatched CVEs.
- **`jmock-junit4` / `jmock-legacy`** test dependencies: older JMock versions may have vulnerabilities; test-scope only.
- **Springfox 2.x**: Not updated since 2020; known incompatibilities with newer Spring Boot.
- **`com.oracle:ojdbc8`**: Version from BOM — must be confirmed against CVE database.

## Technical Debt
1. **Spring Boot 1.5.13 (EOL)** — highest priority.
2. **`compile` Gradle scope** — deprecated; must migrate to `implementation`/`api`.
3. **`RestTemplate`-based clients** (`CmmClient`, `AuthServerClient`): `RestTemplate` is deprecated in Spring 5+; must migrate to `WebClient` or `RestClient`.
4. **`@RequestHeader(value="x-username", required=false) String agentLogin`** in controllers: Agent login passed as a custom HTTP header, not via the authenticated principal. This bypasses the authentication system for audit trail purposes.
5. **`@Size(max = 128)` on `agentLogin`** but no sanitisation: The header value is passed directly to service layer — input validation is minimal.
6. **`T_PIN` column in `CORP_CONTACT`**: No encryption, no masking. Critical data remediation required.
7. **Correlation ID interceptor on CMM only** (`CorrelationIdInterceptor`): Correlation IDs should propagate to all downstream calls (CCP, Brand Server, ISS Auth Server) for distributed tracing.
8. **Swagger host hardcoded** in `application.yml`: `app.swagger.host: localhost:9000` — must be environment-specific.
9. **`bootRepackage.dependsOn = [jar]`** in `corporate-client-module-rest-controller/build.gradle:45`: Suppresses Spring Boot's default test inclusion in the fat JAR, which is non-standard.

## Gen-3 Migration Requirements
Largely identical to `check-agent` plus:
1. **`T_PIN` remediation** (before migration): Determine what `T_PIN` stores; if a PIN, either remove it, replace with a tokenised reference, or implement proper encryption — this is a prerequisite, not a post-migration task.
2. **PII column encryption or masking**: For `DATE_OF_BIRTH`, names, email, phone in `CORP_CONTACT`.
3. **Migrate `BrandsAwareAuthentication`**: Rebuild brand-aware OAuth2 claims extraction for Spring Security 6.x.
4. **Replace `@RequestHeader x-username` with authenticated principal**: Use `Authentication.getName()` or JWT claim for audit username.

## Code-Level Risks

| File | Line | Risk |
|---|---|---|
| `corporate-client-module-config/src/main/resources/application.yml` | 69–70 | `ccp.client.password: aaaa1111` — QA credential committed |
| `corporate-client-module-config/src/main/resources/application.yml` | 93–94 | `cmm.client.password: aaaa1111` — QA credential committed |
| `corporate-client-module-config/src/main/resources/application.yml` | 108–109 | `iss-auth.client.password: aaaa1111` — QA credential committed |
| `corporate-client-module-db-scripts/.../db.changelog-1.0.xml` | `CORP_CONTACT.T_PIN` | `T_PIN VARCHAR2(16)` — potential SAD/PIN storage without encryption |
| `corporate-client-module-db-scripts/.../db.changelog-1.0.xml` | `CORP_CONTACT.DATE_OF_BIRTH` | DOB stored without column encryption |
| `corporate-client-module-rest-controller/.../CorporateClientController.java` | 96 | `x-username` header used for audit trail — bypasses authentication; can be spoofed |
| `build.gradle` | 19 | Wirecard Nexus `http://` (plaintext) — supply chain attack vector |
| `corporate-client-module-rest-controller/build.gradle` | 44–45 | `bootRepackage.dependsOn = [jar]` suppresses standard Spring Boot fat-JAR test inclusion — non-standard build pattern |
| `ansible/inventories/prod` | (not read) | Production hostnames may be committed — must review for credential exposure |
