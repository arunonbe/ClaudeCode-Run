# Data Architect View — crypto-service_SVC

## 1. Data Stores

### Primary Data Store: OS-level PGP Keyring
- **Type**: Native PGP keyring managed by the `pgp` command-line binary on the host OS.
- **Location**: Not specified in code; controlled by the PGP application's own configuration on the Windows host.
- **Access**: Exclusively via `Runtime.getRuntime().exec()` subprocess calls. No JDBC, JPA, or database driver is in scope for the crypto service itself (server.xml contains commented-out JNDI datasource stubs that are not activated).
- **Managed by**: The cryptokeysvc process running as the Tomcat service user on Windows hosts (legacy: `d-na-app03`, `q-na-app03`, `q-na-app04` per `.gitlab-ci.yml`; containerised: AKS via docker-compose).

### Secondary Data Store: Temporary File System
- **Type**: Local filesystem, temporary text files.
- **Location**: Configured via `httpCryptoService.pgpFilesFolderName` property (runtime path, not in repository).
- **Lifecycle**: Created at `ExternalCommandsHelper.createTempFileForPGPAddKeyOutPut()` (line 100–116), read 5 seconds later, then deleted (`ExecuteCommands.java`, line 86).
- **Content**: Raw stdout from the `pgp --key-add` command — contains key name and key ID strings. Does not contain key material itself (public key armored text is passed by file path reference, not content).

### In-Memory Cache
- **Type**: `java.util.HashMap<String, List<KeyDetailsBean>>` (`HttpCryptoSvcClientKeyListCache.java`, line 36).
- **Key**: Static constant `"clientKeyList"`.
- **Content**: The full list of `KeyDetailsBean` objects returned by `getPGPKeyList()`.
- **Invalidation**: Only via explicit call to `refreshPGPClientKeyCache(true)`. No TTL or event-driven invalidation.
- **Persistence**: None; lost on JVM restart.

### Configuration Property Store
- **Location**: `${CBASE_HOME_URL}/config/service/httpCryptoService/httpCryptoService.properties` (resolved at runtime from environment variable `CBASE_HOME_URL`).
- **Docker mount**: Volume `${CONFIG_DIR}:/cbase/config` (`docker-compose.yaml`, line 15).
- **Keys read**:
  - `httpCryptoService.batAddCommandFile` — absolute path to Windows .bat file for adding keys.
  - `httpCryptoService.pgpFilesFolderName` — folder for temp output files.
  - `httpCryptoService.cluster.node.*` — one or more `{host:port}` entries for the client-side URL list (read by `HttpCryptoSvcUrlListUtil.init()`, line 62).

## 2. Schema / Data Model

There is no relational or document database schema. The only structured data model is the Java bean layer:

### KeyDetailsBean (`bean/KeyDetailsBean.java`)
| Field | Type | Source |
|---|---|---|
| `keyId` | String | Extracted from PGP output via regex `[0][xX][0-9a-fA-F]+` |
| `keyName` | String | Extracted from `New userid:` line in PGP output |
| `keyPath` | String | Caller-supplied input parameter |
| `username` | String | Defined in bean but never populated by any code path (dead field) |
| `createdDate` | String | Defined in bean but never populated (dead field) |
| `modifiedDate` | String | Defined in bean but never populated (dead field) |
| `content` | String | Defined in bean but never populated (dead field) |
| `cmdOutPutString` | String | Raw PGP command output on success |
| `errorString` | String | Raw PGP command output on failure |
| `isKeyCmdSuccess` | boolean | Operation success flag |

**Note**: Four fields (`username`, `createdDate`, `modifiedDate`, `content`) are declared in the bean but are never set by any class in the repository. These are dead schema fields, likely from an older version or planned feature.

## 3. Sensitive Data Handling

