# autoclaim-split-svc_LIB — Business Analyst View

## Business Purpose

This library implements the **Autoclaim Split** capability for the Citi Prepaid / eCount prepaid card platform (now operated under Northlane/Onbe). Its single business job is to determine how an inbound eCheck disbursement (a digitally-issued payment coupon) should be split across a cardholder's registered payout devices before the funds are actually transferred. The library is consumed by a host service that drives the autoclaim workflow; it is packaged as a reusable JAR (`autoclaimsplit-svc`) with a companion contract JAR (`autoclaimsplit-common`).

## Business Capabilities

1. **eCheck lookup** — Given a `memberId`, `echeckId`, and `programId`, retrieve the payment record from the core database via the stored procedure `get_payment_detail_echeck_member_program` (`PaymentDaoImpl`).
2. **IEFT (International Electronic Funds Transfer) configuration loading** — Delegate to `IEFTConfigurationLoader` to obtain the cardholder's allotment profile, including ordered device list, fixed/percent allocation rules, per-device velocity limits, and the default fallback device.
3. **Fund allocation** — `UserAllotmentAllocation.execute()` iterates the ordered allotment devices, calculates the dollar amount destined to each device (fixed-dollar or percentage-of-eCheck), enforces min/max velocity limits, deducts allotment fees, and assigns overflow to the default DDA (Demand Deposit Account) or eCard.
4. **Allotment fee processing** — Per-device fees of type `ieft-online-payment-fee` are charged against IEFT devices; the fee amount is added to the eCard total so core ledger can journal the fee separately.
5. **Result packaging** — Returns a fully populated `Allotment` object containing the list of `DeviceVO` allocations, the eCheck verification code (claim code), eCheck amount, eCheck ID, member ID, and program ID.

## Business Entities

| Entity | Class / File | Key Fields |
|---|---|---|
| Payment request | `PaymentVO` | `memberId`, `echeckId`, `programId` |
| Payment record (DB) | `PaymentDTO` | `amount`, `echeck_id`, `action_code`, `verification_code`, `payment_type`, `activation_date`, `expiration_date` |
| Device allocation config | `AllotmentVO` | `deviceId`, `deviceType`, `percentAmt`, `fixedAmt`, `priority`, `minTransLimit`, `maxTransLimit`, `allotmentFee`, `echeckAmt` |
| Allocated device result | `DeviceVO` | `deviceId`, `deviceType`, `deviceAmt`, `priority`, `beneficiaryName`, `country`, `currency`, `fee` |
| Allotment result | `Allotment` | `devices` (list), `claimCode`, `eCheckId`, `programId`, `memberId`, `eCheckAmt` |
| Program profile | `ProgramAutoClaimProfile` | `minTransLimit`, `maxTransLimit`, `claimToCardDays`, `feature` |

## Business Rules & Validations

All rules are enforced inside `AutoclaimSplitImpl.performSplit()` and `UserAllotmentAllocation.execute()` / `allocateFundsToDevice()`.

1. **Null/missing input guard** — If `PaymentVO` is null, or any of `echeckId`, `memberId`, `programId` is null, throw `AutoclaimException` with code `4001` (`INVALID_PAYMENT`).
2. **Payment record must exist** — If the stored procedure returns zero rows, throw `AutoclaimException` with code from the SP `RETURN_VALUE` (see `AutoclaimSplitConstants`: `ECHECK_CLAIMED = 4011`, `ECHECK_NOTFOUND = 4012`).
3. **Program profile must be valid** — If `ieftConfiguration.isProgramProfileInvalid()` is true, throw `AutoclaimException` with code `4002` (`INVALID_PROGRAM_PROFILE`).
4. **Default device must exist** — If `getDefaultDDAForMember(ieftConfiguration)` returns null (no default DDA configured), throw `AutoclaimException` with code `4005` (`NO_DEFAULT_DEVICE`).
5. **Blocked/invalid devices are skipped** — Only allotment devices where `ieftDeviceAllotment.isValid() == true` are processed.
6. **Allocation ceiling** — Once `allotedAmt >= eCheckAmt`, iteration stops; no further devices receive funds.
7. **Min/max velocity enforcement** (`allocateFundsToDevice`):
   - If `deviceAmt < minTransLimit`, the amount is redirected to the eCard (overflow).
   - If `deviceAmt > maxTransLimit`, the device receives exactly `maxTransLimit`.
