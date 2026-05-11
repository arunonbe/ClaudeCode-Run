# DevOps & Operations Report — i18n-utils_LIB

## 1. Build System

### 1.1 Build Tools

| Property | Value |
|---|---|
| Build tool | Apache Maven (primary) |
| Maven Wrapper | Present (`mvnw`, `mvnw.cmd`, `.mvn/wrapper/`) |
| Maven version (wrapper) | See `.mvn/wrapper/maven-wrapper.properties` |
| Compiler source/target | `1.5` (Java 5) — `pom.xml` lines 56–59 |

The Maven Wrapper is present (evidenced by `mvnw`, `mvnw.cmd`, and `.mvn/wrapper/`), which is a modern addition. The wrapper was likely added retroactively during CI/CD setup, as the core library itself targets Java 1.5 — a combination that is anachronistic.

There are no Gradle build files. This project uses Maven only, unlike `global-deposit-batch_LIB` which had dual build systems.

### 1.2 POM Configuration

| Property | Value |
|---|---|
| GroupId | `com.ecount.utils` |
| ArtifactId | `i18n-utils` |
| Version | `2020.9.10` (date-based: September 10, 2020) |
| Packaging | `jar` |
| Final Name | `i18n` (produces `i18n.jar`) |
| Parent | `prepaid-parent:1` (groupId `com.citi.prepaid`) |
| Java Source/Target | `1.5` |

### 1.3 Dependencies

| Dependency | Version | Scope |
|---|---|---|
| `junit:junit` | `3.8.1` | test |
| `javax.servlet.jsp:jsp-api` | `2.1` | compile |

The dependency set is minimal — only JUnit 3.8.1 for tests (an extremely old version; JUnit 5 is current) and the JSP 2.1 API for the tag library implementation. The `jsp-api` at version 2.1 corresponds to Java EE 5 / Servlet 2.5, confirming the library was written for legacy Java EE application servers.

### 1.4 Build Artifacts

The Maven build produces `i18n.jar` in the `target/` directory. The TLD file is packaged into `META-INF/tld/i18n-taglib.tld` inside the JAR (configured via `pom.xml` lines 38–50):

```xml
<resource>
  <directory>${basedir}/src/main/resources/com/ecount/taglibs</directory>
  <targetPath>META-INF/tld</targetPath>
  <includes><include>*.tld</include></includes>
</resource>
```

This is the standard JSP tag library packaging convention — the container auto-discovers TLD files in `META-INF/tld/` at deployment.

### 1.5 Distribution Management

Distribution is configured to the **Wirecard Nexus repository** at `d-na-stk01.nam.wirecard.sys` (`pom.xml` lines 23–34):

```xml
<url>dav:http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/releases</url>
```

This uses the **WebDAV wagon extension** (`wagon-webdav:1.0-beta-2`, `pom.xml` lines 63–68) for upload — a legacy Maven deployment mechanism. The WebDAV wagon version `1.0-beta-2` is extremely old and may have compatibility issues with modern Maven versions.

---

## 2. CI/CD Pipeline

### 2.1 GitHub Actions — CodeQL

`.github/workflows/codeql.yml` configures weekly security scanning:

```yaml
schedule:
  - cron: 42 14 * * 5  # Fridays at 14:42 UTC
```

Uses the shared Onbe CodeQL workflow (`Onbe/om-ci-setup/.github/workflows/codeql-auto.yml@main`) on self-hosted Linux runners. CodeQL scanning of a Java 1.5 codebase provides limited value for modern vulnerability detection but satisfies baseline security scanning requirements.

### 2.2 Dependabot

`.github/dependabot.yml` configures weekly Maven dependency update PRs. Given the library's minimal dependency set (`junit:3.8.1`, `jsp-api:2.1`), Dependabot will generate PRs to update these — but upgrading `junit` to 4.x or 5.x requires code changes (the test class `TestI18NUtils.java` has a `main()` method, not JUnit annotations) and upgrading `jsp-api` to 3.x (Jakarta EE) is a breaking namespace change.

