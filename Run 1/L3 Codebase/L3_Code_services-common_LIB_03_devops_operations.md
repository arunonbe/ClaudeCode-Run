# DevOps / Operations View — services-common_LIB

## Build System

- **Build tool**: Maven with Maven Wrapper (`mvnw`, `mvnw.cmd`)
- **Java version**: Java 21 (`maven.compiler.source=21`, `maven.compiler.target=21`)
- **Parent POM**: `com.parents:prepaid-parent:6.0.12` (Onbe internal parent; skips `service-parent` layer)
- **Version**: `3.0.2-SNAPSHOT` — SNAPSHOT indicates active development
- **Packaging**: JAR library
- **Key dependencies**:
  - `com.ecount.service.core.ecountcore:common:3.0.3` — eCount core common library
  - `commons-lang:commons-lang` — version managed by prepaid-parent
  - `org.apache.commons:commons-pool2:2.11.1` — object pooling (used for thread pooling or connection pooling in custom cache)
  - `jakarta.servlet:jakarta.servlet-api` — provided scope (Jakarta EE namespace confirms Java EE 9+ compatibility despite legacy code patterns)
- **Enforcer**: `banTransitiveDependencies` rule enforced (excluding Spring Boot and ecountcore transitive deps) — prevents accidental transitive dependency pollution
- **Build plugin**: `maven-jar-plugin` for JAR packaging

## CI/CD Pipeline

- **GitHub Actions**: 
  - `.github/workflows/codeql.yml` — CodeQL static analysis (Java)
  - `.github/workflows/github-package-publish.yml` — publishes JAR to GitHub Packages on release
- **Dependabot**: `.github/dependabot.yml` — automated dependency update PRs
- **No deployment workflow**: Library artifact published to GitHub Packages Maven registry; no standalone deployment pipeline
- **No GitLab CI**: GitHub-only pipeline (migrated from GitLab)

## Deployment Model

- **Artifact type**: JAR library published to GitHub Packages Maven registry
- **Consumers**: All Gen-1 and Gen-2 services (`order_SVC`, `xaffiliate-service_LIB`, `xml-rpc-clients_LIB`, request services, job services, etc.)
- **No runtime deployment**: The library is loaded into the JVM of its consuming services
- **Version constraint**: The `3.0.2-SNAPSHOT` version allows continuous updates; consumers must pin to a release version for production stability

## Runtime

- **Java 21** target (compiled with Java 21 source/target)
- **Jakarta Servlet API**: Provided dependency; compatible with Jakarta EE 9+ containers (Tomcat 10+, WildFly 26+)
- **No Spring Boot**: This is a plain JAR library; no Spring Boot auto-configuration
- **Spring-compatible**: Designed to be wired via Spring XML or annotation-based configuration in consuming services

## Secrets Management

- No secrets managed by this library
- DataSource injection is externalized to consuming application Spring context
- No hardcoded connection strings, passwords, or API keys

## Observability

- **Logging**: SLF4J API (via commons-logging or direct SLF4J) — log output depends on the consuming application's logging configuration
- **No standalone metrics**: No Micrometer or Actuator integration; the library contributes to observability through its logging infrastructure
- **Custom cache**: The in-memory `Cache`/`CacheManager` implementation has no metrics or monitoring hooks. Cache hit/miss rates, eviction events, and memory usage are not observable. This is a gap for production monitoring.
- **Thread safety**: `ReadWriteLock`, `Mutex`, and `Semaphore` implementations provide thread safety but have no deadlock detection or monitoring capability

## Known EOL Runtimes and CVEs

- **`3.0.2-SNAPSHOT`**: Active development; the SNAPSHOT label means this should not be used in production builds without a pinned release version
- **Custom threading primitives**: `Mutex`, `Semaphore` in `pi/threads/` predate `java.util.concurrent` (introduced in Java 5). In Java 21, these should be replaced with `ReentrantLock`, `Semaphore` from `java.util.concurrent`, or virtual threads. The custom implementations may have subtle locking bugs.
- **Custom cache implementation**: The `Cache`/`CacheManager` in `cache/` predates Spring Cache, Caffeine, and Redis. In Gen-3, this should be replaced with Spring Cache + Redis or Caffeine. The custom implementation has no TTL monitoring, no cache statistics, and no eviction logging.
- **Custom SAX parser**: `saxtool/` implements a custom SAX parsing framework for eCount XML messages. This is tightly coupled to the legacy XML-RPC message format and has no path to Gen-3 compatibility (Gen-3 uses JSON/Avro).
- **`ecount.service.core.ecountcore:common`**: Transitive dependency on internal eCount core common library; version `3.0.3` must be confirmed available in the current Maven registry and not blocked by `transitiveDependencies` banlist exceptions.
- **`commons-pool2:2.11.1`**: Not the latest (2.12.x); confirm no security advisories for 2.11.1 before next release.
