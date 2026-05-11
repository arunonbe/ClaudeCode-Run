# comment_LIB — Business Analyst View

## Business Purpose

comment_LIB is a shared Java library (`com.ecount.services.comment`, artifact `comment`, version `3.0.1`) that provides a centralised Customer Service Agent (CSA) comment/inquiry recording and escalation capability for the prepaid card platform. It is consumed as a JAR dependency by upstream applications that need to log cardholder service interactions, route escalations to assigned reviewers, and retrieve full comment histories against a member account or transaction reference.

The library is part of the `prepaid-parent` (groupId `com.parents`, version `6.0.12`) module family, meaning it is a reusable infrastructure component rather than a deployable service.

## Business Capabilities

1. **Auto-Comment Recording** — Allows system processes (batch jobs, payment engines, etc.) to automatically post a comment against a member account when a predefined activity occurs (e.g., address change, ACH withdrawal, PIN reset). Entry point: `ICommentService.insertComment(String memberId, String userId, String inquirySource, String commentText, String activity)`.

2. **Manual Comment Recording (CSA-initiated)** — Allows a CSA user to post a typed comment with a specific inquiry type, category, status, and escalation priority against a member/application record. Supports both standard and DDA-number-qualified variants. Entry point: `ICommentService.insertComment(Integer lastRefID, String memberId, ...)`.

3. **Escalation Lifecycle Management** — Supports creation (`insertCommentEscalation`), update (`updateCommentEscalation`), and retrieval (`getEscalationDetail`) of formal escalation records linked to an inquiry. An escalation captures submitter, reviewer, assignee (by role ID), cardholder first/last name, device ID, issue description, and closing comment.

4. **Comment History Retrieval** — Retrieves paginated comment history for a given member ID, application ID, reference ID, and comment ID. Default page size is 100 rows; callers may override via `maxRowSize`. Entry point: `ICommentService.getCommentHistory(...)`.

5. **Reference-Data Lookup** — Provides lookup lists used by CSA UIs:
   - `getCommentCategories()` — returns all inquiry type categories.
   - `getCommentTypesByCategory(Integer)` — returns inquiry types filtered by category.
   - `getCommentTypes()` — returns all inquiry types (flat list).
   - `getEscalationAssignees()` — returns the list of valid escalation assignees.

## Business Entities

| Entity | Class | Key Fields |
|---|---|---|
| Comment (inquiry record) | `CommentHistoryValue` | `inquiryIdNumber`, `applicationSpecificKey` (memberId), `applicationId`, `problemDescription`, `closed`, `inquiryType`, `responseType`, `priority`, `userRole`, `closingComment`, `origDateReceived` |
| Comment Escalation | `CommentEscalationValue` | `id`, `inquiryIdNumber`, `commentId`, `firstName`, `lastName`, `reviewer`, `assignee`, `submitter`, `ecountId`, `deviceId`, `issueDescription`, `closingComment`, `status`, `priority` |
| Escalation Assignee | `EscalationAssigneeValue` | `assigneeId`, `assigneeDescription` |
| Inquiry Type | `GetCsaInquiryTypesByInquiryCategoryValue` | `inquiryType`, `inquiryTypeCategory`, `inquiryDesc` |
| Inquiry Category | `GetCsaInquiryTypesCategoryValue` | `inquiryTypeCategory`, `inquiryTypeCategoryDesc`, `programId` |

## Business Rules & Validations

1. **Auto-comment status defaults to "closed" (value 1)** — Hard-coded in `CommentServiceImpl.insertComment(String, String, String, String, String)` at line 302: `close = 1`. Manual comments pass the status explicitly.

2. **Activity-to-inquiry-type resolution** — For auto-comments, the library looks up the inquiry type code from the `inquiry_type_activity_xref` table via `JDBCCommentorDAOImpl.getInquiryType(String activity)` (line 61–65), then derives the category from `dbo.csa_GetInquiryTypesCategoryByInquiryType`. The `CommentConstants` class defines 40+ valid activity strings (e.g., `"address-update"`, `"pin-reset"`, `"ach-withdrawal"`).

3. **Null guard on escalation detail** — `CommentServiceImpl.getEscalationDetail` (line 406) returns `null` immediately if `inquiryIdNumber` is null, preventing a database call with a null key.

4. **descSolution parameter is always passed as empty string** — All four auto-comment overloads in `CommentServiceImpl` pass `""` as `descSolution` to `InsertCommentDAOImpl`, suppressing the free-text solution field for system-generated comments.

5. **DDA number scope** — DDA (Demand Deposit Account) number is an optional parameter. When not provided in auto-comment flows it is passed as `null` (line 345 of `CommentServiceImpl`); the DAO maps it to an empty string default.

