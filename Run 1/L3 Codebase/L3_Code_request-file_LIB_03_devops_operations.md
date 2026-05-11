# DevOps / Operations View — request-file_LIB

## Build System

Maven with Maven Wrapper (`mvnw`). Multi-module project:
- Parent: `com.ecount.service:requestfile:2.0.0` (inherits from `com.parents:prepaid-parent:6.0.12`)
- Child module: `requestfile-impl` — the single implementation JAR

Java compiler settings:
- `maven.compiler.source: 21`
- `maven.compiler.target: 21`

Key dependencies in `requestfile-impl/pom.xml`:
- `org.springframework:spring-context` — Spring XML application context (Gen-1 wiring)
- `commons-lang:commons-lang` — Apache Commons Lang (Gen-1 era version)
- `com.thoughtworks.xstream:xstream` — XStream XML/Object serialization (note: legacy, has known CVEs)
- `com.sun.xml.bind:jaxb-xjc`, `jaxb-libs`, `jaxb-impl` — JAXB implementation (com.sun legacy artifacts)
- `javax.xml.bind:jaxb-api` — JAXB API
- `sax:sax` — SAX parser
- `com.sun.xml:relaxngDatatype` — RelaxNG data type library

The build enforcer bans transitive dependencies except for explicitly whitelisted groups (Spring, XStream, JAXB). This is a positive dependency hygiene control.

## CI/CD Pipeline

GitHub Actions workflows:

**`.github/workflows/github-package-publish.yml`**: Publishes the library JAR to the GitHub Package Registry on push to `main` or workflow dispatch. Uses `PAT_TOKEN_PACKAGE` for authentication.

**`.github/workflows/codeql.yml`**: CodeQL static analysis for Java. Triggers on push to `main` and pull requests targeting `main`. This provides SAST coverage, though CodeQL may not detect the JAXB/XmlTransient data exposure pattern as a vulnerability (it is a semantic issue rather than a typical injection or memory-safety issue).

**`.github/dependabot.yml`**: Automated dependency update PRs.

The CI pipeline is appropriate for a shared library. No container build; JAR-only artifact.

## Deployment Model

Published as a JAR to the GitHub Package Registry (`com.ecount.service:requestfile-impl:version`). Consumed by downstream batch processing services (e.g., file order manager, sweep processor) as a Maven dependency.

The version `2.0.0` is a release (non-SNAPSHOT) version, consistent with stable library release practices.

## Runtime Details

- **Java target**: 21 (LTS)
- **Spring Context**: Used for XML-based Spring application context wiring (`applicationContext-requestfile.xml`). This is a Gen-1 pattern — Spring XML beans define the `RequestBuilder`, `ReqFileNameGenerator`, and related collaborators.
- **JAXB**: `com.sun.xml.bind:jaxb-impl` (legacy Sun/Oracle JAXB implementation). In Java 11+, JAXB was removed from the JDK standard distribution. The library explicitly includes the standalone JAXB implementation JARs, which is correct for Java 21 compatibility.
- **XStream**: Used for XML/Object mapping. XStream has a history of critical CVEs (remote code execution via crafted XML, CVE-2021-29505 and predecessors). The version in use is not specified in the visible pom.xml (inherited from parent BOM `6.0.12`).

## Secrets Management

No secrets are required or managed by this library. The only configuration is the `REQUEST_FILE_BASE_PATH` property in a properties file managed by `ReqFileNameGenerator` — this is a filesystem path, not a credential.

The GitHub Actions pipeline uses `PAT_TOKEN_PACKAGE` for package registry authentication, stored as a GitHub Actions secret.

## Observability

The library uses SLF4J with Lombok `@Slf4j` for logging. `RequestBuilder` logs errors at ERROR level on file generation failure. However, the primary error handling pattern is `e.printStackTrace()`, which writes stack traces to stdout/stderr rather than the SLF4J logger — this is a code quality defect that reduces log structure and makes automated log alerting on file generation failures unreliable.

There are no metrics, health endpoints, or distributed tracing capabilities — this is a utility library, not a service.

## EOL and CVE Concerns

| Dependency | Risk |
|---|---|
| `com.thoughtworks.xstream:xstream` | High CVE history (RCE via XML deserialization). Version from parent BOM must be audited. XStream requires allowlisting of safe types. |
| `com.sun.xml.bind:jaxb-*` | Legacy Sun JAXB artifacts. These are generally safe but are maintained under the Eclipse GlassFish project as `org.glassfish.jaxb:*`. Migration to the standard artifacts is recommended. |
| `commons-lang:commons-lang` (1.x artifact ID) | Apache Commons Lang 1.x is very old. Version from parent BOM must be audited for CVEs. The modern replacement is `org.apache.commons:commons-lang3`. |
| `sax:sax` | Very old SAX parser artifact. Must confirm version from parent BOM. |

The parent BOM (`prepaid-parent:6.0.12`) controls the actual versions of all these dependencies; it must be audited for pinned versions and outstanding CVEs. The CodeQL pipeline provides partial coverage but does not substitute for a Dependency-Check/OWASP or Trivy dependency scan.
