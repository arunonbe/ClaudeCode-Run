# account-service_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Classification: Gen-2**

Evidence:
- Package root `com.ecount` and `com.citi.prepaid` indicate origin in the ecount/Citi Prepaid platform era.
- Dependency on `com.parents:prepaid-parent:6.0.13` — this is the Gen-2 parent BOM.
- XML-RPC used as the inter-service protocol (`MemberXMLRPCClient`, `DeviceXMLRPCClient`, `TransferXMLRPCClient`, `ProfileXMLRPCClient`, `StrongBoxXMLRPCClient`, `EventXMLRPCClient`) — Gen-2 hallmark pattern.
- Spring XML context configuration (`appCtx-AccountService.xml`, `AccountServiceDAO.xml`) rather than Spring Boot auto-configuration — Gen-2 pattern.
- Dependencies on `cbase.business.*` classes (`TransferManagerImpl`, `ECoreTransfer`, `VirtualExpressLoginHelper`, `AffiliateLocaleSkinHelper`, `AffiliateMapSkin`, `DebitAuditInfoDao`) — these are Gen-2/Cbase platform components.
- `com.citiprepaid.service.*` validator classes (`Validator`, `StringValidator`, `LongValidator`, `InputValidationType`) embedded in the Spring context — these originate from the Citi Prepaid era.
- jTDS JDBC driver (SQL Server Gen-2 connectivity pattern).
- Java 21 as compiler target — this is an upgrade applied to a Gen-2 codebase rather than a greenfield Gen-3 service.

The `_LIB` suffix confirms this is the shared library form of the account service — consumed by multiple Gen-2 services that were built to use this contract.

---

## Business Domain

**Domain**: Prepaid Account Lifecycle Management

Sub-domains covered:
- **Identity/Enrollment**: Cardholder registration (`RegisterUser`, `ExtendedRegisterUser`), profile update (`UpdateUser`, `ExtendedUpdateUser`).
- **Payment Instruments**: Card issuance (`IssueCard`), account provisioning.
- **Funding / Disbursement**: Funds loading (`AddFunds` via QuickLoad, certificate/claimable), withdrawal (`Withdraw`), stop payment / reversal (`StopPayment`).
- **Notifications**: SMS and email notification orchestration (`SendNotification`, `CrcpNotificationService`, `SmsQueueService`).
- **Inventory / Location Management**: Card inventory location assignment (`SetLocationCode`, `SetInventoryLocationAttributes`).
- **Job / ACH Orchestration**: ACH transfer detail management, job-account mapping.

---

## Role in Platform

`account-service_LIB` is the **core account operations library** in the Gen-2 platform. It is the authoritative implementation of the `IAccountService` contract and is consumed by:
- Batch job processors that fund, register, and update accounts in bulk.
- Web-facing service tiers that expose account operations to partner APIs.
- Notification pipelines that trigger SMS/email on account events.

It is **not a microservice** — it is a shared JAR that executes within the host process, sharing the host's Spring context, datasource connections, and thread pools. This pattern was standard Gen-2 architecture: a single WAR/JAR host embedding multiple service libraries.

The library acts as the orchestration hub for calls to:
- The ecount Core (member, device, transfer) via XML-RPC.
- The Payment Service (for certificate/claimable issuance).
- Multiple SQL Server databases (Job, Core, Notification, Cbaseapp).
- External notification channels (SMS API, CRCP).

---

## Dependencies

### Upstream (this library depends on)

