# Data Architect Report: Spring-Config-Server_INFRA_CONT

## Data Models

Spring Cloud Config Server does not maintain a traditional database schema. Its data model is flat file-based: YAML, `.properties`, or JSON files stored in a Git repository (or a local filesystem mount). The naming convention is:

- `{application}.yml` — default properties for a named application
- `{application}-{profile}.yml` — profile-specific properties (e.g., `payment-service-prod.yml`)
- `application.yml` — global defaults shared across all services

The Config Server exposes these as HTTP endpoints: `/{application}/{profile}[/{label}]`

## Sensitive Data Concerns

This repository's source code does not show the backing configuration files; however, the data sensitivity of Spring Cloud Config is determined by what is stored in the configuration repository. In a typical Onbe/Wirecard Gen-2 deployment the following categories of sensitive data are likely served through Config Server:

- **Database connection strings**: JDBC URLs for SQL Server databases containing cardholder data (`cbaseapp`, `ecountcore`, `jobsvc`, `ordersvc`, `strongbox`) — these are not PANs but are credentials enabling access to systems that hold PANs
- **API keys and shared secrets**: Keys for internal service-to-service authentication, APIM gateway credentials, and third-party payment processor API tokens
- **Encryption keys**: Symmetric keys used by services for field-level encryption of sensitive data; if served in plaintext, any reader of Config Server output has the encryption key
- **PGP passphrases**: StrongBox references may be served through Config, linking the Config Server to the cryptographic key management chain

## Encryption Status

Spring Cloud Config Server supports symmetric AES encryption and RSA asymmetric encryption of property values. Encrypted values appear as `{cipher}...` in configuration files and are decrypted server-side before being served to clients (or optionally client-side). The encryption status for this deployment cannot be determined from the repository alone (no application.yml, no Dockerfile). Key questions for assessment:

- Are property values prefixed with `{cipher}` in the backing Git repository?
- Is the Config Server `encrypt.key` or `encrypt.keyStore` configured, and how is the encryption key itself protected?
- Is the Config Server serving over HTTPS?

## Data Flows

Configuration consumers (Gen-2 Spring Boot microservices) make HTTP GET requests to the Config Server at bootstrap using `spring.cloud.config.uri`. The Config Server authenticates to the backing Git repository (if remote) and returns the merged property set. Data flows:

1. Git repository (backing config store) → Config Server (merge, optional decrypt) → Service HTTP response → Spring Boot `Environment` in consuming service
2. If the Config Server uses local filesystem, the filesystem mount is the trust boundary

## Retention Concerns

Git-backed configuration provides an implicit audit trail of all configuration changes (via commit history). This is beneficial for compliance but also means that any secret that was ever committed in plaintext remains in Git history even after rotation, unless the repository history is scrubbed. PCI DSS Requirement 3 requires that sensitive data not be retained longer than necessary; a Git history containing past database passwords or API keys would be a retention violation.

## PCI DSS Compliance Assessment

- **Req 2**: Must verify no default credentials in Config Server's own Spring Boot configuration
- **Req 3**: All sensitive property values in the backing Git repository must use `{cipher}` encryption; plaintext secrets in config files are a critical finding
- **Req 4**: Config Server must be served over TLS; clients must validate server certificates
- **Req 6**: Config Server must be kept patched; Spring Cloud Config has had CVEs related to path traversal and SSRF
- **Req 7**: Access to Config Server HTTP endpoints must require authentication (Basic Auth with strong credentials, or mutual TLS)
- **Req 10**: Config Server access logs (which service retrieved which configuration at what time) should feed into the SIEM

The near-empty state of this repository (no Dockerfile, no application configuration) means compliance cannot be verified here; the assessment depends on the runtime Docker image and the separate configuration Git repository.
