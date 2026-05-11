# Data Architect — test-east-deploy-multiple

## Data Stores
None. Both applications are stateless; they hold no persistent data, no database, no cache, and no message queue. All responses are computed at runtime from environment variables and JVM metadata.

## Schema / Tables
Not applicable. There are no DDL scripts, JPA entities, Liquibase changelogs, or Flyway migrations in this repository.

## Sensitive Data
No sensitive data of any kind is processed, stored, or transmitted:
- No PAN, CVV/CVC, PIN, or track data.
- No PII (name, SSN, DOB, address).
- No authentication credentials beyond the GitHub Actions `PAT_TOKEN_PACKAGE` secret used exclusively for publishing to GitHub Packages.

## Encryption
- Transport: no custom TLS configuration is present. At deployment time the platform is expected to terminate TLS at the load balancer or ingress.
- At-rest: not applicable (no persistence layer).

## Data Flow
```
HTTP Request --> AppA/AppB Controller
                 |-- reads: spring.application.version (build-time token)
                 |-- reads: InetAddress.getLocalHost().getHostName() (runtime)
             --> HTTP JSON Response (no external calls, no DB reads/writes)
```

## Data Quality / Retention
Not applicable. No data is stored. Responses are ephemeral.

## Compliance Gaps
- Not applicable to PCI DSS data-protection requirements.
- No data retention policy is needed.
- No masking or tokenisation requirements.