| Artifact | Version | Function |
|---|---|---|
| `com.ecount.service.core.ecountcore:common` | 3.1.6 | Core domain objects (Member, Account, Funds, Transfer) |
| `com.citi.prepaid.service.core.client:director-client` | 2.0.2 | Director service connectivity |
| `com.citi.prepaid.service.core.client:ecount-core-client` | 2.0.2 | Core XMLRPC clients (Member, Device, Transfer) |
| `com.citi.prepaid.service.core.client:eventserviceclient` | 2.0.2 | Event dispatch client |
| `com.citi.prepaid.service.core.client:profile-client` | 2.0.2 | Profile XMLRPC client |
| `com.citi.prepaid.service.core.client:strongboxclient` | 2.0.2 | StrongBox secrets client |
| `com.ecount.service.common:services-common` | 3.0.1 | Common service utilities, ActionMemo, ServiceObject |
| `com.ecount.service.jobservice:job-common` | 4.0.4 | JobAccountMap value objects |
| `com.citi.prepaid.service.job:job-impl` | 4.0.1 | Job implementation (batch processing) |
| `com.ecount.service.xsecurity:xsecurity-client/common/impl` | 4.0.3 | Security framework |
| `com.ecount.service.paymentservice:payment-common` | 4.1.1 | Payment service value objects |
| `com.ecount.service.paymentservice:payment-service` | 4.1.1 | Payment service implementation (certificate creation) |
| `com.ecount.daoutil:dao-util` | 2.0.1 | DAO helper utilities |
| `com.ecount.custom:custom-files-common` | 2.0.0 | Custom file support |
| `com.ecount:xplatform` | 6.5.8 | Cross-platform utilities |
| `com.ecount.one.service.affiliate:xaffiliate-service` | 4.0.1 | Affiliate metadata, Hibernate5 entities |
| `com.citi.prepaid.webservices.debitapi:debitapi-common/impl` | 3.1.4 | Debit API for withdraw/balance sweep |
| `com.ecount.service.Core2:ecount-system` | 4.0.3 | Core2 system utilities (DirectorConfiguredDBCPdatasourceCreator) |
| `com.citi.prepaid.spring-dbctx:spring-dbctx-container` | 2.0.1 | Spring DB context container |

### Downstream (consumers of this library)

Not determinable from this repository alone. Based on the library's role, likely consumers include:
- The batch job service (loads, registers accounts from partner files).
- The API gateway / web services layer.
- Notification orchestration service.

---

## Integration Patterns

| Pattern | Implementation | Notes |
|---|---|---|
| **XML-RPC (synchronous RPC)** | `MemberXMLRPCClient`, `DeviceXMLRPCClient`, `TransferXMLRPCClient`, `EventXMLRPCClient` | Gen-2 standard inter-service protocol. Tightly coupled, synchronous. |
| **JDBC Stored Procedure** | `AchTransferDetailCreate`, `CreateClaimablePayment`, `GetCliamablePaymentExpiryDate`, `JobAccountMapGet/Update`, `StoredProcGetProgramEnableStatus` | Business logic embedded in SQL Server stored procedures, called via Spring `JdbcTemplate`. |
| **JDBC Direct Query** | `SmsNotificationConfigDao`, `SmsQueueDao`, `ClaimCodeIssuanceInfoDao`, `ClaimablePaymentAddendaDao` | `JdbcTemplate` queries against notification and core databases. |
| **HTTP REST (outbound)** | `CrcpServiceConnector` (HTTPS + OAuth2 JSON), `SmsServiceClient` (HTTPS + OAuth2 JSON), `InternationalFlagService` (`java.net.http.HttpClient`) | Newer outbound integrations use REST; begin transition toward Gen-3 patterns. |
| **Spring XML IoC** | `appCtx-AccountService.xml`, `AccountServiceDAO.xml` | Gen-2 bean wiring. No annotations-based configuration or Spring Boot. |
| **EhCache (in-process)** | `AccountServiceCacheManagerImpl`, `ProgramEmailValidationConfigurationCache` | In-process JVM cache for notification program configuration. No distributed cache. |
| **Hibernate 5 (ORM)** | `appContextFactory` → Affiliate entities | Single Hibernate SessionFactory for the Affiliate table. Mixed with JDBC direct access for other entities. |
| **Database Queue (async)** | `SmsQueueDao.insertQueueMessage()` → `sms_notification_queue` | Outbound SMS messages staged in DB queue for asynchronous delivery by an external worker. |

