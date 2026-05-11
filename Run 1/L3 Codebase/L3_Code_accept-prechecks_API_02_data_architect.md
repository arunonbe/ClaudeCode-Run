# accept-prechecks_API — Data Architect View

## Data Stores

The application connects to three Microsoft SQL Server databases, all configured in `DatabaseConfiguration.java` and referenced in `application.yml` / `.env_bkp`.

| Logical Name | Property Root | Role |
|---|---|---|
| **ecountcore** | `spring.datasource.ecountcore` | Primary ecount Core database; stores `PreCheckDefinition` records, check lifecycle states, and addenda |
| **cbaseapp** | `spring.datasource.cbaseapp` | CBase application database; used by the xplatform business-object layer (member, device queries) |
| **jobsvc** | `spring.datasource.jobsvc` | Job-service database; present in configuration but no direct application-level usage found in this service's Java code |

All three use the Microsoft JDBC driver (`com.microsoft.sqlserver.jdbc.SQLServerDriver`, version `12.8.2.jre11` in boot POM; `12.5.0.jre11-preview` still referenced in war POM at line 129).

The WAR deployment also references a Tomcat JNDI resource `jdbc/EcountCoreDataSource` via `META-INF/context.xml`, which is the pre-boot connection method.

In the test context (`datasourceTestContext.xml`), the ecountcore database is wired directly to `q-lis-db02.nam.wirecard.sys:2231;databaseName=EcountCore`.

## Schema & Tables

No DDL, Liquibase, or Flyway scripts exist in this repository. The schema is owned entirely by the xplatform library (`com.ecount:xplatform:6.5.0`) and the CBase business-layer libraries (`com.cbase.*`). The only table-level evidence available from the code is:

- **PreCheckDefinition** (accessed via `IEManageManager.preCheckDefinitionInquiry`): exposes fields `authorized_amount` (Integer), `serial_number` (String), `status` (String), and `addenda` (Map). These are populated from the `ecountcore` database.
- **Member / Registration** (accessed via `IMember.InquiryExtended` in `LastNameValidatorECountCore`): exposes `getLastName()` via `MemberInquiryExtendedResult.getRegistration().getLastName()`. This is in the `cbaseapp` database.

The `LastNameValidatorXSearch` class accesses `MemberInquiryValue.getLastName()` through the `xsearch` service layer (version `2.0.1`), which performs a card-number search.

## Sensitive Data Handling

| Data Element | Classification | Where It Appears | Risk |
|---|---|---|---|
| `checkNumber` | Bank routing/account identifier (financial sensitive) | Request object, INFO log line 58, response error messages | Logged in cleartext at INFO level |
| `serialNumber` | Check serial (financial identifier) | Request object, INFO log line 58, debug logs | Logged in cleartext |
| `lastName` | PII (cardholder surname) | Request object, INFO log line 58 | Logged in cleartext |
| `vendorId` | Vendor identifier | Request only; never stored or validated | Lower risk, but logged |
| `amount` | Transaction amount (financial) | Request object, INFO log | Logged |
| Azure App Config connection string | Secret / credential | `.env_bkp` line 4 — `Endpoint=https://as-app-configuration.azconfig.io;Id=AkPK;Secret=693k6US7...` | **Credential committed to repository in plaintext** |
| Database credentials (UAT) | Secret | `.env_bkp` lines 14–19 — `username=b2cstage`, `password=b2cstage` for all three databases | **Credentials committed to repository** |
| JWT Bearer token | Authentication secret | `QA.postman_environment.json` line 204 — full signed JWT token | **Token committed to test collection** |

The `.env_bkp` file is tracked in the repository (present in the Glob output and readable). It contains UAT database URLs (`u-lis-db01.nam.wirecard.sys`, `u-lis-db02.nam.wirecard.sys`), usernames, passwords, and an Azure App Configuration connection string with its secret key.

## Encryption & Protection

