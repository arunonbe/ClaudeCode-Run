# Business Analyst Report — wirecard_issuing-boot-actuator-utils_LIB

## Business Purpose

`wirecard_issuing-boot-actuator-utils_LIB` is a shared library (`issuing-boot-actuator-utils:2.0.0`) that provides customized Spring Boot Actuator health endpoint serialization and aggregation logic for all Wirecard/Northlane Gen-2 issuing services. It is consumed by microservices in the Wirecard issuing platform (Singapore bank agent, NAM bank agent, funds transfer coordinator, wire transfer agent, etc.) to produce a Wirecard-specific health response format rather than the standard Spring Boot actuator JSON output.

The library is not a deployable service; it is a shared dependency that is included at compile time in consuming services.

## Capabilities

1. **`CustomHealthAggregator`**: Implements Spring Boot's `StatusAggregator` interface. Aggregates health status across multiple health indicators, considering a `critical` flag in health details. Non-critical unhealthy indicators do not cause the overall status to be reported as `DOWN`. Only indicators explicitly marked `critical: true` in their health details propagate a `DOWN` status.

2. **`CustomHealthSerializer`**: Implements Jackson's `StdSerializer<Health>`. Produces a Wirecard-specific JSON health response format with the following additions over the standard Spring Boot format:
   - `overall_status_ok`: boolean (true/false) at the root level.
   - `reply_host`: hostname of the responding service node.
   - `cached_ts`: ISO 8601 timestamp of when the health status last changed.
   - Nested indicators add `status_ok: true/false` alongside the standard `status` string.

## Client and Cardholder Impact

Indirect. The health endpoint format governs how Wirecard's internal monitoring systems assess the operational status of Gen-2 services. A malfunctioning health aggregator could cause monitoring systems to miss genuine service failures (false positives) or generate unnecessary alerts (false negatives), potentially affecting the availability of cardholder disbursement and wire transfer services.

## Business Rules in Code

- A health indicator marked `critical: false` in its detail map does not bring the service `DOWN` — only `critical: true` (or absence of the `critical` key, which defaults to `true` per the `isCritical()` method) indicators affect overall status.
- The hostname is captured at startup and cached; a change in hostname (e.g., container restart with a different pod name) does not update `reply_host` mid-lifecycle.
- The `cached_ts` timestamp updates only when the `Health` object reference changes, not when the health details change — this is a subtle caching limitation.

## Regulatory Obligations

No direct regulatory obligations arise from this library. Indirectly:
- **PCI DSS Req. 10.5 / 10.6**: Actuator endpoints that expose internal service information must be access-controlled. This library influences what the health endpoint exposes.
- **NIST CSF DE.AE**: The health endpoint is part of the anomaly detection capability; its correctness is important for operational resilience.

## Key Business Risks

1. **Over-exposure of health endpoint**: If the consuming services expose the actuator health endpoint without authentication (as observed in `wirecard_sg-bank-agent_LIB`), the `reply_host` field leaks server hostname information to unauthenticated callers.
2. **Logic defect in `getAggregateStatus`**: A bug in `CustomHealthAggregator.getAggregateStatus()` means this method always returns `Status.UP` regardless of status input (see Solution Architect report). This is a monitoring reliability risk.
3. **`critical` flag default to `true`**: Any health indicator that does not set the `critical` flag will be treated as critical, potentially over-alerting on non-critical dependency failures.
