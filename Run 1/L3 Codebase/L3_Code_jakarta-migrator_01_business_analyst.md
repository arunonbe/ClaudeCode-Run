# Business Analyst Analysis — jakarta-migrator

## 1. System Overview

`jakarta-migrator` is not an application or a service — it is a **Maven build tooling library** that performs **automated bytecode migration from `javax.*` to `jakarta.*` namespaces** for legacy Java libraries that Onbe depends upon. It contains no business logic, no user-facing functionality, and no database access. Its sole purpose is to enable Onbe's application portfolio to run on **Jakarta EE 10+ and Java 21** by producing Jakarta-compatible versions of otherwise-incompatible legacy libraries.

Artifact: `com.onbe.ecount:jakarta-migrator:1.0.2` (pom.xml lines 11–13). Parent: `prepaid-parent:6.0.10`. Java: 21 source and target.

## 2. Business Rationale

### 2.1 The Java EE → Jakarta EE Namespace Split

In 2017, Oracle transferred the Java EE specification to the Eclipse Foundation. The Eclipse Foundation was required to rename the `javax.*` packages to `jakarta.*` starting with Jakarta EE 9. This creates a hard binary incompatibility:

- Libraries compiled against `javax.servlet.*`, `javax.activation.*`, `javax.mail.*`, etc. **cannot run** on Jakarta EE 10+ containers (Tomcat 10.x, WildFly 27+, Spring Boot 3.x) without bytecode transformation.
- Spring Boot 3.x (used in `ivr-ws_API` ivrapi-boot module) **requires Jakarta EE 10** and therefore all dependencies must use `jakarta.*` namespaces.

This affects many legacy libraries in the Onbe portfolio that were compiled against `javax.*`. Rather than waiting for upstream maintainers to release Jakarta-compatible versions, `jakarta-migrator` performs the transformation automatically during the Maven build.

### 2.2 Scope of Migration

The project manages transformation of specific legacy libraries that Onbe's codebase depends upon. The root `pom.xml` defines the following as sub-modules (some currently commented out):

**Currently active module**:
- `acegi-security` → produces `jakarta-acegi-security:1.0.3` (org.acegisecurity:acegi-security)

**Commented-out modules** (previously active, possibly completed):
- `axis` → produces `jakarta-axis:1.4` (Apache Axis SOAP framework)
- `axis-wsdl4j` → produces `jakarta-axis-wsdl4j:1.5.1`
- `axis-saaj` → produces `jakarta-axis-saaj:1.4`
- `axis-jaxrpc` → produces `jakarta-axis-jaxrpc:1.4`
- `spring-remoting` → produces `jakarta-spring-remoting:2.0.8`

**Acegi Security** (currently the only active module) is the predecessor to Spring Security. Version 1.0.3 is extremely old (~2007). Its presence in the active migration list means some Onbe application still depends on Acegi Security for authentication and requires a Jakarta-compatible version.

### 2.3 Dependency Context

The commented-out Axis, Axis-WSDL4J, Axis-SAAJ, Axis-JAX-RPC, and spring-remoting modules tell the migration story:
- These modules were **already migrated** and are no longer in the active build (commented out in `pom.xml` lines 21–26).
- The resulting `jakarta-*` artifacts are likely published to GitHub Packages and consumed by `ivrintegration_API` and `ivr-ws_API`.
- The only remaining active migration is `acegi-security`.

## 3. Business Impact

The business impact of this tooling is indirect but critical:

1. **Enables Spring Boot 3.x migration** of IVR and other services (`ivr-ws_API` uses Spring Boot 3.5.7).
2. **Unblocks Java 21 adoption** across the platform (Java 21 is LTS until September 2029).
3. **Reduces supply chain risk** by eliminating dependency on unmaintained library versions running on outdated runtimes.
4. **Compliance impact**: Running outdated frameworks (Spring 2.5.6, Axis 1.4 compiled for javax.*) on modern containers without this migration tooling would create security vulnerabilities. This tooling is part of Onbe's PCI DSS Requirement 6.3 (security vulnerabilities identified and addressed) compliance posture.

## 4. Stakeholder Value

| Stakeholder | Value Delivered |
|---|---|
| Development teams | Can use modern Jakarta EE / Spring Boot 3 without rewriting all legacy library calls |
| Security/Compliance | Enables platform-wide Java 21 + Spring Boot 3.x adoption — reducing CVE exposure |
| Infrastructure/DevOps | Supports containerization (Docker + K8s) which requires Spring Boot 3.x |
| Architecture team | Enables phased migration strategy rather than big-bang rewrites |

## 5. Limitations and Scope Boundaries

- `jakarta-migrator` transforms **bytecode only** — it renames `javax.*` to `jakarta.*` namespace references in compiled JARs using the Eclipse Transformer.
- It does **not** address semantic API changes between Java EE and Jakarta EE versions (e.g., behavior changes in Servlet 6.0 vs 4.0).
- It does **not** address functional incompatibilities in legacy libraries (Acegi Security's Spring context loading may break under Spring Boot 3.x regardless of namespace transformation).
- The migration tooling is **build-time only** — it produces migrated JARs; the actual compatibility testing must be done by consuming application teams.

## 6. Long-Term Relevance

As libraries graduate to native Jakarta EE 10+ support (e.g., Apache Axis 2.x → Apache CXF, Acegi Security → Spring Security 6.x), the modules in `jakarta-migrator` can be retired and replaced with the native Jakarta-compatible libraries. The `jakarta-migrator` is therefore a **transitional artifact** with a planned obsolescence once all consuming services complete their migration.
