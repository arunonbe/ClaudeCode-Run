# clientapi_API — Data Architect View

## Data Stores

### 1. Microsoft SQL Server — cbaseapp database
- **Purpose**: Stores API security entities (access entities, IP addresses, IP ranges, certificates, host records). Used for per-client, per-program authorization.
- **Driver**: `com.microsoft.sqlserver.jdbc.SQLServerDriver` (`mssql-jdbc` version `12.8.2.jre11`)
- **Connection config**: `spring.datasource.cbaseapp.*` (configured via Azure App Configuration)
- **Production host**: `P-LIS-DB03.nam.wirecard.sys:2231`, database `cbaseapp` (`app-config/prod/appsettings.json`)
- **QA host**: `q-lis-db01.nam.wirecard.sys:2231` (`app-config/staging/appsettings.json`)
- **Credentials**: Stored in Azure Key Vault; referenced as `managepaymentapi-cbaseappdb-username` / `managepaymentapi-cbaseappdb-password`
- **Transaction manager**: `CbaseappDataSourceTransactionManager` with 600-second default timeout (`CbaseAppDataSourceAutoConfiguration.java`)
- **Spring bean**: `CbaseappDataSource` (wrapped in `TransactionAwareDataSourceProxy`)

### 2. Microsoft SQL Server — jobsvc database
- **Purpose**: Job service data store. Configured and available but no direct SQL calls are visible in the business logic source of this repo; likely used by downstream order-service shared infrastructure.
- **Production host**: `P-LIS-DB01.nam.wirecard.sys:2231`, database `jobsvc`
- **QA host**: `q-lis-db01.nam.wirecard.sys:2231`
- **Credentials**: Azure Key Vault references `customerserviceapi-jobsvcdb-username` / `customerserviceapi-jobsvcdb-password`
- **Spring bean**: `JobSvcDataSource` (`JobSvcDataSourceAutoConfiguration.java`)

### 3. Order Service (Remote HTTP)
- **Purpose**: The core prepaid card processing system. All business operations (add funds, update registration, update account status, get request status) are delegated to this downstream service via Spring HTTP Invoker (`HttpInvokerProxyFactoryBean`).
- **Production URL**: `https://prod.nam.wirecard.sys:9003/order/OrderService`
- **Protocol**: Spring `HttpInvoker` (Java serialization over HTTPS) with `XStreamMarshaller`
- **Timeouts**: connect 5000 ms, read 30000 ms (standard); read 9000 ms (synchronous processor client `clientapi.yml`)
- **Spring beans**: `OrderServiceClient`, `SynchronousOrderProcessorTimeoutClient` (`OrderServiceConnectionConfiguration.java`)

### 4. Redis Cache Service (HTTP REST)
- **Purpose**: Provides program-level flags and international country lookup data.
  - `programSetup/{affiliateID}/intlProgram` — returns "yes"/"no" string indicating international program
  - `intlCountries/{country2DigitCode}` — returns JSON array of supported countries
- **Production URL**: `https://was-az1-recipientcacheadminapp-prod-ss.azurewebsites.net/adminservice/` (`app-config/prod/appsettings.json`)
- **Client**: `InternationalFlagService.java` using Java 11 `HttpClient` with 10-second timeout
- **Note**: This is accessed as an HTTP REST API, not a direct Redis connection; it is a wrapper/admin service that fronts Redis

### 5. Azure App Configuration
- **Purpose**: Externalizes all application configuration (database URLs, service URLs, memberId, Redis URL, payment director settings)
- **Endpoint**: `${AZURE_APP_CONFIG_ENDPOINT}` (environment variable)
- **Refresh interval**: 15 minutes default (`bootstrap.yaml`)
- **Key filter**: `clientapiws/` prefix with label filter matching active Spring profile (`bootstrap.yaml`)
- **Authentication**: Managed Identity (non-local) or connection string (local) (`bootstrap.yaml`)

### 6. Azure Key Vault
- **Purpose**: Stores database credentials (usernames and passwords)
- **Authentication**: Managed Identity with `AZURE_MANAGED_IDENTITY_CLIENT_ID`
- **Integration**: Spring Cloud Azure Key Vault Secrets (`spring-cloud-azure-starter-keyvault-secrets`)

## Schema & Tables

No DDL or schema migration scripts exist in this repository. The `cbaseapp` database schema is owned and managed by the `api-security-lib` library (`com.citi.prepaid.security:api-security-lib:3.0.1`). Based on the DAO classes in `APISecurityValidatorConfiguration.java`, the relevant tables are accessed through:

- `JdbcEntityDao` — entity records (clients/programs registered for API access)
- `JdbcEntityIdentificationDao` — entity identification records
- `JdbcAccessEntityIPAddressDao` — IP address allow-list entries
- `JdbcAccessEntityIPRangeDao` — IP range allow-list entries
- `JdbcAccessEntityCertificateDao` — client certificate entries
- `JdbcHostDao` — host records

The `cacheEntityManager` (`CacheEntityManager`) loads these at startup with special entities `WHITE-LIST` and `REGISTRAR`, and with startup registration state `REGISTER` (`api-security.yml` and `APISecurityValidatorConfiguration.java` line 158-163).

