# DevOps & Operations Report: strongbox-remote-client_LIB

## Build System

- **Build tool**: Apache Maven (wrapper in `.mvn/wrapper/`)
- **Parent POM**: None declared (no `<parent>` element in `pom.xml`); this library stands alone without the shared corporate parent POM
- **Java version**: Java 8 (`<source>8</source>`, `<target>8</target>` in maven-compiler-plugin configuration) — **this is the only Java 8 target library in this batch; all others target Java 21**
- **Packaging**: JAR library (`<packaging>jar</packaging>`)
- **Version**: `1.0.0-SNAPSHOT` — snapshot version, indicating this is not a released/stable artifact

## CI/CD Pipeline

Two GitHub Actions workflows:

1. **`codeql.yml`**: GitHub CodeQL static analysis security scan
2. **`dependabot.yml`**: Automated dependency updates

There is **no publish/deploy workflow**. The POM's `distributionManagement` section references the old Wirecard/Northlane internal Nexus at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` for both release and snapshot repositories — these are legacy repository URLs that may no longer be operational.

The combination of no publish workflow, a SNAPSHOT version, and a legacy Nexus URL suggests this library's published lifecycle is managed manually or via a legacy Jenkins process not visible in this repository.

## Deployment Model

Library JAR; not independently deployed. Consumed by Gen-2 Spring services that add it as a Maven dependency. Distribution via the internal Nexus registry (Wirecard/Northlane era) or potentially GitHub Packages.

## Secrets Management

The library itself contains no secrets. The network credentials for connecting to StrongBox are encapsulated in the caller-provided `WriteMapXmlRemoteCall` and `ReadMapXmlRemoteCall` lambda implementations — the library does not see or manage the StrongBox service credentials.

However, the data the library retrieves from StrongBox is itself secret material (keys, passphrases). The library returns this data as plain Java objects with no enforcement of:
- Memory zeroing after use
- Access logging
- Time-limited holds on secret material

## Observability

Minimal. `StrongBoxRemoteServiceImpl` creates a logger with `LogFactory.getLog("SomeLoggerClassName")` — the logger name is a hardcoded placeholder string rather than the class name. This means:
- Log messages from this class appear under `"SomeLoggerClassName"` in log files, making them unidentifiable as originating from the StrongBox client library
- The placeholder name suggests this was never properly reviewed; log level configuration for this class will not work as expected
- Security-relevant events (failed reads, connection errors) will be attributed to a phantom logger name

## EOL Runtimes and CVE Concerns

**Critical EOL concerns:**

1. **Java 8 compile target**: The library targets Java 8, which reached Oracle Extended Support end-of-life in March 2025 (OpenJDK 8 community support varies by distribution). Modern JVM security improvements (stronger encryption algorithms, improved TLS defaults, JNDI remote class loading disabled by default) are not available to services running on Java 8
   
2. **Spring Framework 4.3.27**: Spring 4.x has been end-of-life since December 2020. Known CVEs include:
   - CVE-2022-22965 (Spring4Shell): Remote code execution via Spring MVC (though this library doesn't use MVC directly, transitive exposure is possible)
   - Multiple XXE (XML External Entity) vulnerabilities in Spring's XML processing components
   - Spring 4.x does not receive backported security patches

3. **SLF4J 1.7.30**: Released in 2019; SLF4J 2.x (released 2022) introduces API improvements. 1.7.x is still maintained for critical bugs but is not current

4. **XML-RPC dependency `xmlrpc:2.0.0-SNAPSHOT`**: A SNAPSHOT dependency declared in the POM creates build non-reproducibility; the actual snapshot artifact version at build time is whatever was most recently published to the internal Nexus. This dependency has `com.citi.prepaid.service.core:xmlrpc` as its coordinates — a Citi-era internal library whose current CVE status is unknown

## Technical Risk Summary

This library combines three high-risk characteristics:
1. Handles the most sensitive data in the platform (cryptographic keys)
2. Uses EOL runtime (Java 8, Spring 4) with known CVEs
3. Has a placeholder logger name indicating it was never properly production-hardened

It requires immediate attention: Java/Spring version upgrade, logger name correction, audit log addition, and verification that the transport uses HTTPS in all environments.
