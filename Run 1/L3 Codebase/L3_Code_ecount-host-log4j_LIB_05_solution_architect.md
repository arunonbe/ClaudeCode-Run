# 05 Solution Architect — ecount-host-log4j_LIB

## All Classes and Methods

### `com.ecount.log4j.EcountPatternLayout`
File: `src/main/java/com/ecount/log4j/EcountPatternLayout.java`

| Method | Signature | Purpose |
|---|---|---|
| `createPatternParser` | `protected PatternParser createPatternParser(String pattern)` | Overrides the parent factory method to return an `EcountPatternParser` instead of the standard `PatternParser`. This is the single integration point between the layout and the parser. |

Extends: `org.apache.log4j.PatternLayout`

### `com.ecount.log4j.helpers.EcountPatternParser`
File: `src/main/java/com/ecount/log4j/helpers/EcountPatternParser.java`

| Member | Type | Purpose |
|---|---|---|
| `dnsName` | `static String` (initialised in instance initialiser block, lines 12–21) | Holds the DNS hostname resolved at class-load time via `InetAddress.getLocalHost().getHostName()` |
| `dnsNameIp` | `static String` | Holds `"hostname(ip.addr),"` resolved at class-load time |
| `EcountPatternParser(String pattern)` | Constructor | Passes the pattern string to the parent `PatternParser` |
| `finalizeConverter(char c)` | `public void finalizeConverter(char c)` | Intercepts pattern characters: `'h'` creates `DnsPatternConverter`; `'H'` creates `DnsIpPatternConverter`; all others delegate to `super.finalizeConverter(c)` |

#### Inner Classes

| Class | Purpose |
|---|---|
| `DnsPatternConverter` (private inner, lines 48–56) | Returns `dnsName` for each log event |
| `DnsIpPatternConverter` (private inner, lines 57–65) | Returns `dnsNameIp` for each log event |

Both extend `org.apache.log4j.helpers.PatternConverter` and override `convert(LoggingEvent event)`.

## Security Vulnerabilities

### CVE-2019-17571 — Log4j 1.x SocketServer Remote Code Execution (CRITICAL)
- **Component**: `log4j:log4j:1.2.15` (`pom.xml` line 24)
- **CVSS**: 9.8 (Critical)
- **Description**: The `SocketServer` class in Log4j 1.x deserialises arbitrary log events received over the network. An attacker can send a crafted serialised object to trigger RCE on the JVM hosting the service.
- **Exposure**: The vulnerability exists in any classpath containing Log4j 1.x JARs, even if `SocketServer` is not explicitly configured by the application.
- **Status**: Log4j 1.x is fully end-of-life with no available patches.

### Additional Log4j 1.x CVEs of concern
- **CVE-2020-9488** (CVSS 3.7) — SMTPAppender subject/recipient injection
- **CVE-2022-23302** (CVSS 8.8) — JMSSink JNDI injection via JMS messages
- **CVE-2022-23305** (CVSS 9.8) — JDBCAppender SQL injection via log messages
- **CVE-2022-23307** (CVSS 8.8) — Chainsaw (included in log4j-1.x JAR) deserialisation via log4j socket

**Note**: The well-known Log4Shell vulnerability (CVE-2021-44228) applies to Log4j 2.x versions < 2.15.0, not to Log4j 1.x. However, Log4j 1.x carries its own critical CVEs as listed above.

## Technical Debt

1. **End-of-Life dependency**: Log4j 1.2.15 has been unsupported since 2015. Every build incorporating this JAR introduces known-critical CVEs into the classpath.
2. **Static hostname resolution**: The DNS name is resolved once at class load. In containerised workloads where a pod is restarted and receives a new IP, the logged value will be stale until the JVM restarts. For short-lived containers this is acceptable; for long-lived JVM processes, it can mislead incident responders.
3. **No null-safety in hostname resolution**: If `InetAddress.getLocalHost()` throws `UnknownHostException` (line 18), both `dnsName` and `dnsNameIp` remain `null`. Subsequent calls to `DnsPatternConverter.convert()` will return `null`, which Log4j 1.x will render as the string `"null"` in log output. This is not a crash but produces misleading log lines.
4. **SNAPSHOT version**: See governance flags in `04_enterprise_architect.md`.
5. **No automated release pipeline**: No CI step builds or publishes the artefact.

## Remediation Priority

| Issue | Priority | Recommended Action |
|---|---|---|
| Log4j 1.x CVE-2019-17571 and related CVEs | **P1 — Critical** | Replace Log4j 1.x dependency with Log4j 2 or Logback immediately. Rewrite the layout extension using Log4j 2's `@Plugin` extension mechanism or Logback's `PatternLayoutEncoder` with a custom converter. |
| SNAPSHOT version in production | **P2 — High** | Promote to a release version and enforce immutability in the artefact repository. |
| No CI/CD publish pipeline | **P3 — Medium** | Add a GitHub Actions workflow to build, test, and publish the artefact to Nexus/Artifactory on tag push. |
| Static null hostname | **P4 — Low** | Add a null-check and fall back to a meaningful default (e.g., `"UNKNOWN_HOST"`) when `getLocalHost()` fails. |

## Recommended Replacement Architecture

Replace the library entirely with a **Log4j 2 plugin** or **Logback `LayoutWrappingEncoder`** that inserts the host name via MDC or a custom converter. Since the rest of the Gen-3 stack uses Logback with `logstash-logback-encoder`, the simplest path is:

```xml
<!-- logback-spring.xml -->
<appender name="JSON" class="ch.qos.logback.core.ConsoleAppender">
    <encoder class="net.logstash.logback.encoder.LogstashEncoder">
        <customFields>{"host":"${HOSTNAME}"}</customFields>
    </encoder>
</appender>
```

This delivers equivalent functionality with no CVE exposure and structured JSON output compatible with the Onbe ELK / Splunk stack.