- **TLS for database connections**: Connection strings in `.env_bkp` include `trustServerCertificate=true`, which disables hostname verification. The `datasourceTestContext.xml` test config also uses `trustServerCertificate=true` with `sslProtocol=TLSv1.2`.
- **Azure Key Vault integration**: Production secrets are injected at runtime via `spring-cloud-azure-starter-keyvault-secrets`. In non-local profiles, Managed Identity is used (`managed-identity-enabled: true`). This is the correct production pattern.
- **Azure Managed Identity**: Non-local environments use `AZURE_MANAGED_IDENTITY_CLIENT_ID` for auth to App Configuration and Key Vault (`bootstrap.yaml` lines 27–35).
- **Custom CA certificate**: A Wirecard/nam.wirecard.sys CA certificate (`nam.wirecard.sys.crt`) is imported into the JVM truststore at container build time (`Dockerfile` lines 22–25). This is the legacy Wirecard/Payscout PKI infrastructure.
- **No application-level encryption**: The service does not encrypt any payload fields. Transport security relies entirely on the calling infrastructure (TLS termination at the ingress/load balancer).
- **No field-level masking in logs**: `checkNumber`, `serialNumber`, and `lastName` are passed unmasked to `log.info()` via `request.toString()`.

## Data Flow

```
Caller (SOAP client)
    → SOAP over HTTP/HTTPS
    → Apache Axis servlet (AxisServlet, /*) 
    → JaxRpcAcceptPrecheckService (JAX-RPC endpoint)
    → AcceptPrecheckServiceImpl
        → IEManageManager.preCheckDefinitionInquiry()
            → ECoreEManage (xplatform) → ecount Core service (HTTP, director address)
                → ecountcore SQL Server DB
        → IEManageManager.preCheckMerchantVerify()  [if validation passes, non-test mode]
            → ECoreEManage → ecount Core service
        [Optional LastNameValidatorECountCore path — not wired in current boot config]
            → IMember.InquiryExtended() → ECoreMember → cbaseapp SQL Server DB
    ← AcceptPrecheckResponse (SOAP)
```

The `director.address` (`director-client.yaml`) routes to the ecount Core HTTP dispatch service. In UAT this is `https://uat.nam.wirecard.sys:8080/service/dispatch.asp` (`.env_bkp` line 7).

## Data Quality & Retention

- **No input sanitisation beyond regex**: There is no length cap beyond the regex pattern. Strings are passed directly to downstream services.
- **Amount precision risk**: `BigDecimal.floatValue() * 100` cast to `int` can produce incorrect integer representations for values with three or more decimal places or for amounts like $1.10 due to IEEE 754 float imprecision. The correct approach is `amount.multiply(BigDecimal.valueOf(100)).intValue()`.
- **No data retention policy in this service**: The service is stateless between calls; it does not persist records directly. Data retention is governed by the ecount Core and cbaseapp databases (outside this repo).
- **No audit trail**: The service logs the request and response but does not write to any audit table. There is no structured audit event for accepted or rejected prechecks.

## Compliance Gaps

1. **PCI DSS Req 3.3 / 10.3**: Check numbers (financial account identifiers) and cardholder last names are written to application logs without masking. Logs are accessible to any operator with log-level access.
2. **Credential storage in SCM**: `.env_bkp` containing database passwords and an Azure connection string secret is committed to the repository. This violates PCI DSS Requirement 8.2.1 and general secrets-management standards.
3. **Test data with live credentials**: `datasourceTestContext.xml` wires directly to `q-lis-db02.nam.wirecard.sys` (QA environment) with hardcoded credentials `b2cstage/b2cstage`. Test runs could reach a live QA database.
4. **trustServerCertificate=true**: Bypasses server certificate validation, weakening transport security for database connections.
5. **JWT token in test collection**: `QA.postman_environment.json` contains a signed JWT Bearer token committed to the repository. Even if expired, this represents a secrets-in-SCM violation.
6. **No data-at-rest encryption controls visible**: No column-level encryption or transparent data encryption configuration is present in this repository.
