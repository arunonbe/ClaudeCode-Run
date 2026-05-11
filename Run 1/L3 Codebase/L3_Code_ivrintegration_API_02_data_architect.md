# Data Architect Analysis — ivrintegration_API

## 1. Data Model Overview

`ivrintegration_API` is a **SOAP web service with no direct database access** in its own codebase. It receives structured input via SOAP, delegates to downstream XML-RPC services (eCount Core), and returns structured responses. Data persistence occurs entirely in the downstream eCount Core platform. The service is stateless — no session state or caching is visible in the source.

## 2. Domain Objects (Input / Output DTOs)

### 2.1 Domain Inputs (precheck-impl/src/main/java/com/ecount/precheck/domain/)

| Class | Key Fields | Sensitive Data Assessment |
|---|---|---|
| `CheckAccountAssignInput` | applicationID, checkId, tellerId, payeeId, adminId, assignDDA, ani | `assignDDA` — DDA number (account identifier, cardholder data); `ani` — caller phone number (PII) |
| `CheckAccountAuthorizationInput` | applicationID, checkId, authorizedAmount, ecountId, ani | `ecountId` — internal account ID; `authorizedAmount` — financial; `ani` — caller phone (PII) |
| `CheckAccountDDAInquiryInput` | applicationID, checkId, employeeId, adminDda, ani | `adminDda` — DDA number (CHD); `employeeId` — employee identifier |
| `CheckAccountDetailInquiryInput` | applicationID, checkId, adminId, ani | `adminId` — admin account ID |
| `CheckAccountProfileInquiryInput` | applicationID, ecountId, ani | `ecountId` — internal account identifier |
| `CheckAccountVerifyConfirmInput` | applicationID, checkId, cashFlag, ani | `cashFlag` — indicates cash vs. check payout |
| `CheckAccountVerifyInquiryInput` | applicationID, checkId, authorizationCode, ani | `authorizationCode` — payment authorization code (sensitive) |

### 2.2 Domain Outputs (precheck-impl/src/main/java/com/ecount/precheck/domain/)

| Class | Notable Data Returned |
|---|---|
| `CheckAccountAssignOutput` | Assignment result, assigned DDA |
| `CheckAccountAuthorizationOutput` | Authorization result, authorization code |
| `CheckAccountDDAInquiryOutput` | Employee DDA number |
| `CheckAccountDetailOutput` / `CheckAccountDetail` | Account details (balance, status) |
| `CheckAccountProfileInquiryOutput` | Account profile (member data) |
| `CheckAccountVerifyConfirmOutput` | Confirmation result |
| `CheckAccountVerifyInquiryOutput` | Verification status |

**PCI/Sensitive Data Flag — `CheckAccountDetailInquiryOutput`**: The `CheckAccountDetail.java` response class (in `precheck-ws/src/main/java/com/ecount/precheck/ws/response/CheckAccountDetail.java`) likely contains account balance and card status. If it returns any PAN segment or expiry it must be masked or truncated per PCI DSS Requirement 3.3 (display masking).

### 2.3 XML-RPC Client Input/Output Objects (precheck-impl/src/main/java/com/ecount/precheck/client/)

| Class | Purpose |
|---|---|
| `CheckDDAAvailableAuthInquiryInput/Output` | Checks available authorization balance for a DDA |
| `CheckProgramAccountInquiryInput/Output` | Program account inquiry |
| `DDAInquiryXMLRPCInput` / `DDAInquiryOutput` | DDA account inquiry via XML-RPC |
| `PreCheckActivityFeeInquiryInput/Output` | Fee inquiry for the check activity |
| `PreCheckAddendaSetInput/Output` | Sets addenda data on check account |
| `PreCheckAssignInput/Output` | Assigns check to account |
| `PreCheckAuthorizeInput/Output` | Authorizes check amount |
| `PreCheckDefinitionInquiryInput/Output` | Retrieves check program definition |
| `PreCheckMerchantVerifyInput/Output` | Merchant verification |

