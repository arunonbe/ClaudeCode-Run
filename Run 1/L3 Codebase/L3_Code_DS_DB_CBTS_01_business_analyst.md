# DS_DB_CBTS — Business Analyst View

## 1. Business Purpose

`CBTS` (Cross-Border Transfer Service) is a purpose-built SQL Server database that supports Onbe's international money transfer product. It records cross-border payment transactions from US-based remitters (senders) to international beneficiaries (recipients), managing exchange-rate quotation and locking, transfer lifecycle state, reconciliation file tracking, transfer returns/rejections, and Spring Batch job-execution metadata.

The database is deployed in its own schema (`dbo`) with Liquibase-managed migrations (`DATABASECHANGELOG`, `DATABASECHANGELOGLOCK` tables). File timestamps within DDL scripts indicate the schema was last captured 10 October 2024.

---

## 2. Business Processes Supported

### 2.1 Cross-Border Transfer Initiation
- A **remitter** (the US-based account holder at Onbe) is registered in `REMITTER`. The remitter's identity includes first name, last name, address (FK to `ADDRESS`), an `ACCOUNT_IDENTIFIER`, brand (client program), and gateway identifier (`GATEWAY_REMITTER_ID`).
- A **beneficiary** (the overseas recipient) is registered in `BENEFICIARY`. Key fields: first name, last name, bank currency, payment method, phone number, email, **SWIFT/BIC code**, **bank account number**, **routing code**, gateway beneficiary ID, address (two FK references to `ADDRESS`).
- **Rate quotation**: When a transfer is initiated, a rate (`RATE`) is locked at a point in time — capturing payers' currency, beneficiaries' currency, exchange rate value, request type, and a gateway booking/rate ID. The rate's status progresses through a lifecycle (e.g., QUOTED → LOCKED → USED).
- **Transfer execution**: The `TRANSFER` table records the execution: rate ID, beneficiary ID, fee amount, status, and a gateway-side transfer reference (`GATEWAY_TRANSFER_ID`).

### 2.2 Transfer Return Processing
- If the gateway rejects or reverses a transfer, `TRANSFER_RETURN` records the return event: wire number, payment reference, payee, reason, currency, amount, USD equivalent, and FX rate. The `CLOSED` flag marks when the return is resolved.

### 2.3 Regulatory Rule Enforcement
- `BENEFICIARY_REGULATORY_RULE` links each beneficiary to applicable regulatory rules, enabling country-specific compliance checks (e.g., Mexico SPEI limits, EU transfer caps, OFAC-restricted corridors).

### 2.4 Reconciliation
- `RECON_FILE` tracks inbound reconciliation files from the gateway (each record represents one file: amount, count, currency, file status, source, and timestamps). This supports T+1 settlement reconciliation and is critical for NACHA-equivalent cross-border settlement.

### 2.5 Spring Batch Job Management
The CBTS service is a **Java Spring Batch** application. The database carries the full Spring Batch infrastructure:
- `BATCH_JOB_INSTANCE` — each distinct job definition run
- `BATCH_JOB_EXECUTION` — each execution of a job instance (start/end time, status, exit code)
- `BATCH_JOB_EXECUTION_PARAMS` — parameter values per execution
- `BATCH_JOB_EXECUTION_CONTEXT` — serialised execution context (JSON)
- `BATCH_STEP_EXECUTION` — per-step execution detail (read/write/skip counts, commit counts)
- `BATCH_STEP_EXECUTION_CONTEXT` — serialised step context
- Sequence tables: `BATCH_JOB_EXECUTION_SEQ`, `BATCH_JOB_SEQ`, `BATCH_STEP_EXECUTION_SEQ`

These tables indicate CBTS is a modern (Gen-3 class) microservice, not a legacy stored-procedure-driven component.

### 2.6 Rate History
- `RATE_HISTORY` captures previous versions of rate records, enabling audit of rate changes over the lifecycle of a transfer.

### 2.7 Transfer History
- `TRANSFER_HISTORY` captures previous states of transfer records, supporting dispute resolution and audit.

---

## 3. Business Rules

