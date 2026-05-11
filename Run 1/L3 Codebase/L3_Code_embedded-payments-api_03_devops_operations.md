# 03 DevOps & Operations — embedded-payments-api

## Build System

- Build tool: **Apache Maven** with Maven Wrapper
- Parent: `org.springframework.boot:spring-boot-starter-parent:3.4.5` (root `pom.xml` line 17)
- Java version: **21** (`pom.xml` line 22)
- Multi-module:
  - `embedded-payments-api` — main Spring Boot application
  - `embedded-payments-open-api` — OpenAPI spec + generated stubs
- Version: `0.0.1-SNAPSHOT`

Build commands (from CLAUDE.md):
```bash
./mvnw clean install                                    # Build all modules
./mvnw clean install -DskipTests                        # Skip tests
./mvnw test -pl embedded-payments-api                   # Unit tests only
./mvnw spring-boot:run -pl embedded-payments-api \
  -Dspring-boot.run.profiles=local                      # Local run
```

## OpenAPI Code Generation

The `embedded-payments-open-api` module uses `openapi-generator-maven-plugin:7.11.0` to generate Java server stubs and model classes from `openapi.yaml`. Custom Mustache templates in `openapi-generator-templates/` override the default code generation for:
- `enumClass.mustache` — custom enum generation
- `model.mustache` — custom model base
- `pojo.mustache` — custom POJO generation with nullability annotations
- `problemDetailPojo.mustache` — RFC 7807 Problem Details models

## CI/CD Pipelines

The API repository has `.github/` and `.junie/` directories (AI-assisted development tooling). Build and deployment pipelines are managed via GitHub Actions (no workflow files were visible in the top-level `.github/workflows/` directory at depth 3, but are likely present at deeper depth or in the `app-config/` directory).

Runtime deployment target appears to be **Azure (AKS or Azure Container Apps)** based on:
- Azure App Configuration integration (`bootstrap.yaml`)
- Azure AD OAuth2 for service auth
- Azure Key Vault for secrets
- Application profiles: `local`, `test`, `integration-test`, and default (prod/QA)

## Profiles

| Profile | Azure App Config | Notes |
|---|---|---|
| `local` | disabled | Uses `local-secrets.properties` |
| `test` | disabled | Unit tests |
| `integration-test` | disabled | Integration tests |
| (default/prod/QA) | **enabled** | Full Azure cloud config |

## Database Migrations (Flyway)

Flyway is configured but **disabled by default** (`flyway.enabled: false`, `application.yaml` line 40). Migrations are in `src/main/resources/flyway/`:
- `V001.001__Initial_Creation.sql`
- `V001.002__One_Time_Tokens.sql`
- `V001.003__One_Time_Tokens_DDA.sql`
- `V001.004__One_Time_Tokens_Partner_User_Id.sql`
- `V001.005__Hash_One_Time_Tokens.sql`
- `V001.006__One_Time_Tokens_Member_Id.sql`
- `V001.007__Revoked_Sessions.sql`
- `V001.008__Revoked_Sessions_Expires_At.sql`

Flyway migrations would typically be enabled in the default (non-local) profile and run at startup.

## Security Dependency Overrides (pom.xml lines 63–73)

The POM explicitly pins several dependency versions due to CVEs:

| Dependency | Version Pinned | Reason |
|---|---|---|
| `mssql-jdbc` | `13.3.1.jre11-preview` | CVE fix |
| `netty-codec-http2` | `4.1.132.Final` | HTTP/2 vulnerability fix |
| `tomcat-embed-core` | `10.1.54` | Tomcat CVE fix |
| `spring-security-core` | `6.5.5` | Spring Security CVE fix |
| `spring-core` | `6.2.11` | Spring Core CVE fix |
| `jackson-core` | `2.21.1` | Jackson CVE fix |
| `xstream` | `1.4.21` | XStream CVE fix |

This shows active dependency hygiene — a positive security signal.

## Actuator / Operations Endpoints

Spring Actuator is configured (`application.yaml` lines 58–72):
- Base path: `/`
- Exposed: `health`, `info`
- Health path: `/hc`
- Health shows details: `always`

## Logging

Logback with `logstash-logback-encoder:8.1` for structured JSON logging (`logback-spring.xml`). Log levels:
- Root: `${app.logging.level.root:INFO}`
- `com.onbe`: `${app.logging.level.com.onbe:INFO}`

## TLS / Truststore

A TLS truststore is configured (`application.yaml` lines 53–57):
- Location: `${app.truststore.location}`
- Password: `${secrets.truststore.password}`
- A QA truststore (`truststore_qa.jks`) is bundled in `src/main/resources/keystore/`

## Versioning Concern

Version `0.0.1-SNAPSHOT` indicates this is either very early-stage or version numbers have not been incremented from the project template. For a production service, the version should reflect the actual release cadence.
