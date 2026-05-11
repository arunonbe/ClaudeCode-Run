# onbe_common_framework — Enterprise Architect View

## Strategic Role

`onbe_common_framework` is Onbe East's shared front-end platform library. In enterprise architecture terms it is a **horizontal capability layer** — a reusable foundation that multiple product teams consume rather than building independently. This pattern reduces total cost of ownership for common capabilities (form validation, currency formatting, cross-platform component rendering) and enforces consistency in user experience and business rule implementation across Onbe's consumer-facing applications.

The library is scoped to the `@onbeeast` npm organization namespace, published to GitHub Packages with restricted access, and maintained by the OnbeEast engineering organization. This structure reflects an inner-source model where the library is owned by a specific team but consumed across the organization.

## Position in the Platform Architecture

Based on the `onbeeast-architecture-models` C4 diagrams (analyzed separately), `Recipient Web` (`oneplatform-react_WAPP`) uses React components and REST API integration. `onbe_common_framework` likely provides the validation utilities and loading components used in that application's form flows (card activation, registration, balance inquiry).

The framework bridges:
- **Web applications** (React): `oneplatform-react_WAPP`, `clientzone_WAPP`, `scheduler_WAPP`, etc.
- **Mobile applications** (React Native): Any mobile apps in the Onbe East portfolio.
- **Cross-platform validation**: The same `validatePIN`, `isEmail`, `validatePhone` functions used in web forms can be used in Node.js backend for server-side validation consistency.

## Architecture Decisions and Patterns

### Pattern: Universal JavaScript Library Design
The library implements a universal module pattern: the same npm package works in browsers, React Native, and Node.js environments through:
1. **Conditional exports** in `package.json` (browser vs. node resolution).
2. **Environment detection** in `index.js` (checks for `window`, `navigator`, `process`).
3. **Build-time bundling** with webpack browser field overrides.

This is an established pattern for shared JavaScript libraries. The risk is complexity: three execution environments must be tested (browser, React Native, Node), and a bug in environment detection can cause the wrong code path to be loaded.

### Pattern: Changeset-Based Semantic Versioning
The Changesets workflow implements an approximation of **Conventional Commits + automated release**. Contributors declare their intent (patch/minor/major) in changeset markdown files, and the CI pipeline handles version bumping and publishing. This pattern makes version intent explicit and reviewable in pull requests, rather than being a post-merge automation that developers don't control.

### Pattern: Inner-Source Library
The `ISSUE_TEMPLATE/` and `PULL_REQUEST_TEMPLATE.md` in `.github/` formalize contribution processes for an inner-source model. This is appropriate for a shared platform library — it sets expectations for contributors from other teams.

## Technology Stack Assessment

| Component | Technology | Assessment |
|---|---|---|
| Language | JavaScript (CommonJS + ESM) | No TypeScript — limits type safety for consumers |
| Testing | Jest 29 | Current; well-suited for React and utility testing |
| Bundling | webpack | Mature; appropriate for dual browser/node builds |
| Transpilation | Babel | Standard; `@babel/preset-react` for JSX |
| Release management | Changesets | Modern, appropriate for monorepo-capable versioning |
| CI/CD | GitHub Actions | Consistent with rest of Onbe East platform |
| Static analysis | CodeQL | Appropriate for SAST |
| Lint | ESLint 8 | Current; enforces code quality |

**Missing TypeScript**: The README claims "TypeScript Support: Full type definitions included" but no `.d.ts` files are visible in the source. If type definitions are not generated in the build, consuming TypeScript applications will lack type safety for framework calls. This should be verified and TypeScript support either properly implemented or the claim removed from documentation.

## Package Publication Architecture

```
Developer creates changeset →
  PR with changeset merges to main →
    CI detects changeset →
      Publishes @onbeeast/common-framework@<current version> →
        Creates cleanup PR for consumed changesets

Consuming application teams:
  npm install @onbeeast/common-framework
  (requires GitHub PAT with read:packages scope in .npmrc)
```

The requirement for consuming teams to have a GitHub PAT with `read:packages` is a moderate friction point. Teams must:
1. Generate a personal PAT (or use a service account PAT).
2. Configure `.npmrc` in each project.
3. Manage PAT rotation.

An alternative is using GitHub Actions bot tokens for CI, but developer workstation setup remains manual. This is a standard constraint for GitHub Packages-hosted private npm packages.

## Compliance Considerations

### GDPR / CCPA / Privacy
The library handles email addresses and phone numbers in validation functions. As a pure validation library (no persistence, no network calls), it does not create, store, or transmit personal data. Its compliance posture is correct: it operates on transient form field values without retaining them.

### PCI DSS
The `validatePIN` function processes 4-digit PINs. In a PCI DSS context:
- The PIN itself is cardholder data for card-present transactions. However, in the web/mobile context, this function validates the format of a PIN entry field — the PIN value is not stored by the library.
- The consuming application must ensure PIN values are transmitted only over TLS and are never logged.
- The library's stateless design means it does not create a PCI DSS scope expansion on its own.

### Supply Chain Security
- `codeql.yml` provides SAST coverage.
- `npm audit --audit-level=moderate` provides dependency vulnerability scanning.
- No Software Bill of Materials (SBOM) generation is configured. Given Onbe's PCI DSS obligations, generating an SBOM for this library (and for applications consuming it) would support Requirement 6.3.2 compliance.

## Gaps and Recommendations

1. **TypeScript support**: Either add TypeScript source or generate `.d.ts` type declarations at build time. Remove the README claim if not implemented.

2. **Internationalization**: Extend `formatCurrency` to support multi-currency (EUR, GBP, CAD, etc.) and `validatePhone` to support international phone formats (E.164 standard) for global payouts use cases.

3. **Backup files**: Remove `.backup`, `.broken`, and `.clean` file variants from the repository. These belong in git history, not the working tree.

4. **SBOM generation**: Add CycloneDX or SPDX SBOM generation to the build pipeline for PCI DSS Requirement 6.3.2 compliance.

5. **Bus factor**: Expand the contributor base beyond 2 named individuals. Document contribution and ownership model clearly.

6. **Semantic versioning discipline**: Ensure version bumps (patch/minor/major) are correctly categorized in changesets — a breaking API change published as a patch would break consuming applications silently.
