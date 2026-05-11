# comment_LIB — Data Architect View

## Data Stores

| Store | Type | Connection | Notes |
|---|---|---|---|
| `cbaseapp` | Microsoft SQL Server | JNDI `java:comp/env/jdbc/CbaseappDataSource` (production) | All production reads and writes |
| `cbaseapp` (QA) | Microsoft SQL Server | `jdbc:sqlserver://q-lis-db01.nam.wirecard.sys:2231;instanceName=q-lis-db01;databaseName=cbaseapp` | Test-only; hardcoded in `commentTest.xml` |

The library operates exclusively against a single SQL Server database named `cbaseapp`. There is no secondary store, cache, or message queue.

## Schema & Tables

The library does not create or migrate schema. All DDL is external. The following database objects are referenced directly:

### Stored Procedures (via Spring `StoredProcedure`)

| Stored Procedure | DAO Class | Operation |
|---|---|---|
| `dbo.csa_insertcsdet` | `InsertCommentDAOImpl` | INSERT comment record; returns `inquiry_id` (OUT INTEGER) |
| `dbo.csa_bc_get_comment_history` | `CommentHistoryDAOImpl` | SELECT comment history result set |
| `dbo.csa_insert_service_records_escalation` | `InsertCommentEscalationDAOImpl` | INSERT escalation record; returns `service_records_escalation_id` (OUT INTEGER) |
| `dbo.csa_update_service_records_escalation` | `UpdateCommentEscalationDAOImpl` | UPDATE escalation record; returns `result` (OUT INTEGER) |
| `dbo.csa_get_service_records_escalation` | `CommentEscalationDetailDAOImpl` | SELECT escalation detail result set |
| `dbo.csa_GetInquiryTypesCategoryByInquiryType` | `GetCsaInquiryCategoryByInquiryTypeDAOImpl` | SELECT inquiry_type_category (OUT INTEGER) for a given inquiry_type |
| `dbo.csa_GetInquiryTypesByCategory` | `GetCsaInquiryTypesByInquiryCategoryDAOImpl` | SELECT inquiry types for a given category |
| `dbo.csa_GetInquiryTypesCategory` | `GetCsaInquiryTypesCategoryDAOImpl` | SELECT all inquiry type categories (filtered by programId) |
| `dbo.csa_GetInquiryTypes_All` | `GetCsaInquiryTypesDAOImpl` | SELECT all inquiry types (flat) |
| `dbo.csa_get_escalation_assignee` | `GetEscalationAssigneeDAOImpl` | SELECT escalation assignee list |

### Ad-hoc Query Table

| Table | Query Location | Columns Accessed |
|---|---|---|
| `inquiry_type_activity_xref` | `JDBCCommentorDAOImpl.getInquiryType()` line 61–65 | `inquiry_type` (SELECT), `activity` (WHERE) |

### Inferred Column Surfaces (from RowMapper and parameter declarations)

**Comment record (`dbo.csa_insertcsdet` inputs):**
`lastRefID` (INT), `application_specific_key` (VARCHAR), `ProblemText` (VARCHAR), `close` (INT), `EmployeeID` (VARCHAR), `DescSolution` (VARCHAR), `InquiryType` (INT), `ResponseType` (INT), `Application_id` (INT), `emailorphone` (VARCHAR), `EscalationPriority` (CHAR), `dda_number` (VARCHAR) — output: `inquiry_id` (INT)

**Comment history result set (`dbo.csa_bc_get_comment_history` outputs):**
`reference_id`, `comment_id`, `ErrorId`, `application_specific_key`, `OrigDateReceived`, `ProblemDescription`, `Response1`, `Response2`, `Response3`, `Mostrecentinqdate`, `Closed`, `Date_Closed`, `EmployeeID_Close`, `Tasks`, `Description_of_solution`, `Inquiry_Type`, `Inquiry_Type_Desc`, `Response_Type`, `Response_Type_Desc`, `Application_id`, `emailorphone`, `Inquiry_Type_Category_Desc`, `Inquiry_Type_Category_Code`, `UserRole`, `priority`, `Status_Description`, `closingComment`

**Escalation record inputs (`dbo.csa_insert_service_records_escalation`):**
`inquiry_id_number` (INT), `first_name` (VARCHAR), `last_name` (VARCHAR), `reviewer` (VARCHAR), `assignee` (INT), `closing_comment` (LONGVARCHAR), `issue_description` (LONGVARCHAR), `ecount_id` (VARCHAR), `submitter` (VARCHAR), `device_id` (VARCHAR) — output: `service_records_escalation_id` (INT)

**Escalation record outputs (`dbo.csa_get_service_records_escalation`):**
`id`, `inquiry_id_number`, `first_name`, `last_name`, `reviewer`, `assignee`, `closing_comment`, `submitter`, `issue_description`

**Escalation update inputs (`dbo.csa_update_service_records_escalation`):**
`inquiry_id_number` (INT), `comment_id` (INT), `closer` (VARCHAR), `status` (INT), `closing_comment` (LONGVARCHAR), `issue_description` (LONGVARCHAR), `assignee` (INT) — output: `result` (INT)

## Sensitive Data Handling

