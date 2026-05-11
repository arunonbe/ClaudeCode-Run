# Solution Architect Report — webapp-parent-pom_PARENT

## API Surface

None directly. This is a Maven POM artifact. The APIs of individual web applications inheriting from this parent are defined in those child modules.

## Security Posture

**High risk to the overall estate.** This parent POM is the governance root for the Gen-1 Struts-based web application stack. Its security posture has cascading effects on all inheriting applications.

Key security concerns:

1. **Struts 1.3.8 — Remote Code Execution risk**: Apache Struts 1.x is EOL and carries multiple unpatched CVEs. The most severe include S2-001 (parameter tampering), S2-005, S2-007, and later series vulnerabilities that allow arbitrary Java code execution via OGNL injection. Because Struts 1.x is no longer maintained, there is no patch path; the only remediation is framework replacement. All web applications running Struts 1.x in the CDE are in direct violation of PCI DSS Req. 6.3.

2. **`commons-fileupload` exclusion is not a complete mitigation**: While the exclusion of `commons-fileupload` from `struts-core` is present (`pom.xml` line 109–112), this does not protect against OGNL injection vulnerabilities in the Struts action dispatch mechanism.

3. **Java 1.6 compiler target**: Code compiled to Java 6 cannot benefit from the security improvements in Java 7+ (e.g., JSSE TLS 1.2 support by default, improved PRNG, stronger cryptography defaults). All JVMs running these applications should enforce Java 7+ at runtime.

4. **Jetty 6.1.3 in development**: Mortbay Jetty 6 is EOL with known vulnerabilities. Development use does not directly impact production, but developers running local instances are exposed.

5. **HTTP Nexus dependency resolution**: `pom.xml` line 16: `http://d-na-stk01.nam.wirecard.sys:8080/nexus/content/repositories/` — all Maven dependencies resolved from this server are fetched over unencrypted HTTP, enabling artifact substitution by a network-adjacent attacker.

6. **GitLab CI skips all tests**: `.gitlab-ci.yml` sets `MAVEN_TEST_SKIP=true` for all three phases. This means no security, unit, or integration tests are run in CI for any web application using this pipeline template.

## Critical Vulnerabilities with File:Line Citations

| Severity | Finding | File:Line |
|----------|---------|-----------|
| Critical | Struts 1.3.8 declared — EOL framework with unpatched RCE CVEs | `pom.xml:32` (`<struts.version>1.3.8</struts.version>`) |
| Critical | Java 1.6 compiler target — EOL runtime | `pom.xml:39–40` (`<maven.compiler.source>1.6</maven.compiler.source>`) |
| High | HTTP-only Nexus repository URL — artifact integrity risk | `pom.xml:16` (`http://d-na-stk01.nam.wirecard.sys:8080/nexus/...`) |
| High | All CI tests skipped | `.gitlab-ci.yml:7–9` (`-Dmaven.test.skip=true`) |
| Medium | SNAPSHOT parent version — non-deterministic builds | `pom.xml:13` (`<version>10.0.1-SNAPSHOT</version>`) |
| Medium | Jetty 6.1.3 EOL development server | `pom.xml:37` (`<maven-jetty-plugin.version>6.1.3</maven-jetty-plugin.version>`) |
| Low | xDoclet 1.2.3 abandoned tool — code generation from Javadoc tags is unmaintained | `pom.xml:33–34` |

## Technical Debt

- **Framework migration**: Struts 1.x → Spring MVC 6.x is a full rewrite of all action classes and JSP tag usage.
- **Compiler upgrade**: Java 6 → 21 requires addressing all deprecated API usages, module system compatibility, and Struts OGNL reflective access which is blocked by Java 9+ module encapsulation.
- **CI test enforcement**: Tests must be re-enabled across all child modules; `maven.test.skip=true` must be removed from the GitLab CI template.
- **Nexus HTTPS migration**: All internal artifact repositories must be migrated to HTTPS with valid certificates.
- **Parent POM release**: The SNAPSHOT version must be released before any production deployment to ensure build reproducibility.
