# Business Analyst View — crypto-service_SVC

## 1. Business Purpose

`crypto-service_SVC` (artifact `cryptokeysvc`, deployed as WAR at `/cryptokeysvc`) is an internal PGP public-key management microservice. Its sole stated purpose is to allow the **Wizard UI** (a cardholder / programme onboarding front-end) to add, remove, and list PGP public keys on a **PGP keyring server** that is hosted on the same Windows-based application host. The service acts as a thin HTTP façade over native OS-level `pgp` command-line tool invocations. It does **not** store encrypted files; that responsibility belongs to a separate service called **Strongbox**.

## 2. Capabilities Exposed

| Capability | Interface Method | HTTP Endpoint |
|---|---|---|
| Add client PGP public key to keyring | `addClientPublicKey(keyPath, programId)` | Spring HttpInvoker POST `/cryptokeysvc/httpCryptoService/HTTPCryptoService-httpinvoker` |
| Remove client PGP public key from keyring | `removeClientPublicKey(keyName)` | Same HttpInvoker endpoint |
| List all PGP public keys on keyring | `getPGPKeyList()` | Same HttpInvoker endpoint |
| Service health check | — | GET `/cryptokeysvc/hc` → returns `"OK"` |

All three crypto operations are declared in `ICryptoService` (httpCryptoService-common, `ICryptoService.java`). The transport protocol is **Spring HttpInvoker** (Java object serialisation over HTTP), not REST or SOAP.

## 3. Business Entities

| Entity | Class | Description |
|---|---|---|
| KeyDetailsBean | `bean/KeyDetailsBean.java` | Represents a single PGP key: `keyId`, `keyName`, `keyPath`, `username`, `createdDate`, `modifiedDate`, `cmdOutPutString`, `errorString`, `isKeyCmdSuccess` |
| PGPDetailsBean | `bean/PGPDetailsBean.java` | Configuration carrier: `batAddCommandFile` (path to Windows .bat file), `pgpFilesFolderName` (temp folder for add-key output) |
| CommandsOutputBean | `bean/CommandsOutputBean.java` | Raw stdout/stderr capture from OS process execution |

## 4. Business Rules

- Only **public keys** are handled. Private keys are never transmitted or stored by this service (per README and code inspection).
- A `programId` value is required when adding a key; it is used as a prefix for a UUID-named temp file: `{programId}_{uuid}.txt` (`ExternalCommandsHelper.java`, line 103).
- The key-add flow relies on a Windows `.bat` file whose path is injected via Spring (`httpCryptoService.batAddCommandFile`). The service is therefore **Windows-only by design** (README states "Windows based operating system" requirement).
- The remove command appends `--force` unconditionally (`PGPCommands.java`, lines 22–23), meaning no interactive confirmation is required.
- The key list is **sorted alphabetically** by `keyName` before return (`CryptoServiceImpl.java`, line 93).
- A simple **in-memory cache** (`HttpCryptoSvcClientKeyListCache`) is populated on construction and refreshed only when `invalidate=true` is passed to `refreshPGPClientKeyCache()`.

## 5. Business Flows

### Add Key Flow
1. Wizard UI calls `addClientPublicKey(keyPath, programId)` via Spring HttpInvoker.
2. `CryptoServiceImpl` delegates to `ExternalCommandsHelper.addClientPublicKey()`.
3. A UUID-based temp file path is created in the configured `pgpFilesFolderName`.
4. `ExecuteCommands.execPGPAddKeyCommand()` spawns a Windows cmd process: `cmd /c start/min {batFile} {keyPath} {tempFile}`.
5. After a hard-coded 5-second `Thread.sleep`, the temp file is read and then deleted.
6. `KeyManipulationHelper.extractKeyName()` parses command output for `New userid:` tokens to extract key name and `New signature from keyID` tokens for key ID.
7. `KeyDetailsBean` with success/failure state is returned to Wizard UI.

### Remove Key Flow
1. Wizard UI calls `removeClientPublicKey(keyName)`.
2. `ExternalCommandsHelper` constructs: `pgp --key-remove "{keyName}" --force`.
3. `ExecuteCommands.execPGPRemoveKeyCommand()` runs the command directly via `Runtime.getRuntime().exec(cmd)`.
4. `KeyManipulationHelper.isKeyDeleted()` checks output for `Deleting` or `Deleted` text tokens.
5. Result returned.

### List Keys Flow
1. Wizard UI calls `getPGPKeyList()`.
2. Command `pgp --key-list "` is executed via `ExecuteCommands.execPGPKeyListCommand()`.
3. `KeyManipulationHelper.populateKeyDetailBeanList()` parses output lines containing `pub` token, using regex `[0][xX][0-9a-fA-F]+` to extract hex key IDs.
4. Sorted list returned and also cached in `HttpCryptoSvcClientKeyListCache`.

## 6. Compliance Relevance

- PGP public keys are used to encrypt files (presumably containing cardholder or disbursement data) before transmission to clients. This service manages the **encryption key lifecycle** component of that process, making it **in-scope for PCI DSS** key management controls (PCI DSS v4.0.1 Req 3.7: protect cryptographic keys).
- The service does not handle card data directly, but a failure in key management (adding wrong key, failure to remove a revoked key) could result in data being encrypted with an unauthorised key — a confidentiality breach.
- No authentication or authorisation controls are visible in the code or configuration. Access relies entirely on network perimeter controls and the upstream Wizard UI.

## 7. Business Risks

| Risk | Severity | Detail |
|---|---|---|
| Windows OS lock-in | High | The `cmd /c start/min` invocation in `ExecuteCommands.java` (line 38) and the README dependency on Windows make the service unrunnable on Linux. The Docker image (`Dockerfile`) uses Alpine Linux — a direct contradiction. |
| Hard-coded 5-second sleep | Medium | `Thread.sleep(5000)` in `ExecuteCommands.java` (line 62) is a timing assumption, not a proper synchronisation mechanism. Under load or on a slow host this will cause intermittent failures or data loss. |
| No authentication on the key-management API | High | Any internal caller that can reach the service URL can add or remove PGP keys, which could redirect encrypted data to an attacker-controlled key. |
| Single test class with all tests commented out | Medium | `HTTPCryptoServiceClientTest.java` has all assertions commented out, meaning no automated regression coverage exists for the three core operations. |
| Version history shows Citi Prepaid origin | Low-Medium | `groupId` is `com.citi.prepaid.service.httpcryptoservice` and author is attributed to "OFSS" (Oracle Financial Services Software). Indicates inherited legacy code base not originally developed for Onbe. Provenance and licensing clarity should be confirmed with Legal. |
