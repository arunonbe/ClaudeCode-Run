# ai-guidelines — Solution Architect View

## Technical Architecture

This is a documentation-only repository with no application code. Its technical structure is:

```
.ai/                          # Core reusable guideline files
  app-guidelines.md           # Application-context template (team must customize)
  java-standards.md           # Java language coding standards
  java-spring-standards.md    # Spring Boot framework standards
  java-spring-testing-standards.md  # Testing standards for Spring projects
  security-standards.md       # Security rules for AI agents
  test-guidelines.md          # General test writing guidelines

.github/
  copilot-instructions.md     # GitHub Copilot entrypoint (references .ai/ files)

.junie/
  guidelines.md               # JetBrains Junie entrypoint (references .ai/ files)

README.md                     # Usage instructions
```

The intended architecture for a consuming project is:

- AI agent reads its entrypoint file (e.g., `CLAUDE.md`).
- Entrypoint file directs the agent to read one or more `.ai/` guideline files.
- Agent applies those guidelines when generating or modifying code.

## API Surface

None. This repository exposes no API, no HTTP endpoints, no CLI, and no programmatic interface of any kind.

## Security Posture

The repository's security posture as a codebase is minimal — it contains only Markdown files with no secrets, no credentials, and no executable code.

The security guidelines it prescribes for consuming projects (`security-standards.md`) cover:

- Credential and secret management: Never hardcode secrets; use environment variables or secret management systems; use placeholders (`YOUR_API_KEY`, `${SECRET_NAME}`, `[REDACTED]`); exclude credential patterns from version control.
- Input validation: Whitelist-based validation at all application boundaries; parameterized queries for database operations; context-sensitive output sanitization; enforce input length limits and type constraints.
- Data protection: Encryption at rest and in transit; HTTPS mandatory; GDPR and CCPA compliance.
- Error handling and logging: No sensitive data in error messages; responsible security event logging; graceful exception handling.
- Secure coding practices: Follow language/framework secure coding standards; proper resource management; use static analysis tools.

**Gaps in prescribed security posture:**
- No mention of PCI DSS-specific controls (PAN masking, tokenization, CDE segmentation, SAD prohibition).
- No mention of authentication or authorization standards (OAuth 2.0, OIDC, RBAC, JWT handling).
- No mention of dependency vulnerability scanning (OWASP Dependency-Check, Snyk, Dependabot).
- No mention of secrets scanning tools (e.g., git-secrets, truffleHog) in CI pipelines.
- No mention of OWASP Top 10 or SANS Top 25 as reference frameworks.
- `security-standards.md` ends mid-sentence in section 5 ("Use static analysis tools to detect vulnerabilities" followed by `- ` with no content), indicating the file is incomplete.

## Technical Debt

- **Incomplete security standards file:** `security-standards.md` section 5 ends with a bare list marker (`- `) and no content. The document is truncated.
- **Unfinished application template:** `app-guidelines.md` retains placeholder text throughout ("BLAH-BLAH", "DOES STUFF", "STUFF", "MORE STUFF"). Any team that forgets to customize this file will feed nonsensical context to their AI agent.
- **No entrypoint for Claude Code:** The README instructs teams to create a `CLAUDE.md` file, but no `CLAUDE.md` template is provided in the repository. Only Copilot (`.github/copilot-instructions.md`) and Junie (`.junie/guidelines.md`) have example entrypoints.
- **Duplicate entrypoints:** `.github/copilot-instructions.md` and `.junie/guidelines.md` have identical content. If agent-specific guidance diverges in the future, this duplication will cause inconsistencies.
- **No machine-readable format:** All guidelines are free-form Markdown. There is no structured schema (YAML, JSON) that could be parsed by tooling to validate compliance.

## Gen-3 Migration Requirements

Not applicable as a runtime migration. If this repository is to be evolved into a mature AI governance framework aligned with a Gen-3 platform strategy, the following additions would be required:

- PCI DSS v4.0.1-specific AI guardrails (explicit rules about PAN, CVV, SAD, CDE boundaries).
- NACHA and Reg E-specific coding rules for ACH processing services.
- OFAC/AML screening integration guidance.
- Authentication and authorization standards (OAuth 2.0/OIDC, RBAC patterns).
- Infrastructure-as-code and cloud (Azure) security guidelines.
- A distribution mechanism (Git submodule, package registry, or CI-enforced template) to replace manual file copy.
- A versioning and changelog process.
- Automated validation that consuming projects are using current guideline versions.

## Code-Level Risks

- **Truncated security file:** `security-standards.md` is incomplete. An AI agent reading this file will not receive the full intended security instruction set, potentially generating code that does not meet Onbe's security requirements.
- **Placeholder application context:** Any project that deploys with the uncustomized `app-guidelines.md` will have AI agents operating without accurate project context, increasing the risk of incorrect or non-idiomatic code generation.
- **No null-safety or type-safety in guidelines themselves:** The guideline files prescribe JSpecify `@NonNull`/`@Nullable` and `@NullMarked` usage, but there is no enforcement or self-referential consistency check.
- **Testing standards reference internal class names:** `java-spring-testing-standards.md` references `CoreControllerTests`, `SasiApplicationTest`, `SoapClientInterceptorTestsIT`, and `TestcontainersInitializer` — these appear to be Onbe-internal class names that are project-specific rather than generic patterns, reducing the portability of the template.
- **Maven settings reference:** All Maven commands reference `-s .mvn/wrapper/settings.xml`. This assumes consuming projects have a Maven settings file at this exact path, which is a project-specific assumption embedded in shared guidelines.
