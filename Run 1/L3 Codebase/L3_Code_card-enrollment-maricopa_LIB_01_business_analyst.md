# card-enrollment-maricopa_LIB — Business Analyst View

## Business Purpose

This library implements a **batch card-enrollment process** for the **Maricopa** client program. Its sole purpose is to identify prepaid cardholders who have a Demand Deposit Account (DDA) on file but have not yet been issued a physical plastic card, and then automatically trigger the issuance of that plastic. The program name "Maricopa" references a specific client/affiliate within the eCount (now Onbe) prepaid platform.

The stored procedure name `Get_MaricopaDDA_With_No_Card` (in `GetCardIdsList.java`, line 18) confirms this: it retrieves Maricopa accounts with a DDA association but no card issued against them yet.

## Business Capabilities

1. **Identify unserviced accounts**: Query the eCount Core database for all Maricopa DDA accounts lacking an associated physical card via stored procedure `Get_MaricopaDDA_With_No_Card`.
2. **Batch plastic issuance**: For each account identified, invoke the `issuePlastic` API on the eCount Core platform to order and emboss a physical card.
3. **Zero-fee enrollment**: The plastic issuance is explicitly configured with a fee of `0` (`fee.setAmount(0)` in `EnrollmentHelper.java`, line 74), with a code comment confirming "No fee for MaryCopa" (note: the comment contains a variant spelling "MaryCopa").
4. **Fault-tolerant iteration**: Each account is processed individually within a try/catch in `EnrollmentProcessMain.java` (lines 52–61), so a failure on one account does not abort the full batch.

## Business Entities

| Entity | Source Reference | Description |
|---|---|---|
| Account | `EnrollmentHelper.java` line 76 — `new Account(accountNumber)` | A prepaid cardholder account identified by an account number string |
| AccountId / CardId | `GetCardIdsList.java` line 38 — `rs.getString("accountid")` | Database column `accountid`, representing the eCount internal device/card identifier |
| Funds (Fee) | `EnrollmentHelper.java` line 73–74 | Represents a monetary amount; set to zero for this program |
| Plastic | `IDeviceManager.issuePlastic(...)` called from `EnrollmentHelper.java` line 76 | The physical prepaid card to be produced and mailed |
| DDA | Referenced in stored procedure name `Get_MaricopaDDA_With_No_Card` | Demand Deposit Account — the bank-side account linked to the prepaid card |

## Business Rules & Validations

1. **Eligibility filter is entirely database-driven**: The stored procedure `Get_MaricopaDDA_With_No_Card` encapsulates the selection logic — accounts must be Maricopa DDA accounts with no card currently issued. No additional filtering exists in the Java layer.
2. **No fee charged**: `fee.setAmount(0)` is hardcoded. There is an inline comment (line 75) noting a TODO to retrieve the fee dynamically from an affiliate profile, but this was never implemented.
3. **Not a renewal**: `isRenewal` is hardcoded `false` in `EnrollmentHelper.java` line 76, meaning this is always treated as a first-time card issuance.
4. **Delivery code is null**: `deliveryCode` is passed as `null` (line 76), meaning the default delivery method is used with no special routing instruction.
5. **No duplicate-prevention guard in Java**: The code relies entirely on the stored procedure to return only accounts that lack a card. There is no idempotency check or post-issuance status flag set in the Java layer.
6. **Null-list handling**: `EnrollmentProcessMain.java` lines 40–43 check for a null `accountList` and log "No Records to Process" before exiting gracefully.

## Business Flows

```
[Batch Job Triggered (manual or scheduled)]
        |
        v
[EnrollmentProcessMain.main()]
        |
        v
[Load Spring Application Context from appContext.xml]
        |
        v
[EnrollmentHelper.getRecordsForProcessing()]
        |
        v
[AccountIdDAOImpl.getAccountIds()]
        |
        v
[GetCardIdsList.execute() → SQL Stored Proc: Get_MaricopaDDA_With_No_Card]
        |
        v
[Returns Collection<String> of accountIds]
        |
        v
[For each accountId in collection:]
        |
        v
[EnrollmentHelper.issuePlastic(accountId)]
        |
        v
[IDeviceManager.issuePlastic(Account, null deliveryCode, Funds(0), isRenewal=false)]
        |
        v
[eCount Core API embosses physical card]
```

## Compliance & Regulatory Concerns

1. **Account numbers in logs**: `EnrollmentProcessMain.java` lines 49 and 54–58 log `accountId` directly using `logger.info("Processing Account " + accountId)` and `logger.info("Issue Plastic Successfully for Account " + accountId)`. If `accountId` corresponds to or is derived from a full card number or PAN, this constitutes a PCI DSS violation (Requirement 3.3 — do not log PANs). The field name `accountid` in the stored procedure output column (line 38 of `GetCardIdsList.java`) and the parameter type `accountNumber` in `EnrollmentHelper.java` line 53 both suggest this may be a sensitive identifier. This must be confirmed with the data team and masked to first-6/last-4 if it is card-related.
2. **Fee waiver documentation**: Zero-fee plastic issuance for a named program (Maricopa) should be backed by a client contract or program configuration record. The hardcoded zero in Java is not auditable as a business rule.
3. **No consent or eligibility audit trail**: There is no record written back to the database confirming that a plastic was successfully issued for a given account, leaving no audit trail for dispute resolution under Reg E.
4. **Batch job authorization**: There is no authentication or authorization check before the job runs — any process with classpath access and the config files can execute the enrollment.

## Business Risks

1. **Reprocessing / double-issuance risk**: If the stored procedure is re-run before the card-issuance status is updated in the core system, the same accounts may be selected again and receive duplicate plastics.
2. **Silent per-account failures**: Errors on individual accounts are caught and logged but not escalated. There is no alerting mechanism, no dead-letter queue, and no retry logic (`DEFAULT_RETRY_COUNT = 3` is declared in `EnrollmentHelper.java` line 37 but never used anywhere in the code).
3. **Hardcoded business logic**: Zero fee and null delivery code are hardcoded, making the library unsuitable for reuse across other programs without source-code modification.
4. **No success confirmation**: The code logs "Issue Plastic Successfully" after the API call returns but does not validate any response object, so a silent API failure would be logged as a success.
