# ai-guidelines — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

This repository does not belong to any application platform generation in the runtime sense. It is a shared governance asset. However, its content presupposes a Gen-2 or Gen-3 technology stack:

- Java (with `var`, JSpecify null safety annotations, records/DTOs implied by Spring guidelines) — consistent with Java 17+ / Java 21.
- Spring Boot with Jakarta EE (not `javax`) validation — Spring Boot 3.x / Jakarta EE 9+.
- Testcontainers for integration testing — modern cloud-native testing practice.
- Azure App Configuration reference — suggests Azure as the cloud platform.
- OpenAPI annotations for REST API documentation — consistent with Gen-2/Gen-3 API-first practices.

## Business Domain

This repository belongs to the **Developer Enablement / Engineering Governance** domain. It has no direct business domain (payments, disbursements, card management, etc.). Its consumers span all business domains within Onbe's engineering organization.

## Role in Platform

This repository plays the role of a **shared standards library** within Onbe's engineering platform. Its function is:

- To encode AI agent behavior guardrails so that AI-assisted development produces code consistent with Onbe's engineering and security standards.
- To serve as a single point of update for coding standards, reducing drift between teams.
- To reduce the risk of AI agents generating non-compliant, insecure, or stylistically inconsistent code across the organization.

It is a lateral dependency — no runtime component depends on it, but every team that uses AI coding assistants is expected to reference it.

## Dependencies

**Upstream (inputs to this repo):** None detected. Standards appear to be authored directly.

**Downstream (projects that consume this repo):** Any Onbe Java/Spring Boot project using Claude Code, GitHub Copilot, or JetBrains Junie. The testing standards reference:
- Maven Wrapper (`mvnw`) — standard Spring Initializr artifact.
- SQL Server via Testcontainers — implies downstream projects share a common RDBMS.
- Azure App Configuration (`spring.cloud.azure.appconfiguration`) — implies Azure-hosted projects.

## Integration Patterns

This repository integrates with consuming projects via a **copy-and-reference pattern**:

1. Teams copy the `.ai/` directory into their repository.
2. Teams create an agent-specific entrypoint file that references the `.ai/` files.
3. AI agents read the entrypoint and follow the referenced guidelines at code-generation time.

There is no API, no event, no message queue, and no shared runtime integration. The integration is purely static (file-based) and happens at developer-workstation time, not at runtime.

## Strategic Status

**Active — Foundational.** This repository is strategically important as AI coding assistant adoption increases across Onbe. Its guidelines directly affect the security posture, code quality, and compliance alignment of all AI-generated code. However, it is currently in an early/immature state:

- The application template file (`app-guidelines.md`) is incomplete (contains placeholder text).
- Compliance coverage is partial — PCI DSS specifics, NACHA, Reg E, and OFAC are not addressed.
- No versioning, changelog, or governance process is defined.
- No enforcement mechanism exists to verify adoption or compliance.

## Migration Blockers

Not applicable in the traditional sense (no legacy system to migrate). However, the following gaps would block this repository from being considered a mature enterprise governance asset:

- Absence of PCI DSS-specific AI guardrails (e.g., explicit prohibition on generating code that logs or stores PANs, CVVs, or track data).
- No guidance for AI agents working on non-Java technology stacks (e.g., Node.js, Python, infrastructure-as-code).
- No process for communicating guideline updates to teams that have already copied the files.
- No automated validation that consuming projects correctly reference the guidelines.
