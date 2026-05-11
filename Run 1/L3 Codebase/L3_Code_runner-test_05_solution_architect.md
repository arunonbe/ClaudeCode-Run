# runner-test — Solution Architect View

## Technical Architecture
Two-class Java 8 application: `hello.HelloWorld` (entry point) and `hello.Greeter` (greeting logic). Built as a shaded JAR. No frameworks, no DI, no web layer.

## API Surface
None. Console application only.

## Security Posture

### Authentication / Authorisation
Not applicable — no runtime service.

### Cryptography
None in application code.

### Secrets Management — CRITICAL FINDINGS
The file `.mvn/wrapper/settings.xml` contains **four plaintext passwords committed to source control**:

| Line | Server ID | Credential |
|---|---|---|
| 34 | `wirecard-mavenproxy-repository` | username `acmng`, password in plaintext |
| 39 | `nexus-qa` | username `deployment`, password in plaintext |
| 43 | `ecount.release` | username `deployment`, password in plaintext |
| 47 | `ecount.snapshot` | username `deployment`, password in plaintext |

These must be treated as compromised and rotated. They should be moved to GitHub Actions secrets and referenced via `${env.NEXUS_PASSWORD}` style substitution in settings.xml.

### TLS / Transport Security
`aether.connector.https.securityMode=insecure` is set in both `codeql-java.yml` (line 26) and `nexus-deploy.yml` equivalents, disabling server certificate validation during Maven artifact resolution.

### CVE Exposure
- `log4j:log4j:1.2.17` is referenced in `service-test` parent POM (observed in service-tester_WAPP) but not directly in runner-test. The runner-test POM has no runtime dependencies.
- No explicit dependency versions declared; no transitive dependency risk in application scope.

### CodeQL SAST
CodeQL scanning uses `security-extended` query suite (`.github/codeql/codeql-config-java.yml`). `security-experimental` is commented out.

## Technical Debt
- Misspelled workflow (`marven.yml`).
- Java 8 target — EOL for most distributions; should upgrade to Java 17 or 21.
- No unit tests.
- `maven-shade-plugin` 3.2.4 may have known issues with newer JDK versions.

## Gen-3 Migration Requirements
Not applicable — infrastructure tooling. If modernised: move to GitHub Actions managed runners, remove self-hosted dependency, externalize all secrets to GitHub Actions environment secrets.

## Code-Level Risks
- `.mvn/wrapper/settings.xml:34,39,43,47` — plaintext repository credentials (HIGH severity, PCI DSS Req 8.3).
- `.github/workflows/codeql-java.yml:26` — `aether.connector.https.securityMode=insecure` disables TLS verification (MEDIUM severity).
- `src/main/java/hello/HelloWorld.java:6` — `System.out.println` not a risk in test context but PMD `SystemPrintln` rule would flag it.
