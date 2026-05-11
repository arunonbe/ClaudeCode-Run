# Solution Architect View — qa-test-automation

## API Surface

The framework consumes (does not expose) the following XML-RPC APIs:

| Service | Config File | Key Operations |
|---|---|---|
| CryptoService | `crypto-svc-config.xml` | getPGPKeyList, addClientPublicKey, removeClientPublicKey |
| DirectorService | (XML config) | ping, dispatch |
| ECountCoreService | `ecount-config.xml` | Core account operations |
| RepositoryService | `RepositorySvcTest.xml` | Program/member data reads |
| StrongBoxService | `strongbox-config.xml` | Key retrieval |
| NotificationService | (XML config) | Event dispatch |
| UserManagementService | (XML config) | User account operations |
| OrderManagerService | `client-OrderManager.xml` | Order creation/management |
| OrderService | `client-OrderService.xml` | Sweep and instant issue processing |
| OrderSynchronizerService | `client-OrderSynchronizer.xml` | Order sync |
| FileOrderManagerService | `client-FileOrderManager.xml` | File-based order submission |

## Security Posture

- **TLS**: Configured via JKS truststores (`truststore-qa.jks`, `truststore.jks`) set as system properties before test execution. TLS validation is active.
- **Authentication**: No explicit credentials are configured in the test specification code. Authentication, if any, is embedded in the XML configuration files or delegated to the Spring XML-RPC client proxy beans.
- **Secrets in config**: The Spring XML configuration files (`cbase/config/*.xml`) are not fully visible, but they are likely to contain endpoint URLs and possibly authentication tokens for the XML-RPC connections. These should be reviewed for embedded credentials.
- **Container security**: The CI pipeline uses the `om-ci-setup` composite action with `CONTAINER_SCAN: 'true'`, providing image-level vulnerability scanning.

## Critical Findings

### Finding 1: PII in Source File — Personal Name in PGP Key Path

**File**: `src/test/resources/Environments.groovy`, line 44

```groovy
keyPath: "\\\\q-na-app05\\pgpkeys\\RashmiDhandaronbe.asc"
```

A personal name (`Rashmi Dhandar`) is encoded in a committed file path. While this is a key path rather than cardholder PII, it violates the principle of not embedding personal information in source code and creates a GDPR/CCPA concern (names of Onbe employees in committed code). The path should reference a role-based file name (e.g., `onbe-qa-signing.asc`).

### Finding 2: Potential Real Account Identifier Committed

**File**: `src/test/resources/Environments.groovy`, line 53

```groovy
ecountId: '0401611300741331'
```

This 16-digit value has the format of a payment card account number. Although it is identified as a QA test account eCountId, the format is indistinguishable from a PAN. Under PCI DSS Req 3.3, this value must be confirmed as either synthetic (never a live card number) or a masked/tokenized reference. If it was ever a live PAN, its presence in git history constitutes a PCI DSS violation.

### Finding 3: All SNAPSHOT Dependencies — Non-Deterministic Builds

**File**: `pom.xml`, lines 86–143

Every eCount library dependency uses `-SNAPSHOT` versioning. A SNAPSHOT build pulls the latest artifact from the remote repository at build time, making builds non-deterministic. This means:
- The same source commit can produce different behavior on different build dates.
- CVEs introduced into a SNAPSHOT dependency are immediately incorporated without a version bump or audit trail.
- CI failures may be caused by upstream SNAPSHOT changes rather than local code changes, obscuring root cause.

### Finding 4: No Java Compiler Version Declared

**File**: `pom.xml` — `<properties>` section is absent

The `pom.xml` does not declare `maven.compiler.source` or `maven.compiler.target`. The effective Java version is inherited from the `prepaid-parent:6.0.x` BOM, which is not visible in this repository. The Dockerfile specifies Java 21, but if the parent BOM targets a lower version (e.g., Java 8 or 11), there could be a mismatch between compile-time bytecode compatibility and runtime JVM version.

## Technical Debt

1. All service configuration is XML-based Spring contexts — incompatible with modern Spring Boot auto-configuration and test slice patterns.
2. No test coverage for error paths or boundary conditions; all specs test the single happy-path scenario.
3. The `BaseSpec.setupSpec()` pattern loads the QA environment unconditionally with no mechanism to select stage or production configurations, limiting reuse as a smoke test tool.
4. Hardcoded QA server URLs (`ppnaut.nam.wirecard.sys`) represent a Gen-2 infrastructure dependency that creates fragility if the Wirecard DNS namespace changes.
5. JKS-format truststores committed to source — should be managed via secrets and provided at runtime.
