# Business Analyst Report — DS_CCP_sftp

## Repository Overview

DS_CCP_sftp is a **reusable SSIS project** providing generic, parameterised SFTP Send and Receive capabilities for the CCP ETL pipeline. The repository contains a Visual Studio Integration Services project (`SFTP.dtproj`, Product Version 14.0.3002.113 = SSDT for Visual Studio 2017) with two executable SSIS packages (`Send.dtsx` and `Receive.dtsx`) and a project parameter file (`Project.params`). There are no SQL scripts, stored procedures, or database schema objects. The repo's sole business function is to provide **reusable file transfer components** that other CCP ETL packages can invoke as sub-packages or templates.

## Business Processes Supported

### 1. Inbound File Delivery (Receive.dtsx)
The Receive package downloads files from remote SFTP servers to local ETL landing zones. In the CCP ecosystem, this supports:
- Receiving FIS settlement and fee files from FIS SFTP endpoints
- Receiving Mastercard network settlement files
- Receiving WDP/CCP unposted transaction export files from Wirecard processing systems
- Any future inbound file from bank partners or card networks

### 2. Outbound File Delivery (Send.dtsx)
The Send package uploads files from local ETL output directories to remote SFTP endpoints. In the CCP ecosystem, this supports:
- Sending OAS reconciliation reports to `sftp.wirecard.com` / `sftp.amer1.wirecard.com` for Sunrise Banks
- Sending WIRED client reports to client SFTP directories (referenced in DS_CCP_wired-output as `send_client_sftp.dtsx`)
- Any outbound file delivery to bank partners or external counterparties

## Parameters Defined (Project.params)

The project exposes the following parameters, configured at the SSISDB environment level per deployment:

| Parameter | Type | Default Value | Sensitive | Purpose |
|---|---|---|---|---|
| `SourceFolder` | String | `C:\ETL\In\` | No | Local input folder for inbound files |
| `ArchivedFolder` | String | `C:\ETL\Archived\` | No | Local archive folder for processed files |
| `GP_SFTP_Enable` | Boolean | `false` | No | Toggle: enable GP (Great Plains) SFTP source |
| `GP_SFTP_HostName` | String | `sftp-qa.nam.wirecard.com` | No | GP SFTP server hostname |
| `GP_SFTP_Password` | String | (empty) | **YES** | GP SFTP password — sensitive |
| `GP_SFTP_Port` | Integer | `22` | No | GP SFTP port |
| `GP_SFTP_SSHKey` | String | (empty) | No | Path to GP SSH key file |
| `GP_SFTP_SSHPassphrase` | String | (empty) | **YES** | GP SSH key passphrase — sensitive |
| `GP_SFTP_Username` | String | (empty) | No | GP SFTP username |
| `NotifyEmailAddress` | String | (empty) | No | Email address for SFTP operation notifications |
| `MailServerAccount` | String | (empty) | No | Database Mail account name for notifications |

**Key observation**: The default `GP_SFTP_HostName` value is `sftp-qa.nam.wirecard.com` — a Wirecard QA environment hostname. If deployed without overriding this value via SSISDB environment, a package execution could accidentally target the QA SFTP endpoint rather than production. This is a configuration risk.

## Data Flows

The SFTP packages themselves handle binary file movement and do not parse or transform file content. Data flows through the CCP ecosystem as follows:

```
Remote SFTP Server (FIS / Mastercard / WDP)
    ↓ (Receive.dtsx — inbound)
Local ETL Landing Zone (C:\ETL\In\)
    ↓ (Parsed by specific CCP import SSIS packages)
ODS Database (processed data)
    ↓ (Reporting / transformation)
Local ETL Output Zone (C:\ETL\Out\)
    ↓ (Send.dtsx — outbound)
Remote SFTP Server (Sunrise Banks / Client / OAS)
```

## Integration Points

| Integration Point | Direction | Purpose |
|---|---|---|
| FIS SFTP server | Inbound | Daily settlement/fee/cardholder activity files |
| Mastercard file delivery | Inbound | Network settlement files |
| WDP (Wirecard Data Platform) | Inbound | Unposted transaction files |
| GP (Great Plains) SFTP | Inbound | GP financial data for PBR cache |
| `sftp.wirecard.com` / OAS | Outbound | Sunrise Banks reconciliation reports |
| `sftp.amer1.wirecard.com` / WEP | Outbound | Client report delivery |
| Client SFTP servers | Outbound | Direct client file delivery |
| ODS.dbo.SFTPHosts | Configuration | SFTP connection parameters stored in ODS database |
| SSISDB Environment | Configuration | All sensitive credentials (passwords, passphrases) |

## Regulatory Relevance

| Regulation | Relevance |
|---|---|
| **PCI DSS Req 4.2** | Transmission of PANs over public networks must be protected. FIS cardholder activity files potentially contain PANs and are transmitted over SFTP (SSH-encrypted). SFTP provides transport encryption, satisfying PCI DSS Req 4.2.1 for in-transit protection. |
| **PCI DSS Req 8.6** | SFTP credentials (passwords, SSH keys) must be managed under individual accountability. The project uses parameterised credentials stored in SSISDB sensitive variables — this is acceptable, but the key file paths and usernames are not personalised. |
| **NACHA / Reg E** | FIS ACH settlement data transmission is subject to NACHA security requirements. SFTP with SSH key authentication meets NACHA file transmission security standards. |
| **GDPR / CCPA** | If FIS cardholder activity files contain names or account identifiers, they constitute personal data. SFTP encryption protects the data in transit but the files must be handled securely at rest in landing zones. |

## Business Rules

1. **SSH key vs. password authentication**: The project supports both password (`GP_SFTP_Password`) and SSH key (`GP_SFTP_SSHKey` + `GP_SFTP_SSHPassphrase`) authentication. SSH key authentication is the preferred pattern for server-to-server integration (more secure, no password rotation risk).

2. **Archival after transfer**: The `archivepath` parameter in `Send.dtsx` (from SFTP.dtproj project metadata) indicates sent files are archived locally after successful transmission — providing a local copy for reconciliation and reprocessing.

3. **File pattern filtering**: The `filepattern` parameter on `Send.dtsx` (`*.*` default) controls which files in the source directory are sent — allowing targeted transfer of specific file types.
