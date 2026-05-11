# auto-card-batch_LIB — Business Analyst View

## Business Purpose

`auto-card-batch_LIB` (artifact `autocard-batch`, version `2.0.2-SNAPSHOT`) is a Spring Batch library that automates the provisioning of prepaid cards for eligible members. It operates as a scheduled batch process that:

1. Loads eligible member records from the core prepaid platform into a staging transaction table.
2. Processes each eligible member by issuing a virtual eCard (and optionally a physical/plastic card) via the `eCount` card management platform.
3. Enrolls the cardholder in the "card" product option if not already enrolled.
4. Updates the transaction journal with the outcome status of each record.

The business context is prepaid card issuance for B2C disbursements and incentive programs. The "threshold" logic (`ThresholdProgramVirtualCardSP`, `CardCreateService.issueCard()` lines 135–148) adds plastic card issuance for DDA (Demand Deposit Account) accounts that qualify under a program-specific threshold rule, indicating this also covers virtual-to-plastic upgrade scenarios.

## Business Capabilities

| Capability | Implementation Evidence |
|---|---|
| Eligible member record loading | `autoCardLoadRecordsJob` → SP `dbo.auto_card_creation_order_load` |
| Total count retrieval | `autoCardProcessJob` → SP `dbo.autocard_get_count` |
| Paginated record retrieval | SP `dbo.autocard_get_record` with `autocard.pagesize` parameter |
| Virtual eCard creation | `CardCreateService.issueCard()` → `IDeviceManager.createECard()` |
| Default eCard retrieval (idempotency check) | `IDeviceManager.getDefaultEcard()` — card is only created if no default eCard exists |
| Physical plastic issuance for threshold programs | `IDeviceManager.issuePlastic()` with delivery code lookup |
| Cardholder enrollment | `CardCreateService.enrollCardHolder()` → `AppProfileUserEnrollmentClass.create()` |
| Transaction status update | `AutoCardDaoImpl.updateAutoCardMemberStatus()` — updates `autocard_creation_transaction_journal` |
| Exception threshold guardrail | `AutoCardLimitDecider` halts processing if `exceptionTransactionsCount >= exceptionThreshold` |
| Infinite-loop detection | `AutoCardCountSavingListener.isInfinite()` — compares three successive record counts |

## Business Entities

| Entity | Class / Table | Key Fields |
|---|---|---|
| AutoCardMember | `AutoCardMember.java` (VO) | `id`, `memberid`, `created`, `status`, `isIssuance` |
| AutoCardCount | `AutoCardCount.java` (VO) | `transactionCount` |
| Transaction Journal | `autocard_creation_transaction_journal` (DB table, `autocardbatch.properties` line 12) | `id`, `memberid`, `status` |
| Program Identifier | `ProgramIdUtils.java` | 8-character programId decomposed into `product` (chars 0-1), `brand` (chars 2-3), `affiliate` (chars 4-7) |

## Business Rules & Validations

1. **Idempotency on card creation** (`CardCreateService.issueCard()`, lines 116–133): If a default eCard already exists for the member, no new card is created. Card creation is skipped, not errored.

2. **isIssuance flag** (`AutoCardConstants`: `NOT_ISSUNACE = 0`, `ISSUNACE = 1`): Enrollment is only performed when `isIssuance == 0`. If `isIssuance == 1`, card creation proceeds without the enrollment step (lines 151–153 and 227–229 of `CardCreateService`).

3. **Threshold plastic issuance** (lines 135–148): Triggered only when `autocard.threshold.issue.plastic = Y`. The DDA number's first 8 characters are parsed as a program ID. If the stored procedure `dbo.check_threshold_program_virtual_card` returns a count > 0, a plastic card is issued at zero fee with the default delivery code (`000` = 7–10 business day regular delivery).

4. **Delivery codes** (defined inline in `AutoCardProcessJob.xml`, lines 229–246): `000` (regular 7–10 days), `007` (4-day express), `910` (DHL to Ecount HQ). Default is `000`.

5. **Status lifecycle** (`AutoCardConstants.Status` enum): `N` (New) → `P` (Processing) → `C` (Completed) / `I` (Invalid) / `F` (Failed) / `R` (Retry).

6. **Failure error codes triggering INVALID status** (`AutoCardConstants`, lines 78–86): Address failures (14102–14105), home phone failures (14106), state/zip failures (14133), system errors (14091, 14134).

