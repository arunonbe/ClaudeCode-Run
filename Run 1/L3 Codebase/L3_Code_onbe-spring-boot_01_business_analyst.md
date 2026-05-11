# Business Analyst Report — onbe-spring-boot

## Business Purpose

`onbe-spring-boot` is Onbe's internal shared framework library — a multi-module Maven project that standardizes the construction of Spring Boot microservices across the Gen-3 (NexPay/Onbe) platform generation. It is not a deployable application; it is a reusable software development kit (SDK) distributed as a set of Maven artifacts to other Onbe engineering teams via GitHub Packages. Its purpose is to enforce consistent configuration, security posture, observability, secrets management, and reactive programming patterns across all Onbe-built services.

## Capabilities

- **Secrets Management via Dapr:** `DaprSecretsConfiguration` integrates the Dapr sidecar secret store (e.g., Azure Key Vault) at Spring context startup, injecting secrets as Spring environment properties. This removes hardcoded credentials from service configuration files and aligns with PCI DSS Requirement 8 (credential management) and Requirement 3 (protection of stored sensitive data).
- **REST Client Standardization:** `WebAutoConfiguration` and `RetryRateLimitRequestInterceptor` provide a pre-configured `RestClient.Builder` with configurable connect/read timeouts, retry-on-rate-limit behavior (HTTP 429/503 handling), and default JSON headers. All downstream HTTP calls from Onbe services inherit these defaults.
- **Reactive R2DBC Database Access:** `ConnectionFactoryFactory` standardizes reactive (non-blocking) database connection pool construction for both Microsoft SQL Server and PostgreSQL, supplying configurable pool sizing, idle timeouts, and validation queries.
- **Structured Logging:** The framework enforces Logstash JSON-formatted log output (logstash format) for both console and file, compatible with centralized SIEM/log aggregation pipelines required by PCI DSS Requirement 10.
- **Data Masking Utilities:** `TextUtils.mask()` provides a standardized masking function (reveal prefix-2/suffix-2, mask up to 8 characters) and is explicitly used in `DaprSecretsConfiguration` debug logging to prevent secret values from appearing in logs.
- **Observability Standards:** The default YAML configures Spring Boot Actuator with Prometheus metrics, liveness/readiness health probes, and Zipkin distributed tracing (enabled in local profile, configurable for QA/prod). Health endpoint is mapped to `/hc`.
- **Virtual Threads:** Enabled by default (`spring.virtual-threads.enabled: true`), aligning the framework with Java 21 Project Loom capabilities for high-throughput I/O.
- **Azure Functions Profile:** A `spring-cloud-azure-function` Maven profile provides plugin configurations for deploying Spring Cloud Function workloads to Azure Functions on Java 21 Linux runtime.

## Client/Cardholder Impact

This library is not directly consumer-facing. However, its quality and correctness directly affect every Onbe service that depends on it. Bugs in the secrets loader, HTTP retry logic, or logging configuration would propagate to production payment services that handle cardholder disbursements, prepaid card loads, and ACH transfers.

## Business Rules in Code

- Retry-after wait is capped at 60 seconds (`Duration.ofMinutes(1)`); longer retry-after headers cause immediate failure return without retrying.
- Dapr secrets loading is gated on both classpath presence (`@ConditionalOnClass`) and explicit property enablement (`dapr.secrets.enabled=true`), preventing accidental credential exposure in environments where Dapr is not available.
- Bootstrap default properties are only applied on the second pass of the `EnvironmentPostProcessor` and only when `onbe.bootstrap.default.enable=true` system property is set.

## Regulatory Obligations

- **PCI DSS v4.0.1 Req 3/8:** Dapr-based secrets abstraction eliminates hardcoded credentials. The mask utility prevents PANs or secret values from appearing in logs.
- **PCI DSS Req 10:** Structured JSON logging (Logstash format) supports SIEM ingestion and log integrity requirements.
- **PCI DSS Req 6:** CycloneDX SBOM generation (via `cyclonedx-maven-plugin`) supports software composition analysis and vulnerability tracking.
- **GLBA/GDPR:** Masking utilities and structured logging reduce risk of PII exposure in operational logs.

## Key Business Risks

- As a shared library dependency, any breaking change or security vulnerability introduced here affects all downstream services simultaneously. There is no isolation boundary — a bad release propagates instantly to all consumers.
- The framework is at version `0.0.22-SNAPSHOT`, indicating active development. SNAPSHOT dependencies in production services carry the risk of non-reproducible builds.
- The `RetryRateLimitRequestInterceptor` uses `Thread.sleep()`, which is a blocking call. Although acceptable with Java 21 virtual threads, use within reactive Webflux pipelines without virtual thread awareness could cause thread starvation in older consumers.
- License exclusion plugin filters GPL/AGPL licenses but relies on correct artifact metadata, which may not catch all license compliance risks.
