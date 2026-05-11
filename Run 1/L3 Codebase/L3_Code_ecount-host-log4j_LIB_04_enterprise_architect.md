# 04 Enterprise Architect — ecount-host-log4j_LIB

## Platform Generation

`ecount-host-log4j_LIB` is a **Generation 1 (Gen-1)** component of the Onbe / EcountCore platform. Evidence:

- Depends on `log4j:log4j:1.2.15`, which was published in 2007 and reached end-of-life more than a decade ago.
- Parent POM is `com.ecount:module-parent:4` — an internal Gen-1 parent predating the `prepaid-parent` lineage used by Gen-2/3 modules.
- Version `1.0.1-SNAPSHOT` with no release history suggests the library was written in the early platform era and has never been formally versioned for release.

Contrast with Gen-3 services such as `embedded-payments-api` (Spring Boot 3.4, Java 21, Azure App Configuration) — this library is at least two generations behind.

## Role in the Platform Architecture

The library occupies the **observability / cross-cutting concerns** layer. It is not in any critical transaction path; its sole function is to enrich log records with host identity. In the Onbe platform:

```
[EcountCore WAR / microservices]
        |
        | configured Log4j appenders
        v
[ecount-host-log4j_LIB] --> enriches log lines with %h / %H tokens
        |
        v
[Log destination: file, console, syslog, ELK/Splunk]
```

## Dependencies

| Dependency | Version | Status |
|---|---|---|
| `log4j:log4j` | 1.2.15 | End of Life, CVE-2019-17571 (critical) |
| `com.ecount:module-parent` | 4 | Internal Gen-1 parent |

The library has **no transitive dependencies** beyond Log4j 1.2.15 itself.

## Consumers

The library is referenced (directly or via the Log4j 1.x API) by EcountCore platform services. Confirmed consumers visible in this repository set:
- `emboss-extract_LIB` — ships `log4j-1.2.8.jar` in its `lib/` directory; could adopt this layout.
- `ecount-core_SVC` — the `eCoreWar` module depends on `log4j-1.2-api` (the Log4j 2 → 1.x bridge), meaning the Log4j 1.x API is still present in the runtime classpath.

## Migration Complexity

| Migration Scenario | Effort | Risk |
|---|---|---|
| Replace Log4j 1.x layout with Log4j 2 plugin in this library | Medium | Low (isolated library) |
| Remove `log4j-1.2-api` bridge from ecount-core_SVC and all consumers | High | Medium (runtime behaviour changes) |
| Adopt structured JSON logging (logstash-logback-encoder) consistently | High | Low (additive change) |

## Strategic Recommendation

This library should be **deprecated and replaced** rather than maintained. The Gen-3 services (`embedded-payments-api`, `embedded-payments-sdk`) already use Logback with `logstash-logback-encoder` for structured JSON logging. The long-term target should be a unified structured-logging approach across all platform tiers. The functionality this library provides (host identification) is natively available in Log4j 2 via `%X{hostName}` and in Logback via MDC or the `logstash-logback-encoder`'s built-in host fields.

## Governance Flags

1. SNAPSHOT version in production — artefact immutability not enforced.
2. Log4j 1.x — no longer receiving security patches.
3. No automated publish pipeline — release process relies on manual execution.
