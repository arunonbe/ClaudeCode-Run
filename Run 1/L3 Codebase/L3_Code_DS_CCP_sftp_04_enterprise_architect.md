# Enterprise Architect Report — DS_CCP_sftp

## Platform Generation Classification

**Generation: Gen-2 (Wirecard/Northlane — SSIS-based ETL infrastructure)**

Evidence:
- Product version `14.0.3002.113` places this in SSDT for Visual Studio 2017 toolchain — Wirecard-era tooling
- Creator: `WIRECARD\van.nguyen2` (embedded in `SFTP.dtproj` project metadata)
- All SFTP endpoint references are Wirecard-branded hostnames: `sftp-qa.nam.wirecard.com`, `sftp.wirecard.com`, `sftp.amer1.wirecard.com`
- SSISDB folder path `wdnam-ccp-etl` — Wirecard NAM CCP ETL namespace
- Creation date in project file: `2019-06-06` — mid-Wirecard era

This is a **shared infrastructure component** built by the Wirecard North America Data Services team to provide a reusable SFTP abstraction, avoiding duplication of connection management logic across each individual CCP ETL package.

## Role in Overall Payments Architecture

DS_CCP_sftp is a **platform utility layer** — it does not implement business logic but provides the transport mechanism for the entire CCP ETL ecosystem's external file exchange:

```
┌────────────────────────────────────────────────────────────┐
│                   EXTERNAL CONNECTIVITY LAYER              │
│                                                            │
│  External FIS SFTP ──────► DS_CCP_sftp ────► ETL Landing  │
│  (FIS processor)            (Receive.dtsx)   (C:\ETL\In\) │
│                                                            │
│  Mastercard Files ──────────────────────────────────────►  │
│  (card network)                                            │
│                                                            │
│  ETL Output Zone ──────► DS_CCP_sftp ────► sftp.wirecard  │
│  (C:\ETL\Out\)           (Send.dtsx)       .com (Sunrise) │
│                                                            │
│                                          sftp.amer1        │
│                                          .wirecard.com     │
│                                          (WEP/client)      │
└────────────────────────────────────────────────────────────┘
```

The SFTP project is consumed as a sub-project by:
- `DS_CCP_wired-caching\Receive_SFTP.dtsx` — inbound GP file retrieval
- `DS_CCP_ccp-export\oas_export_*.dtsx` — outbound OAS report delivery
- `DS_CCP_wired-output\send_client_sftp.dtsx` and `send_wep.dtsx` — outbound WIRED report delivery
- Any future CCP ETL package requiring SFTP I/O

## Dependencies on Other Repos and Services

| Dependency | Direction | Notes |
|---|---|---|
| DS_CCP_ods (ODS.dbo.SFTPHosts) | Reads | Runtime SFTP configuration at package execution |
| DS_CCP_wired-caching | Consumed by | References this project's patterns (Receive_SFTP.dtsx) |
| DS_CCP_wired-output | Consumed by | References Send pattern (send_client_sftp.dtsx, send_wep.dtsx) |
| DS_CCP_ccp-export | Consumed by | OAS export SFTP delivery |
| SSISDB on p-db09 | Deployment target | Project deployed to `wdnam-ccp-etl\SFTP` catalog folder |
| `sftp-qa.nam.wirecard.com` | External | Wirecard QA SFTP (hardcoded default) |
| `sftp.wirecard.com` | External | Wirecard production SFTP (OAS delivery target) |
| `sftp.amer1.wirecard.com` | External | Wirecard Americas SFTP (WEP delivery target) |
| FIS SFTP servers | External | Inbound file source |

## Architectural Assessment

### Strengths
1. **Reusability**: Centralising SFTP logic in a shared project avoids code duplication across 10+ CCP packages.
2. **Project Deployment Model**: Modern SSIS deployment pattern enabling centralised credential management via SSISDB environments.
3. **DontSaveSensitive protection level**: Credentials are not accidentally committed in package files.
4. **Parameterisation**: All connection attributes (host, port, credentials, paths) are fully parameterised — no hardcoded connections.

### Weaknesses
1. **Only two packages**: The entire SFTP capability is in just `Send.dtsx` and `Receive.dtsx`. If a new transfer pattern emerges (e.g., batch download with checksum validation, or retry logic), the monolithic packages must be modified or new ones created alongside.
2. **No component versioning**: The project has no version history mechanism beyond Git commits. Packages that depend on this project are implicitly coupled to whatever version is deployed in SSISDB.
3. **No schema contract**: There is no formal interface definition for how consuming packages should call Send/Receive. Parameters can change between deployments, breaking callers.

## Migration Complexity for Modernisation

### Complexity: MEDIUM

1. **SSIS → Azure Data Factory**: Microsoft Azure Data Factory v2 has native SFTP connectors. Migration would involve:
   - Creating ADF Linked Services for each SFTP endpoint (replacing SSISDB environments)
   - Creating ADF Copy Activities replacing the SSIS data flow
   - Migrating SSISDB sensitive variable values to Azure Key Vault references
   - Updating all consuming pipelines from SSIS package references to ADF activities

2. **Credential migration to Azure Key Vault**: The SSISDB-stored SFTP passwords and passphrases should be migrated to Azure Key Vault, with ADF Linked Services using Key Vault secret references. This aligns with PCI DSS requirements for cryptographic key management.

3. **ETL server filesystem migration**: The `C:\ETL\In\` and `C:\ETL\Out\` paths must be migrated to Azure Blob Storage or SFTP-to-Blob landing zones in a cloud migration. This requires reconfiguring all downstream package references to paths.

4. **Wirecard SFTP endpoint migration**: The Wirecard SFTP endpoints (`sftp.wirecard.com`, `sftp.amer1.wirecard.com`) need to be validated as active Onbe-managed infrastructure or replaced with current Onbe equivalents. This is a **blocking dependency** for any cloud migration.

### Blockers
- Active Wirecard SFTP endpoint dependency (must be migrated to Onbe-managed SFTP first)
- Multiple consuming SSIS projects (DS_CCP_wired-caching, DS_CCP_wired-output, DS_CCP_ccp-export) must be updated simultaneously
- FIS inbound file delivery: FIS must be notified of new SFTP endpoint details for file delivery
