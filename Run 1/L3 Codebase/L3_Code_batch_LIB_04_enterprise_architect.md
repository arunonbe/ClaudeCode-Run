# batch_LIB — Enterprise Architect View

## Platform Generation (Gen-1/Gen-2/Gen-3)

**Generation: Gen-1 / Legacy**

Evidence:
- Spring 2.5.6 (released 2009) and Spring Batch 2.1.9 (released 2011) — both long past end-of-support.
- Java 5 source compilation target (`<source>1.5</source>` in `pom.xml`).
- IBM WebSphere MQ 7.0 (released ~2009).
- XML-only Spring configuration (no annotations, no Spring Boot, no auto-configuration).
- Deployment via bare-metal Windows host with Active Batch scheduler.
- Perl and VBScript pre-processing scripts.
- Raw JDBC `StoredProcedure` subclasses and Hibernate 3 with `AnnotationSessionFactoryBean`.
- Group IDs `com.citi.prepaid` and `com.ecount` — the platform predates the Northlane/Onbe brand transition.
- All 25+ property files are hard-coded to `D:\c-base\config\...` Windows paths.

No evidence of Spring Boot, microservices, REST APIs, event-driven architecture, containerisation, or modern cloud-native patterns in the core framework (though `ClaimableChoiceAPIClient` does make a REST POST call to a newer service, indicating partial integration with a newer layer).

## Business Domain

**Payments — Batch Processing Layer**

batch_LIB covers the scheduled/asynchronous processing domain across all Onbe payment rails:
- **Prepaid card** (auto card issuance, balance sync, account status sync, embosser data)
- **ACH** (Auto Claim / Disney Global Deposit, BACS/PACS direct load for UK)
- **Push-to-debit** (TabaPay settlement import, transaction extract for Sunrise/FTB)
- **PayPal** (recurring sweep, settlement file parse, transaction detail extract, drawdown reports)
- **Venmo** (recurring sweep, transaction detail extract)
- **Check** (Payment Hub check issuance, selection notification)
- **Rewards** (Citi-funded and client-funded rewards posting)
- **Settlement / Reconciliation** (ECS ATPT/ATGT settlement, encashment Paypoint settlement, GPP Alto reports)
- **Compliance / Housekeeping** (claim expiration reversal, returned email processing, CBTS confirmation, allowed domain list)

## Role in Platform

batch_LIB is a **shared library** — it is not a standalone deployable microservice. It serves as the single batch processing engine for the entire Onbe Gen-1 platform. Every scheduled overnight/periodic process depends on this library:

```
Active Batch Scheduler
    |
    |--> java -jar batch-1.0.0.jar [job context XMLs] [jobId]
                |
                |--> Spring Batch (2.1.9)
                        |
                        |--> ecountDataSource (core platform DB)
                        |--> cbaseappDataSource (cbase profile/device DB)
                        |--> jobsvcDataSource (ACH/job service DB)
                        |--> notificationsvcDataSource (notification DB)
                        |--> batchRepoDataSource (Spring Batch metadata)
                        |
                        |--> ecount Core XML-RPC (port 40000)
                        |--> Payment Service Library
                        |--> Affiliate Service
                        |--> Director Service (DB routing)
                        |--> IBM WebSphere MQ (account status sync)
                        |--> Microsoft Exchange EWS (returned email)
                        |--> PayPal Shared Service (REST)
                        |--> Claimable Choice API (REST)
```

There is **no separation of concerns** at the service level — all 30+ batch jobs are compiled into one fat JAR, sharing the same Spring application context bootstrap on every invocation.

## Dependencies

### Upstream dependencies (what batch_LIB depends on)

| Artifact | Version | Nature |
|---|---|---|
| `com.ecount.service.paymentservice:Payment-Common` | 2016.1.1 | Payment certificate/ACH creation |
| `com.ecount.service.paymentservice:Payment-Service` | 2016.1.1 | Payment service library |
| `com.ecount.service.core.ecountcore:common` | 2014.1.1 | ecount core common utilities |
| `com.citi.prepaid.service.core.client:ecountCoreClient` | 2016.1.1 | ecount core client (XML-RPC) |
| `com.ecount.one.service.affiliate:xAffiliateService` | 2016.1.1 | Affiliate metadata service |
| `com.ecount.service.Core2.director:director-client` | 1.0.11 | Director DB connection routing |
| `com.ecount.service.Core2:ecount-system` | 2.0.0 | ecount platform system utilities |
| `com.ecount.service.brandedcurrency:brandedCurrency-common/impl` | 2016.1.1 | Currency utilities |
| `com.ecount.service.xSearch-New:xSearch-impl` | 2014.1.1 | Search service |
| `com.ecount.xPlatform` | 7.0.24 | Cross-platform utilities |
| `com.ecount.service.repositoryservice:repository-client` | 2013.3.2 | Repository/file service |
| `com.ecount.service.jobservice:jobmanager-client` | 2015.1.1 | Job lifecycle management |
| `com.ecount.customfiles.CustomFilesCommon:CustomFilesCommon` | 1.1.1 | Custom file processing |
| `com.ecount.services:comment` | 1.0.4 | Comment service |
| `com.citi.prepaid.service.core.strongbox:strongboxImpl` | 1.0.2 | Secret vault |
| `ibm.websphere:com.ibm.mq` (etc.) | 7.0.1.4 | IBM WebSphere MQ |
| `com.microsoft.ews-java-api:ews-java-api` | 2.0 | Microsoft Exchange Web Services |
| `com.microsoft.aad.msal4j` (transitive) | — | Microsoft OAuth2 for Exchange |
| `org.springframework.batch:spring-batch-core/infrastructure` | 2.1.9.RELEASE | Batch framework |
| `org.springframework:spring-*` | 2.5.6 | Spring framework |
| `org.springframework:spring-oxm` | 3.0.0.RELEASE | Spring OXM (XML marshalling) |

