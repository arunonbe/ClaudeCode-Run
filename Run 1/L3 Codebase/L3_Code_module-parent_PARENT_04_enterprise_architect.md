# Enterprise Architect Report — module-parent_PARENT

## 1. Role in the Enterprise Architecture

`module-parent_PARENT` occupies the **governance layer** of the Gen-2 platform's build architecture. In Maven's multi-module hierarchy, it is a structural POM — one of three POM inheritance tiers in the Gen-2 stack:

```
Tier 1: com.citi.prepaid:prepaid-parent:3  (corporate root — not in this repo)
    └── Tier 2: com.citi.prepaid:module-parent:7  (THIS REPO)
            └── Tier 3: Individual module POMs (many repos)
```

This contrasts with the Gen-3 NexPay stack which has its own two-tier hierarchy:
```
com.onbe.nexpay:nexpay-parent:0.2.8-SNAPSHOT  (Gen-3 root)
    └── Individual NexPay service POMs
```

And the interim Gen-2.5 hierarchy used by services like `message-center_SVC`:
```
com.parents:prepaid-parent:6.0.12  (Gen-2.5 root)
    └── message-center_SVC root POM
```

The coexistence of three separate POM inheritance chains reflects the platform's generational evolution without a unified dependency governance strategy.

## 2. Strategic Significance

Despite being a build artifact with no runtime function, `module-parent_PARENT` has high strategic significance:

- It governs the build output quality for all Gen-2 library modules (`_LIB` repos)
- Library modules built with this parent are consumed by Gen-2 services AND potentially by Gen-3 services that bridge generations
- The Wirecard/Citi Prepaid legacy group ID (`com.citi.prepaid`) in this POM means artifacts published under this governance are not clearly branded as Onbe products

## 3. Technical Debt Assessment

| Debt Category | Description | Impact |
|---|---|---|
| Group ID namespace | `com.citi.prepaid` predates Onbe ownership | Brand confusion; potential IP/licensing audit questions |
| Integer versioning | No semantic versioning | Cannot distinguish breaking from non-breaking changes |
| SVN SCM reference | Points to Wirecard internal SVN server | Dead reference; no version history accessible |
| Parent POM version 3 | `prepaid-parent:3` is an extremely low version number | Suggests the root governance POM is ancient and may not have been updated |
| No dependency management in this POM | All management deferred to `prepaid-parent:3` | Adds an extra inheritance hop with no value |

## 4. Gen-3 Migration Considerations

`module-parent_PARENT` does **not** need to be migrated to Gen-3; it should be **sunset**. The migration strategy is:

1. Identify all active Gen-2 modules that still declare `<parent>com.citi.prepaid:module-parent</parent>`.
2. For each module being actively maintained, migrate to inheriting from `com.onbe.nexpay:nexpay-parent` (Gen-3) or `com.parents:prepaid-parent:6.0.12` (Gen-2.5 current).
3. For modules in maintenance-only mode (no active development), freeze the dependency state and do not migrate.
4. Once no active module references `module-parent:7`, archive this repository.

## 5. Compliance and Governance Observations

From an enterprise governance standpoint:
- The Wirecard-era provenance of this POM raises questions about what dependency management rules (if any) were in place at the time of the Wirecard acquisition. IP and licensing audit for artifacts governed by this POM is advisable.
- Dependabot is configured, which partially mitigates supply chain risk, but a formal Software Bill of Materials (SBOM) process is not visible.
- The `ecount.project.type=modules` property is consumed by CI infrastructure logic, meaning changes to this value would affect how build outputs are routed — an undocumented side-effect that requires CI pipeline knowledge to understand.
