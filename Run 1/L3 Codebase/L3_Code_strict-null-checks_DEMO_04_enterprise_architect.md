# Enterprise Architect View — strict-null-checks_DEMO

## Platform Generation
**Gen-1 / Internal Standards Artifact** — This is not a deployable service. It is an internal developer reference project and does not fit neatly into Gen-1/2/3 classification.

## Business Domain
Developer Experience / Engineering Standards. No Onbe business domain (payments, disbursements, cardholder management) applies.

## Role in Ecosystem
- Provides a canonical code example for the Onbe Java null-safety standard.
- Serves as a reference for code reviews and onboarding documentation.
- Has no runtime integrations with any other service.

## Dependencies
| Type | Artifact | Version | Notes |
|------|----------|---------|-------|
| Runtime | `spring-core` | 6.1.6 | Only used for `@NonNullApi` / `@NonNullFields` / `@Nullable` annotations |
| Build/Compile | `lombok` | 1.18.32 | Annotation processing |
| Build | `notnull-instrumenter-maven-plugin` | 1.1.1 | Bytecode instrumentation |

## Integration Patterns
None. No inbound or outbound integrations.

## Strategic Status
- **Keep as reference only.** Should not be promoted to a library dependency.
- Maintain alongside engineering onboarding materials.
- Consider adding a CI/CD pipeline to confirm the demo builds correctly on every push.

## Migration Blockers
Not applicable. This repo does not need migration; it needs curation as a living standards document.
- The Java 17 ceiling on `notnull-instrumenter-maven-plugin` should be noted if Onbe's standard JDK moves to 21+. An alternative runtime enforcement strategy (e.g., Hibernate Validator, `@jakarta.validation.constraints.NotNull` with Bean Validation) would be needed.