8. **Fee must not exceed device amount** — If `deviceAmt > 0 && deviceAmt <= allotmentFee`, the entire amount is redirected to the eCard.
9. **IEFT fee deduction** — For `DeviceTypes.IEFT` devices, `allotmentFee` is subtracted from `deviceAmt`; the fee is added to `ecardAmt` for journal-split purposes.
10. **Remainder assignment** — Any unallocated amount (`eCheckAmt - allotedAmt > 0`) is assigned to the default DDA device.
11. **Duplicate device merging** — `addDeviceToAllotments()` aggregates amounts when the same `deviceId`+`deviceType` appears more than once in the output list.
12. **Invalid allotment auto-fix** — `ieftConfigurationLoader.fixAllotments()` is called before allocation; a warning is logged if adjustments were needed.
13. **Country code mapping** — If `ieftDeviceAllotment.getCountry()` equals `"ZZ"`, it is mapped to `"USD"` (`UserAllotmentAllocation.populateAllotmentVO`, line 120-124).

## Business Flows

```
Caller
  └─► AutoclaimSplit.performSplit(PaymentVO)        [AutoclaimSplitImpl]
        1. Validate PaymentVO inputs
        2. PaymentDao.getPaymentDetail(memberId, echeckId, programId)
              └─► SP: get_payment_detail_echeck_member_program  [DB]
        3. IEFTConfigurationLoader.populateIEFTConfiguration(ieftConfig, memberId, programId)
        4. IEFTConfigurationLoader.fixAllotments(ieftConfig)
        5. UserAllotmentAllocation.execute(ieftConfig, paymentDTO, paymentVO, allotmentFee)
              └─► For each valid IEFTDeviceAllotment (priority order):
                    a. populateAllotmentVO(...)
                    b. allocateFundsToDevice(allotmentVO)
                         - Apply fixed or percent amount
                         - Enforce min/max velocity limits
                         - Charge IEFT fee; route fee to eCard
                         - Overflow → defaultDevice (DDA/eCard)
              └─► Merge duplicate devices
              └─► Add defaultDevice if it received any amount
        6. Package Allotment result (devices, claimCode, amounts, IDs)
        7. Return Allotment to caller
```

## Compliance & Regulatory Concerns

- **Reg E / NACHA** — The library governs ACH/DDA splits. Incorrect velocity enforcement or fee calculation could produce unauthorized debits or incorrect fund routing, creating Reg E exposure.
- **PCI DSS** — No PANs, CVVs, or track data are processed in this library. The `verification_code` field from `PaymentDTO` is a claim/authorization code, not payment card data. The `deviceId` fields represent account references but there is no evidence they are PANs. Risk is moderate; the data classification of `deviceId` values depends on the host system and should be confirmed.
- **OFAC / Sanctions** — The library routes funds to beneficiary accounts identified by `beneficiaryName`, `country`, and `currency`. There is no OFAC/sanctions screening within the library itself; this must occur upstream.
- **GLBA / CCPA** — Member identifiers (`memberId` as UUID string) and device identifiers are in scope as financial/personal data. No masking or redaction is implemented within the library.
- **Audit trail** — The library emits Log4j DEBUG/INFO log lines that include `memberId`, `echeckId`, `programId`, device IDs, and dollar amounts. Depending on log retention policy, this constitutes a financial audit trail. Log output to production systems must be reviewed to ensure no sensitive data (e.g., full account numbers) is emitted.

## Business Risks

1. **Test data with real member/eCheck UUIDs hard-coded in test class** — `TestAutoclaimSplitImpl.java` contains production-looking UUIDs for `MEMBERID`, `ECHECKID`, and `PROGRAMID` (e.g., `MEMBERID = "0E3C9230-0705-461D-B0EF-A3BD54CD7ACA"`). If these are real production identifiers, they constitute a data exposure risk in source code.
2. **Tests are fully commented out / non-functional** — Both `AllotmentConfigLoaderImplTest` and `TestAutoclaimSplitImpl` have their meaningful assertions commented out; the test suite provides no actual regression protection.
3. **No fee profile retrieval implemented** — The `FeeStructure` fee lookup in `AutoclaimSplitImpl` is commented out (lines 96-109); `allotmentFee` is always passed as `0` to `UserAllotmentAllocation`. Fee deduction logic in `allocateFundsToDevice` will silently no-op for all devices.
4. **AllotmentConfigLoaderImpl is entirely stubbed** — The entire implementation body is commented out. The `IAllotmentConfigLoader` interface has its only method commented out as well. Program profile caching is non-functional.
5. **`double` used for monetary amounts** — `Allotment.eCheckAmt` is declared as `double` (line 13, `Allotment.java`). Floating-point representation of currency is a known source of rounding errors in financial systems. All other monetary fields use `long` (in cents/minor units) correctly.
6. **Operator, CreditCard, and Plastic device types declared but not handled** — `DeviceTypes` defines `Operator`, `CreditCard`, and `Plastic` constants but none of the allocation logic handles them explicitly; they would fall through to the default device.
