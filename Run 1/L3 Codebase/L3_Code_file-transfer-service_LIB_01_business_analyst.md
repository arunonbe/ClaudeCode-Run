# Business Analyst Report — file-transfer-service_LIB

## 1. Executive Summary

`file-transfer-service_LIB` is a Java-based batch library that provides secure SFTP file exchange between Onbe's (formerly Citi Prepaid / Northlane) internal card-program platforms and external partners including card bureaus, processors, and content-distribution infrastructure. The library originated under the `com.citiprepaid.process` package namespace and is packaged as a standalone executable JAR (`FileTransferService`). It is version-controlled on GitLab under `northlane/development/application-development/libraries/file-transfer-service` and is currently at version `1.0.1-SNAPSHOT`.

The service acts as an automated, scheduled process responsible for bi-directional movement of program files — requests, replies, errors, exceptions, reports, business reports, program materials, and status files — across SFTP endpoints and local file shares. It is a foundational infrastructure component in Onbe's prepaid card processing pipeline.

---

## 2. Business Capabilities

### 2.1 Core Capabilities

| Capability | Description |
|---|---|
| SFTP inbound pull | Downloads files from a remote SFTP server to a local file share |
| SFTP outbound push | Uploads files from local file share to remote SFTP server |
| Folder-type routing | Routes files based on folder type: REQUEST, HIERARCHYREQUESTS, REPLY, ERROR, EXCEPTION, REPORTS, BUSINESSREPORTS, BUSINESSPGMMAT, STATUS |
| xContent automation | Secondary operational mode for distributing content packages to Web Box servers and triggering re-indexing workflows |
| Exception recovery | Queries a database for previously-interrupted transfers (status = "processing") and retries or cleans them up |
| Concurrent processing | Multi-threaded execution pool allows parallel folder-type processing |

### 2.2 Folder-Type Business Meanings

The `FolderType` enumeration (referenced in `FileTransferProcessMain.java` lines 181–296) defines nine distinct business data flows:

- **REQUEST**: Card program order or request files sent to the processor (pull from SFTP server)
- **HIERARCHYREQUESTS**: Hierarchical program structure requests (pull from SFTP server)
- **REPLY**: Processor acknowledgment or fulfillment responses (push to SFTP server or retrieve)
- **ERROR**: Files that encountered processing errors at the processor
- **EXCEPTION**: Files that raised business exceptions (exception codes include 14012, 14011, 14003 per `configuration.properties` line 91)
- **REPORTS**: Standard operational and settlement reports from the processor
- **BUSINESSREPORTS**: Client-facing business intelligence reports
- **BUSINESSPGMMAT** (Program Materials): Card design and program marketing materials
- **STATUS**: Program status update files

### 2.3 xContent Flow

A secondary mode (`xContent` argument at startup, `FileTransferProcessMain.java` lines 43–51) automates the distribution of content packages:
1. Connects to multiple remote "Web Box" servers via SFTP
2. Transfers package folders to each Web Box
3. Moves packages locally to a `[reIndex]` folder for content indexing
4. Deletes the original package from the `[content]` folder after successful transfer

This flow supports the xContent/xPlatform web content management system used by Onbe's cardholder-facing web applications.

---

## 3. Business Processes Supported

### 3.1 Card Order Fulfillment

The REQUEST and REPLY folder processing drives the lifecycle of card order fulfillment files exchanged with card bureau partners (Citi Prepaid infrastructure, referenced via SCM URL and parent POM `service-parent` version 8, `pom.xml` lines 4–8).

### 3.2 Dispute and Exception Management

ERROR and EXCEPTION folders carry files related to processing failures, disputed transactions, and exception conditions. The exception recovery routine (`processExceptions()`, `FileTransferProcessMain.java` lines 580–629) queries the `sftp_process_status` database table for records in "processing" state that were not completed in a prior run, enabling at-least-once delivery semantics.

### 3.3 Financial Reconciliation Files

REPORTS and BUSINESSREPORTS folders carry settlement and reconciliation data files. These files are critical for financial close processes and directly support Onbe's SOX control environment for accurate revenue and expense recognition.

### 3.4 Program Material Distribution

The BUSINESSPGMMAT folder type handles card design artwork and marketing materials, supporting Onbe's card issuance operations.

---

## 4. Regulatory Relevance

### 4.1 PCI DSS

This service is directly relevant to PCI DSS v4.0.1 requirements because it transfers files that may contain cardholder-related data (program IDs, card order files, processor reports) between network zones:

- **Requirement 4.2** (Protect PAN during transmission over open networks): The service uses SSH/SFTP (JScape library `jscape` version 9.3.21, `pom.xml` line 153) which encrypts data in transit. However, the transport-layer encryption is only as strong as the key management practices.
- **Requirement 8.2/8.3** (User authentication): Three authentication modes are supported — password (`USERPWD`), private key (`KEY`), and private key with passphrase (`KEYPASS`) — per `Configuration.java` lines 34–36 and `FileTransferProcessMain.java` lines 107–123.
- **Requirement 9.4** (Protecting media): The file archive path (`archivePath`) and local path configurations define where program data files are stored on-disk.
- **Requirement 12.3** (Risk assessment): The exclusion lists (`excludefolders`, `excludeReplyFolder`, etc., `configuration.properties` lines 76–86) represent manual risk-based decisions about which program folders are excluded from processing.

### 4.2 NACHA / Reg E

The xContent flow and the STATUS folder type carry operational status updates that may affect ACH-linked cardholder accounts, making this service tangentially relevant to NACHA rules on timely processing and Reg E error resolution timelines.

### 4.3 Data Retention

The `SftpProcessStatusDTO` (`db/SftpProcessStatusDTO.java`) records include `datecreated` timestamps and processing state, forming an audit trail of all file movements. This is relevant to Onbe's record-keeping obligations under GLBA and PCI DSS Requirement 10.

---

## 5. Business Stakeholders

- **Card Operations** — depends on REQUEST/REPLY flows for order file delivery
- **Finance / Accounting** — depends on REPORTS/BUSINESSREPORTS for reconciliation
- **IT Infrastructure / Platform Engineering** — owns deployment and scheduling of the batch process
- **Compliance** — depends on exception recovery and audit trail for PCI DSS evidence
- **xPlatform / Content Management** — depends on xContent flow for website updates

---

## 6. Operational Model

The service is a standalone batch executable invoked by an external scheduler (cron or Windows Task Scheduler, inferred from the hard-coded `D:\c-base\config\FileTransferService\` path in `Configuration.java` line 93). It runs to completion and exits with code `0` (success) or `1` (failure). There is no daemon or listening socket. The process is intended to be run on a schedule, sweeping all folder types in sequence per run cycle.

---

## 7. Known Gaps and Business Risks

1. **No event-driven trigger**: The service is purely batch/scheduled. There is no mechanism for real-time alerting when a file arrives or fails.
2. **Hard-coded environment references**: Configuration paths reference `D:\c-base\` which ties execution to a specific Windows host.
3. **Single-server SFTP endpoint**: `configuration.properties` line 40 shows a single `remoteServer=169.171.30.166` IP address with no failover or load balancing.
4. **No message-level encryption**: Files are transferred via SFTP (transport encryption) but there is no evidence of payload-level encryption (e.g., PGP/GPG) for the file contents themselves — a PCI DSS concern for any files containing cardholder data.