7. **Exception threshold** (`autocard.exceptionthreshold = 100`): If more than 100 exceptions accumulate across partitioned steps, the batch exits with `EXCEPTION THRESHOLD` exit code (exit code 12).

8. **Program ID format validation** (`ProgramIdUtils.getProgramIdUtils()`, line 10–18): Program ID must be exactly 8 characters, otherwise an `IllegalArgumentException` is thrown.

## Business Flows

### Flow 1 — Load Records Job (`Job1.bat`)
```
CommandLineJobRunner → autoCardLoadRecordsJob
  → autoCardLoadRecordsStep
      → StoredProcedureItemReader (dbo.auto_card_creation_order_load)
      → PassThroughProcessor
      → AutoCardLoadRecordsWriter (no-op write — data loaded by SP side-effect)
```

### Flow 2 — Process Job (`Job2.bat`)
```
CommandLineJobRunner → autoCardProcessJob
  → autoCardCountStep
      → StoredProcedureItemReader (dbo.autocard_get_count)
      → AutoCardCountWriter (stores totalTransactionsCount in StepContext)
      → AutoCardCountSavingListener (determines exit status)
        ├─ "RECORDS FOUND" → autoCardProcessStep
        ├─ "NO RECORDS FOUND" → END
        ├─ "EXCEPTION THRESHOLD" → END (exit 12)
        └─ "RECORDS FOUND:INFINITELOOP" → END
  → autoCardProcessStep (partitioned, grid-size=5)
      → autoCardCreateStep (per partition)
          → StoredProcedureItemReader (dbo.autocard_get_record, pagesize=5)
          → PassThroughProcessor
          → AutoCardCreateWriter
              → CardCreateService.processAutoCardRecord()
                  ├─ issueCard() [eCard creation + optional plastic]
                  ├─ enrollCardHolder() [if isIssuance==0]
                  └─ updateAutoCardMemberStatus() [write status back to DB]
  → autoCardLimit (AutoCardLimitDecider)
      ├─ "CONTINUE" → loop back to autoCardProcessStep
      └─ "COMPLETED" → END ("ALL RECORDS PROCESSED FOR DAY COMPLETED")
```

## Compliance & Regulatory Concerns

- **Prepaid card issuance (Reg E)**: The batch issues prepaid cards. Each issuance event must comply with Reg E cardholder disclosure requirements. There is no evidence of disclosure tracking within this batch; this is presumably handled at enrollment time in the upstream profile system.
- **PCI DSS**: The batch handles `memberid` and `dda_number` (a bank account number extracted from the DDA of the eCard). The `dda_number` is passed to the stored procedure `dbo.check_threshold_program_virtual_card` (`ThresholdProgramVirtualCardSP.java`, line 49). DDA numbers are sensitive financial identifiers. No masking or tokenisation is observed.
- **OFAC / AML**: No sanctions screening is performed within this batch. This batch is a downstream provisioning step; screening is assumed to occur upstream at account opening / onboarding.
- **Audit trail**: Status updates are written back to `autocard_creation_transaction_journal`. There is no separate audit event log produced by the batch. Spring Batch job repository tables (`BATCH_*`) capture step-level execution metadata.

## Business Risks

1. **No re-enrollment safeguard after card creation failure**: `processAutoCardRecord()` (lines 223–231) calls `enrollCardHolder()` a second time even when `issueCard()` already called it internally (line 152). Dual enrollment attempts may cause inconsistent state if the first succeeds and the second raises a `ProfileException` setting status back to `INVALID`.

2. **Silent no-op load step**: `AutoCardLoadRecordsWriter.write()` is an empty method (line 32). The actual record load is a side effect of the stored procedure. If the SP fails silently, the batch will report success with zero records loaded, and there is no alert or error propagation.

3. **Hard-coded delivery address references**: Delivery code `910` sends cards to "Ecount Hdqtrs" — referencing a legacy company name (Ecount) that has since been rebranded. This may cause operational confusion or routing errors.

4. **Exception swallowed on `CoreServiceException`** (`CardCreateService`, lines 176–179): A `CoreServiceException` is caught and logged but the member status is not updated (no `setStatus()` call). The record remains in its current status, risking reprocessing in an undefined state.
