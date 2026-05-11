# Solution Architect View — jakarta-migrator

## Technical Architecture

`jakarta-migrator` is a **Maven multi-module aggregator project** with a single active submodule (`acegi-security`). There is no application runtime — it is a pure build-time artifact factory.

### Module Structure

```
jakarta-migrator/                    ← Root POM (aggregator)
├── pom.xml                          ← Defines modules, dependency management, build plugins
├── acegi-security/                  ← Active module
│   └── pom.xml                      ← Declares Eclipse Transformer execution
├── axis/                            ← Commented out (migration complete)
├── axis-jaxrpc/                     ← Commented out
├── axis-saaj/                       ← Commented out
├── axis-wsdl4j/                     ← Commented out
└── spring-remoting/                 ← Commented out
```

### Transformation Mechanism

Each active module's `pom.xml` declares the **Eclipse Transformer Maven Plugin** (`org.eclipse.transformer:transformer-maven-plugin:0.5.0`) with the `jakartaDefaults:true` rule set. The plugin executes at the `prepare-package` phase and:

1. Resolves the source artifact from its Maven coordinates (e.g., `org.acegisecurity:acegi-security:1.0.3`).
2. Applies the Eclipse Foundation's standard namespace mapping rules (the same rules used to produce Jakarta EE 9/10 from Java EE 8).
3. Produces a new JAR with the `jakarta-` prefix in the artifact ID, published under `com.onbe.ecount` / `org.acegisecurity` groupIds.

The plugin operates on compiled `.class` bytecode (constant pool string references), resource files (`MANIFEST.MF`, Spring XML contexts, service descriptors in `META-INF/services/`), and descriptor files (`web.xml`, etc.).

## API Surface

None. This project produces Maven artifacts, not APIs. The "API" is the Maven artifact coordinates:
- `org.acegisecurity:jakarta-acegi-security:1.0.3`

## Security Posture

### Supply Chain Risks

| Issue | Severity | Detail |
|---|---|---|
| TLS disabled for Maven downloads | High | `-D aether.connector.https.securityMode=insecure` in all CI workflows disables TLS cert validation for artifact resolution. A MITM attack on a Maven repository connection could substitute a malicious JAR. |
| Source artifact integrity | Medium | No SHA-256 verification of the source JAR before transformation. Maven checksum verification is the only protection (`sha1`/`md5` from Central, which is weak). |
| Acegi Security CVEs | Critical | `org.acegisecurity:acegi-security:1.0.3` is a 2007 library with multiple known CVEs. The transformation renames namespaces but does not fix security vulnerabilities in the library code. Any consuming service should be isolated from public internet access for the Acegi-dependent code paths. |
| Eclipse Transformer version | Low | Version `0.5.0` (2023). Should be verified against current 0.6.x releases for any transformation correctness fixes. |

### Positive Controls

- CodeQL scanning runs weekly (`codeql.yml`), though since there is no Java source code in the project (only POMs), the scan scope is limited.
- Dependabot is configured (`dependabot.yml`) to raise PRs for dependency updates.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| Parent version mismatch | Low | `acegi-security/pom.xml` declares parent version `1.0.1` while root is `1.0.2` — version drift |
| Commented-out modules | Medium | Five commented-out modules create confusion about project state. Completed migrations should be removed from the POM or the modules archived. |
| No transformation verification test | High | There is no automated test that verifies the output JAR contains no `javax.*` references. Silent transformation failures are possible (e.g., reflection-based `Class.forName("javax.servlet....")` strings). |
| Acegi Security still required | High | The continued active status of the `acegi-security` module signals that a consuming service has not migrated to Spring Security 6.x. This should be tracked as a migration debt item. |
| Spring Remoting and Axis (legacy protocols) | High | Although the modules are commented out, `manage-payment-rest-api` still depends on `jakarta-spring-remoting` and `jakarta-axis-*` artifacts, indicating these protocols are still in production use. Spring Remoting was removed from Spring 6.x and Apache Axis 1.4 is EOL. |

## Gen-3 Migration Context

`jakarta-migrator` is itself a **migration enabler for Gen-3** rather than a Gen-3 service. Its lifecycle should be:

1. **Current state**: Provides `jakarta-acegi-security` for the unknown Acegi-dependent service.
2. **Target state**: All consuming services migrated to Spring Security 6. The `acegi-security` module becomes inactive (commented out). The entire repository becomes dormant.
3. **Retirement trigger**: When no `jakarta-*` artifacts from this project appear in any active service's dependency tree.

The solution architect should ensure a dependency audit is run across the entire portfolio to identify all transitive consumers of `jakarta-acegi-security`, `jakarta-spring-remoting`, `jakarta-axis`, and related artifacts, then assign migration tasks to the owning teams.

## Code-Level Risks

1. **No Java source code** — The project contains no `.java` files. All code is in the pom.xml plugin configurations. This makes the project very simple but means that any issues with the transformation plugin configuration will only surface when a consuming service fails to start.

2. **`prepare-package` phase execution** — The transformer runs at `prepare-package`. If the Maven build is run with `-DskipPackage` or in a phase earlier than `package`, the transformation will not execute and the untransformed JAR would be installed/deployed. This is a build process risk.

3. **Artifact coordinate confusion** — The `acegi-security` module uses `groupId: org.acegisecurity` (matching the original) rather than `com.onbe.ecount` (the standard Onbe groupId). This may cause dependency resolution confusion if a consuming service has both the original and the transformed artifact on the classpath.
