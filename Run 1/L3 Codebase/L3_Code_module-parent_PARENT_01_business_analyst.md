# Business Analyst Report — module-parent_PARENT

## 1. Service Identity and Business Purpose

`module-parent_PARENT` is a **Maven parent POM** — not a deployable service. Its business function is purely organizational: it provides a common POM inheritance point for all Gen-2 module projects in the Onbe (formerly Wirecard/Citi Prepaid) platform. By centralizing dependency management and build configuration in a single parent POM, it reduces duplication across the many `_LIB` and `_WAPP` module artifacts that make up the Gen-2 platform.

The POM at `pom.xml` declares:
- `groupId: com.citi.prepaid`
- `artifactId: module-parent`
- `version: 7`
- `packaging: pom`
- Inherits from `com.citi.prepaid:prepaid-parent:3`

The description reads: *"Parent POM for all module projects. Mainly for documentation purposes."*

## 2. Historical Context and Provenance

The SCM URL in the POM (`scm:svn:https://d-na-stk01.nam.wirecard.sys/svn/prepaid/modules/module-parent/trunk`) confirms this POM originated in the Wirecard legacy platform, hosted on an internal SVN server. The `d-na-stk01.nam.wirecard.sys` hostname is the North America Wirecard Subversion server, predating the Onbe rebrand and the migration to Git/GitHub.

The `com.citi.prepaid` group ID traces back even further — to the Citi Prepaid era when the platform was white-labeled for Citibank's prepaid card program. This means `module-parent_PARENT` carries lineage from at least two prior ownership structures (Citi Prepaid → Wirecard → Onbe), making it one of the oldest artifacts in the repository.

## 3. Functional Scope

The POM provides no functional code — it contains:
- A single `pom.xml` with POM metadata and SCM information
- `.github/workflows/codeql-java.yml` — a CodeQL static analysis workflow targeting Java
- `.github/dependabot.yml` — automated dependency update configuration
- `src/site/site.xml` — Maven site documentation configuration (legacy, rarely used)
- `.mvn/wrapper/` — Maven wrapper configuration for consistent build tooling

Because it is a pure POM with no source code, business analysts have no direct functional domain to analyse. Its business value lies entirely in **build governance**: enforcing consistent dependency versions, compiler targets, and plugin configurations across the Gen-2 module portfolio.

## 4. Governance Role

In the Maven multi-module build hierarchy, `module-parent_PARENT` sits at a specific layer:

```
com.citi.prepaid:prepaid-parent:3  (top-level corporate POM)
    └── com.citi.prepaid:module-parent:7  (module-type projects)
            └── (child module POMs inheriting from this)
```

This contrasts with the NexPay Gen-3 hierarchy where `com.onbe.nexpay:nexpay-parent` serves the equivalent role for the new platform, and `com.parents:prepaid-parent:6.0.12` serves the role for Gen-2 services like `message-center_SVC`.

## 5. Risk Assessment

- **Version staleness**: The version is `7` — a plain integer version, consistent with the Wirecard-era versioning policy. There is no semantic versioning or SNAPSHOT lifecycle. This means changes to this POM require a version bump coordinated across all child modules.
- **Orphan risk**: If this POM is no longer actively maintained (its `src/site/` directory and SCM pointer to Wirecard SVN suggest low recent activity), child modules inheriting from it may drift from intended governance policies.
- **Cross-generation confusion**: The `com.citi.prepaid` group ID is confusing in the current Onbe context. Developers unfamiliar with the heritage may attempt to publish or resolve artifacts under this group ID in modern package registries.
- **No functional business risk**: Since this is a build artifact, the primary risk is build governance regression — an uncontrolled update to this POM could cascade breaking changes across all Gen-2 module builds.
