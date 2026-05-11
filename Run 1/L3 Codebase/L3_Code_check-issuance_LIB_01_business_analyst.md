# check-issuance_LIB — Business Analyst View

## Business Purpose

`check-issuance_LIB` is a Java batch-processing library that automates the physical check issuance lifecycle for prepaid cardholders. It was originally developed under the Citi Prepaid / ecount platform (groupId `com.citi.prepaid.service`, parent `service-parent:8`; library groupId `com.ecount.process`, artifactId `CheckIssuance`). The library debits a cardholder's DDA (Demand Deposit Account) device and triggers a downstream check printing and mailing workflow via Citi CPS (Card Processing Services). It also manages stop-refund-check file transmission to Citi via Sterling Commerce Connect:Direct (NDM).

The description in `pom.xml` line 16 reads: _"Instant Issue card related service client batch process classes"_.

## Business Capabilities

1. **Batch Check Issuance** — Reads pending check-issuance records from a SQL database, deducts funds from a DDA device via the ecount `TransferManager`, and marks transactions as complete, cancelled, or failed.
2. **Auto vs. Manual Request Processing** — Supports two separate processing modes: `AUTO_CHECK_REQUEST` (code `0`) and `MANUAL_CHECK_REQUEST` (code `1`), driven by `CheckIssuanceConstants` and selected via stored procedure parameter `check_type` (`CheckIssuanceTransactionsList.java` line 44).
3. **Check Re-issuance** — Special handling for source code `255` (`REISSUANCE_SOURCE`): fees are zeroed out (`CheckIssuanceHelper.java` line 418: `fee.amount = 0`), and balance validation is loosened.
4. **Transaction Retry with Max-Retry Guard** — Retry counter is tracked per transaction. If `retryCount > maxRetryCount` (default `3`, `CheckIssuanceHelper.java` line 45), the transaction is force-cancelled to prevent infinite retry loops.
5. **Enrollment Verification** — Before processing, `enrollmentProcessor()` checks the cardholder's app-profile enrollment option. If the member has switched away from "check" as their preferred payment method, the transaction is cleanly cancelled (`CheckIssuanceHelper.java` lines 650–718).
6. **Stop / Refund Check File Generation** — `citiCPSStopRefundCheck.vbs` extracts stop-refund records via BCP, transforms them via `citiReportParser.pl` (`createStopRefundCheck` sub-routine), and transmits the resulting file to Citi via NDM using the CDP process script `CITISTOPREFUNDCHECK.cdp`.
7. **Concurrency** — Transactions are processed in a configurable fixed thread pool (`ProcessCheckRecordsImpl`); batch size per thread and maximum threads are both externally configurable.

## Business Entities

| Entity | Source Location | Key Fields |
|---|---|---|
| `CheckIssuanceData` (abstract) | `data/CheckIssuanceData.java` | `transaction_uuid`, `old_transaction_uuid`, `dda_number`, `total_amount`, `member`, `ddaDeviceId`, `ecardDeviceId`, `status`, `error_code`, `retryCount`, `source`, `validityDays`, `isEnrollment`, `isIssuance`, `paymentId` |
| `CheckIssuanceRequest` | `data/CheckIssuanceRequest.java` | Extends `CheckIssuanceData`; used for DB update calls |
| `CheckIssuanceResponse` | `data/CheckIssuanceResponse.java` | Extends `CheckIssuanceData`; populated from SP result set |
| Check Issuance File Record | `citi-cps-checks.fmt` | 27 fields: `account_number`, `amount`, `check_id`, `first_name`, `last_name`, `address1`–`address2`, `city`, `state`, `postal`, `country`, `check_expiration_date` |
| Stop-Refund Record | `citi-cps-stop-refund-checks.fmt` | 4 fields: `account_number`, `amount`, `check_number`, `check_issue_date` |

## Business Rules & Validations

1. **Minimum balance threshold (standard):** `CHECK_ISSUANCE_AMT_MINIMUM_LIMIT = 99` cents. Checks are not issued if `availableBalance <= 99` (`CheckIssuanceHelper.java` line 460).
2. **Minimum balance threshold (issuance program):** `ISSUANCE_PROGRAM_CHECK_AMT_MINIMUM_LIMIT = 0`. Effectively `availableBalance > 0` is required.
3. **Validity check:** `data.getValidityDays() > 0` must be true for standard checks; expired checks are cancelled with error code `6` (`CHECK_ISSUANCE_VALIDITY_EXPIRED`) (`CheckIssuanceHelper.java` line 487).
4. **Fee handling:** `simpleFeeInquiry()` is called before every transfer. For `REISSUANCE_SOURCE`, fee is overridden to `0`. Fee is deducted from available balance before minimum-limit comparison.
5. **Enrollment guard:** If member has changed payment preference from "check" to another option, the pending transaction is cancelled rather than processed (`CheckIssuanceHelper.java` lines 654–719).
6. **Max retry guard:** Transactions that have exceeded `maxRetryCount` retries are force-cancelled with message `"TRANSACTION REACHED MAX RETRY COUNT AND CANCELLED"` (`CheckIssuanceHelper.java` lines 121–126).
7. **DDA vs. eCard device selection:** If `ecardDeviceId` is non-null and non-empty, the ecard device is used for balance inquiry; otherwise the DDA device is used (`CheckIssuanceHelper.java` lines 302–306).
8. **Enrollment-program balance computation:** For `IS_ENROLLMENT_PROGRAM` programs, available balance is derived differently — it is the lesser of `realTimeBalance` and `total_amount`, adjusted for `pendingBalance` (`CheckIssuanceHelper.java` lines 422–441).
9. **Exception code list:** Certain `CoreServiceException` / `CoreBusinessException` error codes are treated as expected terminal outcomes (not retried). These are configured externally via `exception_code_list` property (`CheckIssuanceHelper.java` lines 539–543).
10. **Bulk update block code record cap:** `citiReportParser.pl` enforces a hard limit of 2000 records per bulk-update file (line 277).

