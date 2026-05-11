# Solution Architect Report — wirecard_test-utilities_LIB

## API Surface

No HTTP endpoints. The library provides Java classes and resource files consumed by test code and (problematically) by production code in the case of `CountryCode` and `CurrencyCode` validators.

## Security Posture

**High risk.** Multiple sensitive artefacts are committed to the repository's main source tree and published to the artifact registry.

## Critical Vulnerabilities with File:Line Citations

| Severity | Finding | File:Line |
|----------|---------|-----------|
| **CRITICAL** | PGP private key committed to `src/main/resources` — packaged into production JAR | `src/main/resources/pgp/0x6392B27D-sec.asc` (entire file) |
| **HIGH** | SFTP username hardcoded as static constant in production source | `EmbeddedSftpServer.java:36` (`SFTP_USER_NAME = "wirecard"`) |
| **HIGH** | SFTP password hardcoded as static constant in production source | `EmbeddedSftpServer.java:38` (`SFTP_PASSWORD = "FxDMahi4TU"`) |
| **HIGH** | Password comparison in `PasswordAuthenticator` uses string equality, not constant-time comparison | `EmbeddedSftpServer.java:62–65` |
| **HIGH** | PGP passphrase `wirecard` hardcoded in test — if reused on production keys, key is compromised | `PGPUtilsTest.java:21` (`PASSPHRASE = "wirecard"`) |
| **HIGH** | PGP private key passed as char array from hardcoded string (`"wirecard".toCharArray()`) | `PGPUtilsTest.java:47` |
| **MEDIUM** | JUnit declared without test scope — bundled into production JAR | `pom.xml:63` (no `<scope>test</scope>`) |
| **MEDIUM** | SFTP RSA public key committed to `src/main/resources` | `src/main/resources/sftp/id_test_rsa.pub` (entire file) |
| **LOW** | `EmbeddedSftpServer` uses `SimpleGeneratorHostKeyProvider` with a temp file for host key — host key is regenerated each test run, preventing host key pinning in test validation | `EmbeddedSftpServer.java:70–71` |

## Key Security Issues Detail

### Issue 1: PGP Private Key in Packaged JAR

`src/main/resources/pgp/0x6392B27D-sec.asc` is in the `main` (not `test`) resource path. This means it is:
1. Included in `target/classes/` during compilation.
2. Packaged into `test-utilities-2.0.0.jar`.
3. Published to GitHub Packages and accessible to anyone with the `PAT_TOKEN` permission.
4. Loadable via `getClass().getResourceAsStream("/pgp/0x6392B27D-sec.asc")` from any application that includes the JAR.

If this key is or was used for any production PGP file exchange, all historical files encrypted with the corresponding public key must be considered potentially decryptable by unauthorized parties.

### Issue 2: Hardcoded SFTP Credentials in Production Source

`EmbeddedSftpServer.java` lines 36–38 define static final constants:
```java
private static final String SFTP_USER_NAME = "wirecard";
private static final String SFTP_PASSWORD = "FxDMahi4TU";
```

These are compiled into the library's bytecode. The password `FxDMahi4TU` is burned into the JAR. If any production SFTP server was configured with this credential set, it must be rotated immediately.

### Issue 3: Password Comparison Timing Attack

`EmbeddedSftpServer.java:62–65`:
```java
return (username.equals("wirecard") && password.equals("FxDMahi4TU"));
```
Standard string `equals()` is not constant-time. In a production context this would be a timing oracle for password comparison. For a test SFTP server, impact is low, but it reflects poor security practice that could be copied to production code.

## Technical Debt

- **Extract production validators**: `CountryCode.java` and `CurrencyCode.java` are in `src/main/java` under `com.wirecard.utilities.validation.validator`. They must be moved to a dedicated `wirecard-validation-utils` library to prevent test infrastructure from leaking into production deployments.
- **Fix JUnit scope**: `junit:junit` in `pom.xml` must have `<scope>test</scope>` added.
- **PGP key rotation and removal**: Rotate the `0x6392B27D` key pair; remove private key from repository; use Git history scrubbing (BFG or `git filter-repo`).
- **Replace hardcoded credentials with generated test credentials**: `EmbeddedSftpServer` should generate credentials dynamically per test run using `java.security.SecureRandom`.
- **Migrate to Testcontainers**: For Gen-3 services, `testcontainers/sftp` container provides a more realistic embedded SFTP test server without requiring custom code.
