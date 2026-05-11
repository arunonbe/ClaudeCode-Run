# Business Analyst Analysis — exemplar-cross-border-transfer-service_WAPP

## Important Note: Partial Clone Limitation

**This repository was cloned with a Windows MAX_PATH limitation that prevented some source files from being written to disk.** The repository contains 10 Maven modules (per `pom.xml` lines 44–55), but only a subset of source files is present in the local clone. Analysis is based on available files; conclusions about missing modules are inferred from module names, `pom.xml` dependencies, the README, and available batch module source code. All findings should be verified against the full repository in the source control system.

**Available modules (fully analysed):**
- `cross-border-transfer-service-batch` — full source present
- `cross-border-transfer-service-cambridge-client` — partial source present

**Partially or fully missing modules (inferred from pom.xml):**
- `cross-border-transfer-service-rest-controller`
- `cross-border-transfer-service-service`
- `cross-border-transfer-service-config`
- `cross-border-transfer-service-data`
- `cross-border-transfer-service-db-app`
- `cross-border-transfer-service-db-scripts`
- `cross-border-transfer-service-persistence`
- `cross-border-transfer-service-qa`

---

## Repository Overview

**Repo name:** `exemplar-cross-border-transfer-service_WAPP`
**Type:** Gen-3 reference implementation — cross-border money remittance service
**Primary language:** Java 8 (pom.xml line 33; note README says Java 11 — mismatch)
**Framework:** Spring Boot 2.5.2 + Spring Batch + Spring Cloud OpenFeign + Resilience4j
**Build:** Maven multi-module (10 modules, `pom.xml` lines 44–55)
**Partner:** Cambridge Payments (FX and cross-border remittance provider)
**Coverage threshold:** 90% instruction/class/line/branch/method (`pom.xml` lines 35–41)

---

## Business Purpose

This service implements **cross-border money remittance** — the capability for Onbe's prepaid card clients to send funds internationally via the Cambridge Payments network. It is described in `README.md` as "responsible for handling cross border money remittance."

### Business Workflow

The service handles the full remittance lifecycle:

1. **Remitter management** — Create/edit the sending party (`createEditRemitter`, `CambridgeClient.java` line 66).
2. **Beneficiary management** — Create/edit the receiving party (`createEditBeneficiary`, line 72).
3. **Spot rate quoting** — Request a live FX exchange rate from Cambridge (`getSpotRate`, line 39).
4. **Deal booking** — Lock the FX rate (`bookDeal`, line 48).
5. **Transfer instruction** — Execute the remittance (`instructDeal`, line 78).
6. **Cancellation** — Request and book deal cancellations (`requestCancellation`, `bookCancellation`, lines 54–64).

### Batch Jobs

The Spring Batch module provides automated batch processing:
| Job | Direction | Purpose |
|-----|-----------|---------|
| `import-cambridge-recon-file` | Inbound (Cambridge → Onbe) | Import reconciliation file from Cambridge via SFTP |
| `import-cambridge-reject-file` | Inbound (Cambridge → Onbe) | Import rejected transfer records from Cambridge via SFTP |
| `publish-cambridge-recon-file` | Outbound (Onbe → Cambridge) | Publish reconciliation data to Cambridge via SFTP |
| `publish-cambridge-reject-file` | Outbound (Onbe → Cambridge) | Publish rejected records to Cambridge via SFTP |
| `automatic-rate-cancellation` | Internal | Automatically cancel FX rate bookings that have expired |

The directory `cross-border-transfer-service-batch/src/main/rpm/application/scripts/` contains shell scripts for each batch job, consistent with RPM-based deployment on Linux (pre-Kubernetes).

### Partner Integration: Cambridge Payments

Cambridge (`CambridgeClient.java`) is a Feign HTTP client that calls Cambridge's API with two-level authentication:
- **Partner-level token** — obtained via `getPartnerToken()` with Cambridge partner credentials.
- **Client-level token** — obtained via `getClientToken()` using the partner token; scoped to a specific client/brand.

All Cambridge API calls include `CMG-AccessToken` header. This is an OAuth-like token exchange pattern.

### Regulatory Relevance

Cross-border money transfers are subject to:
- **OFAC sanctions screening** — the service must not transfer funds to sanctioned individuals or countries. No evidence of sanctions screening in the available source; this may be in the missing REST/service modules.
- **FinCEN/BSA** — international wire transfers trigger AML/CTF obligations.
- **Reg E** — consumer protection for electronic fund transfers.
- **FATF travel rule** — for transfers above threshold, remitter and beneficiary identity data must accompany the transfer.
- **GLBA** — PII of remitters and beneficiaries.

### Business Risk Observations

| Risk | Detail |
|------|--------|
| Partial clone — missing REST/service layers | Cannot fully assess business logic; reconciliation and AML checks may be in missing modules |
| `automatic-rate-cancellation` batch | FX rate cancellation must be reliable; failure to cancel expired rates incurs financial cost |
| Cambridge API dependency | Service availability depends on Cambridge uptime; circuit breaker (Resilience4j) is included in dependencies |
| Hardcoded bootstrap credentials | `bootstrap.yml` contains `username: application / password: [REDACTED — rotate immediately]` for the config server (see Security section) |

---

## Stakeholders

| Role | Concern |
|------|---------|
| Programme Managers | Which clients/brands can initiate cross-border transfers |
| Compliance / AML | OFAC screening, AML CTF, FATF travel rule |
| Operations | Batch job monitoring, reconciliation accuracy |
| Cambridge Payments | Integration SLA, API changes |
| Finance | FX rate accuracy, deal booking confirmation |
| Cardholders | Transfer accuracy, status notifications |
