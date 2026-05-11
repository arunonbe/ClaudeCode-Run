# Enterprise Architect — infrastructure

## Platform Generation

The `infrastructure` repository represents **Generation 1 / legacy operations** tooling. Evidence:

- No infrastructure-as-code templates (no Terraform, Bicep, ARM). Configuration management is entirely file-based and manual.
- IIS ISAPI Redirector with AJP/1.3 connector to Tomcat — a web tier architecture pattern that predates cloud-native application hosting by over a decade.
- Internal Active Directory domain `nam.wirecard.sys` — an on-premises Windows domain joined to what was Wirecard North America infrastructure, predating Onbe's acquisition.
- Legacy brand domains (`wirecard.com`, `northlane.com`) alongside the current `mypaymentadmin.com` brand indicate this infrastructure has been carried forward through multiple corporate identity transitions without replacement.
- Connection pool sizing (`connection_pool_size=200` per node × 3 nodes = 600 AJP connections per web server) and sticky session configuration represent an architecture tuned for stateful session-pinning, a characteristic of pre-cloud monolithic application tiers.

## Position in Onbe Architecture

```
Internet / CDN / Load Balancer
        │
        ▼
┌─────────────────────────────────────────────────────┐
│  Azure Windows Server VMs — IIS Web Tier            │
│  p-az-web02/08/09/10/11/13/14 (PROD)                │
│                                                     │
│  IIS ISAPI Redirector (isapi_redirect.dll)          │
│    ↓ AJP/1.3 TCP port 9127 (unencrypted)            │
│  clientzone-cluster LB                              │
│    → clientzone1 → p-az-app01.nam.wirecard.sys      │
│    → clientzone2 → p-az-app02.nam.wirecard.sys      │
│    → clientzone3 → p-az-app03.nam.wirecard.sys      │
│                                                     │
│  Application Tier (Tomcat on app servers)           │
└─────────────────────────────────────────────────────┘
        │
        ▼
  eCount Core / Database tier
```

This repository defines **the web tier entry point** for Onbe's legacy payment platform. All external client-facing traffic to `clientzone.mypaymentadmin.com`, `clientzone.northlane.com`, `csa.northlane.com`, `login.northlane.com`, and related domains passes through the IIS servers configured by these files.

## Domain Portfolio and Brand History

| Domain Pattern | Brand Era | Status Assessment |
|----------------|-----------|------------------|
| `*.wirecard.com` | Wirecard North America (pre-acquisition) | Legacy; may still serve live traffic |
| `*.northlane.com` | Northlane (post-acquisition transitional brand) | Active |
| `*.mypaymentadmin.com` | Onbe / mypaymentadmin (current brand) | Active |
| `na.citiprepaid` | CitiPrepaid North America co-brand | Active (partner arrangement) |

The presence of all three domain patterns in PROD worker configurations means this web tier must be treated as a multi-brand reverse proxy serving clients under different contract eras. Decommissioning any domain requires coordination with client relationship management to confirm no active cardholders or client portals rely on that domain.

## External Integration Dependencies

| Integration | Direction | Protocol | Files | Risk |
|-------------|-----------|----------|-------|------|
| Harland (card manufacturer) SFTP | Outbound | SFTP/SSH | `platform-certificates-keys/harland/` | CRITICAL — private key in repo |
| Titan / Northlane SFTP (card personalization) | Outbound | SFTP/SSH | `platform-certificates-keys/titan/` | CRITICAL — PROD private key in repo |
| Tomcat app servers (AJP) | Internal | AJP/1.3 TCP 9127 | `workers.properties` | MEDIUM — unencrypted internal protocol |
| Client browsers | Inbound | HTTPS (assumed TLS termination upstream) | `uriworkermap.properties` | Managed upstream |

## Coupling and Dependencies

### Upstream (what infrastructure depends on)
- **Azure Windows Server VMs**: The configuration files only have value when deployed to specific server paths. The servers must pre-exist.
- **IIS + ISAPI Redirector DLL**: `extension_uri` in `isapi_redirect.properties` points to a specific DLL path on each server.
- **Active Directory domain `nam.wirecard.sys`**: App server hostnames use this domain. Any AD domain migration or rename would require updates to all `workers.properties` files.
- **Harland and Titan SFTP endpoints**: The SFTP keys are only valid if the corresponding public keys remain registered at the remote SFTP servers (`sftp.northlane.com`, Harland SFTP host).

### Downstream (what depends on infrastructure)
- **All Onbe client-facing web applications**: ClientZone, CSA, Enrollment, Login, One Platform Hub — all depend on IIS ISAPI Redirector correctly routing to Tomcat.
- **NDM/MFT file exchange pipelines**: SFTP keys enable secure outbound file delivery to Harland (card manufacturing orders) and Titan (card personalization data).

## Architectural Risk Assessment

| Risk | Severity | Description |
|------|----------|-------------|
| Private keys in source control | Critical | PROD SFTP private key accessible to all repo readers; enables unauthorized access to card manufacturing / personalization partner systems |
| No secrets rotation evidence | Critical | Same passphrase `n0ty0u` used across PROD and QA with no documented rotation cycle |
| Manual deployment with no drift detection | High | Repository state may not reflect actual server state; no way to detect unauthorized changes on servers |
| AJP/1.3 unencrypted server-to-server | High | Session cookies, POST bodies, and request headers traverse internal network in plaintext |
| Legacy domain retention | Medium | `wirecard.com` domains create attack surface and brand confusion; decommission timeline unclear |
| AD domain dependency `nam.wirecard.sys` | Medium | Cross-company domain dependency; domain ownership continuity must be confirmed |
| No IaC | Medium | Infrastructure drift cannot be detected or remediated programmatically |

## Modernization Roadmap

### Short-term (0–3 months)
- Rotate all SFTP key pairs and remove keys from the repository.
- Enable secret scanning with push protection.
- Migrate SFTP keys to Azure Key Vault.

### Medium-term (3–12 months)
- Replace manual file copy deployments with an Ansible playbook or Azure DSC configuration enforced via Azure Automation.
- Evaluate replacing AJP/1.3 with HTTPS reverse proxy (IIS ARR or Azure Application Gateway) to encrypt server-to-server traffic.
- Formally assess and schedule decommission of all `wirecard.com` domain configurations.

### Long-term (12–36 months)
- Migrate the web tier from IIS-on-VM to Azure Application Gateway + Azure Front Door, eliminating the IIS ISAPI Redirector configuration management problem entirely.
- Migrate app tier from Tomcat-on-VM to Azure App Service or AKS, enabling managed TLS, auto-scaling, and infrastructure-as-code via Bicep.
- Consolidate brand domains under a single `onbe.com`-rooted namespace with proper redirect management.

## Compliance Posture

This repository and the infrastructure it configures carries significant PCI DSS compliance obligations:

- All domains listed route cardholder-facing web applications (ClientZone, CSA, Login). These servers are **within the CDE or directly adjacent to it**.
- The Titan SFTP connection transmits card personalization data (embossed card files). The private key in this repository is an access credential to that data pathway.
- IIS logging on these servers captures HTTP request data including session tokens, which must be protected per PCI DSS Requirement 9.4 (physical and logical protection of audit logs).
- Any practitioner with repository read access has effectively obtained the Titan PROD SFTP private key and its passphrase, representing a potential unauthorized access path to cardholder data. This must be reported to the Onbe CISO and treated as a key compromise event pending investigation.
