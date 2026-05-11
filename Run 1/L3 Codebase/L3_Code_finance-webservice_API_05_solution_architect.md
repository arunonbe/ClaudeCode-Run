# Solution Architect Report — finance-webservice_API

## 1. Complete Class and Method Inventory

### Namespace: `FinanceWS`

| Class / Interface | Key Methods | File |
|---|---|---|
| `IFinanceWS` | `createSalesTransaction(SalesTransactionRequest)`, `voidSalesTransaction(VoidSalesTransactionRequest)`, `getDenomiationTier(DenominatonTierRequest)` | `src/FinanceWS/IFinanceWS.cs` |
| `FinanceWS` (service implementation) | (delegates to Impl classes) | `src/FinanceWS/FinanceWS.svc.cs` |

### Namespace: `FinanceWS.FinanceWSImpl`

| Class | Key Methods | File |
|---|---|---|
| `SalesTransactionImpl` (abstract) | `process(SalesTransactionRequest)`, `createGPDoc()`, `createPDF()`, `sendEmail()`, `getSalesTranDO(SalesTransactionRequest)` (abstract), `doesTranasactionExistDB()` (abstract) | `src/FinanceWSImpl/SalesTransactionImpl.cs` |
| `InvoiceImpl` | `getSalesTranDO(SalesTransactionRequest)`, `doesTranasactionExistDB()` | `src/FinanceWSImpl/InvoiceImpl.cs` |
| `SalesOrderImpl` | `getSalesTranDO(SalesTransactionRequest)`, `doesTranasactionExistDB()` | `src/FinanceWSImpl/SalesOrderImpl.cs` |
| `InvoiceDO` | GP invoice domain object constructor/getters | `src/FinanceWSImpl/InvoiceDO.cs` |
| `SalesOrderDO` | GP order domain object constructor/getters | `src/FinanceWSImpl/SalesOrderDO.cs` |
| `SalesTransactionDO` (abstract) | `getSalesTransactionType()`, `getDocPrefix()`, `getDocType()`, `getBillToCustomer()`, `getBatchNumber()`, getters/setters for all fields | `src/FinanceWSImpl/SalesTransactionDO.cs` |

### Namespace: `FinanceWS.GreatPlains`

| Class | Key Methods | File |
|---|---|---|
| `GPCreateSalesDoc` (abstract static) | `createSalesTransaction(SalesTransactionDO)`, `SerializeCreateSalesDocumentObject(string, SalesTransactionDO, String)`, `getListofItems(SalesTransactionDO)`, `summarizeItems(ItemDetails[])` | `src/GreatPlains/GPCreateSalesDoc.cs` |
| `GPVoidSalesDoc` | `voidSalesTransaction(...)` | `src/GreatPlains/GPVoidSalesDoc.cs` |
| `GPDBHelper` | `getGPConnectionString(Customer)`, `getSalesOrderFromJobId(Customer, Source)`, `getItemsPricePercontract(SalesTransactionDO)`, `getFVDRanges(Customer)`, `getIssuanceItems()`, `removeBrackets(string)` | `src/GreatPlains/GPDBHelper.cs` |

### Namespace: `FinanceWS.Audit`

| Class | Key Methods | File |
|---|---|---|
| `AuditDBHelper` | `insertAuditTable(SalesTransactionDO, String, String)`, `updateAuditTable(SalesTransactionDO, String, String, Boolean, String)`, `checkStatus(SalesTransactionDO, String, String, out Decimal, out String)` | `src/Audit/AuditDBHelper.cs` |
| `AuditHelper` | `checkDocCreate(SalesTransactionDO)`, `auditDocCreate(SalesTransactionDO)`, `updateDocCreate(SalesTransactionDO)`, `updateDocCreate(SalesTransactionDO, String)`, `auditReportCreate(SalesTransactionDO)`, `updateReportCreate(SalesTransactionDO)`, `updateReportCreate(SalesTransactionDO, String)` | `src/Audit/AuditHelper.cs` |

### Namespace: `FinanceWS.EmailReport`

| Class | Key Methods | File |
|---|---|---|
| `EmailHandler` | `sendEmail(SalesTransactionDO)` | `src/EmailReport/EmailHandler.cs` |
| `EmailnReportDBHelper` | `getCustomerEmail(Customer)` | `src/EmailReport/EmailnReportDBHelper.cs` |
| `ReportHandler` | `createReport(SalesTransactionDO)` | `src/EmailReport/ReportHandler.cs` |

### Namespace: `FinanceWS.FWSException`

