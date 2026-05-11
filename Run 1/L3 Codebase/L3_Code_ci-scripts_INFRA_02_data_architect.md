# ci-scripts_INFRA — Data Architect View

## Data Stores

This repository does not own or manage any persistent data stores itself. It interacts with the following external data stores as a consumer or writer during pipeline execution:

| Store | Type | Access Method | Purpose |
|---|---|---|---|
| Nexus Repository Manager | Maven binary repository | HTTP/HTTPS `curl` | Source of `.war` artifact downloads (RELEASE and SNAPSHOT) |
| GitLab (gitlab.com) | Source code repository / REST API | HTTPS REST API (Bearer token) | Source of configuration/properties files (dormant path) |
| Remote Windows server filesystem | SMB file share (Windows D: drive) | `smbclient` over SMB | Destination for `.war` and config file deployments |
| Windows Registry (remote) | Key-value store | `net rpc registry` over SMB/RPC | Read Tomcat `catalina.home` path from Apache Procrun registry key |
| Windows Service Control Manager | Service state store | `net rpc service` over SMB/RPC | Read and control Tomcat service state |
| Local CI runner filesystem | Ephemeral temp directory | Shell `find`, `cp`, `fs.writeFileSync` | Intermediate download staging area (`DOWNLOAD_DIR`) |
| JSON mapping files | Flat files (JSON) | Node.js `require()` | Environment and component deployment descriptors (dormant) |
| `.properties` files | Java properties format | `properties-reader` npm package | Artifact GAV metadata for war deployments (dormant) |

## Schema & Tables

There are no database schemas or tables. The structured data formats in use are:

### gitlabMetadata.json (mapping file, schema inferred from code)
```
{
  "apiUrlPath": "api/v4",
  "projects": [
    {
      "alias": "<string>",
      "projectId": "<number>"
    }
  ]
}
```

### environment.<name>.json (mapping file, schema inferred from code)
```
{
  "name": "<environment-name>",
  "domain": "<server-domain>",
  "components": [
    {
      "name": "<componentName>",
      "serverServiceNames": ["<serviceName>", ...],
      "componentDeployments": [
        {
          "filename": "<string>",
          "serverName": "<string>",
          "fileType": "config" | "war",
          "skip": "true" | "false",
          "gitProjectAlias": "<string>",     // config type only
          "gitFile": "<relative-path>",       // config type only
          "serverFile": "<relative-path>",    // config type only
          "serviceName": "<string>",          // war type only
          "localArtifactInfo": "<relative-path>" // war type only
        }
      ]
    }
  ]
}
```

### artifactInfo properties file (schema from `deployFromNexus.sh` and `deployWar()`)
```
artifactGroup=<maven-group-id>
artifactId=<maven-artifact-id>
artifactVersion=<maven-version>
artifactPackaging=war
deploymentName=<optional-override-name>
```

## Sensitive Data Handling

- **Domain Credentials**: Active Directory domain username and password (`GL_NAM_USER`, `GL_NAM_PASSWORD`) are consumed as environment variables. They are used directly in `smbclient` and `net rpc` commands. `serverFunctions.sh` logs the password value in plain text to stdout during execution (`echo "transfer_file_to_server, ... password($password)"`). This is a confirmed sensitive data exposure in pipeline logs.
- **GitLab Bearer Token**: A credential value is embedded as a literal string in `deployFilesFromMappings.js` within the HTTPS request `headers` object. The token is present in the committed source code. Location: `deployFilesFromMappings.js`, line 187, `Authorization` header. The value is not reproduced here.
- **Git Token (CLI argument)**: `deployFilesFromMappings.js` accepts a `git token` as the 8th positional command-line argument, making it visible in process listings on the CI runner host.
- **NAM Password (CLI argument)**: `deployFilesFromMappings.js` accepts `nam_password` as the 7th positional argument; also visible in process listings.

## Encryption & Protection

- **In-transit encryption**: GitLab REST API calls in `deployFilesFromMappings.js` use `https` (Node.js `require('https')`), providing TLS encryption.
- **Nexus downloads**: `curl` calls in `nexusFunctions.sh` and `deployFromNexus.sh` do not explicitly specify HTTPS. The URL is constructed from `$SNAPSHOTS_REPO` and `$RELEASES_REPO` environment variables; whether these use HTTP or HTTPS is determined entirely by those variables at runtime. No TLS certificate validation enforcement is present in the scripts.
- **SMB transfers**: File and WAR transfers use `smbclient` over SMB. SMB protocol version and signing/encryption are not enforced by the scripts; this is dependent on system and domain configuration. SMB without signing is susceptible to man-in-the-middle attacks.
- **Credentials at rest**: No encryption at rest for credentials. They are stored as CI/CD pipeline environment variables (GitLab CI secrets), not managed by a secrets vault in this codebase.
- **No artifact integrity verification**: There is no hash/checksum or signature verification of downloaded artifacts from Nexus before deployment.

## Data Flow

```
[Nexus RELEASES_REPO / SNAPSHOTS_REPO]
        |  curl (HTTP/HTTPS)
        v
[CI Runner: DOWNLOAD_DIR (ephemeral temp)]
        |  smbclient
        v
[Target Server: D:\<catalina.home>\<service>\webapps\<artifact>.war]

[GitLab REST API]
        |  https.request (TLS)
        v
[CI Runner: DOWNLOAD_DIR/<filename> (ephemeral temp)]
        |  smbclient
        v
[Target Server: D:\<server_directory>\<filename>]

[GitLab repository: artifactInfo .properties file]
        |  read at pipeline start (local file)
        v
[deployFromNexus.sh: shell variables (GROUP, ARTIFACT_ID, VERSION, PACKAGING)]
        |
        v
[Nexus download URL construction → curl]
```

## Data Quality & Retention

- **No data validation**: Artifact coordinates (group, artifactId, version) read from `.properties` files are used without format validation.
- **No checksum validation**: Downloaded `.war` files are not hash-verified against Nexus-published checksums (`.md5`, `.sha1`).
- **Ephemeral staging**: The `DOWNLOAD_DIR` is a temporary directory on the CI runner, discarded after pipeline completion.
- **No deployment history**: There is no data store or log file that records deployment history, making audit trails dependent entirely on CI system job logs.
- **Partial cleanup**: In `deployFromNexus.sh`, the `transfer_artifact` function removes the `temp` and `work` directories of the Tomcat service and deletes individual war files and exploded war directories before deploying. In the older `deploy.sh`, the entire `webapps` directory content is deleted (`deltree *`).

## Compliance Gaps

1. **Plain-text credential logging** violates PCI DSS Requirement 8.3 (protect individual authentication factors) and general security logging hygiene.
2. **Credential in source code** (hard-coded bearer token in `deployFilesFromMappings.js`): violates PCI DSS Requirement 8.6 (management of system/application accounts) and Requirement 6.4 (protecting public-facing web applications / secure development). Even for dormant code checked into `master`, this is a credential exposure in version control history.
3. **No artifact integrity check**: Without checksum verification, a compromised Nexus repository could serve a malicious `.war` to production Tomcat servers — a supply chain risk relevant to PCI DSS Requirement 6.
4. **Nexus URLs may be plain HTTP**: If `RELEASES_REPO`/`SNAPSHOTS_REPO` resolve to `http://`, artifact downloads are unencrypted, contrary to PCI DSS in-transit encryption requirements (Requirement 4).
5. **No change authorisation record**: Deployments leave no tamper-evident audit trail independent of the CI system, which may be insufficient for PCI DSS Requirement 10 (audit logs) and SOC 2 CC6/CC7 controls.
