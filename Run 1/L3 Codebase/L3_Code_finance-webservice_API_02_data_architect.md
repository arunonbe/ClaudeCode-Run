# Data Architect Report — finance-webservice_API

## 1. Overview

The `finance-webservice_API` operates primarily against the `Banker_NA` SQL Server database and the Microsoft Dynamics GP databases. All data flows are synchronous and request-response based via WCF SOAP.

---

## 2. Data Entities

### 2.1 Domain Objects (`FinanceWS/src/DomainObjects/`)

| Class | Fields | Description |
|---|---|---|
| `Customer` | `ProgramId`, `PromotionId`, `IsBillToECount`, customer identifiers | Card program customer entity; `ProgramId` is 8-character |
| `Source` | `SourceId`, `SourceName`, `getPrefixID()` | Source system identifier (job ID, batch reference) |
| `Item` | `ItemCode`, `ItemName`, `Count`, `Qty` | Card order line item |
| `ItemDetails` | `ItemCode`, `ItemDesc`, `Price`, `IsCount`, `IsIssuance`, `QtyOrCount` | Enriched item with contract pricing |
| `DenominationTier` | `MinValue`, `MaxValue`, `ItemCode` | FVD range entry |
| `AdditonalInfo` | (additional metadata) | Supplementary transaction metadata |
| `Commons` | (shared enums/constants) | Shared domain constants |

### 2.2 Transaction Domain Objects (`FinanceWSImpl/`)

| Class | Parent | Description |
|---|---|---|
| `SalesTransactionDO` | (abstract base) | Core sales transaction: `Cust`, `Source`, `Items[]`, `DocumentNumber`, `DocumentDate`, `Total`, `CustEmail`, `Facility` |
| `InvoiceDO` | `SalesTransactionDO` | Invoice-type transaction; `getDocPrefix()` returns invoice prefix |
| `SalesOrderDO` | `SalesTransactionDO` | Order-type transaction; `getDocPrefix()` returns order prefix |
| `SalesTransactionDO.getSalesTransactionType()` | — | Returns `SalesTransactionType.Invoice` or `SalesTransactionType.Order` |

### 2.3 Request/Response Objects

| Class | Key Fields | Usage |
|---|---|---|
| `SalesTransactionRequest` | `Task`, `Customer`, `Source`, `Items[]`, `DocumentDate` | Input to `createSalesTransaction` |
| `SalesTransactionResponse` | `ReturnCode`, `Message`, `Items[]`, `DocumentId` | Output of `createSalesTransaction` |
| `VoidSalesTransactionRequest` | (void parameters) | Input to `voidSalesTransaction` |
| `VoidSalesTransactionResponse` | `ReturnCode`, `Message` | Output of `voidSalesTransaction` |
| `DenominatonTierRequest` | Customer identifier | Input to `getDenomiationTier` |
| `DenominationTierResponse` | `DenominationTier[]` | Output of `getDenomiationTier` |
| `FinanceWSRequest` / `FinanceWSResponse` | (base classes) | Shared base request/response |

---

## 3. Database Schema

### 3.1 Banker_NA Database

All application data is stored in the `Banker_NA` SQL Server database, accessed via the connection string in `Web.config` line 74:

```
Data Source=ppamwdcdifsql1\ppamwdcdifsql1;Initial Catalog=Banker_NA;Integrated Security=SSPI;
```

**Tables and Stored Procedures** (from `GPDBHelper.cs` and `AuditDBHelper.cs`):

| Object | Type | Columns / Parameters | Purpose |
|---|---|---|---|
| `so.FWSAuditTable` | Table | `program`, `promo`, `sourceid`, `source`, `RequestType`, `Step`, `DocType`, `Success`, `DateCreated`, `DateUpdated`, `facility`, `docDate`, `documentId`, `totalAmount`, `isBillToEcount`, `Mesg` | Audit log of every transaction attempt |
| `so.get_gp_database` | Stored Proc | `@prefix IN`, `@server_name OUT`, `@database_name OUT` | Looks up GP database server and name by 4-digit BIN prefix |
| `so.get_so_from_job_id` | Stored Proc | `@customer_id`, `@jobid`, `@order OUT` | Retrieves existing sales order by job ID (idempotency) |
| `so.items_price_per_contract` | Stored Proc | `@customer_id`, `@is_bill_to_ecount`, RETURNS item rows | Returns pricing contract items for a customer |
| `so.get_customers_and_fvd_ranges` | Stored Proc | `@customer_id`, RETURNS tier rows | Returns FVD denomination ranges |
| `so.get_issuance_items` | Stored Proc | (none), RETURNS issuance_action rows | Returns card issuance action item names |

### 3.2 Great Plains Databases

The GP databases are looked up dynamically per card program via `so.get_gp_database`. The eConnect API calls target the specific GP company database (e.g., `ECNT`, `ECAN`, `EMXN`) based on the 4-character BIN prefix. Data written to GP includes:

