# Business Analyst Report — finance-webservice_API

## 1. Executive Summary

`finance-webservice_API` is a C# .NET WCF (Windows Communication Foundation) SOAP web service that provides a programmatic interface for creating and voiding sales transactions — orders and invoices — within Microsoft Dynamics GP (Great Plains) ERP. The solution was originally developed under the Citi Prepaid / ecount brand (email addresses `@citi.com` visible in `Web.config` lines 55–64) and is deployed to Windows IIS servers within the Onbe East Campus environment.

The service serves as the **bridge between Onbe's card program billing engine and the Great Plains general ledger**, enabling automated creation of GP sales orders and invoices without human data entry into GP. It also generates and emails PDF invoices to clients. The solution is named `FinanceWS.sln` and contains two Visual Studio projects: the service (`FinanceWS`) and a test client (`FinanceWSClient`).

---

## 2. Business Capabilities

### 2.1 Service Contract (IFinanceWS.cs)

The WCF service interface (`FinanceWS/src/FinanceWS/IFinanceWS.cs`) exposes three operations:

| Operation | Request Type | Response Type | Business Purpose |
|---|---|---|---|
| `createSalesTransaction` | `SalesTransactionRequest` | `SalesTransactionResponse` | Create a Sales Order or Invoice in Great Plains |
| `voidSalesTransaction` | `VoidSalesTransactionRequest` | `VoidSalesTransactionResponse` | Void/cancel an existing GP sales document |
| `getDenomiationTier` | `DenominatonTierRequest` | `DenominationTierResponse` | Retrieve denomination tier/FVD (face value denomination) ranges for a card program |

### 2.2 Sales Transaction Processing

The `createSalesTransaction` operation supports two document types via the `Task` enum:

- **`Task.DocOnly`**: Creates only the GP document (sales order or invoice)
- **`Task.ReportnEmail`** / **`Task.All`**: Creates the GP document AND generates a PDF invoice AND emails it to the client

The implementation (`SalesTransactionImpl.cs` lines 36–55) follows this flow:
1. Build domain object from request
2. Check audit table for prior transaction (idempotency check)
3. Create GP document via eConnect API
4. Optionally generate PDF report
5. Optionally send email with PDF attachment

### 2.3 Sales Transaction Types

The service supports two GP document types:
- **Invoice** (`InvoiceImpl.cs`) — mapped to `SOPInvoice` eConnect document type
- **Sales Order** (`SalesOrderImpl.cs`) — mapped to `SOPOrder` eConnect document type

Document numbering is managed via eConnect's `GetNextDocNumbers` API (`GPCreateSalesDoc.cs` lines 43–59), which increments the GP SOP number sequence. Rollback is handled if the eConnect call fails.

### 2.4 Denomination Tier Lookup

The `getDenomiationTier` operation supports card load operations by returning the FVD (face value denomination) min/max ranges configured per card program in the `Banker_NA` database (`GPDBHelper.cs` lines 200–248, stored procedure `so.get_customers_and_fvd_ranges`). This is used by upstream systems to validate load amounts before billing.

---

## 3. Business Processes Supported

### 3.1 Client Billing (SOX-Relevant)

The primary process is **automated client billing**: when a card order is fulfilled, the billing engine calls `createSalesTransaction` to generate a GP sales document. This creates the revenue recognition entry in Great Plains. This process is directly relevant to SOX controls over:

- **Revenue recognition accuracy**: Each call creates a binding financial record in GP
- **Invoice completeness**: The PDF generation and email delivery creates the client-facing invoice artifact
- **Audit trail**: The `FWSAuditTable` (`so.FWSAuditTable`) in the `Banker_NA` database records every transaction attempt, success, and failure with timestamps

### 3.2 Order Fulfillment Billing

Sales orders (`SalesOrderDO.cs`) represent pre-fulfillment billing commitments. The service creates GP orders that are later converted to invoices upon delivery.

### 3.3 Invoice Voiding

The `voidSalesTransaction` operation (`GPVoidSalesDoc.cs`) allows upstream systems to reverse a previously created GP document, supporting order cancellation and billing correction workflows.

### 3.4 Financial Reporting

The PDF report generation (`ReportHandler.createReport()`, called from `SalesTransactionImpl.cs` line 135) produces client-facing invoice documents stored temporarily at `D:\c-base\FinanceWS\temp` (`Web.config` lines 43–47). These PDFs are emailed directly to the customer email address retrieved from the `Banker_NA` database.

---

## 4. Regulatory Relevance

### 4.1 SOX (Sarbanes-Oxley)

This service is in-scope for SOX IT General Controls (ITGCs) because it directly creates financial records in Great Plains (the system of record for Onbe's financial statements). Key SOX considerations:

- **Change management**: Any modification to billing logic, pricing stored procedures (`so.items_price_per_contract`), or document numbering sequences directly affects financial statement accuracy
- **Access controls**: The `IFinanceWS` endpoint uses `basicHttpBinding` with no transport security (`Web.config` lines 20–34) — no authentication or authorization is enforced at the service level, meaning any system with network access to the endpoint can create financial documents
- **Idempotency / duplicate detection**: The `AuditHelper.checkDocCreate()` mechanism (`SalesTransactionImpl.cs` line 81) provides duplicate-transaction detection, which is a SOX completeness control

### 4.2 GLBA

Customer email addresses are retrieved from the `Banker_NA` database (`EmailnReportDBHelper.getCustomerEmail()`) and included in email transmissions. The email server is `mail.citicorp.com` (`Web.config` line 49), which is an external mail relay. This represents a data flow of customer information to an external system, subject to GLBA privacy protections.

### 4.3 PCI DSS

While the service operates at the billing/ERP layer rather than directly handling PANs, the `programid`, customer IDs, and `prefixID` (card BIN prefix) that flow through the service are card-program-level identifiers that could indirectly expose card program topology. The `Integrated Security=SSPI` connection string (`Web.config` line 74) uses Windows authentication, which is appropriate for an internal deployment.

---

## 5. Integration Points

| External System | Integration Method | Data Exchanged |
|---|---|---|
| Microsoft Dynamics GP | eConnect .NET API (`Microsoft.Dynamics.GP.eConnect`) | Sales orders, invoices, document numbers |
| `Banker_NA` SQL Server | ADO.NET SqlConnection (stored procedures) | Customer data, pricing, GP connection strings |
| Email server (`mail.citicorp.com`) | SMTP (port 25) | PDF invoice attachments |
| IIS / WCF caller | SOAP over basicHttpBinding | Sales transaction requests/responses |

---

## 6. Business Constraints and Known Limitations

1. **GP Dependency**: The service requires Microsoft Dynamics GP eConnect DLL to be installed on the host server. Per `README.md` lines 4–7, the project must be compiled on the same server that hosts it (`q-na-app01` for QA, `p-na-app31` for production).

2. **No Versioning**: The WCF service has a single endpoint version. Breaking changes to the `IFinanceWS` interface would affect all callers immediately.

3. **Email Server Dependency**: Hard-coded email server `mail.citicorp.com` (`Web.config` line 49) may no longer be accessible in the Onbe environment post-acquisition. Failure to send email does not roll back the GP transaction.

4. **Temp File Management**: GP XML document files are written to and deleted from `D:\c-base\FinanceWS\temp` during every transaction (`GPCreateSalesDoc.cs` lines 70–80). File system failures or permission issues on this directory will cause transaction failures.

5. **No Pagination on FVD Query**: The `getDenomiationTier` operation returns all FVD ranges for a customer in a single call with no pagination, which could be a performance concern for programs with many denomination tiers.