| Data Item | Classification | Handling |
|---|---|---|
| PGP public keys | Low sensitivity | Key IDs (hex strings) and user IDs (names/emails) are logged at INFO level. Public keys by themselves do not expose private key material. |
| `keyPath` parameter | Medium | Full filesystem path to a public key file is logged at INFO level (`CryptoServiceImpl.java` line 48, `ExternalCommandsHelper.java` line 49). Paths may embed organisational naming conventions or reveal directory structure. |
| PGP command stdout | Low-Medium | Entire raw command output is stored in `cmdOutPutString` and logged at INFO level. Should not contain key material but may contain operational details. |
| `programId` | Low | Logged at INFO and used as filename prefix. No cardholder data present in this field based on usage. |

**No PAN, CVV, account numbers, or private key material is handled, stored, or transmitted by this service** based on full code review.

## 4. Encryption in Transit

- **Server-side**: Tomcat is configured with only a plain HTTP/1.1 connector on port 80 (`server.xml`, line 105). The HTTPS connector block (port 8443) is present but entirely commented out (lines 127–137).
- **Transport layer**: TLS must be provided by an upstream load balancer, reverse proxy, or API gateway. There is no evidence of such a component in this repository.
- **Client-side**: Spring `HttpInvokerProxyFactoryBean` constructs service URLs using `httpCryptoService.protocol` property at runtime. The protocol value is not hardcoded; if configured as `http`, all key-management operations traverse the network in plaintext.
- **Docker port exposure**: Port 80 is exposed (`docker-compose.yaml` line 9: `9315:80`). No TLS at the container level.
- **Conclusion**: Encryption in transit is **not enforced at the application layer**. This is a risk that must be mitigated at the infrastructure layer.

## 5. Encryption at Rest

- The PGP keyring itself is managed by the native PGP binary; filesystem-level encryption of the keyring is outside the scope of this service and not verified here.
- Temp files containing PGP command output are written to the filesystem briefly (~5 seconds) and then deleted. If the host filesystem is not encrypted, there is a brief window where this data is at rest unencrypted.
- No HSM integration is present anywhere in the codebase.

## 6. Data Flow Diagram (Textual)

```
Wizard UI
  |
  | Spring HttpInvoker (serialised Java object over HTTP)
  v
HTTPCryptoService WAR (Tomcat, port 80)
  |-- CryptoServiceImpl
        |-- ExternalCommandsHelper
              |-- ExecuteCommands
                    |-- Runtime.exec("cmd /c start/min {bat} {keyPath} {tempFile}")
                    |          --> OS PGP keyring (add)
                    |-- Runtime.exec("pgp --key-remove {name} --force")
                    |          --> OS PGP keyring (remove)
                    |-- Runtime.exec("pgp --key-list")
                               --> OS PGP keyring (read)
              |-- Temp file write/read/delete on local FS
```

## 7. Data Quality Issues

| Issue | Location | Impact |
|---|---|---|
| Output sentinel `NAVIN\\` embedded in data | `ExecuteCommands.java` lines 77, 127, 132, 171, 176 | Every output line has the literal string `NAVIN\` appended. This is a developer debug artifact that has shipped to production. Downstream parsing in `KeyManipulationHelper` strips it via `CryptoServiceConstants.STR_NEW_LINE`, but it is an egregious data hygiene issue. |
| Key list command constructed with unclosed quote | `PGPCommands.java` line 23: `pgp --key-list "` | The command string ends with an open double-quote. Correct PGP CLI syntax likely requires a closed argument or wildcard. Behaviour is determined by the PGP binary's argument handling on the host. |
| `getKeyName()` may return null | `KeyManipulationHelper.java` line 191 | If the regex split yields only one token, `keyName` is null and `compareTo()` in `KeyDetailsBean` will throw `NullPointerException`. |
| Dead fields never populated | `KeyDetailsBean.java` lines 21-24 | `username`, `createdDate`, `modifiedDate`, `content` are never set, making the bean misleading to consumers. |

## 8. Compliance Notes

- **PCI DSS v4.0.1 Req 3.7.1**: Cryptographic key management policies require key custodianship, dual control, and split knowledge. This service has no such controls — any caller can add or remove keys.
- **PCI DSS Req 3.7.6**: Key-use periods must be defined and enforced. This service does not track `createdDate` (field present but never set).
- **NIST CSF 2.0 PR.DS**: Data security controls require protection of data at rest and in transit. As noted, TLS is not enforced at the application layer.