| Class | Description | File |
|---|---|---|
| `FWSBaseException` | Base exception with `getErrCode()`, `ErrMesg` | `src/FWSException/FWSBaseException.cs` |
| `FWSDBException` | Database error | `src/FWSException/FWSDBException.cs` |
| `FWSEConnectException` | eConnect/GP error | `src/FWSException/FWSEConnectException.cs` |
| `FWSEmailException` | Email send error | `src/FWSException/FWSEmailException.cs` |
| `FWSInvalidDataException` | Validation error | `src/FWSException/FWSInvalidDataException.cs` |
| `FWSReportException` | PDF report error | `src/FWSException/FWSReportException.cs` |

### Namespace: `FinanceWS.DomainObjects`

| Class | Description | File |
|---|---|---|
| `Customer` | Card program customer | `src/DomainObjects/Customer.cs` |
| `Source` | Source/origin reference | `src/DomainObjects/Source.cs` |
| `Item` | Order line item | `src/DomainObjects/Item.cs` |
| `ItemDetails` | Priced item from contract | `src/DomainObjects/ItemDetails.cs` |
| `DenominationTier` | FVD denomination range | `src/DomainObjects/DenominationTier.cs` |
| `AdditonalInfo` | Additional metadata | `src/DomainObjects/AdditonalInfo.cs` |
| `Commons` | Shared enums | `src/DomainObjects/Commons.cs` |

### Namespace: `FinanceWS.Request`

| Class | File |
|---|---|
| `FinanceWSRequest` | `src/Request/FinanceWSRequest.cs` |
| `SalesTransactionRequest` | `src/Request/SalesTransactionRequest.cs` |
| `VoidSalesTransactionRequest` | `src/Request/VoidSalesTransactionRequest.cs` |
| `DenominatonTierRequest` | `src/Request/DenominatonTierRequest.cs` |

### Namespace: `FinanceWS.Response`

| Class | File |
|---|---|
| `FinanceWSResponse` | `src/Response/FinanceWSResponse.cs` |
| `SalesTransactionResponse` | `src/Response/SalesTransactionResponse.cs` |
| `VoidSalesTransactionResponse` | `src/Response/VoidSalesTransactionResponse.cs` |
| `DenominationTierResponse` | `src/Response/DenominationTierResponse.cs` |

---

## 2. Security Vulnerability Assessment

### VULN-001 — CRITICAL: No Authentication on WCF Endpoint

**Location**: `Web.config` lines 29–33

```xml
<endpoint address="" binding="basicHttpBinding" contract="FinanceWS.IFinanceWS"/>
```

**Risk**: `basicHttpBinding` with no `<security mode="...">` element defaults to no transport or message security. Any host on the internal network can call `createSalesTransaction` and create arbitrary financial documents in Great Plains without authentication. This is a SOX control failure — unauthorized journal entries could be created.

**Remediation**: Add `<security mode="Transport">` (HTTPS) or `<security mode="Message">` (WS-Security) with certificate authentication. For internal services, consider mutual TLS (mTLS). Priority: **CRITICAL**.

---

### VULN-002 — HIGH: `debug="true"` and `includeExceptionDetailInFaults="true"` in Web.config

**Location**: `Web.config` lines 14, 23

```xml
<compilation debug="true" targetFramework="4.0"/>
<serviceDebug includeExceptionDetailInFaults="true"/>
```

**Risk**: Debug compilation exposes stack traces and internal class names in SOAP fault responses, providing attackers with detailed information about the application's internals. This also degrades performance.

**Remediation**: Set `debug="false"` and `includeExceptionDetailInFaults="false"` in production. Use the Web.Release.config transform to ensure these are disabled during release builds. Priority: **HIGH**.

---

### VULN-003 — HIGH: Personal Email Addresses in Web.config

**Location**: `Web.config` lines 55–65

```xml
<value>kanchan.sardana@citi.com</value>
```

**Risk**: Personal email addresses (likely departed employee, Citi era) are hardcoded as `EmailSendFrom`, `EmailReplyTo`, and `EmailCCTo`. All invoice emails and report emails copy this address. This is a privacy (GDPR/CCPA) issue for the individual and a business continuity risk — if this mailbox was deprovisioned, email send operations may fail silently.

**Remediation**: Replace with a functional mailbox (`finance-noreply@onbe.com` or equivalent) managed by the finance operations team. Priority: **HIGH**.

---

### VULN-004 — HIGH: SMTP Email over Port 25 (No TLS)

**Location**: `Web.config` line 51 (`EmailServerPort=25`), `EmailServer=mail.citicorp.com`

**Risk**: Port 25 SMTP without TLS transmits email content, including PDF invoice attachments with financial amounts and customer information, in cleartext. This violates GLBA requirements for protecting customer financial information in transit.

