# onbe_common_framework — DevOps / Operations View

## CI/CD Pipeline Architecture

The pipeline is defined in `.github/workflows/ci-cd.yml` — a 1,178-line workflow that reflects significant iteration and engineering investment. It supports three triggers:
- Push to `main` (with path filters for `src/`, `test/`, `scripts/`, `package.json`, `.changeset/`)
- Pull request to `main` (same path filters)
- `workflow_dispatch` (manual with `run_type` and `force_release` inputs)

### Job Dependency Graph

```
setup (install deps, cache node_modules)
  ├── lint     (ESLint)
  ├── test     (Jest)
  ├── build    (scripts/build-simple.js)
  └── security (npm audit --audit-level=moderate)
        └── release (changeset detection + publish)
              └── notify (always runs)
```

All of `lint`, `test`, `build`, and `security` run in parallel after `setup`, with `release` gated on all four passing. This is an efficient parallel pipeline.

### Node.js Version

All jobs use `node-version: '18'` (setup-node@v4). The package.json specifies `engines.node >= 14.0.0`. Node 18 is the current LTS and is appropriate for the CI environment.

## Dependency Caching Strategy

The workflow generates a cache key from `package-lock.json` hash (line 77: `hashFiles('package-lock.json')`). The cache path is `./node_modules`. This is shared across parallel jobs via cache restore — each parallel job (lint, test, build, security) restores from the same cache key created by the `setup` job. This significantly reduces redundant `npm install` time.

## Publishing Pipeline

### Changeset Detection
```bash
find .changeset -name '*.md' -not -name 'README.md' | wc -l
```
If changesets exist, the `has-changesets` output is set to `true`, triggering the publish path.

### Publish on Push to Main
When a push to `main` contains changesets, the publish step:
1. Validates GITHUB_TOKEN format and availability.
2. Validates `publishConfig.registry` is set to `https://npm.pkg.github.com`.
3. Validates package scope format (`@owner/package-name`).
4. Runs `npm run build` to generate `dist/`.
5. Validates `dist/index.js` and `dist/browser.js` exist.
6. Runs `npm publish --registry https://npm.pkg.github.com --verbose` with retry (3 attempts, exponential backoff starting at 5s).
7. Verifies package availability with retry (8 attempts, exponential backoff starting at 3s).
8. Consumes changesets by deleting `.changeset/*.md` files.
9. Creates a cleanup PR via `gh pr create`.

### PR Validation (Dry Run)
For PRs with changesets, the workflow runs a dry-run simulation that:
1. Creates a temporary branch.
2. Runs `changeset:version` to preview version changes.
3. Runs `npm run build`.
4. Runs `npm publish --dry-run` to validate publishability without actually publishing.
5. Cleans up the temporary branch.

This comprehensive dry-run prevents publishing failures from surfacing only after merge — a sound DevOps practice.

### Retry Mechanism
The publish step implements exponential backoff retry (3 attempts: 5s, 10s, 20s gaps). This handles transient GitHub Packages API failures. However, a failed publish after 3 retries causes the workflow to `exit 1` with detailed error messages, appropriately failing the build rather than silently proceeding.

### Version Publish Verification
After a successful publish, the workflow verifies package availability with up to 8 retries (3s, 6s, 12s, 24s, 48s, 96s, 192s, 384s gaps — total ~12 minutes max). If verification times out, the workflow continues with a warning rather than failing — acknowledging that GitHub Packages propagation can be slow for private registries.

## Security Audit

`npm audit --audit-level=moderate` runs as a required CI gate. Only vulnerabilities at `moderate` severity or higher will fail the build. The `--audit-level=moderate` threshold balances security rigor with practical maintainability — low-severity advisories in transitive dependencies do not block development.

## CodeQL Static Analysis

`codeql.yml` workflow runs GitHub CodeQL analysis — static security scanning for JavaScript. This provides SAST coverage aligned with PCI DSS Requirement 6.3.2 (security vulnerability identification).

## Manual Publishing Scripts

The `scripts/` directory contains emergency publishing fallbacks:
- `scripts/manual-release.js` — invokable as `npm run publish:manual` for out-of-band releases.
- `scripts/code-checkin.js` — quick validation script for developer commits.
- `scripts/dev-workflow.js` — comprehensive local validation before creating a release PR.
- `scripts/check-published-versions.js` — queries GitHub Packages to verify published versions.

These scripts reflect the operational reality that automated publishing sometimes requires manual intervention, and they provide a documented, repeatable fallback path.

## Stale Issue/PR Management

`stale.yml` workflow automatically marks and closes stale issues and PRs. This is good housekeeping for an inner-source library.

## PR Labeling

`pr-labeler-unified.yml` automatically applies labels to PRs based on branch name patterns (feature/, fix/, chore/, etc.). This aids in changelog generation and release note quality.

## Build System

The build is implemented in `scripts/build-simple.js` (invoked as `npm run build`). It uses webpack (config in `webpack.config.js`) with:
- CommonJS output for Node.js (`dist/index.js`)
- Browser-safe output for browser (`dist/browser.js`)
- Browser field overrides for Node.js builtins (`fs: false`, `path: false`, etc.)

Babel config (`babel.config.js`) provides transpilation with `@babel/preset-env` and `@babel/preset-react`.

## Known CI Issues (Evidenced by Backup Files)

The presence of:
- `.github/workflows/ci-cd.yml.backup` — previous version of the workflow
- `.github/workflows/ci-cd.yml.broken` — a broken workflow iteration
- `test/index.test.js.backup`, `test/index.test.js.clean` — test file evolution

indicates the CI/CD setup went through several iterations before reaching its current state. The `WORKFLOW-CHANGES.md` document records the evolution. These backup files should be removed from the repository — they add noise, can confuse developers, and should not be in version control (use git history instead).

## Operational Risks

| Risk | Severity | Detail |
|---|---|---|
| Backup/broken files in repo | Low | `.backup`, `.broken` files should be removed |
| `cleanup.bat` in repo root | Medium | Windows batch script (`cleanup.bat`) — likely for local development cleanup; should not be run in CI; its presence suggests some operations require manual cleanup |
| Long verification retry loop | Low | Up to 12 minutes of verification waiting could delay pipeline feedback |
| No npm audit fail for low-severity | Low | Low-severity vulnerabilities in dependencies are silently ignored |
| Manual PR required for changeset cleanup | Low | Changeset cleanup creates a PR that must be manually merged to complete the cycle |
