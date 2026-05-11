# Business Analyst Report — wirecard_test-utilities_LIB

## Business Purpose

`wirecard_test-utilities_LIB` is a shared test support library (`com.wirecard.issuing:test-utilities:2.0.0`) providing reusable test infrastructure for Wirecard/Northlane Gen-2 issuing microservices. It enables integration testing by providing:

- An embedded SFTP server (Apache SSHD) for testing SFTP file exchange without requiring a real SFTP endpoint.
- An embedded email server (GreenMail) for testing email notification functionality.
- General file system utilities (`TestUtils`) for managing test directories and resources.
- Country code and currency code validation components (`CountryCode`, `CurrencyCode`) that are part of the main production source (under `src/main/java`) — not test-only utilities.
- PGP key material for testing file encryption/decryption.
- Pre-provisioned RSA public key for SFTP authentication in tests.

## Capabilities

1. **`EmbeddedSftpServer`**: A Spring-lifecycle-managed embedded SFTP server built on Apache SSHD. Supports both password authentication and public key authentication. Provides virtual filesystem isolation for each test run. Configurable home folder and port.

2. **`TestUtils`**: Utility methods for batch file testing — clearing test directories, copying classpath resources to filesystem, reading classpath resources, building ACH block filler strings, checking directory emptiness.

3. **`EmailUtils`**: Email utilities using GreenMail (embedded SMTP server) for testing email notification workflows.

4. **`CountryCode` / `CurrencyCode`**: JSR-303/Jakarta validation annotations for country and currency code validation — these are production validation components that happen to be packaged in the test utilities module.

5. **PGP test key pair**: `0x6392B27D-pub.asc` (public) and `0x6392B27D-sec.asc` (private) stored in `src/main/resources/pgp/`. These are described as test keys but they are packaged in the main (non-test) source set.

## Client and Cardholder Impact

Indirect. This library improves test coverage quality for Wirecard issuing services, which directly serve Singapore and other international cardholders. Better test infrastructure reduces the probability of defects reaching production.

However, the library contains security risks (hardcoded credentials, committed private key) that could, if the library jar is included in a production classpath or the credentials are reused, create direct cardholder risk.

## Business Rules in Code

- `EmbeddedSftpServer` defaults to username `wirecard` and password `[REDACTED — rotate immediately]` (hardcoded constants).
- `TestUtils.buildAchOutFileBlockFiller()` generates a 94-character block of '9's — this is the NACHA ACH file block filler format (NACHA requires ACH files to be padded to multiples of 10 records using 9-filled lines).
- Country and currency code validators enforce ISO 3166-1 alpha-2 and ISO 4217 standards in production validation.

## Regulatory Obligations

- The NACHA block filler utility confirms ACH file format compliance knowledge is embedded in test utilities — this must match the actual production ACH file generation logic.
- PGP private key and SFTP credentials in the library, if reused in any production context, would violate PCI DSS Req. 3.5 and Req. 2.2.

## Key Business Risks

1. **Hardcoded SFTP credentials** (`wirecard` / `[REDACTED — rotate immediately]`) in production main source code. If any production service accidentally references the embedded SFTP server, real SFTP servers are protected only by these known credentials.
2. **PGP private key in production main source** (`src/main/resources/pgp/0x6392B27D-sec.asc`). This key material is packaged into the production JAR and is accessible to anyone with the JAR.
3. **PGP passphrase `wirecard` hardcoded in test** (`PGPUtilsTest.java:21`). If this passphrase is reused on production PGP keys, the private key is compromised.
4. **RSA SFTP public key committed** (`sftp/id_test_rsa.pub`). Combined with the corresponding private key (which may exist elsewhere), this enables authentication to any SFTP server configured to trust this key.
