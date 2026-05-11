# Business Analyst Analysis — ivrintegration_API

## 1. System Overview

`ivrintegration_API` is a **SOAP web service** that forms the server-side integration layer between the telephony IVR (Interactive Voice Response) system and the prepaid card account management platform. Artifact ID: `precheck-migration` (pom.xml line 8), version `2.0.0-SNAPSHOT`. The SCM URL (`gitlab.com/northlane/development/.../ivrintegration.git`, pom.xml line 19) confirms this is the Northlane/Classic IVR integration.

The service name "precheck" refers to the **check authorization pre-screening** workflow — a business process whereby the IVR allows merchants or cardholders to pre-authorize check-cashing transactions against prepaid card account balances. This is distinct from the general IVR cardholder balance inquiry service (that is `ivr-ws_API`).

## 2. Business Function

### 2.1 Check Management Workflow

The core business function is **check account lifecycle management via IVR telephony**. The workflow supports payroll check cashing at merchant locations (such as check-cashing stores, retail merchants). The IVR allows a merchant teller or automated system to:

1. **Look up a DDA account** — `checkAccountDDAInquiry`: given an employee ID and admin DDA, returns the DDA number associated with the employee's account.
2. **Retrieve account profile** — `checkAccountProfileInquiry`: given an eCount ID, retrieves account profile details.
3. **Retrieve account detail** — `checkAccountDetailInquiry`: retrieves full account details for a given check ID and admin ID.
4. **Assign a check to a DDA** — `checkAccountAssignRequest`: assigns a presented check to an employee's prepaid account (teller ID, payee ID, admin ID, DDA).
5. **Authorize a check** — `checkAccountAuthorizationRequest`: authorizes a check for a specified amount against the account.
6. **Verify a check (inquiry)** — `checkAccountVerifyInquiry`: retrieves verification status for a check using an authorization code.
7. **Confirm check verification** — `checkAccountVerifyConfirm`: confirms/finalizes the check verification with a cash flag.
8. **Ping** — `ping`: health check that returns current date/time.

All methods are exposed via Apache Axis (SOAP) at the `CheckManagementWebService` endpoint.

### 2.2 IVR Call Flow Context

The IVR call flow implied by these operations:
1. Cardholder calls IVR → IVR collects card/DDA number + authentication (likely DTMF-entered data).
2. IVR calls `checkAccountDDAInquiry` to locate the account.
3. Merchant teller enters check details → IVR calls `checkAccountAssignRequest` to link check to account.
4. Authorization check runs via `checkAccountAuthorizationRequest` — validates available balance against check amount.
5. Teller/IVR calls `checkAccountVerifyConfirm` to finalize the transaction.

### 2.3 Check-Cashing Use Case

This service is specifically designed for **payroll distribution at merchant check-cashing locations**. The `adminId` / `employeeId` / `adminDDA` parameters in `CheckManagementWebServiceImpl.java` (lines 67–68, 221–222) indicate a hierarchical employer-employee account structure where an "admin" (employer) account manages "employee" (worker) sub-accounts. This pattern is common in payroll card programs for unbanked workers.

## 3. User / Caller Base

The service is called by:
- The **IVR telephony platform** (automated phone system) — primary caller
- Potentially **teller terminal software** at merchant check-cashing locations

The `ani` (Automatic Number Identification) parameter is passed to every method (`CheckManagementWebServiceImpl.java`, line 68, 154, 222, 288, etc.) — this is the caller's phone number, captured by the IVR for fraud detection and audit purposes.

## 4. Input Parameters and Validation

All web service methods perform input validation (`CheckManagementWebServiceImpl.java`) using Spring bean validators loaded from `contentValidation.xml`:

| Method | Key Inputs | Validators Applied |
|---|---|---|
| `checkAccountAssignRequest` | applicationId, checkId, tellerId, payeeId, adminId, assignDDA, ani | applicationIdValidator, checkIdValidator, adminIdValidator, assignDDAValidator |
| `checkAccountAuthorizationRequest` | applicationId, checkId, authorizedAmount, ecountId, ani | applicationIdValidator, checkIdValidator, ecountIdValidator, authorizedAmountValidator |
| `checkAccountDDAInquiry` | applicationId, checkId, employeeId, adminDda, ani | applicationIdValidator, checkIdValidator, employeeIdValidator, adminDdaValidator |
| `checkAccountDetailInquiry` | applicationId, checkId, adminId, ani | applicationIdValidator, checkIdValidator |
| `checkAccountProfileInquiry` | applicationId, ecountId, ani | applicationIdValidator, ecountIdValidator |
| `checkAccountVerifyConfirm` | applicationId, checkId, cashFlag, ani | applicationIdValidator, checkIdValidator |
| `checkAccountVerifyInquiry` | applicationId, authorizationCode, checkId, ani | applicationIdValidator, checkIdValidator |

## 5. Back-End System Integration

The service delegates to `CheckManagementService` / `CheckManagementServiceImpl` in the `precheck-impl` module, which in turn calls XML-RPC services:
- `DeviceXMLRPCClient` — card/device account operations
- `EManageXMLRPCClient` — employee management operations
- `JobManagerServiceXMLRPCClient` — job service operations

These XML-RPC clients connect to the **eCount Core XML-RPC service layer**, the Gen-1 internal service bus. The service registry (`DirectorySettings.xml`) directs clients to registered XML-RPC endpoints.

## 6. Regulatory Relevance

- **Reg E**: Check authorization and cash disbursement from prepaid accounts fall under Reg E for prepaid accounts. Error resolution procedures must be documented.
- **NACHA**: If any ACH component underlies the check transaction, NACHA rules apply.
- **PCI DSS**: The service receives card/DDA numbers and financial amounts — in-scope for CDE.
- **UDAAP**: Check cashing fee structures and merchant authorization processes must comply with UDAAP.