**Remediation**: Migrate to TLS-enabled SMTP on port 587 (STARTTLS) or 465 (SMTPS). Update email server to an Onbe-controlled relay. Priority: **HIGH**.

---

### VULN-005 — HIGH: SQL Server Connection String Discloses Server Name

**Location**: `Web.config` line 74

```xml
connectionString="Data Source=ppamwdcdifsql1\ppamwdcdifsql1;Initial Catalog=Banker_NA;..."
```

**Risk**: The full SQL Server hostname is disclosed in a config file committed to source control. While this is an internal name, it exposes database server topology. If the source repository is compromised, the attacker has a direct target for SQL Server attacks.

**Remediation**: Move connection strings to Azure App Configuration or Key Vault. Do not commit hostnames or connection strings to source control. Priority: **MEDIUM**.

---

### VULN-006 — MEDIUM: Transaction Document Temp Files Contain Financial Data

**Location**: `GPCreateSalesDoc.cs` lines 70–80, 117

**Risk**: The GP XML transaction document (containing customer numbers, item codes, prices, document amounts, and document prefixes) is written to `D:\c-base\FinanceWS\temp\SalesTranXXXX.xml` before submission to eConnect. The file is deleted in the `finally` block but is exposed on disk during the transaction window. Directory listing of this temp folder reveals in-flight transactions.

**Remediation**: Use in-memory XML serialization instead of a temp file (pass XML via memory stream directly to eConnect). If temp file is unavoidable, set restrictive filesystem ACLs on the temp directory. Priority: **MEDIUM**.

---

### VULN-007 — MEDIUM: No Input Validation on SOAP Requests

**Location**: `SalesTransactionImpl.cs`, `GPCreateSalesDoc.cs`

**Risk**: No evidence of input validation (null checks, length validation, type validation) on incoming SOAP request parameters before they are used in SQL stored procedure calls or GP XML documents. Malformed input could cause GP document creation errors that leave orphaned audit records.

**Remediation**: Add `DataAnnotations` validation to request DTOs. Validate `ProgramId` format (8 characters), `DocumentDate` range, and `Items[]` array content before processing. Priority: **MEDIUM**.

---

### VULN-008 — LOW: Typo in Method Name `doesTranasactionExistDB()`

**Location**: `SalesTransactionImpl.cs` line 89; `InvoiceImpl.cs` line 23

**Risk**: The abstract method `doesTranasactionExistDB()` (note the typo "Tranaasaction") is part of the WCF service's internal idempotency check. This is a code quality issue that makes the codebase harder to maintain.

**Remediation**: Fix typo to `doesTransactionExistDB()` and update all overrides. Low risk change. Priority: **LOW**.

---

## 3. Technical Debt Summary

| Debt Item | Severity | Effort |
|---|---|---|
| No authentication on WCF endpoint | CRITICAL | MEDIUM — add WCF security binding |
| debug="true" in production | CRITICAL | LOW — single config change |
| Personal email in config | HIGH | LOW — replace with functional mailbox |
| SMTP without TLS | HIGH | LOW — update port and server |
| .NET Framework 4.0 | HIGH | VERY HIGH — full migration |
| Manual deployment | HIGH | HIGH — add CI/CD pipeline |
| No automated tests | HIGH | HIGH — write from scratch |
| eConnect server-bound deployment | HIGH | VERY HIGH — ERP migration |
| GP eConnect on-premise DLL | HIGH | VERY HIGH — tied to GP version |
| Multiple Web.config variants | MEDIUM | LOW — use Azure App Config |
| Temp file financial data | MEDIUM | MEDIUM — refactor to memory stream |
| No input validation | MEDIUM | MEDIUM — add model validation |

---

## 4. Remediation Priority Matrix

| Priority | Action | Owner |
|---|---|---|
| P1 — Immediate | Set `debug="false"` and `includeExceptionDetailInFaults="false"` in all production Web.configs | Dev/Ops |
| P1 — Immediate | Replace personal email address with functional mailbox | Finance Ops + Dev |
| P1 — Sprint 1 | Add WCF transport security (HTTPS/mTLS) | Dev + Infra |
| P2 — Sprint 2 | Migrate SMTP to TLS-enabled relay | Dev + Infra |
| P2 — Sprint 2 | Move connection strings to Azure App Configuration | Dev + Infra |
| P3 — Q3 | Add input validation to request DTOs | Dev |
| P3 — Q3 | Refactor GP XML to use memory stream (eliminate temp file) | Dev |
| P4 — Roadmap | .NET Framework 4.0 → .NET 8 migration | Platform Engineering |
| P4 — Roadmap | CI/CD pipeline in Azure DevOps | DevOps |
| P5 — ERP Roadmap | Dynamics GP → Dynamics 365 Finance migration | Enterprise Architecture |
