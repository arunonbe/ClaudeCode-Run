# Business Analyst View — strict-null-checks_DEMO

## Business Purpose
This is an internal developer education and standards repository. Its sole purpose is to demonstrate and codify Onbe's Java null-safety coding standards. It is not a deployable service and carries no production workload.

## Capabilities
- Demonstrates use of Spring Framework `@NonNullApi` / `@NonNullFields` package-level annotations.
- Shows `@Nullable` override for exceptional parameters.
- Shows use of `Objects.requireNonNull` for runtime enforcement.
- Shows Null Object pattern via a sentinel `Employee.NULL_EMPLOYEE` record constant.
- Shows `Optional<T>` return type as an alternative to null.
- Shows returning empty collections instead of null.
- Uses the `se.eris:notnull-instrumenter-maven-plugin` to generate JVM bytecode assertions from annotations at build time.

## Entities
| Entity | Description |
|--------|-------------|
| `Employee` | Java record with fields `id` (String) and `name` (String). Has sentinel constant `NULL_EMPLOYEE`. |
| `Service` | Interface with a single method accepting a nullable `String` and a non-null `BigDecimal`. |
| `ServiceImpl` | Intentionally broken implementation demonstrating anti-patterns (returns null from Optional, null from list). |

## Business Rules
- All package-level parameters and fields are non-null by default (enforced by `@NonNullApi` / `@NonNullFields`).
- `@Nullable` must be explicitly declared on any parameter or return value that may be null.
- Runtime guard `Objects.requireNonNull` must be placed at method entry to enforce non-null.
- Value objects should use a null-sentinel constant rather than returning `null`.
- Collections should return empty rather than `null`.
- `Optional.empty()` should be returned instead of `null` where optionality is required.

## Flows
1. Developer reads `README.md` for guidelines.
2. Developer implements `package-info.java` with `@NonNullApi` / `@NonNullFields`.
3. IDE (VS Code / IntelliJ) flags nullable violations at development time.
4. Maven build runs `notnull-instrumenter-maven-plugin` which instruments bytecode with runtime assertions.
5. Unit or integration tests exercise the instrumented code.

## Compliance Relevance
- Not a production system; no direct PCI DSS, GLBA, or Reg E applicability.
- Contributes indirectly to Onbe's secure-by-default coding culture, supporting PCI DSS Requirement 6 (secure development practices).

## Risks
- `ServiceImpl` contains intentional anti-patterns (`return null` from `Optional`, null list return). If this class were ever copied into production code, it would introduce defects.
- No test classes are present; the demo relies on compile-time and IDE-time checks only.
- The `notnull-instrumenter-maven-plugin` explicitly supports only up to Java 17; if the project is upgraded beyond Java 17, runtime instrumentation will silently stop working.
