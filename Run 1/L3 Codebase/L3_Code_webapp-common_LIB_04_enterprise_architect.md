# Enterprise Architect — webapp-common_LIB

## Platform Generation
**Gen-1** (legacy Java EE / Spring MVC era). Indicators:
- `com.citi.prepaid` group ID — predates Wirecard acquisition and Onbe rebranding.
- `javax.servlet.Filter` (Java EE namespace, not Jakarta EE).
- Parent POM `webapp-parent:6` with no declared Java version (inferred Java 7/8 era).
- `junit:3.8.1` — from 2002; predates all modern testing frameworks.
- No Spring Boot, no embedded servlet container, no Actuator.

## Business Domain
Web infrastructure / security (HTTPS enforcement) for legacy prepaid card web applications originally built on the Citi prepaid platform before the Wirecard/Onbe transition.

## Role in the Architecture
- **Shared security infrastructure library** for Gen-1 web applications.
- Consumed at compile/runtime by older `_WAPP` repositories that are deployed as WARs on shared Tomcat servers.
- No known Gen-2 or Gen-3 consumers (those platforms use Spring Boot 2.x/3.x embedded Tomcat with Spring Security for HTTPS enforcement).

## Dependencies
| Dependency | Version | Notes |
|---|---|---|
| `com.citi.prepaid.web:webapp-parent` | `6` | Internal Onbe parent POM; resolves servlet API, Commons Logging, etc. |
| `junit:junit` | `3.8.1` | Test-scope only; obsolete |

## Integration Patterns
- **Filter chain pattern**: Java Servlet filter inserted into the `javax.servlet.FilterChain` of the consuming web application.
- No service-to-service integration, no events, no messaging.

## Strategic Status
- **Sunset candidate**: This library is Gen-1 with no active development. Gen-2 and Gen-3 applications handle HTTPS enforcement at the Spring Security / ingress / reverse-proxy level.
- **Blocked on Jakarta migration**: `javax.servlet` namespace is incompatible with Jakarta EE 9+ and Spring Boot 3.x. A Jakarta-namespace port would be required to use this library in any modern stack — but the preferred migration path is to retire it entirely and use platform-level HTTPS enforcement.
- **PCI DSS relevance**: Active Gen-1 applications using this filter must retain it until those applications are decommissioned or migrated, as it constitutes an HTTPS enforcement control.

## Migration Blockers
1. **`javax.servlet` namespace**: Must be ported to `jakarta.servlet` for Spring Boot 3.x / Tomcat 10+ compatibility. Given the library's simplicity (one filter class), this is a minor code change but requires parent POM updates.
2. **`com.citi.prepaid.web` parent POM**: Dependency on a legacy internal parent POM that may not be maintained or available in modern build environments.
3. **No owner identified**: Author field `vv27499` (legacy Citi username) suggests the original developer may no longer be at Onbe. Ownership must be assigned before any migration work.
4. **Unknown consumer count**: Without a dependency graph, it is unknown how many active applications depend on this library. Decommissioning requires all consumers to migrate first.