| Field | Classification | Current Handling |
|---|---|---|
| `application_specific_key` / `memberId` | Member identifier (PII) | Plain VARCHAR; no masking at library layer |
| `dda_number` | Bank account number (PII / financial) | Plain VARCHAR; stored as-is via `dbo.csa_insertcsdet` parameter `dda_number` |
| `first_name`, `last_name` | Cardholder name (PII) | Plain VARCHAR in escalation insert/retrieve |
| `ecount_id` | Internal cardholder identifier | Plain VARCHAR in escalation table |
| `emailorphone` | Contact data (PII) | Plain VARCHAR in comment record |
| `device_id` | Device identifier | Plain VARCHAR in escalation record |
| `ProblemText` / `ProblemDescription` | Free-text CSA note (may contain PII) | Unstructured VARCHAR/LONGVARCHAR; no scanning or redaction |
| `issue_description`, `closing_comment` | Free-text escalation notes (may contain PII) | LONGVARCHAR; no scanning or redaction |
| `EmployeeID` | Internal staff ID | Plain VARCHAR |

None of these fields is masked, tokenised, or encrypted within the library. All protection must be provided by the consuming application or at the database/infrastructure level.

`CommentHistoryValue.getProblemDescriptionJSEscape()` applies `StringEscapeUtils.escapeJavaScript()` (Apache Commons Lang) to the problem description before returning it — this is an output-encoding safeguard for web rendering, not a data protection measure.

## Encryption & Protection

- No field-level encryption is implemented in this library.
- No data masking is applied to any parameter before it is sent to the stored procedures.
- The test JDBC URL (`commentTest.xml`) specifies `sslProtocol=TLSv1.2` and `trustServerCertificate=true`. `trustServerCertificate=true` disables server certificate validation, which presents a man-in-the-middle risk for the test configuration.
- The production connection is obtained via JNDI (`java:comp/env/jdbc/CbaseappDataSource`). TLS configuration for the production connection is controlled by the Tomcat/application-server JNDI resource definition, which is outside this library.
- Credentials for the test database (`username=csa`, `password=csa`) are committed in plaintext in `src/test/resources/commentTest.xml`.

## Data Flow

```
Caller Application
    │
    │  (Spring bean injection via comment.xml)
    ▼
CommentServiceImpl
    │
    ├─► InsertCommentDAOImpl ──────────────────► dbo.csa_insertcsdet         [WRITE: comment row]
    ├─► InsertCommentEscalationDAOImpl ────────► dbo.csa_insert_...escalation [WRITE: escalation row]
    ├─► UpdateCommentEscalationDAOImpl ────────► dbo.csa_update_...escalation [UPDATE: escalation row]
    ├─► CommentHistoryDAOImpl ─────────────────► dbo.csa_bc_get_comment_history [READ: result set]
    ├─► CommentEscalationDetailDAOImpl ────────► dbo.csa_get_...escalation    [READ: result set]
    ├─► JDBCCommentorDAOImpl ──────────────────► inquiry_type_activity_xref   [READ: inline SQL]
    │       └─► GetCsaInquiryCategoryByInquiryTypeDAOImpl ► dbo.csa_GetInquiryTypesCategoryByInquiryType
    ├─► GetCsaInquiryTypesCategoryDAOImpl ─────► dbo.csa_GetInquiryTypesCategory [READ]
    ├─► GetCsaInquiryTypesByInquiryCategoryDAOImpl ► dbo.csa_GetInquiryTypesByCategory [READ]
    ├─► GetCsaInquiryTypesDAOImpl ─────────────► dbo.csa_GetInquiryTypes_All [READ]
    └─► GetEscalationAssigneeDAOImpl ──────────► dbo.csa_get_escalation_assignee [READ]
```

All traffic flows to a single `DataSource` bean named `CbaseappDataSource`.

## Data Quality & Retention

- **No input validation** exists in the library. Length limits, null checks (except for `inquiryIdNumber` in `getEscalationDetail`), and format constraints are entirely delegated to the SQL Server stored procedures.
- **`descSolution` is always passed as empty string** for auto-comments (`CommentServiceImpl` lines 303, 344, 365), meaning the `Description_of_solution` column will be blank for all system-generated records.
- **Default row limit of 100** is applied to comment history queries when no `maxRowSize` is given (`CommentHistoryDAOImpl` line 42). This may silently truncate history for high-volume accounts.
- **Retention policy** is not defined in this library. The `Date_Closed`, `OrigDateReceived`, and `Mostrecentinqdate` columns are read back but no archival or purge logic exists here.
- **`programId` defaults to `"00000000"`** in `GetCsaInquiryTypesCategoryDAOImpl.execute()` (line 36), which may return a superset of categories not valid for a specific program if callers use the no-argument variant.

## Compliance Gaps

1. **DDA number stored in clear text** — `dda_number` is a bank account number stored as a plain VARCHAR in the `cbaseapp` database. Under GLBA and Reg E this field is a sensitive financial identifier; it should be masked or tokenised at insert time.

2. **No PII field-level classification** — Free-text fields (`ProblemText`, `issue_description`, `closing_comment`) may contain PANs, SSNs, or full cardholder details typed by CSA agents. There is no detection, masking, or DLP hook.

3. **Cardholder name in escalation table** — `first_name` + `last_name` are stored linked to `ecount_id` and `device_id`. This combination is a personal data record under GDPR Article 4 and CCPA, requiring a lawful basis for retention, subject-access support, and a documented retention period.

4. **Test credentials committed** — Username `csa` / password `csa` against a named QA server (`q-lis-db01.nam.wirecard.sys`) are stored in `src/test/resources/commentTest.xml`. Even for a QA environment this violates credential hygiene standards and may be material for SOC 2 CC6.1.

5. **`trustServerCertificate=true` in test config** — Disables TLS certificate validation, allowing potential MITM during test runs against the QA database which may hold real or near-real data.

6. **No data lineage metadata** — There is no correlation ID, trace ID, or request identifier attached to inserted records, making it difficult to link a comment row back to the originating business transaction for audit purposes.
