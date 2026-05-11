# Data Architect Analysis — jakarta-migrator

## 1. Data Architecture Overview

`jakarta-migrator` is a **build-time tooling project** with no runtime data architecture. It does not connect to any database, does not persist data, does not define domain models, and does not process PII or cardholder data at runtime. This analysis covers the artifact data model — the inputs and outputs of the transformation pipeline — and the Maven repository topology used to distribute migrated artifacts.

## 2. Build Artifact Data Model

### 2.1 Inputs

The transformation pipeline consumes existing compiled JAR artifacts from Maven repositories. Each sub-module `pom.xml` declares an upstream source dependency:

| Module | Source Artifact | Upstream Maven Coordinates |
|---|---|---|
| `acegi-security` | `acegi-security-1.0.3.jar` | `org.acegisecurity:acegi-security:1.0.3` |
| `axis` (commented out) | `axis-1.4.jar` | `org.apache.axis:axis:1.4` |
| `axis-wsdl4j` (commented out) | `wsdl4j-1.6.3.jar` | `wsdl4j:wsdl4j:1.6.3` |
| `axis-saaj` (commented out) | `saaj-impl-1.3.28.jar` | `com.sun.xml.messaging.saaj:saaj-impl:1.3.28` |
| `axis-jaxrpc` (commented out) | `axis-jaxrpc-1.4.jar` | `org.apache.axis:axis-jaxrpc:1.4` |
| `spring-remoting` (commented out) | `spring-remoting-2.0.8.jar` | `org.springframework:spring-remoting:2.0.8` |

### 2.2 Transformation Process (Data Pipeline)

The transformation is performed by the **Eclipse Transformer Maven Plugin** (`org.eclipse.transformer:transformer-maven-plugin:0.5.0`). The transformation is configured in each module's `pom.xml` with:
```xml
<jakartaDefaults>true</jakartaDefaults>
```
This applies the standard Eclipse Foundation mapping rules that rename:
- `javax.servlet.*` → `jakarta.servlet.*`
- `javax.activation.*` → `jakarta.activation.*`
- `javax.mail.*` → `jakarta.mail.*`
- `javax.xml.rpc.*` → `jakarta.xml.rpc.*`
- `javax.xml.soap.*` → `jakarta.xml.soap.*`
- Other `javax.*` packages covered by Jakarta EE 10 specification

The transformation operates on compiled bytecode (`.class` files inside the JAR) and on descriptor files (`MANIFEST.MF`, `web.xml`, Spring XML context files) embedded in the artifact. It does **not** modify Java source code — it is a binary transformation.

### 2.3 Outputs

Each active module produces a migrated JAR artifact published to GitHub Packages:

| Module | Output Artifact | Output Coordinates |
|---|---|---|
| `acegi-security` | `jakarta-acegi-security-1.0.3.jar` | `com.onbe.ecount:jakarta-acegi-security:1.0.3` |
| `axis` (completed) | `jakarta-axis-1.4.jar` | `com.onbe.ecount:jakarta-axis:1.4` |
| `axis-wsdl4j` (completed) | `jakarta-axis-wsdl4j-1.5.1.jar` | `com.onbe.ecount:jakarta-axis-wsdl4j:1.5.1` |
| `axis-saaj` (completed) | `jakarta-axis-saaj-1.4.jar` | `com.onbe.ecount:jakarta-axis-saaj:1.4` |
| `axis-jaxrpc` (completed) | `jakarta-axis-jaxrpc-1.4.jar` | `com.onbe.ecount:jakarta-axis-jaxrpc:1.4` |
| `spring-remoting` (completed) | `jakarta-spring-remoting-2.0.8.jar` | `com.onbe.ecount:jakarta-spring-remoting:2.0.8` |

## 3. Maven Repository Topology

### 3.1 Distribution Target

All migrated artifacts are published to **GitHub Packages** (`https://maven.pkg.github.com/Onbe/`) via the `github-packages-deploy` Maven profile declared in `prepaid-parent`. This is the internal Maven artifact registry for the Onbe platform.

### 3.2 Consuming Projects

The migrated artifacts are consumed by services in the Onbe portfolio that require Jakarta EE 10 compatibility:
- `ivr-ws_API` (`ivrapi-ws` module) — consumes `jakarta-axis`, `jakarta-axis-jaxrpc`, `jakarta-spring-remoting`
- `ivrintegration_API` — likely consumes `jakarta-axis` and `jakarta-axis-jaxrpc`
- Any service that previously depended on Acegi Security will consume `jakarta-acegi-security`

## 4. No Runtime Data, PII, or CDE Scope

Because `jakarta-migrator` runs exclusively at Maven build time:

- There is **no runtime data** of any kind.
- There is **no PII**, cardholder data (CHD), or Sensitive Authentication Data (SAD) processed.
- The tool is **outside PCI DSS CDE scope** entirely — it produces build artifacts, not payment flows.
- There are **no database schemas**, no connection strings, no data models.
- There is **no logging of financial data** (there is no financial data to log).

## 5. Artifact Integrity Considerations

While there is no runtime data risk, the artifact output carries **supply chain integrity** considerations:

- The Eclipse Transformer may silently fail to transform some class files (e.g., classes that use reflection-based `javax.*` string references like `Class.forName("javax.servlet.ServletContext")`). These would produce syntactically valid but functionally broken migrated JARs.
- Transformed JARs contain no source provenance metadata by default. There is no SHA-256 checksum verification of the source JAR before transformation.
- GitHub Packages provides basic package integrity via Maven checksums (`.sha1`, `.md5` files generated at publish time).

**Recommendation**: Add a Maven Enforcer rule or a test module that verifies no `javax.*` references remain in the transformed artifact output. The Eclipse Transformer plugin supports a `--verify` mode that can confirm transformation completeness.

## 6. Summary

`jakarta-migrator` has no data architecture in the traditional sense. Its "data" is compiled Java bytecode — JAR files consumed from Maven repositories and re-published after namespace transformation. The entire system is stateless, builds only, and carries no compliance scope regarding financial data or PII. The relevant data governance concern is artifact supply chain integrity: ensuring that the transformation applied to each upstream library is complete and correct before the migrated artifact is consumed by production payment services.
