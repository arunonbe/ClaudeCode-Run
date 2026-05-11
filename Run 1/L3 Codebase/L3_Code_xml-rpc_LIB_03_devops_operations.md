# DevOps / Operations Report — xml-rpc_LIB

## Build System

**Maven 3.x** via Maven Wrapper. Parent: `com.parents:prepaid-parent:6.0.13`. Produces JAR artifact. Compiler: Java 21.

Key build plugins:
- `maven-jar-plugin`: Standard JAR packaging.
- `maven-enforcer-plugin`: Enforces no-SNAPSHOT dependencies (`requireReleaseDeps`) and bans transitive dependencies (with explicit exclusions for `springutils-generic`, `ecountcore-common`, `commons-httpclient`, and `spring-boot:*`).

**Important version discrepancy**: The parent is `prepaid-parent:6.0.13` while the actuator-utils and test-utilities use `6.0.12`. This means xml-rpc_LIB is on a newer parent version than the other libraries, suggesting staggered update cadence across the library estate.

## CI/CD Pipeline

**GitHub Actions** with three workflow files:

1. **`cicd-deployment.yml`**: Manual workflow dispatch only; calls `build-east-java.yml` with Java 21, self-hosted runner, `DEPLOY_TO_PACKAGES: true`. Supports `skip_tests` and `deploy_to_production` inputs.
2. **`codeql.yml`**: GitHub CodeQL Java static analysis.
3. **`dependabot.yml`**: Automated dependency update PRs.

The presence of `cicd-deployment.yml` (vs. just `build.yml`) indicates this library has a formal production deployment workflow, consistent with its role as the most critical shared dependency.

## Deployment Model

Published to GitHub Packages as `com.citi.prepaid.service.core:xmlrpc:3.1.3-SNAPSHOT`. Consumed by every Gen-1/Gen-2 service as a compile-time dependency.

**CRITICAL**: The version is `3.1.3-SNAPSHOT` — a snapshot. In Maven, snapshot versions are mutable: the same version string can resolve to different artifact content at different build times. For the most critical shared library in the estate, a SNAPSHOT version means:
- Every build that re-resolves this dependency might pick up a different version of the library.
- There is no artifact immutability guarantee.
- Rollback is impossible without explicit version pinning.

## Runtime

- **Java 21** (compiler target) — current LTS. However, the consuming services that this library is deployed into run on older JVMs in Gen-1 environments.
- **Spring Core / Spring WebMVC**: Version from parent BOM (prepaid-parent:6.0.13).
- **Apache Commons HttpClient 3.x** (`commons-httpclient:commons-httpclient`): **EOL — last release 2007**. HttpClient 3.x does not support TLS 1.2+ natively; TLS configuration requires custom provider setup. This is a significant security vulnerability in the outbound RPC client.
- **Commons IO**, **Commons Codec**, **Commons BeanUtils**: Versions from parent BOM — older commons versions have known CVEs.
- **Jakarta Servlet API**: Provided scope — consumed services must provide this.
- **springutils-generic:3.1.0** (internal eCount library).
- **ecountcore-common:3.1.5** (internal eCount library).

## Secrets Management

No secrets in this repository. Authentication and credentials are handled by the consuming services; this library is credential-agnostic.

## Observability

- SLF4J logging throughout.
- Thread-local logger pattern (`ThreadLocalLogger`) used in servlet and helper classes.
- Global request ID propagation via HTTP header and MDC — enables end-to-end request tracing across RPC hops.
- DEBUG-level logging includes full request/response payloads — must be disabled in production.

## EOL Runtimes / CVEs

| Component | Version | EOL Since | CVE Risk |
|-----------|---------|-----------|---------- |
| Commons HttpClient | 3.x | 2007 | No TLS 1.2 default; CVE-2012-5783 (HTTPS host verification bypass in 3.x) |
| Commons BeanUtils | 1.x (BOM) | See NVD | CVE-2019-10086 (class loader manipulation) |
| Commons IO | 2.4 (BOM est.) | Older | No critical CVEs but aged |

**CVE-2012-5783** in Commons HttpClient 3.x: SSL certificate host verification is not performed by default, making the outbound RPC client vulnerable to man-in-the-middle attacks on HTTPS connections. All outbound XML-RPC calls over HTTPS are at risk.

## Operational Notes

- `connectionManager.getParams().setDefaultMaxConnectionsPerHost(1000)` and `setMaxTotalConnections(1000)`: The connection pool is configured for very high concurrency (1000 connections per host). This was set explicitly to override the default of 2. If the target services have limited thread pools, this could cause resource exhaustion on the server side.
- `XmlRPCServlet.doGet()` delegates to `doPost()`: GET requests are treated identically to POST requests, which could enable data exposure via browser access or GET-based CSRF.
