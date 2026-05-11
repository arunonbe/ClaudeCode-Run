# Business Analyst — test-east-deploy-multiple

## Business Purpose
This repository is a **CI/CD pipeline validation harness**, not a production payment service. Its sole purpose is to prove that the OnbeEast GitHub Actions workflow (`om-ci-setup/.github/workflows/build-east-java.yml`) can build, package, and deploy **multiple WAR artefacts from a single Maven multi-module project** in one pipeline run. It is used by the platform/DevOps team to certify multi-WAR deployment flows before applying the pattern to production services.

## Capabilities
- Provides two minimal Spring Boot web applications (`app-a` and `app-b`) that each expose identical REST endpoints under their own context paths.
- Exposes `/`, `/health`, `/version`, `/hostname`, and `/slow` endpoints on each app for deployment-smoke-test purposes.
- Returns hostname, application identity (`a` or `b`), and version metadata to allow testers to verify which instance is serving traffic and whether rolling-update balancing is correct.
- Supports a configurable "slow" endpoint (default 10 seconds sleep) to exercise timeout and rolling-restart behaviour in the target platform.

## Entities / Domain Objects
- No domain entities. The only data in flight is: `app` (string ID), `version` (string from Maven token `@project.version@`), `hostname` (runtime JVM hostname), and `sleptSeconds` (integer for the slow endpoint).

## Business Rules
1. `app-a` must always identify itself as `"a"`; `app-b` as `"b"`. Misidentification would invalidate deployment tests.
2. `version` is injected at build time from the Maven project version (`@project.version@` token replacement); it must not be `"unknown"` in a successful build.
3. `/health` must return `{ "status": "UP" }` for liveness/readiness probe validation.
4. The `/slow?seconds=N` endpoint must honour the `seconds` parameter (default 10) to simulate long-running requests.

## Flows
1. Developer pushes to `main`, `release/**`, or `feature/**` branch.
2. GitHub Actions triggers `build-east-java.yml` reusable workflow.
3. Maven builds both `app-a` (WAR) and `app-b` (WAR) and deploys artefacts to GitHub Packages.
4. Deployment tooling picks up the two WARs and deploys them to a target environment.
5. Smoke tests hit `/health` and `/version` on both apps to verify successful deployment.

## Compliance Relevance
- No payment data, PII, or cardholder data is processed.
- PCI DSS scope: out of scope for the Cardholder Data Environment (CDE).
- GLBA / CCPA / GDPR: not applicable — no personal data handled.
- The repository is relevant to PCI DSS Requirement 6.4 (change-management / deployment process validation) and Requirement 12.3 (tested deployment procedures).

## Risks
- Low production risk. Risk is confined to CI/CD pipeline stability.
- If this test harness is broken it may block unrelated release pipelines that depend on the same shared workflow.
- Hardcoded `Thread.sleep` in `/slow` endpoint could cause OOM on small test containers if many concurrent slow requests are issued.
