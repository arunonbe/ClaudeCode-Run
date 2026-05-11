# Data Architect Report — file-transfer-service_LIB

## 1. Overview

This report describes the data entities, file formats, data classification, and data-at-rest/in-transit posture of the `file-transfer-service_LIB` library.

---

## 2. Data Entities

### 2.1 Database Entity: sftp_process_status

The sole relational entity tracked by this service is the `sftp_process_status` table, accessed via `SftpProcessStatusDaoImpl.java`. The DTO mapping is in `SftpProcessStatusDTO.java`:

| Column | Java Field | Type | Description |
|---|---|---|---|
| `id` | `id` | `long` | Auto-generated primary key |
| `hostname` | `hostname` | `String` | Source/destination host name or "Fileshare" |
| `filepath` | `filepath` | `String` | Remote or local directory path |
| `filetype` | `filetype` | `String` | Folder type (REQUEST, REPLY, etc.) |
| `filename` | `filename` | `String` | File name |
| `programid` | `programid` | `String` | 8-digit card program identifier |
| `processstatus` | `processstatus` | `String` | "processing" or "processed" |
| `datecreated` | `datecreated` | `Date` | Timestamp of record creation |

This table is in the `jobsvc_database` schema, accessed via a Director-configured DBCP datasource defined in `spring.xml` (lines 22–33). The connection agent and database name are injected from `db-config.properties` and `director-client.properties` (referenced in `spring.xml` lines 10–11).

SQL operations performed (`SftpProcessStatusDaoImpl.java`):
- **SELECT**: Query files in "processing" state (line 44): `select id ,hostname , filepath, filetype , filename , processstatus, programid, datecreated from sftp_process_status where processstatus = ?`
- **INSERT**: Record new file transfer state (line 56): `insert into sftp_process_status ( hostname , filepath, filetype , programid, filename , processstatus ) values ( ? , ?, ?, ?, ?, ? )`
- **UPDATE**: Update processing status by id (line 93): `update sftp_process_status set processstatus = ? where id = ?`
- **DELETE**: Remove completed records (line 128)

### 2.2 In-Memory / Runtime Entities

The `Utility` class (referenced throughout `FileTransferProcessMain.java`) maintains static/shared state:
- `SFtpConnection` reference (shared across threads via `Utility.getSFtpConnection()` / `Utility.setSFtpConnection()`)
- `remoteDirList` — list of remote program-ID directories
- `localDirList` — list of local program-ID directories
- `hasErrors` boolean flag

### 2.3 Configuration Entities

Key configuration properties loaded from `D:\c-base\config\FileTransferService\configuration.properties` (`Configuration.java` line 93):

| Property | Sensitivity |
|---|---|
| `remoteServer` | Internal IP (169.171.30.166) — network topology disclosure |
| `remoteServerUser` | SFTP credential — HIGH sensitivity |
| `remoteServerPwd` | SFTP password — HIGH sensitivity / PCI DSS Req. 8 |
| `privateKeyFilePath` | Path to SSH private key — HIGH sensitivity |
| `privateKeyPassphrase` | Private key passphrase — HIGH sensitivity |
| `connectRemote` | Auth mode selector (KEY/KEYPASS/USERPWD) |

---

## 3. File Formats and Data in Transit

### 3.1 File Transfer Protocol

All file transfers use SFTP over SSH-2 via the JScape `jscape` library (version 9.3.21, `pom.xml` line 153). The JScape `Sftp` class from `com.jscape.inet.sftp` is used exclusively. SSH parameters are set via `SshParameters` in `SFtpConnection.java` (lines 86–88, 112–113, 136–137, 160–161).

Transfer mode is explicitly set to `setBinary()` on all upload/download operations (`SFtpConnection.java` lines 273, 317, 328, 338), preserving file integrity for binary formats.

### 3.2 File Content Classification

The service treats files as opaque binary blobs — it does not parse file content. Based on the folder types and the Onbe card-bureau context, the files transferred are expected to contain:

