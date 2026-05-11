# DevOps / Operations View — xml-rpc-clients_LIB

## Build System

- **Build tool**: Maven with Maven Wrapper (`.mvn/wrapper/settings.xml` present)
- **Java version**: Determined by parent `service-parent:7`; given the 2016 version stamp and eCount/Citi heritage, Java 8 or earlier is the effective compile target (no explicit Java 21 target observed in sub-module POMs, unlike modernized libs such as xaffiliate-service)
- **Parent POM**: `com.citi.prepaid.service:service-parent:7` — Gen-1 Citi-era parent (older than the `service-parent:9.0.1-SNAPSHOT` seen in Gen-2 repos)
- **Version**: `2016.1.1` — version number encodes a 2016 release year; no SNAPSHOT suffix indicates this is treated as a stable release, but the version has been frozen for approximately a decade
- **Packaging**: Multi-module POM project with 7 child JAR modules:
  - `directorClient` — Director service client
  - `ecountCoreClient` — Core member/device/transfer/event client
  - `profileClient` — Profile service client
  - `eventServiceClient` — Event service client
  - `orderXMLRPCClient` — Order service client
  - `securityServiceClient` — Security service client
  - `strongBoxClient` — StrongBox secure credential service client
- **Key dependencies** (from root POM dependency management):
  - `com.ecount.service.core.ecountcore:common:2014.1.1` — ecountcore shared value objects and XML-RPC infrastructure; version stamps 2014
  - `com.citi.prepaid.service.core:xmlrpc:1.0.5` — the XML-RPC protocol serialization/deserialization engine
  - `com.citi.prepaid.service.order:order-common:2.4.12` — order value objects
  - `com.ecount.service.common:services-common:1.0.0` — earlier version of services-common (1.0.0, not 3.0.x)
  - `junit:junit:4.4` — test scope; JUnit 4.4 (released 2007)
- **Apache Commons HttpClient**: `DirectorXMLRPCClient` imports `org.apache.commons.httpclient.*` (Commons HttpClient 3.x), an EOL library that was succeeded by Apache HttpComponents in 2011

## CI/CD Pipeline

- **GitHub Actions**: `.github/workflows/codeql.yml` present — CodeQL static analysis (Java) is configured
- **Dependabot**: `.github/dependabot.yml` present — automated dependency update PRs
- **No publish workflow observed**: Unlike wirecard_utilities_LIB or xaffiliate-service_LIB, no `github-package-publish.yml` is evident; the library may rely on manual Maven deployment or a legacy Nexus/Artifactory publishing process matching the `service-parent:7` era
- **GitLab**: May have a legacy `.gitlab-ci.yml` from the Northlane/Wirecard GitLab era; migration status should be confirmed
- **No SBOM plugin**: CycloneDX or similar SBOM generation not observed; given the number of legacy dependencies, SBOM generation is important for vulnerability tracking

## Deployment Model

- **Artifact type**: 7 JAR libraries; consumed as Maven dependencies by Gen-1/Gen-2 consumer applications
- **Consumers**: All Gen-1 OnePlatform web applications, CSA tools, and batch processes that need to invoke eCountCore backend services
- **No containerization**: No Docker or Docker Compose configuration; library has no standalone runtime; pure compile-time dependency
- **Registry**: Assumed to be published to an internal Maven repository (Nexus/Artifactory or GitHub Packages); publishing mechanism not fully documented in the repository

## Runtime

- **Java 8 or earlier** (inferred from service-parent:7 and 2016 version stamps; no override observed in sub-module POMs)
- **Apache Commons HttpClient 3.x** (EOL): Used for HTTP XML-RPC transport in `DirectorXMLRPCClient`; EOL since 2011 with multiple known CVEs including SSRF-class vulnerabilities in URL handling
- **JUnit 4.4** in test scope: Released 2007; should be upgraded to JUnit 5
- **No Spring, no Spring Boot**: The library itself is a plain Java library with no framework dependencies; it uses `commons-logging` for logging

## Secrets Management

- No secrets managed by this library
- Director endpoint URLs are resolved at runtime from the Director service — the Director URL itself must be provided by the consumer application's configuration; it is not embedded in this library
- The `Testing.java` and `ClientTest1.java` files in `orderXMLRPCClient/src/main/java` (not test scope) must be reviewed for any hardcoded test URLs, credentials, or real server addresses

## Observability

- **Logging**: `commons-logging` (Apache Commons Logging) — delegates to the underlying logging framework configured by the consuming application (typically Log4j or SLF4J)
- **`DirectorXMLRPCClient`**: Logs HTTP errors at `log.error()` level; exceptions caught and logged at `log.debug()` — note that exceptions during XML-RPC calls are caught, logged at DEBUG, and the method returns `null`. This means a Director call failure produces a null return value silently (from the caller's perspective unless they check for null)
- **`MemberXMLRPCClient`**: Logs combined field values at INFO level in `puidMemberSearch()`, including `lookupPartnerUserID` — PII risk (see business analyst view)
- **No distributed tracing**: No correlation ID propagation, no OpenTelemetry, no Zipkin/Sleuth integration; consistent with Gen-1 era; requests cannot be traced end-to-end across service calls
- **No health endpoint**: Library has no standalone health check; availability is inferred from caller's success/failure rate

## Known EOL Runtimes and CVEs

- **Apache Commons HttpClient 3.x** (EOL 2011): Used in `DirectorXMLRPCClient`. CVEs affecting this version include SSRF issues, cookie handling vulnerabilities, and SSL/TLS configuration deficiencies. PCI DSS Req 6.3.3 requires all system components to be protected from known vulnerabilities
- **`ecountcore:common:2014.1.1`**: Core value objects stamped 2014; the XML-RPC infrastructure (`com.citi.prepaid.service.core:xmlrpc:1.0.5`) is similarly aged. Security posture of the XML parsing layer (XXE vulnerability in XML parsers that do not disable external entity processing) must be verified
- **JUnit 4.4** (test scope): Not a runtime risk, but indicates no test modernization
- **`2016.1.1` frozen version**: No version increment for approximately 10 years suggests the library is in maintenance-only mode with no active evolution. This is consistent with Gen-1 status but means consumers are permanently bound to 2011-era HTTP transport and 2014-era value objects
- **`Testing.java` and `ClientTest1.java` in main source**: Test harness code compiled into production JAR artifacts increases attack surface and may expose internal endpoint information
- **XML-RPC protocol**: The XML-RPC protocol itself has no built-in authentication, encryption, or integrity protection. All security relies on transport-level (HTTPS) and network-level (VPN/private network) controls. If XML-RPC traffic traverses any non-private network without TLS, it is a direct PCI DSS violation
- **Exception swallowing in DirectorXMLRPCClient**: Exceptions in `get()` are logged at DEBUG and the method returns null. Callers that do not null-check will encounter NullPointerException rather than a meaningful error; this degrades operational debuggability