### Downstream dependants (what depends on batch_LIB)
The library is deployed as a standalone JAR — there are no compile-time dependants. Operational dependants are the Active Batch job definitions that invoke it.

## Integration Patterns

| Pattern | Usage |
|---|---|
| **Stored Procedure invocation** | Primary read/write pattern for all batch jobs. Spring `StoredProcedureItemReader` for reads, `StoredProcedure` subclasses for writes. |
| **XML-RPC (remote procedure call)** | ecount Core platform calls (`coreLiteXMLRPCClient`, `memberXMLRPCClient`, `transferXMLRPCClient`) via `DirectorServiceLocator` (port 40000). |
| **JMS / IBM WebSphere MQ** | Account status sync publishes XML messages to a queue (`FPAccountStatQueue.xml`). `RequestSendMessageCreator` builds JMS messages. |
| **REST (HTTP POST)** | `ClaimableChoiceAPIClient` calls `POST /redeemDefaultExpiredClaimCode`. `SharedServiceHelper` calls PayPal Shared Service. Uses `org.javalite.http.Http`. |
| **Flat file I/O** | FlatFileItemReader/FlatFileItemWriter for encashment settlement, GPP Alto reports, rewards posting, push-to-debit. `PaypalSettlementFileMultiResourceItemReader` for multi-file PayPal settlement. |
| **Spring Batch partitioning** | Auto claim, balance sync, account status sync, Payment Hub jobs, Alto BACS load, GPP Alto reports — all use `Partitioner` + `SimpleAsyncTaskExecutor` for parallel processing. |
| **Exchange Web Services (EWS)** | Returned email batch reads Microsoft Exchange inbox via EWS Java API with MSAL4J OAuth. |
| **File system staging** | VBS/Perl scripts download and pre-process files to a staging path; Java batch reads from database after Perl direct-loads. `FileMovingTasklet` archives processed files. |
| **Hibernate 3 (ORM)** | Auto claim job uses `AnnotationSessionFactoryBean` for `AffiliatePartnerDetail` and `ProgramMapDetail` entities — the only ORM usage; all other DAOs use JDBC. |

## Strategic Status

**Status: Legacy / Technical Debt — Retirement Candidate**

- All dependency versions are at minimum 8 years old (2016 vintages) and most are substantially older.
- No modern observability, no containerisation, no automated testing in CI.
- The codebase is tightly coupled to the Gen-1 `ecount`/`cbase` platform — all business logic flows through XML-RPC calls to the ecount core, which is also a legacy system.
- The mix of Windows-only deployment, VBScript, Perl, IBM Active Batch, and Java 5 source code represents the full Gen-1 technology stack.
- New functionality has been partially grafted on (REST calls, MSAL4J OAuth, `PushtodebitTransactionVo` with modern fields like `PAR` and `MAC`) without modernising the surrounding framework.
- The PayPal and Venmo recurring choice processors (`PayPalChoiceRecurringDetailsProcessor`, `VenmoChoiceRecurringDetailsProcessor`) contain the most recent business logic but are embedded in the same legacy framework.

## Migration Blockers

1. **Direct ecount Core XML-RPC dependency**: All member/device/transfer operations go through `CoreLiteXMLRPCClient` at port 40000. There is no REST or gRPC abstraction. Migration requires Gen-3 equivalents for `DeviceManager`, `MemberManager`, `TransferManager`, `INotificationManager` etc. from the `com.cbase.*` namespace.

2. **Payment Service Library tight coupling**: `AutoClaimProcessHelper` calls `PaymentServiceLibraryImpl.createCertificate()` — a Gen-1 library. No API abstraction exists.

3. **Stored procedures as business logic**: All reads and some writes are via stored procedures (`auto_claim_process_count_extract`, `auto_claim_process_extract_transaction`, `core_profile_global_deposit_file_update`, `dbo.payout_transfer_details_fetch`, ECS settlement procs, etc.). These procedures encapsulate business logic that must be replicated or replaced during migration.

4. **Director service dependency**: Database connections are routed through the proprietary `DirectorConfiguredDBCPdatasourceCreator` — there is no standard JDBC URL or connection string. Migration requires replacing Director with a cloud-native secrets/config mechanism (e.g., AWS Secrets Manager, Azure Key Vault).

5. **IBM WebSphere MQ**: Account status sync uses IBM MQ 7.0 JMS. Migration to a cloud-native message broker (Kafka, SQS/SNS, Azure Service Bus) requires full rework of `FPAccountStatQueue.xml` and `RequestSendMessageCreator`.

6. **Active Batch scheduler**: No cloud-native job orchestration. Migration requires replacing Active Batch XML job definitions with AWS Step Functions, Azure Data Factory pipelines, or Kubernetes CronJobs.

7. **VBScript / Perl pre-processors**: File download and parsing scripts (`*.vbs`, `*.pl`) are Windows-specific and have no container-portable equivalent. File processing must be replaced with cloud storage event triggers or managed ETL.

8. **Windows file system paths**: 25+ property files and file I/O paths are hard-coded to `D:\c-base\...`. All path dependencies must be externalised via environment variables or cloud storage URIs.

9. **Hibernate 3 / Spring 2.5**: These versions are 15 years behind the current release. A major framework upgrade (Spring 6+, Spring Batch 5+, Hibernate 6+) is required before containerisation is feasible, and would involve breaking API changes throughout.

10. **CVV2 field in import VO**: `PushtodebitTransactionVo.cvv2` must be resolved (field removed or confirmed never persisted) before any migration to ensure the new system does not inherit a potential PCI DSS violation.