## Business Flows

### Primary Check Issuance Flow
```
CheckIssuance.main()
  └─ createCheckIssuanceProcessRecords()         [SP: check_process_create_records]
  └─ issueCheck(AUTO_CHECK_REQUEST)
      └─ loop: getCheckIssuanceTransactionsList() [SP: check_process_transaction_auto_post]
          └─ ProcessCheckRecordsImpl.processTransactions()  [thread pool]
              └─ RequestProcessorThread.run()
                  └─ enrollmentProcessor()        [check app profile]
                  └─ if status==0: processTransaction()
                      └─ getAccountDetails()      [DeviceInfoManager]
                      └─ simpleFeeInquiry()       [TransferManager]
                      └─ transferFunds()          [TransferManager.transferDDAToOperator]
                      └─ updCheckIssuanceTransaction() [SP: check_process_transaction_auto_post_status_upd]
                  └─ if status==1: transactionInquiryAndExceptionHandler()
                      └─ transactionInquiry()     [TransferManager.inquiry]
                      └─ commit() or cancel() depending on state/converged flags
  └─ issueCheck(MANUAL_CHECK_REQUEST)            [same loop]
  └─ shutdownThreadpool()
```

### Stop-Refund Check Flow
```
citiCPSStopRefundCheck.vbs
  └─ BCP export via SP: check_process_transaction_refundcheck_stop_extract
  └─ citiReportParser.pl -r CITISTOPREFUNDCHECK  [creates NDM file]
  └─ NDM-EXEC.VBS (Sterling Connect:Direct)      [transmits to Citi mainframe: NDMTEST]
      └─ CITISTOPREFUNDCHECK.cdp (CDP process)
          └─ Copy to MVS dataset CATDLTQX.NDMFILES.PP5499IR
          └─ Run PGM=CSYUEV3 (mainframe batch)
          └─ Run PGM=ENCRYPT (encryption step)
```

## Compliance & Regulatory Concerns

1. **Cardholder PII in transit:** The `citi-cps-checks.fmt` format file (lines 18–29) defines `first_name`, `last_name`, `address1`, `address2`, `city`, `state`, `postal`, `country` as fields in the check file sent to Citi. These are full cardholder mailing addresses transmitted in plaintext delimited files — a potential data-in-transit risk (PCI DSS Req 4.2.1, GLBA).
2. **Account numbers in files:** `citi-cps-checks.fmt` column 9 is `account_number` (17 chars); `citi-cps-stop-refund-checks.fmt` column 1 is `account_number` (8 chars). These may represent DDA account identifiers sent to Citi — sensitivity level depends on whether these are tokenised or raw.
3. **Plaintext credentials in config file:** `citiCPSStopRefundCheck.vbs` reads `SERVER`, `DATABASE`, `USER`, and `PASSWORD` from a local INI file at `D:\C-Base\runtime\ndmroot\<USER>\program\importconfig.ini` (lines 75–78). DB passwords are read as plaintext strings — non-compliant with PCI DSS Req 8.3.1 (no shared/stored credentials in scripts).
4. **Plaintext password passed to BCP:** Line 95 of `citiCPSStopRefundCheck.vbs` constructs a BCP command that includes `-U <username> -P <password>` on the command line — passwords visible in process listings (PCI DSS Req 8.3.1).
5. **Reg E / NACHA:** DDA debit transfers via `transferDDAToOperator` are ACH-adjacent operations and must maintain proper error-handling, reversal capability, and audit trails. The retry/cancel logic partially addresses this.
6. **Audit trail:** All transaction state changes are persisted via `updCheckIssuanceTransaction()` with status, error code, and a free-text description. However, no immutable audit log or event stream is produced — relying entirely on the mutable SQL record.
7. **NDM/mainframe transmission:** The CDP script targets `SNODE=NDMTEST` — the node name suggests a test environment is hardcoded, which may indicate the production CDP script is a different (unversioned) artefact.

## Business Risks

1. **Hard-coded Windows file paths:** Log path `D:/c-base/log/CheckIssuance/checkissuance.log` (`log4j.properties` line 6) and config path `d:/c-base/config/checkissuance/checkissuance.properties` (`appContext.xml` line 9) are absolute Windows paths, creating deployment fragility.
2. **Single-process guard is fragile:** `CheckIssuance.VBS` checks for a running instance by comparing full command-line strings (line 34). If the classpath or JVM args change, duplicate instances can run concurrently, double-processing transactions.
3. **No compensation on partial thread failure:** If a thread in the pool crashes silently, there is no dead-letter queue or compensation mechanism — transactions remain in status `1` (in-progress) until the next retry cycle.
4. **Shared mutable state counters:** `CheckIssuanceHelper` holds counters (`failuresCount`, `successCount`, etc.) as plain `int` fields with no synchronisation. These are accessed from multiple `RequestProcessorThread` instances, leading to race conditions and inaccurate reporting.
5. **Tests are effectively absent:** `src/test/java/TestClass.java` contains only a `System.out.println("hii")` stub. There is no coverage of any business logic.
6. **Citi/ecount branding:** All packages, class names, and SCM URLs reference `ecount`, `citi`, and `northlane` — the library has not been rebranded to Onbe and carries legacy platform identity.
