# 05 Solution Architect — xaffiliate-service_LIB

## Technical Architecture
Spring/Hibernate JPA library JAR (`com.ecount.one.service.affiliate:xaffiliate-service:4.0.1`). Java 21 compile target with Spring 6.x (via `prepaid-parent:6.0.12` BOM), Hibernate ORM (latest via BOM), and Spring JDBC for stored-procedure wrappers. The primary service class is `AffiliateServiceImpl` (Spring `@Transactional`, Hibernate `SessionFactory`). A secondary legacy implementation `AffiliateServiceImplOld` is also present.

Key structural layers:
- **Service**: `AffiliateService` (interface) + `AffiliateServiceImpl` — orchestrates affiliate CRUD via stored-procedure and Hibernate-backed DAOs
- **Stored-procedure wrappers** (`IProcXxx` / `ProcXxx` pattern): each stored procedure has a dedicated interface and implementation class; approximately 16 procedures covering affiliate creation, locale management, CSA detail screen entry/update, partner contact details, affiliate locale copy save/remove, and skin template retrieval
- **JPA entities**: `Affiliate`, `AffiliateDetail`, `AffiliateLanguage`, `AffiliateLocale`, `AffiliateLocaleAffiliate`, `AffiliateLocaleCopy`, `AffiliateLocaleSkin`, `AffiliateProperty`, `AffiliateLocaleErrors`, `AffiliateLocaleMessages` — full locale-aware affiliate data model
- **DAO**: `AccessLevelConfigDAO` / `IAccessLevelConfigDAO` — access level configuration retrieval
- **Lombok** (`@Slf4j`) for logging

## API Surface
No HTTP API. Programmatic library interface:

```java
// AffiliateService interface — key methods (partial)
AffiliateProperty getContext(Integer affiliateId, String languageCountryCode)
// Additional CRUD operations for affiliate, locale, CSA, partner details
// Locale copy management: save, remove
// Affiliate presentation and skin template retrieval
// B2C CSA detail screen entry and update
// Partner contact details CRUD
```

`AffiliateServiceImpl` is injected via Spring XML or Spring Java config into consumer applications; it requires a `SessionFactory` and ~16 stored-procedure bean dependencies wired by the consumer's Spring context.

## Security Posture
- No authentication or authorisation at the library level; all callers assumed to be trusted internal services
- `@Transactional("affiliateTransactionManager")` — transaction manager must be wired by the consumer; correct transaction management is critical for affiliate data integrity
- `AffiliateServiceImplOld` present — dead code; should be removed to reduce attack surface and confusion
- Affiliate data contains: affiliate name, locale settings, skin templates, partner contact details (name, address, contact info) — PII adjacent; access should be restricted to authorised programme-management services
- No input validation visible in the service interface; caller must validate `affiliateId` and `languageCountryCode` before calling
- `languageCountryCode` is validated to have exactly 5 characters in `getContext()` — basic length check only; no format validation (e.g., `en_US` pattern)
- Hibernate `SessionFactory` injection: if misconfigured, all operations will fail at runtime with no early warning
- Docker Compose file present (`docker-compose.yml`) with `init.sql` — local development database; must not contain production credentials

## Technical Debt
| Item | Severity |
|---|---|
| `AffiliateServiceImplOld` — dead code, active `@Transactional` class in production codebase | Medium |
| ~16 separate stored-procedure wrapper classes (high boilerplate) — should migrate to `SimpleJdbcCall` or Spring Data JDBC | Medium |
| Setter injection for `SessionFactory` and all stored-procedure beans (Java 21 era should use constructor injection) | Medium |
| `serialVersionUID` placement inconsistency (declared after instance fields in `AffiliateServiceImpl`) | Low |
| Commented-out `defaultAffiliateId` field — should be removed or documented | Low |
| `GitLab CI` pipeline (`.gitlab-ci.yml`) and `GitHub Actions` workflows coexist — dual-VCS era artifact | Low |
| `init.sql` committed to repo — verify no sensitive data | Low |
| `change.log` present but content unknown — confirm it does not contain credentials | Low |

## Gen-3 Migration
The library is already at Java 21 compile target and modern Spring/Hibernate (via parent BOM) — a positive. Recommended next steps:
1. Remove `AffiliateServiceImplOld` entirely
2. Replace `SessionFactory` direct usage with Spring Data JPA repositories (`@Repository` with `JpaRepository<AffiliateLocale, ...>`)
3. Replace individual stored-procedure wrapper classes with `@Repository` methods using `SimpleJdbcCall` or Spring Data JPA `@Procedure`
4. Migrate to constructor injection throughout
5. Add bean validation annotations to the `AffiliateService` interface method parameters (`@NotNull`, `@Size`, etc.)
6. Expose a REST API facade in a companion service if affiliate data needs to be accessible outside the JVM (currently library-only)

## Code-Level Risks
- `getContext()` returns `null` if `languageCountryCode` is null or not 5 chars long — callers silently receive null without an exception; this is an inconsistent API contract (some callers may NPE on the return value)
- `@Transactional("affiliateTransactionManager")` class-level annotation: if the consumer's Spring context names the transaction manager differently, all transactional methods will fail at runtime with a `NoSuchBeanDefinitionException`
- `Serializable` on `AffiliateServiceImpl` is unusual for a service class; if instances are serialised (e.g., HTTP session), the transient `SessionFactory` and all `ProcXxx` beans will be null after deserialization
- The `IAccessLevelConfigDAO` field is not included in the constructor; it is setter-injected and will be null if the consumer forgets to wire it — any method calling `accessLevelConfigDAO` will throw NPE