- Each `TRANSFER` must reference a valid `BENEFICIARY` and a valid `RATE` (enforced via `FK_TRANSFER_BENEFICIARY` and `FK_TRANSFER_RATE`).
- Each `BENEFICIARY` must reference a valid `REMITTER` (`FK_BENE_REMITTER`) and two valid `ADDRESS` records (holder address and bank address).
- Each `RATE` must reference a valid `REMITTER` (`FK_RATE_REMITTER`).
- `TRANSFER_ID` on `TRANSFER` has a unique constraint (`UDX_TRANSFER_TX_REF_ID`), enforcing idempotent transfer references.
- `BENEFICIARY_ID` on `BENEFICIARY` has a unique constraint (`UDX_BENEFICIARY_ID`).
- `REMITTER_ID` on `REMITTER` has a unique constraint (`UDX_REMITTER_ID`).
- `ENABLED` flag on `BENEFICIARY` and `REMITTER` allows soft-deactivation without data deletion.

---

## 4. Regulatory Relevance

### OFAC / Sanctions
- `BENEFICIARY_REGULATORY_RULE` provides the hook for sanctions/corridor restrictions. The gateway routing in `GATEWAY` and `SWIFT_BIC_CODE` fields indicate international wire transfers subject to OFAC screening.
- Account numbers (`ACCOUNT_NUMBER` in `BENEFICIARY`) and routing codes (`ROUTING_CODE`) for foreign bank accounts must be screened before transfer initiation.

### FinCEN / BSA / AML
- Cross-border wire transfers above USD 3,000 trigger FinCEN Travel Rule recordkeeping requirements (31 CFR § 1010.410). `REMITTER` and `BENEFICIARY` hold the required originator/beneficiary information.
- Transfers above USD 10,000 may trigger CTR (Currency Transaction Report) obligations.
- `TRANSFER_RETURN` records failed/returned transfers relevant to SAR (Suspicious Activity Report) investigations.

### GDPR / CCPA
- `BENEFICIARY`: first name, last name, email, phone number, bank account number, bank address — personal data of an international individual.
- `REMITTER`: first name, last name, address, account identifier — personal data of a US cardholder.
- Both sets of data are subject to privacy regulations, including international transfer provisions of GDPR (Chapter V for transfers outside the EU).

### Reg E
- Cross-border remittance transfers to consumers are governed by the CFPB's Remittance Transfer Rule (an extension of Reg E, 12 CFR Part 1005 Subpart B). Key requirements: pre-payment disclosure, recipient information, exchange rate and fee disclosure, cancellation rights, and error resolution.
- `RATE` table fields (exchange rate, fee amount) directly support the required disclosures.
- `TRANSFER_RETURN` supports the error-resolution and cancellation processes required by Reg E.

---

## 5. Data Flows

```
US Remitter (Onbe cardholder)
         |
         v
CBTS API (Spring Batch / REST service)
         |
         +---> REMITTER (register/update sender identity)
         |
         +---> BENEFICIARY (register overseas recipient)
         |
         +---> RATE (lock FX rate with gateway)
         |           |
         |           v
         |     Gateway (external FX/wire provider)
         |
         +---> TRANSFER (initiate transfer; gateway executes)
         |
         +---> RECON_FILE (reconcile settlement T+1)
         |
         +---> TRANSFER_RETURN (handle returns/rejections)
         |
         +---> BATCH_JOB_EXECUTION (Spring Batch job tracking)
```

---

## 6. Table Count and Object Summary

| Object Type | Count |
|---|---|
| Tables | 22 |
| Views | 0 (none found) |
| Stored Procedures | 0 (none found — application logic in Java) |
| Functions | 0 |
| Security scripts | 5 (cbts_data.sql, cbts_user.sql, individual NAM grants) |

---

## 7. Key Observations for Business Stakeholders

1. **Modern architecture**: CBTS uses Liquibase for schema migrations and Spring Batch for job management — a significantly more modern pattern than cbaseapp.
2. **Minimal stored-procedure logic**: All business logic resides in the Java service layer; the database is a pure data store.
3. **International payment risk**: This database holds foreign bank account numbers and SWIFT codes — among the most sensitive financial data in the Onbe platform.
4. **Gateway dependency**: The `GATEWAY` column on `TRANSFER`, `BENEFICIARY`, `RATE`, and `REMITTER` indicates all operations route through a single configurable gateway provider. Gateway failure or credential compromise would halt all cross-border transfers.