**PCI/Sensitive Data Flags on XML-RPC Layer**:
- `CheckDDAAvailableAuthInquiryOutput` — contains available authorization amount. This is financial data in scope.
- `PreCheckAuthorizeOutput` — contains authorization code. This must be handled as sensitive payment data.

## 3. Response Objects (precheck-ws/src/main/java/com/ecount/precheck/ws/response/)

The SOAP response classes wrap outputs:

| Response Class | Notable Fields |
|---|---|
| `CheckAccountAssignResponse` | Assignment status, response code |
| `CheckAccountAuthorizationResponse` | Authorization result |
| `CheckAccountDDAInquiryResponse` | DDA number for employee — **FLAG: DDA number returned in SOAP response** |
| `CheckAccountDetailInquiryResponse` | Account detail — check for PAN/balance exposure |
| `CheckAccountProfileInquiryResponse` | Account profile — PII |
| `CheckAccountVerifyConfirmResponse` | Confirmation |
| `CheckAccountVerifyInquiryResponse` | Verification status |
| `PingResponse` | Current date/time |
| `Response` / `ServiceResponse` | Base response with `responseCode`, `completionMessage` |

## 4. Data Flow and Transmission Security

```
IVR Telephony System
    → SOAP/HTTP call to CheckManagementWebService (Apache Axis)
        → Input validation (contentValidation.xml bean validators)
            → CheckManagementServiceImpl
                → DeviceXMLRPCClient / EManageXMLRPCClient
                    → eCount Core XML-RPC service (TCP, proprietary protocol)
                        → eCount Core databases (SQL Server)
```

**Sensitive Data in Transit — Critical Findings**:

1. **DDA numbers** are passed as plaintext SOAP parameters. SOAP over HTTP (not HTTPS) would expose CHD in transit. The `.gitlab-ci.yml` (line 8) specifies `PROJECT_SERVICE_PROTO: http` — indicating the IVR integration service may be deployed over **plain HTTP** in dev/QA environments. This is a PCI DSS violation if TLS is not enforced at the load balancer layer.

2. **Authorization codes** (`authorizationCode` parameter in `checkAccountVerifyInquiry`) flow through the SOAP layer as plaintext strings. Authorization codes are sensitive payment data.

3. **`ani` (Automatic Number Identification)** — the caller's phone number — is logged in every method (`CheckManagementWebServiceImpl.java` line 79: `logger.info("applicationId="+applicationId+",checkId="+checkId+...",ani="+ani)`). ANI is PII and its logging to log files means log files become PII-bearing and must be protected under CCPA/GDPR.

4. **Full objects logged via `Utility.reflectionToString()`** — every input/output object is logged using reflection (`CheckManagementWebServiceImpl.java` lines 119, 127, 143, etc.). If any field in these objects contains a DDA number or authorization code, those values appear in application logs. This is a significant CHD/PII log exposure risk.

## 5. External Service Data Dependencies

The service depends on downstream XML-RPC endpoints registered in the Director service registry (`DirectorySettings.xml`). The service locator (`DirectorServiceLocator`) resolves endpoint URLs dynamically from the registry. If the registry is compromised or misconfigured, service routing can be manipulated.

## 6. PCI DSS Classification Summary

| Data Element | Location | Classification | Risk |
|---|---|---|---|
| DDA number (assignDDA, adminDda) | SOAP parameters, logs | CHD (PAN-equivalent) | CRITICAL — logged plaintext |
| Authorization code | `authorizationCode` parameter | Sensitive payment data | HIGH — in logs |
| ANI (caller phone) | All method inputs, logs | PII | HIGH — logged in plaintext |
| Account balance | `CheckAccountDetailInquiryResponse` | Financial CHD | HIGH |
| ecountId | SOAP parameters | Internal account identifier | MEDIUM |
