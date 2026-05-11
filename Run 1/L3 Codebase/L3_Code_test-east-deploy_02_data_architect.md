# Data Architect Report — test-east-deploy

## Data Models

No domain data models exist. The application has one resource file: `application.properties` containing only `spring.application.name` and `spring.application.version`. No database, no JPA entities, no DTOs, and no data access layer.

## Sensitive Data

No sensitive data is processed or stored. Specifically:
- No PAN, CVV, SSN, DDA, or any cardholder data.
- No PII of any kind.
- No credentials embedded in application configuration.
- Maven settings (`settings.xml` in `.mvn/wrapper/`) uses `${env.GITHUB_TOKEN}` for the GitHub Packages repository — this is an environment variable reference, not a hardcoded value.

## Encryption Status

Not applicable. No data is persisted or transmitted beyond the build pipeline itself.

## Database Schemas

None. No database connectivity is configured.

## Data Flows

The only meaningful data flow is at build time:
1. GitHub Actions triggers `build-east-java.yml` from `om-ci-setup`.
2. Maven builds the WAR artifact.
3. If `DEPLOY_TO_PACKAGES: true`, the WAR is published to GitHub Packages (`https://maven.pkg.github.com/onbe/onbe_maven_releases`) using the `PAT_TOKEN_PACKAGE` secret.
4. No runtime data flows exist; the application has no endpoints that accept or return business data.

## Retention Concerns

None for cardholder or PII data. Build artifacts (WAR files) published to GitHub Packages should have a retention policy to avoid unbounded storage growth, but this is an infrastructure concern rather than a compliance data-protection concern.

## PCI DSS Compliance

This application is outside PCI DSS scope as it does not interact with cardholder data. However, it exercises the build pipeline that all production services share, making pipeline security indirectly relevant to PCI DSS Req. 6.3 (secure development practices) and Req. 6.4 (protection of web-facing applications). Ensuring the shared `build-east-java.yml` workflow includes SAST/SCA scanning would satisfy PCI DSS Req. 6.3.2 for the entire estate.
