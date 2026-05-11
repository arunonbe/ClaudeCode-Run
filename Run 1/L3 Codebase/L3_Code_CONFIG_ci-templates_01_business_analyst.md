# Business Analyst View — CONFIG_ci-templates

## Business Purpose
This repository provides shared, reusable GitLab CI/CD pipeline templates for all Java/Maven application teams at Onbe (formerly Northlane/Wirecard NA). Its goal is to enforce a consistent build, test, release, and deploy lifecycle (DRY principle) across the application portfolio without requiring each team to maintain their own pipeline definitions.

## Business Capabilities
- Centralised build pipeline definition for Maven-based Java applications
- Automated artifact publishing to a Nexus repository (snapshot and release)
- Automated deployment of WAR artifacts to Tomcat servers across DEV and QA environments
- Post-deployment health checking (HTTP 200 verification)
- Dependency vulnerability scanning via Mend/WhiteSource
- Integration test execution with JUnit reporting
- Maven release preparation (version tagging, Git commit, release:perform)

## Business Entities
- **Application** — any Maven-based Java project consuming these templates
- **Environment** — development, QA (staging environments supported; UAT/PROD not directly targeted by these templates)
- **Artifact** — WAR file or JAR library published to Nexus
- **Tomcat Server** — deployment target host identified by host variable (DEV_SERVICE_HOSTS, QA_SERVICE_HOSTS)
- **Service** — a named Tomcat instance identified by SERVICE_NAME

## Business Rules
- Release branch naming convention enforced: branches matching `/Release-/` trigger release pipeline
- Feature branches trigger automatic DEV deploy; QA deploy is manual
- Only `application/` path projects build WARs; `libraries/` path projects build JARs
- Tests can be skipped via MAVEN_TEST_OPTS flag but WhiteSource scan only runs when WHITESOURCE=yes
- Integration tests are skipped when Maven profile `no-it` is set

## Business Flows
1. Developer pushes to feature or master branch
2. Build job compiles and packages the artifact
3. Test jobs run integration tests and optionally WhiteSource scan
4. On master/feature branches: artifact deployed automatically to DEV, manually to QA
5. On Release branches: release:prepare + release:perform executes, then deploy to DEV/QA
6. After deploy: HTTP health check validates each target host

## Compliance Concerns
- TLSv1.2 enforced for HTTPS Maven artifact downloads (`-Dhttps.protocols=TLSv1.2`)
- Credentials for scripts repository are injected via GitLab CI variables (`$NORTHLANE_CI_RO_USER`, `$NORTHLANE_CI_RO_PASS`) — not hardcoded in templates
- Deploy credentials (`GL_NAM_USER`, `GL_NAM_PASSWORD`) are referenced as CI variables
- No UAT or PROD deployment logic is present in these templates — change-control gates must exist upstream
- WhiteSource (Mend) SCA scan available but opt-in only

## Business Risks
- These templates only cover DEV and QA environments; UAT and PROD deployments are handled elsewhere (separate repos or manual processes), creating a potential deployment process gap
- Artifact repository URLs reference internal DNS hostnames (`d-na-stk01.nam.wirecard.sys`) — legacy Wirecard infrastructure names; these may become stale as infrastructure migrates
- Unit tests are commented out in the template, meaning unit test coverage is not enforced at CI level
- Healthcheck uses basic auth credentials via CI variables; if those variables are misconfigured, deployments appear successful but services may not be running