| Folder Type | Likely File Format | Data Sensitivity |
|---|---|---|
| REQUEST | Fixed-width or delimited card order files | HIGH — may contain cardholder names, addresses, program IDs |
| REPLY | Processor acknowledgment files | HIGH — fulfillment confirmation with card identifiers |
| REPORTS / BUSINESSREPORTS | CSV, fixed-width, or proprietary report formats | HIGH — financial amounts, program-level settlement data |
| ERROR / EXCEPTION | Error detail files | MEDIUM — processing error codes, file references |
| BUSINESSPGMMAT | Binary artwork files (likely PDF, image formats) | LOW |
| STATUS | Status update flat files | MEDIUM |

### 3.3 xContent Packages

In xContent mode, the service transfers entire directory trees (packages) to Web Box servers using `uploadDirectory()` (`SFtpConnection.java` lines 290–308). Package contents are website content assets (HTML, images, JavaScript). The xContent remote path pattern `/D:/c-base/runtime/repository/content/` (`configuration.properties` line 57) points to the xPlatform content server.

---

## 4. Data-at-Rest Classification

### 4.1 Local File Share

Files reside temporarily at `localPath=c:/temp/b2c/` (`configuration.properties` line 53) and may be archived to `archivePath=c:/temp/b2c/archive/`. These local paths on the application server represent a PCI DSS in-scope data-at-rest boundary if any transferred files contain cardholder data.

### 4.2 SFTP Server

Remote files are stored at `remotePath=/C:/c-base/runtime/fileroot/jobsvc/` on the SFTP server host `169.171.30.166`. The SFTP server represents an external-facing data store.

### 4.3 Database

The `sftp_process_status` table records file metadata (filenames, paths, program IDs). While it does not store file content, the combination of `filepath`, `filename`, and `programid` could reveal card program topology and file movement patterns — classified as internal-sensitive.

---

## 5. Data Flow Diagram (Narrative)

```
[External SFTP Server: 169.171.30.166]
         |
         | SSH/SFTP (JScape, binary mode)
         v
[Local File Share: c:/temp/b2c/]
         |
         | Java file operations (download/upload)
         v
[Application Server (Windows)]
         |
         | JDBC (Spring JdbcTemplate)
         v
[jobsvc_database: sftp_process_status table]
```

For the xContent flow:
```
[Local Content Share: \\PPNACLDDJAS3\d$\NA_SFTP\xContent\content\]
         |
         | SSH/SFTP (multi-server)
         v
[Web Box Servers (multiple)]
         |
         | Local file move
         v
[Local reIndex folder: \\PPNACLDDJAS3\d$\NA_SFTP\xContent\reIndex\]
```

---

## 6. Sensitive Data Handling Assessment

### 6.1 Credential Handling (Critical Gap)

In `SFtpConnection.java` lines 83–84, both DEBUG and INFO log statements print the SFTP hostname, username, and password in plaintext:

```java
LOG.debug("... ftpHostname, ftpUsername,ftpPassword" + " - " + ftpHostname + " " + ftpUsername + " " + ftpPassword);
LOG.info("... ftpHostname, ftpUsername,ftpPassword" + " - " + ftpHostname + " " + ftpUsername + " " + ftpPassword);
```

The comment `// remove` on the INFO line (line 84) indicates this was known to be a temporary debug statement that was never removed. This violates PCI DSS Requirement 3.4 (do not store sensitive authentication data) and Requirement 12.10 (incident response for credential exposure).

### 6.2 Properties File Credential Storage

The SFTP password `remoteServerPwd` is stored in plaintext in `configuration.properties`. The file is loaded from a filesystem path (`D:\c-base\config\FileTransferService\`) with no evidence of encryption or secrets management.

### 6.3 No Payload Encryption

Files are transferred via SFTP (transport encryption) only. There is no PGP/GPG or AES envelope encryption on the file content itself, which is a control gap if files contain PANs or other PCI-sensitive data requiring end-to-end encryption under PCI DSS Requirement 4.2.1.

---

## 7. Data Lineage

The service is a pass-through conduit: it neither creates nor transforms data, only moves it between systems. The origin data source is the remote SFTP server (external partner/processor) and the sink is the local file share (Onbe internal systems). The `sftp_process_status` table records the metadata audit trail of every file movement.
