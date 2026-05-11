# Solution Architect — platform-system-utilities

## Technical Architecture

Multi-module Maven monorepo. No deployable artifact; outputs are JAR libraries published to GitHub Packages.

```
Root POM (pom packaging)
  platform-dependencies-bom/   -- import BOM only, no code
  platform-idempotency/        -- parent POM
    platform-idempotency-core/ -- Spring Boot 4 auto-configured library
      IdempotencyAspect        -- @Around AOP interceptor
      IdempotencyService       -- orchestration (lock → verify → execute → cache)
      IdempotencyStore (SPI)   -- pluggable storage interface
      IdempotencyMetrics       -- Micrometer counters
      IdempotencyProperties    -- @ConfigurationProperties
      IdempotencyKey/Result    -- value objects (Java records)
    platform-idempotency-redis/ -- Spring auto-configured Redis store
      RedisIdempotencyStore    -- StringRedisTemplate SETNX + SET/GET
  platform-envers-db-audit/   -- Envers extension
    CustomRevisionEntity       -- @Entity revinfo table
    CustomRevisionListener     -- OTel Baggage → audit fields
```

## API Surface

This repo exposes no HTTP APIs. Its public API surface is purely Java:

| Class / Annotation | Package | Consumer Usage |
|---|---|---|
| `@Idempotent` | `com.onbe.idempotency.core.annotation` | Annotate Spring-managed methods |
| `IdempotencyStore` (SPI) | `com.onbe.idempotency.core.spi` | Implement to provide custom backing store |
| `IdempotencyProperties` | `com.onbe.idempotency.core.config` | Override via `application.yml` |
| `CustomRevisionEntity` | `com.onbe.platform.envers.audit` | Extended by consumers' audit entity if needed |
| `CustomRevisionListener` | `com.onbe.platform.envers.audit` | Registered via `@RevisionEntity` — no consumer action required |

## Security Posture

### Authentication / Authorisation
- Library itself has no authentication surface
- Redis access credentials are supplied by the consumer service's Spring configuration
- GitHub Packages authentication uses `secrets: inherit` from `om-ci-setup` reusable workflow

### Cryptography
| Usage | Algorithm | Implementation |
|---|---|---|
| Request body fingerprinting | SHA-256 | `MessageDigest.getInstance("SHA-256")` in `IdempotencyService:177` — standard JCA, correct |
| Redis value encryption | None | Values stored as plaintext JSON strings — gap if CHD in payload |

### Secrets Management
- No secrets in source code
- Redis connection string is Spring Boot external configuration (consumer responsibility)
- GitHub Actions CI uses `secrets: inherit`

### CVE / Dependency Risk
| Concern | Detail |
|---|---|
| Spring Boot 4.0.5 | Very recent release; verify CVE scan via CodeQL workflow (runs weekly) |
| Testcontainers 1.21.0 | Test scope only; no runtime exposure |
| Apache Commons HttpClient (NOT present) | profile_SVC uses legacy HttpClient; this repo does not |
| `0.0.1-SNAPSHOT` artifacts | Mutable; consumers should pin to released versions |

### CodeQL / SAST
- CodeQL configured (`codeql.yml`), runs weekly on Wednesdays and on `workflow_dispatch`
- Delegates to `Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`

## Technical Debt

| Item | Location | Severity |
|---|---|---|
| `IdempotencyProperties.ttl` and `lockTtl` are defined but `IdempotencyService` uses hardcoded `DEFAULT_TTL = Duration.ofHours(24)` and does not inject the properties bean | `IdempotencyService.java:41`, `IdempotencyProperties.java:26` | High — configuration change has no effect |
| `platform-envers-db-audit` publish workflow path filter watches wrong path (`platform-idempotency/**` instead of `platform-envers-db-audit/**`) | `.github/workflows/github-package-publish-envers-audit.yml:26` | Medium — publish may not trigger on envers changes |
| All modules at `0.0.1-SNAPSHOT` — no stable release | Root `pom.xml:9` | Medium — consumers depend on mutable snapshot |
| `IdempotencyAspect.serialiseRequestBody` silently skips `List` parameters | `IdempotencyAspect.java:229` | Low — collections are not hashed; could allow payload swaps with list bodies |
| No test for OTel Baggage extraction in `CustomRevisionListener` | Inspection of test files | Low — baggage path is untested |

## Gen-3 Migration Requirements

This repo IS already Gen-3. For consuming legacy (Gen-1/Gen-2) services to adopt this library they must:
1. Upgrade to Java 25 (from Java 8/11/17/21)
2. Upgrade to Spring Boot 4.0.5 (from Spring Boot 2.x/3.x)
3. Add Redis infrastructure if not already present
4. Configure OTel agent/SDK for trace propagation (otherwise audit actor fields will be null)
5. Replace any custom idempotency/audit implementations with this library

## Code-Level Risks (file:line references)

| Risk | File | Line | Detail |
|---|---|---|---|
| `DEFAULT_TTL` hardcoded, ignores `IdempotencyProperties` | `platform-idempotency-core/.../IdempotencyService.java` | 41 | `private static final Duration DEFAULT_TTL = Duration.ofHours(24)` — property bean is never injected into this field |
| Fail-open: Redis errors are caught and swallowed | `IdempotencyService.java` | 76–78, 85–87, 124–128, 137–140, 148–151 | All store operations wrapped in try/catch that log and continue — zero idempotency under Redis outage |
| `serialiseRequestBody` skips `List` parameters entirely | `IdempotencyAspect.java` | 229 | `if (List.class.isAssignableFrom(type)) continue;` — bulk-operation endpoints with list bodies will have empty hash |
| Wrong path trigger in envers publish workflow | `.github/workflows/github-package-publish-envers-audit.yml` | 26 | `paths: - 'platform-idempotency/**'` should be `platform-envers-db-audit/**` |
| `toIdempotencyResult` catches `JsonProcessingException` and stores empty body | `IdempotencyAspect.java` | 249 | Silently returns empty string as cached body on serialisation failure — cached no-content response returned for subsequent identical requests |
