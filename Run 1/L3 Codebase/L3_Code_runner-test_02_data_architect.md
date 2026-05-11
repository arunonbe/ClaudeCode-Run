# runner-test — Data Architect View

## Data Stores
None. The application produces no persistent data at runtime.

## Schema / Tables
None applicable.

## Sensitive Data Present in Repository
| Location | Content | Sensitivity |
|---|---|---|
| `.mvn/wrapper/settings.xml` line 39 | `<password>dwil15?</password>` for `nexus-qa` server | HIGH — plaintext credential |
| `.mvn/wrapper/settings.xml` line 43 | `<password>d3v0nly</password>` for `ecount.release` | HIGH — plaintext credential |
| `.mvn/wrapper/settings.xml` line 47 | `<password>d3v0nly</password>` for `ecount.snapshot` | HIGH — plaintext credential |
| `.mvn/wrapper/settings.xml` line 34 | `<password>acmng</password>` for `wirecard-mavenproxy-repository` | HIGH — plaintext credential |

The `GITHUB_TOKEN` reference (`${env.GITHUB_TOKEN}`) for `github-releases` is correctly externalised via environment variable.

## Encryption
No encryption or sensitive data handling in application code. The Nexus HTTPS URL uses `aether.connector.https.securityMode=insecure` in CI workflows — TLS certificate validation is disabled.

## Data Flow
Compile-time only: source → `.class` files → shaded JAR. No runtime data processing.

## Data Quality / Retention
Not applicable.

## Compliance Gaps
- PCI DSS Req 3.4 / 8.3: Plaintext repository credentials committed to source control violate secret management requirements.
- The `aether.connector.https.securityMode=insecure` flag disables TLS verification in the build pipeline, creating a man-in-the-middle risk on artifact downloads.