## Sensitive Data Handling

| Data Element | Where Present | Handling |
|---|---|---|
| SSN (9 digits) | `UpdateRegistrationInput.ssn`, SOAP request body | Formatted as XXX-XX-XXXX in `ClientApiServiceImpl.formatSsn()`, then embedded in `SecureUserProfile.toXML()` inside `ActionSecureMemo`; transmitted to OrderService. No masking in API layer. |
| Date of Birth | `UpdateRegistrationInput.date_of_birth` (YYYYMMDD), SOAP body | Parsed to `java.util.Date` and passed to `SecureUserProfile`; no masking. |
| Email address | `UpdateRegistrationInput.e_mail` | Passed as-is through SOAP; stored twice (both `email` and `email2` fields in `Registration` constructor, `UpdateRegistrationService.java` line 137). |
| Database passwords | `spring.datasource.cbaseapp.password`, `spring.datasource.jobsvc.password` | Stored exclusively in Azure Key Vault; never in source code or App Config properties section. |
| memberId (UUID) | `app-config/prod/appsettings.json` line 8 | Stored in Azure App Configuration (not Key Vault); this is an operational UUID, not a personal data element. |
| ACH routing numbers | `clientapi.yml` (dfiNA=553, routingNA=011001234) | In source-controlled config; routing numbers are not secret but exposure of DFI prefix could reveal internal account structure. |

## Encryption & Protection

- **Transport**: All external endpoints use HTTPS (verified from `appsettings.json` production values: `https://prod.nam.wirecard.sys:...`)
- **Certificate trust**: A custom CA certificate (`nam.wirecard.sys.crt`) is imported into the JVM truststore at Docker build time (`Dockerfile` lines 25-27), enabling mTLS-capable connections to `nam.wirecard.sys` internal infrastructure
- **Database connections**: Use `trustServerCertificate=true` in JDBC URL (both prod and QA `appsettings.json`). This disables server certificate validation for SQL Server connections, which is a security gap.
- **API Security**: IP address, IP range, and client certificate-based access control enforced by `AuthenticationCheckFilter` (registered in `WebConfiguration.java`) and `APISecurityValidator`
- **Secret management**: Azure Key Vault via Managed Identity for credentials; Azure App Config for non-secret configuration
- **SecureUserProfile**: SSN and DOB are wrapped in `SecureUserProfile.toXML()` before being sent downstream, suggesting the downstream OrderService applies additional protection, but the API layer itself does not encrypt these fields

## Data Flow

```
External Client (SOAP over HTTPS)
        |
        v
AuthenticationCheckFilter  <-- cbaseapp DB (IP/cert validation)
        |
        v
AxisServlet -> ClientApiWebServiceImpl -> ClientApiWebServiceHandlerImpl
        |
        |-- [field validation] (regex validators)
        |
        v
{AddFunds|UpdateRegistration|UpdateAccountStatus|GetRequestStatus}Service
        |
        |-- [security check] <-- CacheEntityManager (cbaseapp DB, cached)
        |
        v
SynchronousOrderProcessor (HTTP Invoker + XStream)
        |
        v
OrderService (nam.wirecard.sys:9003)
        |
        v
Response back to caller
        
UpdateRegistrationService also calls:
InternationalFlagService -> Redis Admin Service (HTTP REST, 10s timeout)
```

## Data Quality & Retention

- **Idempotency**: Duplicate request detection is handled by OrderService (`isRequestAlreadyFound()` flag). The API layer re-throws as `DUPLICATE_REQUEST` exception.
- **Input sanitization**: All inputs validated by regex validators before processing. No explicit SQL injection prevention visible at this layer (not applicable since no direct SQL from business logic).
- **Timeout handling**: JMS/HTTP timeouts return PROCESSING (code 2) rather than FAILED, allowing callers to re-query status — this prevents data inconsistency from premature failure reporting.
- **No caching of PII**: The `CacheEntityManager` caches security entities (IP addresses, certificates) not PII.
- **No data retention policy** is implemented in this service; it does not own persistent storage of transaction or cardholder data.

## Compliance Gaps

1. **`trustServerCertificate=true` in all JDBC URLs**: Disables validation of the SQL Server certificate. This is a PCI DSS 4.0.1 Requirement 4 gap (protection of data in transit). The MSSQL connection to `cbaseapp` and `jobsvc` does not validate server identity.
2. **SSN transmitted in SOAP XML without field-level encryption**: The SOAP body carrying SSN and DOB is only protected by transport-layer TLS. There is no application-level encryption of individual PII fields before transmission. Risk under GLBA and PCI DSS.
3. **No logging redaction**: The `logPerformanceInfo()` method in handler logs `programId`, `packageId`, and `transactionId`. No evidence of SSN/DOB/email redaction from logs. If DEBUG level is enabled, full stack traces (including request objects) may expose PII.
4. **Email stored twice**: In `UpdateRegistrationService.java` line 137, both `email` and `email2` fields in the `Registration` constructor receive the same email value, suggesting a schema legacy that stores email in two places.
5. **Redis accessed over HTTPS but without credential**: `InternationalFlagService` calls the Redis admin service with no authentication headers. If the service URL is compromised or intercepted, program configuration data could be read or manipulated.
