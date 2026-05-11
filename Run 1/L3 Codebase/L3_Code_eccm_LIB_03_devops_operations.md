# eccm_LIB — DevOps & Operations Report

## Build System

`eccm_LIB` uses **Apache Maven** with a Maven Wrapper. Build configuration:
- Artifact: `com.ecount.web.tags:eccm:1.1.1` (JAR packaging)
- Parent POM: `com.citi.prepaid:module-parent:5`
- Java source target: **not explicitly set** in the build section — defaults to the parent POM's setting, likely Java 1.5 or 1.6 based on the era
- Dependencies use WebDAV wagon extension (`wagon-webdav:1.0-beta-2`) for artifact publication — a very old Maven extension

The `pom.xml` has no `<build><plugins>` section defining compiler source/target, meaning the compilation target is inherited from the parent POM (which is `module-parent:5` from the Citibank prepaid lineage). This is a risk because changing the parent POM version could silently change the compilation target.

---

## CI/CD Pipeline

### GitHub Actions — CodeQL
`.github/workflows/codeql.yml` (271 bytes) — minimal CodeQL workflow. Provides basic static analysis security scanning.

### Dependabot
`.github/dependabot.yml` (515 bytes) — automated dependency update PRs.

### No GitLab CI
Unlike `ecap-backend-process_LIB`, this repository has **no `.gitlab-ci.yml`**. The SCM is not configured in the POM, suggesting the library was originally developed in a CVS/SVN environment and migrated to git without a corresponding CI/CD pipeline being established.

---

## Test Coverage

A single test class exists: `CreatePropertyIndexTest.java` (3,470 bytes). This tests the Lucene index property creation utility. There are no tests for:
- JSP tag rendering logic
- Rules engine evaluation
- CMS HTTP content retrieval
- URL rewriting
- The `CMSService.fire()` search method

Test coverage is minimal for a library that drives portal rendering logic for all client-branded eCount web applications.

---

## Deployment Model

`eccm_LIB` is deployed as a JAR dependency consumed by eCount web applications (WAR files). It is not a standalone service. The deployment lifecycle is:
1. `mvn install` publishes the JAR to the internal Maven repository (via WebDAV)
2. Consumer WARs (e.g., `clientzone_WAPP`, `enrollment_WAPP`, `scheduler_WAPP`) include `eccm:1.1.1` as a runtime dependency
3. The WAR deployment carries `eccm.jar` in its `WEB-INF/lib/`

The Lucene content index at `D:/c-base/Runtime/xContent/content` must be separately deployed and populated — this is managed by the `xcontent_SVC` and `eccm_LIB`'s own `CreatePropertyIndex` utility.

---

## Operational Risks

### Risk 1: Apache Lucene 2.0.0 — CRITICAL (EOL)
`pom.xml` line 97: `org.apache.lucene:lucene-core:2.0.0`
Lucene 2.0.0 was released in 2006. The current version as of 2026 is Lucene 9.x. Using Lucene 2.x means:
- No security patches for 15+ years
- No support for modern index formats
- No compatibility with modern Java versions (Lucene 2.x has known compatibility issues with Java 11+)
- No performance improvements (Lucene 2.x is significantly slower than Lucene 8/9 for large indexes)

This is a **blocking issue** for any Java version upgrade — Lucene 2.0.0 may not compile or run correctly on Java 11+.

### Risk 2: Spring 2.0.2 — HIGH
`pom.xml` line 78: `org.springframework:spring:2.0.2`
Spring 2.0.2 (released ~2007) is approximately 18 years old. Multiple known CVEs exist in Spring 2.x that were patched in later versions.

### Risk 3: Apache Struts 1.2.8 — CRITICAL
`pom.xml` line 92: `struts:struts:1.2.8`
Apache Struts 1.x is **end-of-life** and has numerous critical vulnerabilities, including remote code execution vulnerabilities (CVE-2016-1181, CVE-2016-1182 in Struts 1.x). Using Struts 1.2.8 in any web application is a critical security risk.

### Risk 4: Commons HttpClient 3.0.1 — HIGH
`pom.xml` line 36: `commons-httpclient:commons-httpclient:3.0.1`
Commons HttpClient 3.x is deprecated (replaced by Apache HttpComponents). It:
- Does not support TLS 1.2 or 1.3 by default
- Has no modern cipher suite support
- Cannot validate modern TLS certificates properly

### Risk 5: In-Memory Lucene Index — Operational Risk
The RAM directory (`RAMDirectory`) configuration in `CMSApplicationContext.xml` (line 16) means:
- Index content is lost on JVM restart
- Index must be re-built from `D:/c-base/Runtime/xContent/content` on every startup
- Under heavy load or large index sizes, RAM consumption is a concern
- If the content directory is unavailable at startup, the application starts with an empty index

### Risk 6: Hard-coded Production Filesystem Path
`CMSApplicationContext.xml` line 38: `D:/c-base/Runtime/xContent/content`
This path is hardcoded in the Spring configuration XML. While it can be overridden via the externalized properties file, the hardcoded fallback means any environment that does not have this exact path will fail silently or use the wrong content directory.

---

## Version Management

| Component | Version in POM | Risk |
|---|---|---|
| `eccm` library | 1.1.1 (released) | OK — released version |
| Apache Lucene | 2.0.0 | EOL 2006 |
| Spring Framework | 2.0.2 | EOL ~2012 |
| Apache Struts | 1.2.8 | EOL; critical CVEs |
| Commons HttpClient | 3.0.1 | EOL; no TLS 1.2+ |
| log4j | 1.2.9 | EOL; CVEs present |