### 2.3 Missing CI/CD

There is **no build or test pipeline**. There is no `.gitlab-ci.yml` and no GitHub Actions workflow that:
- Compiles the library
- Runs unit tests
- Publishes the artifact to a repository

All three phases (build, test, publish) are manual operations. This means:
- The library's version `2020.9.10` may not actually reflect the last time anyone ran `mvn deploy`
- There is no automated verification that the library compiles with the stated Java 1.5 source level
- Dependabot PRs that update `junit` will have no automated test run to verify they don't break the build

---

## 3. Artifact Repository

Artifacts are published to the Wirecard Nexus at `d-na-stk01.nam.wirecard.sys:8080`. As with `global-deposit-batch_LIB`, this Nexus instance is from the Wirecard era and may be decommissioned or inaccessible post-acquisition.

Any downstream Maven project that depends on `com.ecount.utils:i18n-utils:2020.9.10` and has this Nexus configured as a dependency repository will fail to resolve the artifact if the Nexus is offline. This is a supply chain risk for all JSP web applications in the Onbe portfolio.

---

## 4. Deployment

### 4.1 Deployment Model

As a `_LIB` repository, `i18n-utils_LIB` is not independently deployed. It is included as a Maven dependency in downstream web application projects. The JAR is included in those applications' `WEB-INF/lib/` directory when packaged as a WAR file.

Downstream deployment environments (inferred from the broader Onbe portfolio):
- Apache Tomcat or JBoss/WildFly application server
- Java EE 5 / Servlet 2.5 containers (matching `jsp-api:2.1` dependency)
- On-premise Windows or Linux application servers

### 4.2 TLD Discovery

When deployed inside a WAR, the container discovers the TLD from `META-INF/tld/i18n-taglib.tld` inside `i18n.jar`. JSP pages reference it via:
```jsp
<%@ taglib prefix="i18n" uri="http://ecount.com/tags/i18n-taglib" %>
```

---

## 5. Testing

### 5.1 Test Coverage

The `src/test/` directory contains one test file:
- `TestI18NUtils.java` — a manual test driver with a `main()` method

This is **not a JUnit test class** — it has no `@Test` annotations and no assertion methods. It is a command-line program that prints formatted output to stdout for visual inspection. Running `mvn test` will not execute this class via the Surefire plugin (which only picks up classes matching `**/Test*.java` or `**/*Test.java` with test runner annotations).

In practice, this means **there are zero automated tests**. All validation of the library's correctness is manual (run the main method, eyeball the output).

### 5.2 Operational Impact

The lack of automated tests means:
- No regression detection when upgrading dependencies
- No validation that locale-specific formatting produces correct output for all 13+ supported locales
- No verification that edge cases (null dates, null locales, negative pennies values) are handled correctly

---

## 6. Monitoring and Observability

As a pure utility library with no network I/O or state, there is nothing to monitor at the library level. Observability for consumers of this library is the responsibility of the consuming web application (logging framework, APM agent).

Relevant operational note: The `fixSymbol()` method silently replaces broken euro characters without logging or alerting. If the encoding environment changes and a different symbol is affected, the fix will silently fail and incorrect characters will be rendered on cardholder-facing pages.

---

## 7. Operational Risks

| Risk | Severity | Notes |
|---|---|---|
| Wirecard Nexus may be offline | HIGH | Downstream builds fail if Nexus unreachable |
| No automated build/test CI | HIGH | No regression protection |
| Java 1.5 target (EOL) | HIGH | Security patches for Java 1.5 unavailable since 2009 |
| JUnit 3.8.1 | MEDIUM | 2003-era test framework; no assertion library |
| No Maven deploy pipeline | MEDIUM | Manual artifact publication only |
| Euro symbol encoding workaround | LOW | Silently broken if encoding changes |
