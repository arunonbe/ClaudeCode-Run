# ai-guidelines — Business Analyst View

## Business Purpose

This is a documentation-only repository. It contains no deployable application, no business logic, and no data processing. Its sole purpose is to provide a reusable, shareable set of AI-agent instruction files that standardize how AI coding assistants (Claude Code, GitHub Copilot, JetBrains Junie) behave when working on Onbe Java/Spring Boot projects. The repo acts as a central source of truth for AI guardrails and coding standards that individual project teams pull into their own repositories.

## Business Capabilities

- Provides per-technology guideline files (Java, Spring Boot, security, testing) that AI agents must follow when generating or modifying code.
- Provides an application-context template (`app-guidelines.md`) that project teams customize to describe their specific service.
- Provides agent-specific instruction entrypoints: `CLAUDE.md` (Claude Code), `.github/copilot-instructions.md` (GitHub Copilot), `.junie/guidelines.md` (JetBrains Junie).
- Enforces consistent standards organization-wide by distributing one canonical set of rules rather than each team maintaining their own.

## Business Entities

There are no data entities, domain objects, or persistent records in this repository. All content is governance documentation.

## Business Rules & Validations

The following rules are explicitly encoded in the guideline documents:

- AI agents must never include actual credentials, API keys, passwords, or tokens in generated code.
- AI agents must use placeholder values (`YOUR_API_KEY`, `${SECRET_NAME}`, `[REDACTED]`) for any secrets.
- Sensitive information must be excluded from version control via `.gitignore`.
- AI agents must validate all inputs at application boundaries using whitelist-based approaches.
- All database operations must use parameterized queries or prepared statements.
- Sensitive data must be encrypted at rest and in transit; HTTPS is mandatory for all network communication.
- Sensitive data must never appear in log messages or error outputs.
- AI agents must not remove, alter, or disable correct tests simply to make a test suite pass.
- Test coverage must reach 80%; unit tests must follow the Arrange-Act-Assert (AAA) pattern.

## Business Flows

There is no runtime business flow. The intended adoption flow is:

1. A project team copies the `.ai/` directory into their own repository.
2. The team customizes `app-guidelines.md` with project-specific context (replacing the template placeholder text).
3. The team creates the appropriate agent-specific entrypoint file (`CLAUDE.md`, `.github/copilot-instructions.md`, or `.junie/guidelines.md`) that references the chosen `.ai/` files.
4. When an AI agent operates on the project, it reads the entrypoint file and the referenced guideline files before generating or modifying code.

## Compliance & Regulatory Concerns

- `security-standards.md` explicitly mandates GDPR and CCPA compliance in data protection practices.
- The security file mandates encryption of sensitive data at rest and in transit, which aligns with PCI DSS requirements relevant to Onbe as a payments processor.
- The logging standard ("Don't log sensitive information") is directly relevant to PCI DSS Requirement 3 and Requirement 10 (protection of cardholder data and audit log integrity).
- The prohibition on hardcoding credentials or secrets addresses PCI DSS Requirement 8 (identification and authentication).
- No explicit mention of NACHA, Reg E, OFAC, SOC 1/SOC 2, or NIST CSF within the guideline content — these are gaps if this repo is intended to be a comprehensive AI governance document for a PCI-regulated payments business.

## Business Risks

- **Template Not Customized:** `app-guidelines.md` still contains placeholder text ("BLAH-BLAH project", "DOES STUFF", "STUFF", "MORE STUFF"). Any AI agent pointed at this file in a real project that has not customized it will receive meaningless application context.
- **No Enforcement Mechanism:** The guidelines are advisory only. There is no tooling, linter, or CI gate to verify that teams have adopted them or that AI agents are actually following them.
- **Incomplete Compliance Coverage:** Security standards do not reference PCI DSS, NACHA, Reg E, or OFAC — all material obligations for Onbe's payments environment.
- **No Versioning Policy:** There is no changelog, versioning scheme, or deprecation process. Teams that have copied old versions of these files have no way to know that updates have been made.
- **Single Branch, No Review Process Documented:** No contribution or review process is defined in the README.
