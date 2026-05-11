# Enterprise Architect Analysis — EstimationChatApp-_MISC

## Repository Overview

**Repo:** `EstimationChatApp-_MISC`
**Classification:** Internal POC / developer tooling — not a production service
**Platform generation:** N/A (sandbox; does not fit the Gen-1/2/3 production service taxonomy)
**Technology stack:** Node.js + Express + Socket.IO + Docker

---

## Enterprise Architecture Position

### Application Landscape Classification

`EstimationChatApp-_MISC` sits outside Onbe's core payment platform entirely. It belongs to the **developer productivity tooling** category — specifically, Agile ceremony support tooling. It has no connection to the Cardholder Data Environment (CDE), no payment processing capability, and no PII beyond team names.

In an enterprise application portfolio, this would be classified as:
- **Category:** Internal tools
- **Tier:** Non-production (development/internal)
- **Data classification:** Public (team names only)
- **Business criticality:** Low (estimation sessions can be conducted without the tool)

### Technology Stack Assessment

| Dimension | This Repo | Onbe Gen-3 Standard |
|-----------|-----------|---------------------|
| Runtime | Node.js 15 (EOL) | JVM / Node.js 18+ |
| Framework | Express + Socket.IO | Spring Boot / Next.js |
| Deployment | Docker (broken) | Kubernetes |
| CI/CD | CodeQL only | Full pipeline |
| Auth | `.env` team codes | Corporate SSO (OAuth2/OIDC) |
| Persistence | None | PostgreSQL / SQL Server |
| Monitoring | None | Prometheus + Grafana |

The technology choices (Node.js, Express, Socket.IO) are modern and appropriate for a real-time collaboration tool. The deficiencies are all in the operational and security hardening dimensions, not the fundamental technology selection.

---

## Strategic Architecture Assessment

### 1. Make vs. Buy vs. SaaS

Before investing any engineering effort in hardening this application, the enterprise architecture team should evaluate the make/buy decision:

| Option | Examples | Cost | Effort |
|--------|---------|------|--------|
| Continue with this tool (hardened) | This repo | Low $ | Medium engineering |
| Free SaaS planning poker | PlanITpoker, PointingPoker | Free | Zero engineering |
| Jira Planning Poker plugin | Atlassian Marketplace | Low $ | Minimal setup |
| Commercial Agile tools | Miro, TeamRetro | Medium $ | Low engineering |

Given that free and low-cost alternatives exist, the enterprise architecture recommendation is to **replace this tool with a SaaS alternative** rather than invest engineering effort in production-hardening a custom application.

### 2. `.env` in Source Control

The presence of `.env` in the repository and committed to Git history is a **software development practice anti-pattern** that warrants attention at the enterprise level. While the values in this `.env` are not sensitive payment data, the same pattern — if applied to production services — could result in credentials, API keys, or database passwords being committed to source control.

**Enterprise recommendation:** Enforce a `pre-commit` hook (e.g., via `detect-secrets` or `gitleaks`) across all Onbe repositories to prevent credential files from being committed. This aligns with PCI DSS v4.0.1 Req 3.3 and Req 6.3.

### 3. North Lane / TCS Contractor Artefact

The `"author": "TCS"` field in `package.json` indicates this was built by Tata Consultancy Services contractors. The `_MISC` suffix and the `north-lane-white.png` image in `assets/images/` confirm it was created during the North Lane brand era.

From an enterprise governance perspective, contractor-authored code in the repository should be:
- Reviewed for IP rights (contractor agreement coverage).
- Assessed for whether it remains maintained or is orphaned.
- Archived if it is no longer actively used.

### 4. Brand Asset in Repository

`assets/images/north-lane-white.png` — a North Lane logo — is included in the repository. Post-Onbe-rebranding, this asset should be updated or removed to prevent brand confusion in any internal deployments.

---

## Recommendations

1. **Evaluate replacement** — assess whether a free SaaS planning poker tool meets the team's needs before investing in this application.
2. **If retained** — implement SSO authentication (replace `.env` team codes with Onbe's corporate identity provider), add HTTPS, fix the Dockerfile, and add a process manager.
3. **Archive if unused** — if the application is not actively deployed or used, archive the repository to reduce maintenance overhead.
4. **Enterprise-wide `.env` governance** — use this finding as a catalyst for enforcing `detect-secrets` or `gitleaks` pre-commit hooks across all Onbe repositories.
5. **Update brand assets** — replace `north-lane-white.png` with current Onbe branding.