6. **Application ID is configurable per consumer** — `CommentServiceImpl.applicationId` is injected at wire-up time (Spring XML, `comment.xml` line 25: `value="12"`). Each consuming application sets its own application ID.

7. **Comment history default row limit** — `CommentHistoryDAOImpl.execute(...)` defaults `maxRowSize` to 100 when no limit is supplied (line 42).

## Business Flows

### Auto-Comment Flow
```
Caller (batch/service) → ICommentService.insertComment(memberId, userId, source, text, activity)
  → JDBCCommentorDAO.getInquiryType(activity)       [SELECT from inquiry_type_activity_xref]
  → JDBCCommentorDAO.getInquiryCategoryCode(type)   [dbo.csa_GetInquiryTypesCategoryByInquiryType]
  → InsertCommentDAOImpl.execute(...)               [dbo.csa_insertcsdet → returns inquiry_id]
```

### Manual Comment Flow
```
CSA UI → ICommentService.insertComment(lastRefID, memberId, text, status, userId, ...)
  → InsertCommentDAOImpl.execute(...)               [dbo.csa_insertcsdet → returns inquiry_id]
```

### Escalation Creation Flow
```
CSA supervisor → ICommentService.insertCommentEscalation(inquiryIdNumber, firstName, ...)
  → InsertCommentEscalationDAOImpl.execute(...)     [dbo.csa_insert_service_records_escalation → returns escalation_id]
```

### Escalation Update Flow
```
Reviewer → ICommentService.updateCommentEscalation(inquiryIdNumber, commentId, status, ...)
  → UpdateCommentEscalationDAOImpl.execute(...)     [dbo.csa_update_service_records_escalation → returns result code]
```

### Comment History Retrieval Flow
```
CSA UI → ICommentService.getCommentHistory(memberId, appId, refID, commentId [, maxRows])
  → CommentHistoryDAOImpl.execute(...)              [dbo.csa_bc_get_comment_history → result set]
  ← List<CommentHistoryValue>
```

## Compliance & Regulatory Concerns

1. **PII in comment text** — `ProblemText` / `problemDescription` is a free-text VARCHAR stored in the `cbaseapp` database. CSA agents and automated processes may embed cardholder name, address, phone, email, or account identifiers in comment text. There is no PII masking, tokenisation, or field-level encryption at the library level.

2. **DDA number as clear text** — `dda_number` is passed as a plain VARCHAR parameter to `dbo.csa_insertcsdet` and stored without any masking. DDA numbers are bank account identifiers; their clear-text storage may be material under Reg E, GLBA, and PCI DSS CDE boundary assessments.

3. **Cardholder name in escalation records** — `InsertCommentEscalationDAOImpl` passes `first_name` and `last_name` as plain VARCHAR to `dbo.csa_insert_service_records_escalation`. Escalation records containing cardholder names are PII under CCPA, GDPR, and GLBA.

4. **`ecountId` in escalation records** — `ecountId` (an Onbe/eCount member identifier) is stored in the escalation table alongside cardholder name, device ID, and issue description. The combination constitutes a linked personal data record.

5. **Reg E audit trail** — The comment history mechanism (`dbo.csa_bc_get_comment_history`) serves as part of the Reg E dispute and error-resolution audit trail. Data retention adequacy of the `cbaseapp` database is not governed by this library.

6. **No access control** — The library accepts a `userId` / `employeeId` string but performs no authentication or authorisation check. Callers are assumed to be already authenticated.

## Business Risks

1. **Unchecked raw SQL in `JDBCCommentorDAOImpl`** — The `getInquiryType` method at line 61 constructs a SQL string inline and passes the `activity` parameter via a positional `?` placeholder (safe). However the log statement at line 60 (`log.info("getInquiryType : " + activity)`) could leak internal activity labels to log aggregators.

2. **No input length validation** — `commentText` / `problemText` and `issueDescription` are passed directly to `LONGVARCHAR` stored procedure parameters without truncation or validation. Excessively long strings could cause silent truncation in the database.

3. **Silent descSolution suppression** — Passing `""` unconditionally as `descSolution` means the description-of-solution field is never populated for auto-comments, reducing the value of the comment history audit trail.

4. **Activity string typos not caught at compile time** — `CommentConstants` strings (e.g., `"ach-other"`, `"pin-reset"`) are runtime strings. A misspelled activity will result in a `EmptyResultDataAccessException` at runtime from `getInquiryType`.

5. **Test credentials in version control** — `src/test/resources/commentTest.xml` contains a hardcoded JDBC URL pointing to `q-lis-db01.nam.wirecard.sys:2231` (a QA environment) with username `csa` and password `csa`. This is a legacy Wirecard-era hostname and credential pair committed to the repository.
