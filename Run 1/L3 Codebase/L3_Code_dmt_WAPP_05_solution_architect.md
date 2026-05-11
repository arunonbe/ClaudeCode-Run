# Solution Architect Report — dmt_WAPP

## Architecture Summary
The repository is a **binary artefact store** for a Gen-1 Excel VBA application. There is no source code in the traditional sense — only `.xlsm` binary containers and a README. The architecture is:

```
[User Desktop]
  Excel + VBA (Data Management Tool - Production.xlsm)
    │  Direct ODBC/ADODB connection
    └─► [RiskDB — SQL Server on-premises]
```

The link-file (`DMT Production Copy Link.xlsm`) acts as a bootstrap/updater:
```
User runs link file → Downloads .xlsm from RiskDB file share → Opens in Excel
```

## API Surface
- **None.** There is no REST, SOAP, or RPC API. All data access is via direct SQL from VBA.

## Security Architecture
| Control | Present | Notes |
|---|---|---|
| Authentication | Implied (Windows Auth to SQL) | Not visible in repo; inferred from firewall/permission model |
| Authorisation | Firewall + SQL permissions | No RBAC artefact visible |
| Transport encryption | Unknown | TLS/SSL for SQL Server not confirmed in repo |
| Macro signing | Unknown | `.xlsm` files not verified as digitally signed |
| DLP | None | No controls preventing data exfiltration from Excel |
| Audit logging | None in repo | Depends entirely on SQL Server audit |

## Technical Debt
| Item | Severity |
|---|---|
| VBA application logic stored as binary blob in Git | Critical |
| No SDLC controls (no build, no test, no pipeline) | Critical |
| OPTIC application shares repository with DMT — no separation of concerns | Medium |
| `.gitignore` is Visual Studio template — suggests original intent was different | Low |
| Confluence docs at former brand domain (`northlane.atlassian.net`) | Low |

## Gen-3 Migration Assessment
| Dimension | Current State | Target State |
|---|---|---|
| UI | Excel VBA desktop | Web (Vue.js — see dmt-web_WAPP) |
| Backend | Direct SQL on RiskDB | Flask REST API + MongoDB (see dmt-web_WAPP) |
| Auth | Windows/SQL firewall | JWT + bcrypt (dmt-web_WAPP) |
| Deployment | Manual file copy | Docker Compose (short term); container orchestration (target) |
| Distribution | Link-file self-update | Browser (zero-install) |

**Key migration risk**: The RiskDB SQL schema and VBA business logic are not available in any repository. Migration to Gen-3 requires a discovery and reverse-engineering phase before any code can be written.

## Code Risks
- **`Data Management Tool - Production.xlsm`** (2,881,836 bytes): Large binary. Risk of embedded hardcoded credentials, connection strings, or sensitive data caches inside the VBA project. Must be audited with `olevba` or equivalent before any compliance attestation.
- **`OPTIC - Production.xlsm`** (1,353,218 bytes): Same risk profile as above.
- **`DMT Production Copy Link.xlsm`** (39,698 bytes) and **`OPTIC Production Copy Link.xlsm`** (39,222 bytes): Smaller bootstrappers — still warrant macro audit for hardcoded server paths and credentials.
- No unit tests, integration tests, or static analysis tooling of any kind.
