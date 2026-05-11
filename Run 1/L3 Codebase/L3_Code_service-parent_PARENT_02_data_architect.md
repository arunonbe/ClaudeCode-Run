# Data Architect View — service-parent_PARENT

## Data Models

service-parent_PARENT (`com.parents:service-parent:9.0.1-SNAPSHOT`) is a Maven parent POM only. It contains no application source code, no Java classes, and no data models. Its sole function is to provide shared Maven build configuration (plugin versions, repository settings, dependency management) for all Gen-1 and Gen-2 service libraries and applications that inherit from it.

The data architecture of this artifact is therefore entirely meta — it defines the build-time framework within which data models in child projects are governed.

## Sensitive Data Handled

None. As a parent POM, service-parent_PARENT does not process, store, transmit, or receive any data at runtime. It is a build artifact only.

However, the parent POM has indirect data governance implications:

- **Dependency management**: The parent POM governs which versions of shared libraries (Spring, logging, JDBC drivers) are available to child projects. EOL library versions inherited from this parent expose child projects to CVEs that could compromise data protection.
- **Repository configuration**: The parent POM references the internal Nexus repository at `http://d-na-stk01.nam.wirecard.sys:8080/nexus/` (Wirecard/Northlane infrastructure). If this hostname is no longer resolvable, child project builds will fail. Unencrypted HTTP is used for the repository URL — artifact downloads over HTTP are vulnerable to MITM attacks.
- **Codehaus Snapshots repository**: The parent POM configures the `http://snapshots.repository.codehaus.org/` plugin repository (Codehaus is defunct since 2015). Attempts to resolve plugins from this URL will fail silently or with network errors.

## Encryption and Protection Status

Not applicable as a runtime artifact. Build-time considerations:

- Repository URL uses HTTP (not HTTPS) — vulnerable to supply chain attacks
- Codehaus repository URL is dead — no longer serves artifacts
- No checksum or signature verification configured for artifact downloads beyond Maven defaults

## Database Schemas

None — parent POM only.

## Data Flows

None at runtime. At build time:

```
Maven build (child project)
  → service-parent_PARENT (POM inheritance)
    → Nexus (d-na-stk01.nam.wirecard.sys) — dependency resolution
    → Codehaus Snapshots (defunct) — plugin resolution (fails)
```

## Retention Concerns

Not applicable. Build artifacts (POM files) are versioned in the Maven repository and subject to the repository's retention policy.

## PCI DSS Data Storage Compliance

Not directly applicable. Indirect compliance implications:

- **PCI DSS Requirement 6.3.3** (all system components are protected from known vulnerabilities): The parent POM's dependency management governs which library versions child projects use. If the parent POM does not enforce minimum secure versions of transitive dependencies (e.g., old Spring versions, old JDBC drivers), child projects in the CDE may inherit vulnerable libraries.
- **PCI DSS Requirement 6.4.1** (public-facing web applications protection): The parent POM's build plugin configuration affects how WAR/JAR artifacts are assembled. Misconfigured build plugins could include development dependencies or test credentials in production artifacts.
- **Supply chain risk**: HTTP-only Nexus repository and defunct Codehaus repository in the POM represent supply chain risks. A MITM attacker on the build network could substitute malicious artifacts for legitimate ones.