---

## Strategic Status

**Status: Active Gen-2 — Migration Candidate**

- Actively maintained: version is at 4.0.33-SNAPSHOT, with recent additions (CRCP notification service, claimable choice payments, SMS queue, `ClaimCodeIssuanceInfoDao`, international flag service via Redis).
- The addition of `CrcpNotificationService` and `SmsQueueService` (outbound REST with OAuth2, DB queue pattern) represents incremental Gen-3-style features grafted onto a Gen-2 library.
- The `InternationalFlagService` using `java.net.http.HttpClient` is a modern Java 11+ pattern added within the Gen-2 shell.
- XML-RPC, jTDS, commons-dbcp, Spring XML config, and Cbase platform dependencies are blocking factors for full Gen-3 migration.
- CodeQL scanning is active (weekly schedule), indicating security governance attention.
- Dependabot is configured for weekly Maven dependency updates.

---

## Migration Blockers

| Blocker | Description | Impact |
|---|---|---|
| **XML-RPC Protocol** | All core service calls (member, device, transfer, event, profile, strongbox) use XML-RPC. Gen-3 pattern requires REST/gRPC. | High — requires core service API migration first. |
| **`com.citi.prepaid.*` Dependencies** | `director-client`, `ecount-core-client`, `eventserviceclient`, `profile-client`, `strongboxclient`, `spring-dbctx-container`, `job-impl`, `debitapi-common/impl` are Citi-era internal artifacts. | High — requires Gen-3 equivalents or elimination. |
| **`com.cbase.business.*` Classes** | `TransferManagerImpl`, `ECoreTransfer`, `EcountBusinessObject`, `VirtualExpressLoginHelper`, `AffiliateLocaleSkinHelper`, `AffiliateMapSkin`, `DebitAPIController/Helper`, `StrategyProfileHelper` embedded in Spring context. | High — these are Gen-1/2 Cbase business objects with no known Gen-3 equivalent. |
| **Spring XML Context** | All wiring is in XML files (`appCtx-AccountService.xml`, `AccountServiceDAO.xml`). Gen-3 services use Spring Boot auto-configuration or annotations. | Medium — refactor to `@Configuration` classes is feasible but requires comprehensive test coverage. |
| **jTDS JDBC Driver** | `net.sourceforge.jtds:jtds` is unmaintained. Azure SQL / modern SQL Server authentication requires Microsoft JDBC Driver. | Medium — driver swap is relatively contained but requires integration testing. |
| **Hibernate 5 for Affiliate** | `appContextFactory` uses Hibernate 5 with `SQLServerDialect` (`hibernate.dialect`). Spring 6/Spring Boot 3 require Hibernate 6+ and Jakarta namespace. | Medium — Hibernate upgrade requires entity/query review. |
| **`com.citiprepaid.service.*` Validator Classes** | `Validator`, `StringValidator`, `LongValidator`, `InputValidationType` from Citi Prepaid webservices are referenced in XML bean definitions for the debit API withdraw flow. | Medium — must be replaced with in-house or standard validation in Gen-3. |
| **No Unit/Integration Test Coverage in CI** | Tests are skipped in all CI pipelines (`-Dmaven.test.skip=true`). Migration without test coverage is high risk. | High — must be resolved before any refactoring. |
| **Hardcoded Platform Identifiers** | Hardcoded phone `610-941-4600` in `RegisterUserInput.validate()`; hardcoded `"B2C Affiliate ECard"` in `RegisterUser.execute()`; hardcoded DDA device type in `AccountDefinition`. | Low-Medium — need to be driven from configuration in Gen-3. |
| **commons-dbcp / commons-pool** | Legacy pooling libraries. Gen-3 standard is HikariCP (bundled with Spring Boot). | Low — swap is routine but requires connection pool configuration review. |