| eConnect Object | Fields | Description |
|---|---|---|
| `taSopHdrIvcInsert` | `SOPTYPE`, `CUSTNMBR`, `BACHNUMB`, `DOCID`, `SOPNUMBE`, `DOCDATE`, `CREATETAXES`, `SUBTOTAL`, `DOCAMNT` | Sales order/invoice header |
| `taSopLineIvcInsert` | `ITEMNMBR`, `QUANTITY`, `UNITPRCE`, `CUSTNMBR`, `SOPNUMBE`, `DOCDATE`, `SOPTYPE`, `DOCID`, `XTNDPRCE` | Line item details |
| `taSopUserDefined` | `SOPNUMBE`, `SOPTYPE`, `USERDEF1` (= prefix ID) | User-defined fields |
| `taSopTrackingNum` | `Tracking_Number` (= source name), `SOPNUMBE`, `SOPTYPE` | Tracking/reference number |

---

## 4. Data Sensitivity Classification

| Data Element | Classification | PCI/Regulatory Relevance |
|---|---|---|
| `ProgramId` (8-char) | INTERNAL | Card program identifier — maps to BIN prefix |
| `PromotionId` | INTERNAL | Program promotion identifier |
| `CustEmail` | PII — MEDIUM | Customer email address; subject to GLBA/CCPA |
| `CUSTNMBR` (GP customer number) | INTERNAL | GP customer identifier |
| `Facility` | INTERNAL | Card issuance facility code |
| `DocumentDate` | FINANCIAL | Transaction date — SOX-relevant |
| `totalAmount` / `DOCAMNT` | FINANCIAL | Invoice/order total — SOX revenue recognition |
| `sourceId` / `jobid` | INTERNAL | Job/batch tracking identifier |
| SQL connection string | CREDENTIAL | In `Web.config` — see section 5 |

---

## 5. Data Security Assessment

### 5.1 Connection String Security

`Web.config` line 74 contains the `BankerNA` connection string:
```xml
<add name="BankerNA" connectionString="Data Source=ppamwdcdifsql1\ppamwdcdifsql1;Initial Catalog=Banker_NA;Persist Security Info=False;Integrated Security=SSPI;" />
```

Use of `Integrated Security=SSPI` (Windows Authentication) is appropriate — no password is embedded in the connection string. However, the server name `ppamwdcdifsql1` discloses internal SQL Server topology.

### 5.2 Temp File Risk

GP XML transaction documents are written to `D:\c-base\FinanceWS\temp\` before eConnect submission and deleted after (`GPCreateSalesDoc.cs` lines 70–80 and `File.Delete(fileName.ToString())` line 117). The temp file contains full sales transaction XML including customer numbers, item codes, prices, and document amounts. If the delete fails (e.g., due to an exception), sensitive financial data persists on disk.

The `finally` block in `GPCreateSalesDoc.cs` (lines 114–119) ensures deletion occurs even on exception, which mitigates but does not eliminate this risk (e.g., process kill, server crash).

### 5.3 Email Security

Customer email is retrieved from `Banker_NA` and used as a SMTP recipient. The email server is `mail.citicorp.com` on port 25 (`Web.config` lines 49–51) with no TLS/SSL configuration specified. SMTP over port 25 without TLS transmits email content (including PDF attachments with financial data) in plaintext, which is a data-in-transit risk.

### 5.4 WCF Transport Security

The WCF `basicHttpBinding` endpoint (`Web.config` lines 29–33) has no transport security configured:
```xml
<endpoint address="" binding="basicHttpBinding" contract="FinanceWS.IFinanceWS"/>
```

SOAP messages are transmitted over plain HTTP, meaning financial transaction data is in cleartext on the network. This is acceptable only if the service is accessed exclusively on a private internal network segment with no exposure to untrusted networks.

---

## 6. Data Flow

```
[Calling System (billing engine)]
    |
    | SOAP over basicHttpBinding (HTTP)
    v
[FinanceWS WCF Service]
    |
    |--[1] Query Banker_NA (so.get_gp_database) → GP connection string
    |--[2] Query Banker_NA (so.items_price_per_contract) → pricing
    |--[3] INSERT into so.FWSAuditTable (audit record)
    |--[4] Write temp XML file to D:\c-base\FinanceWS\temp\
    |--[5] Call eConnect API → GP database (ECNT, ECAN, etc.)
    |--[6] DELETE temp XML file
    |--[7] UPDATE so.FWSAuditTable (success/failure)
    |--[8] (Optional) Query Banker_NA for customer email
    |--[9] (Optional) Generate PDF report
    |--[10] (Optional) Send SMTP email with PDF to customer
    |
    v
[Response to caller]
```

---

## 7. Multi-Company GP Architecture

A notable data architecture feature is the multi-company GP database resolution (`GPDBHelper.cs` lines 18–68). The service does not use a single GP database but dynamically selects the appropriate GP company database (e.g., `ECNT` for US, `ECAN` for Canada, `EMXN` for Mexico) based on the 4-character BIN prefix of the card program. This supports Onbe's multi-entity ERP structure.

The `removeBrackets()` method (`GPDBHelper.cs` lines 71–85) handles server names returned with SQL Server square-bracket escaping — evidence of real-world troubleshooting that became permanent code.
