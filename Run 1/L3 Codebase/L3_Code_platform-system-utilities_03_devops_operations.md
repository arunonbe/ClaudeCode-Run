# DevOps / Operations — platform-system-utilities

## Build System

| Property | Value |
|---|---|
| Build tool | Apache Maven 3.9+ (Maven Wrapper `./mvnw` provided) |
| Java version | 25 (Liberica JDK) — enforced by maven-enforcer-plugin |
| Root artifact | `com.onbe.platform:platform-system-utilities:0.0.1-SNAPSHOT` (POM packaging) |
| Modules | `platform-dependencies-bom`, `platform-idempotency` (parent), `platform-idempotency-core`, `platform-idempotency-redis`, `platform-envers-db-audit` |
| Integration tests | Testcontainers 1.21.0 — Docker required for local runs |
| Test report | JaCoCo 0.8.11 (configured in parent POM, used per consumer) |

### Maven Enforcer Rules
- Maven ≥ 3.9
- Java ≥ 25

## Deployment / Publishing

This repo publishes **Java library JARs** to GitHub Packages, not deployable services.

| Workflow | File | Trigger | Target |
|---|---|---|---|
| Publish idempotency-core | `github-package-publish-idempotency.yml` | Push to `main` paths `platform-idempotency/**`; `workflow_dispatch` | GitHub Packages (`Onbe/om-ci-setup` reusable workflow) |
| Publish envers-db-audit | `github-package-publish-envers-audit.yml` | Push to `main` paths `platform-idempotency/**`; `workflow_dispatch` | GitHub Packages (note: path filter appears to be a copy-paste bug; see risks) |
| CodeQL analysis | `codeql.yml` | Weekly schedule (Wednesdays 08:23 UTC); `workflow_dispatch` | GitHub Security tab |

All publishing delegates to `Onbe/om-ci-setup/.github/workflows/java-package-publish.yml@main` with `secrets: inherit`.

## Configuration Management

| Property | Location | Default |
|---|---|---|
| `idempotency.key-prefix` | `IdempotencyProperties` / Spring `application.yml` in consumer | `idem` |
| `idempotency.ttl` | `IdempotencyProperties` | `24h` — **note: not wired to `IdempotencyService.DEFAULT_TTL`** |
| `idempotency.lock-ttl` | `IdempotencyProperties` | `30s` |
| `idempotency.fail-open-on-redis-error` | `IdempotencyProperties` | `true` |
| `spring.application.name` | Consumer service | Used as the `service` tag in Redis keys and Micrometer metrics |
| `idempotency.key-prefix` (AOP) | `@Value("${idempotency.key-prefix:idem}")` in `IdempotencyAspect` | `idem` |

Auto-configuration is registered via `META-INF/spring/org.springframework.boot.autoconfigure.AutoConfiguration.imports` for both `IdempotencyCoreAutoConfiguration` and `IdempotencyRedisAutoConfiguration`.

## Observability

| Signal | Mechanism | Metrics emitted |
|---|---|---|
| Metrics | Micrometer (`IdempotencyMetrics`) | `idempotency.hit`, `idempotency.miss`, `idempotency.lock.conflict`, `idempotency.payload.mismatch`, `idempotency.redis.error` — all tagged with `service` and `endpoint` |
| Logging | SLF4J / Logback (via `@Slf4j`) | INFO on key resolution; DEBUG on lock/result operations; WARN on conflicts and mismatches; ERROR on store failures |
| Distributed tracing | OpenTelemetry | OTel Baggage and Span used as inputs (not exported by this library) |
| Audit trail | Hibernate Envers → `revinfo` table | Populated with actor.id, source, reason, trace_id from OTel context |

## Infrastructure Dependencies

| Dependency | Purpose | Fail behaviour |
|---|---|---|
| Redis | Idempotency lock and result cache | Fail-open (default) — requests proceed without idempotency |
| Relational DB (consumer) | Hibernate Envers `revinfo` persistence | Hard dependency for audit; consumer controls connection pool |
| Docker | Integration tests (Testcontainers) | Tests fail without Docker at build time |
| GitHub Packages registry | Library publication and consumption | Build fails if registry unreachable during `mvn install` |

## Operational Risks

| Risk | Severity | Mitigation |
|---|---|---|
| Fail-open Redis behaviour means zero idempotency when Redis is down | High | Set `idempotency.fail-open-on-redis-error=false` for payment-critical services; implement Redis cluster / sentinel |
| `platform-idempotency.ttl` property is not wired to `IdempotencyService.DEFAULT_TTL` | Medium | `DEFAULT_TTL` is hardcoded to 24 h in the service; changing the property has no effect without a code fix |
| envers-audit publish workflow path filter watches `platform-idempotency/**` (likely copy-paste error) | Medium | Changes to `platform-envers-db-audit` may not auto-trigger publish; manual `workflow_dispatch` required |
| Java 25 is a preview/early-access JDK release | Medium | Limited LTS support; dependency on Liberica JDK build; upgrade path unclear |
| No Dependabot config for this repo | Low | `.github/dependabot.yml` exists for `platform-idempotency` sub-path only; root-level dependencies unmonitored |

## CI/CD Pipeline Summary

```
Push to main (platform-idempotency/**) 
  --> github-package-publish-idempotency.yml
      --> om-ci-setup java-package-publish.yml
          mvn -pl platform-idempotency/platform-idempotency-core -am
          --> Publish JAR to GitHub Packages

Pull Request to main
  --> Same workflow (build/test only, no publish)

Weekly Wednesday
  --> codeql.yml
      --> om-ci-setup codeql-auto.yml
          --> GitHub Security alerts
```
