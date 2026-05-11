# 01 Business Analyst — ecount-host-log4j_LIB

## Overview

`ecount-host-log4j_LIB` is a small, purpose-built Java library that extends the Apache Log4j 1.x logging framework to add hostname and IP-address awareness to log output. It is consumed by the EcountCore platform and other Onbe back-end services that use the legacy Log4j 1.x API. The library is packaged as a JAR and distributed via Onbe's internal Maven repository under the group `com.ecount.log4j`, artifact `ecount-host-log4j`, version `1.0.1-SNAPSHOT` (`pom.xml` line 15).

## Business Purpose

In a distributed payments platform, correlating log lines to the specific server or container that emitted them is essential for incident response, capacity planning, and regulatory audit trails. The standard Log4j 1.x `PatternLayout` provides thread name, class name, log level, and message, but does not include the host identity by default. `ecount-host-log4j_LIB` fills this gap: it introduces two custom pattern tokens (`%h` and `%H`) that inject the server's DNS hostname and hostname-plus-IP into every log line.

## Stakeholder Value

| Stakeholder | Benefit |
|---|---|
| Operations / SRE | Can immediately identify which host emitted an error without cross-referencing deployment maps |
| Security / Compliance | Log lines carry host identity, supporting PCI DSS Req 10 (audit log integrity and traceability) |
| Development | No code change needed in consuming services — only a logging-config change to adopt the new pattern |

## Functional Scope

The library provides exactly two classes:

1. `EcountPatternLayout` — a drop-in replacement for `org.apache.log4j.PatternLayout`. Consuming services configure this class in their `log4j.xml` or `log4j.properties` file as the layout class for any appender.
2. `EcountPatternParser` (inner to the `helpers` package) — extends `org.apache.log4j.helpers.PatternParser` to recognise `%h` (hostname only) and `%H` (hostname + IP address in parentheses, comma-terminated). Hostname and IP are resolved once at class-load time via `java.net.InetAddress.getLocalHost()`.

## Integration Context

The library is consumed by at least:
- `emboss-extract_LIB` — the `lib/log4j-1.2.8.jar` file in that repo's `lib/` folder, and the `log4j.xml` configuration file, both reference Log4j 1.x; the ecount-host-log4j layout could be wired in via that config.
- `ecount-core_SVC` (legacy War module) — the `eCoreWar/pom.xml` depends on `log4j-1.2-api` (the Log4j 2 bridge) and could still reference the legacy layout.

## Limitations and Observations

- The library contains no business logic — it is a pure cross-cutting concern (observability).
- It does not implement log filtering, masking, or redaction. If a consuming service logs sensitive data such as PANs or account numbers, this library will include them in the formatted output without any protection.
- The hostname resolution occurs at startup; in a containerised environment with dynamic hostnames (e.g., Kubernetes pods), this is generally correct, but the value will not update if the network identity changes at runtime.
- The library is versioned as `1.0.1-SNAPSHOT`, indicating it has never been promoted to a release version. In a PCI DSS environment, deploying SNAPSHOT artefacts to production is a governance concern.

## Regulatory Relevance

PCI DSS v4.0.1 Requirement 10 mandates that audit logs include sufficient information to reconstruct events, including the originating system. By stamping every log line with the host identity, this library directly supports Req 10.3 (log entries must include the originating system or process name).
