# Solution Architect — oneplatform-rest_API

## Technical Architecture
- **Framework**: Spring Boot 3.x (parent `onbe-spring-boot-parent:0.0.15`), Java 21, Maven.
- **Security**: Spring Security with stateless JWT (HS256); `JwtAuthFilter` intercepts all requests.
- **Caching**: Jedis 5.2.0 (Redis) + Ehcache (JCache/javax.cache) + Spring Boot Cache abstraction.
- **Database access**: Spring JDBC (`JdbcTemplate`, `StoredProcedure`) for stored procedure calls; three data sources (cbaseapp, EcountCore, jobsvc) configured via `DatabaseBeanConfig`, `ECountCoreBeanConfig`.
- **Service communication**: Dapr SDK (dapr-sdk-springboot 1.12.0) for internal service invocation and pub/sub; Apache HttpClient 5 for direct HTTP calls (CBTS, BioCatch, reCAPTCHA).
- **Legacy integration**: xplatform XMLRPC library for all core ecount backend calls.
- **Logging**: Log4j2 with SLF4J bridge.
- **OpenAPI**: SpringDoc OpenAPI 3 UI.
- **Validation**: Jakarta Bean Validation (`spring-boot-starter-validation`); custom `PasswordValidator`.

## API Surface (Controller Summary)
| Controller | Path Prefix | Key Operations |
|-----------|-------------|----------------|
| `LoginController` | `/login` | Login, logout, SSO login, forgot username/password, VE login |
| `MFAController` | `/mfa` | OTP generate, validate, get request |
| `RegistrationController` | `/registration` | Card validate, register, save registration, password change |
| `DashboardController` | `/dashboard` | Dashboard data, card status update |
| `TransactionController` | `/transaction` | Transaction history, unclaimed history |
| `BankTransferController` | `/bankTransfer` | ACH bank details, one-time transfer, auto ACH, confirm |
| `DebitTransferController` | `/debitTransfer` | Push-to-debit OTT, recurring, retrieve transaction |
| `OffCardTransferController` | `/offCard` | PayPal and Venmo payout, getUserInfo, confirm |
| `IEFTController` | `/ieft` | FX rate, bank search, IBAN validate, OTT, auto-claim allotments |
| `WesternUnionController` | `/westernUnion` | WU transfer operations |
| `RiaController` | `/ria` | Ria token save |
| `ChoiceController` | `/choice` | Payment hub choice (returning user) |
| `ClaimableChoiceController` | `/claimableChoice` | First-time claimable payment selection |
| `CardActivationController` | `/cardActivation` | Activate, PIN change, submit PIN |
| `OrderController` | `/order` | Order card, request check, update address |
| `MyAccountController` | `/myAccount` | Profile details, country/state list |
| `DisclosuresController` | `/disclosures` | Program disclosures, properties |
| `GenericController` | `/v1/generic` | Affiliate data, menu/wizard settings, promo image |
| `WebToWalletController` | `/webToWallet` | Apple/Google Pay push provisioning |

## Security Posture

### Authentication
- **JWT HS256** with 10-minute access token and 60-minute refresh token.
- `JwtConfig.java` uses `Jwts.parser().setSigningKey(getSignKey())` — note: `setSigningKey()` is deprecated in JJWT 0.12.x (should be `verifyWith()`). [JwtConfig.java:37]
- `SignatureAlgorithm.HS256` passed to `signWith()` — deprecated in JJWT 0.12.x. [JwtConfig.java:67, 72]
- **CSRF disabled** for all paths (`csrf.ignoringRequestMatchers("/**")`). [SecurityConfig.java:21]
- `SKIP_AUTHENTICATION_REQUEST_MATCHERS` whitelist defined in `OPConstants` — not read in this analysis; confirm it does not over-permit.
- Session management: `STATELESS` — correct for JWT.

### Hardcoded Secrets (CRITICAL FINDINGS)
| Secret | Location | Line |
|--------|----------|------|
| Azure App Config connection string (with embedded secret) | `application.yaml` | 12 |
| Redis cache key (Base64) | `application.yaml` | 218 |
| CBTS password | `application.yaml` | 169 |
| CBTS username | `application.yaml` | 168 |
| Western Union static key | `application.yaml` | 126 |
| Azure App Config connection string (with embedded secret) | `azure.appconfig.connection-string` section | 237-238 |
| PayPal client IDs (sandbox and prod) | `application.yaml` (dev) / `application-prod.yaml` | 118-119 / 82-83 |

All of the above are committed to source and represent PCI DSS Req 3.5 / Req 6.3 violations.

### Cryptography
- JWT: HS256; secret from Key Vault in production (`mypaymentvaultapi-jwt-secret`).
- AES for DDA encryption: key/IV from Key Vault.
- JWE for selective payload encryption.
- TLS 1.2 on all SQL Server connections.
- Redis TLS in production.
- `citi.crt` bundled in resources for Western Union trust store.

### External API Risk
- BioCatch customer ID `osiristest` hardcoded in dev YAML (line 137); prod value `osiris` in prod YAML.
- reCAPTCHA API keys injected from Key Vault in production.

## Technical Debt
- **Deprecated JJWT API**: `setSigningKey()`, `SignatureAlgorithm.HS256`, `setClaims()`, `setSubject()`, `setIssuedAt()`, `setExpiration()` are all deprecated in JJWT 0.12.x (`JwtConfig.java`).
- **`@SuppressWarnings` on raw types**: `PaymentServiceImpl` (in payment-service) uses raw `Map` and `Hashtable` — not this service but indicates shared legacy patterns.
- **`spring.main.allow-bean-definition-overriding=true`** (`application.yaml` line 3) — suppresses Spring's safe bean definition check; indicates bean definition conflicts.
- **SNAPSHOT dependency**: `onbe-cloud-starter:2.0.0-SNAPSHOT` makes builds non-reproducible.
- **Test profile embeds H2** for in-memory DB — integration tests cannot verify SP behavior against real SQL Server.
- **commented-out feature management config** in `pom.xml` (lines 403-460) indicates incomplete Azure App Configuration feature flag integration.
- **Dead PayPal client ID configuration** in `application.yaml`: two keys `paypalClientIdSunrise` and `paypalClientIdMB` with identical values.

## Gen-3 Migration Requirements
1. Remove all hardcoded secrets from `application.yaml`; replace with Key Vault references.
2. Upgrade JJWT to remove deprecated API usage.
3. Enable CSRF protection or document the justification for global disable with compensating controls.
4. Replace `xplatform`, `xsecurity`, and director-service XMLRPC with direct microservice APIs.
5. Remove `allow-bean-definition-overriding=true`.
6. Add distributed tracing (OpenTelemetry).
7. Promote `onbe-cloud-starter` to a stable release.
8. Add container scan / SCA to CI/CD pipeline.

## Code-Level Risks (File:Line References)
| Risk | File | Line(s) |
|------|------|---------|
| Azure App Config secret hardcoded | `src/main/resources/application.yaml` | 12 |
| Redis cache key hardcoded | `src/main/resources/application.yaml` | 218 |
| CBTS credentials hardcoded | `src/main/resources/application.yaml` | 168-169 |
| Western Union static key hardcoded | `src/main/resources/application.yaml` | 126 |
| Deprecated JJWT API | `src/main/java/.../config/token/JwtConfig.java` | 37, 65-72 |
| CSRF disabled globally | `src/main/java/.../config/SecurityConfig.java` | 21 |
| `allow-bean-definition-overriding` | `src/main/resources/application.yaml` | 3 |
| Production PayPal client IDs in source | `src/main/resources/application-prod.yaml` | 82-83 |
