# runner-test — Business Analyst View

## Business Purpose
runner-test is a minimal CI/CD validation harness for GitHub Actions self-hosted runners. It exists to confirm that a self-hosted Windows/Linux runner can compile and execute a Java project end-to-end. It has no business logic, no customer-facing behaviour, and no payment-processing function. Its sole purpose is infrastructure validation.

## Capabilities
- Compiles a two-class Java application (HelloWorld + Greeter) via Maven.
- Produces a shaded executable JAR.
- Triggers on every push via the `marven.yml` (sic) workflow.
- Runs CodeQL SAST scans on push/PR to main/master (codeql-java.yml) and on a weekly schedule via the centralised `om-ci-setup` reusable workflow (codeql.yml).
- Dependabot weekly scans for Maven dependency updates.

## Entities
- `hello.HelloWorld` — entry point; instantiates Greeter and prints output.
- `hello.Greeter` — single method `sayHello()` returning the literal "Hello world!".

## Business Rules
None applicable. There is no business logic.

## Process Flows
1. Developer pushes code → `marven.yml` triggers on self-hosted Windows X64 runner → `mvn -B package` → JAR produced.
2. Push/PR to main/master → `codeql-java.yml` triggers on Linux ubuntu-docker runner → Maven build → CodeQL Java-Kotlin analysis → results uploaded as GitHub security events.
3. Weekly Tuesday 12:30 UTC → `codeql.yml` delegates to centralised `Onbe/om-ci-setup` reusable workflow.

## Compliance Relevance
No direct compliance scope. Indirectly relevant because it validates the self-hosted runner infrastructure used by all Onbe CI/CD pipelines, including pipelines that build PCI-in-scope services.

## Risks
- The settings.xml committed in `.mvn/wrapper/` contains **plaintext credentials** (passwords `acmng`, `dwil15?`, `d3v0nly`) for Nexus and a historical Wirecard proxy. These are live secrets if the Nexus/ecount servers still exist.
- The `marven.yml` workflow name is misspelled ("marven" not "maven") — a minor but visible quality indicator.
- No test coverage; the application has no unit tests.
