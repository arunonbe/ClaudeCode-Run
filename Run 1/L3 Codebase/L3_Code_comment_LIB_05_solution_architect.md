# comment_LIB — Solution Architect View

## Technical Architecture

comment_LIB is a **Spring-managed, stateless service library** compiled to a JAR for Java 21. It follows a layered architecture:

```
ICommentService (interface)
    └─ CommentServiceImpl (service layer)
            ├─ CommentHistoryDAOImpl          extends StoredProcedure
            ├─ InsertCommentDAOImpl            extends StoredProcedure
            ├─ InsertCommentEscalationDAOImpl  extends StoredProcedure
            ├─ UpdateCommentEscalationDAOImpl  extends StoredProcedure
            ├─ CommentEscalationDetailDAOImpl  extends StoredProcedure
            ├─ GetCsaInquiryTypesCategoryDAOImpl     extends StoredProcedure
            ├─ GetCsaInquiryTypesByInquiryCategoryDAOImpl extends StoredProcedure
            ├─ GetCsaInquiryTypesDAOImpl       extends StoredProcedure
            ├─ GetEscalationAssigneeDAOImpl    extends StoredProcedure
            ├─ GetCsaInquiryCategoryByInquiryTypeDAOImpl extends StoredProcedure
            └─ JDBCCommentorDAOImpl            extends JdbcTemplate
```

All DAO classes are concrete implementations that extend Spring JDBC abstractions directly. There are no interfaces for the DAO layer — `CommentServiceImpl` is tightly coupled to concrete DAO `Impl` classes (e.g., `private InsertCommentDAOImpl insertCommentDAO` at line 34 of `CommentServiceImpl`), which prevents DAO substitution or mocking without Reflection or Powermock.

Domain objects (value objects) are in the `com.ecount.services.comment.dao.domain` package. All implement `java.io.Serializable` and provide manually coded `equals` / `hashCode` based on their fields.

Bean wiring is XML-only (`comment.xml`). Spring IoC is the only lifecycle manager; there is no constructor injection — `CommentServiceImpl` uses setter injection exclusively.

## API Surface

The library exposes a single public service interface:

### `ICommentService` — `src/main/java/com/ecount/services/comment/ICommentService.java`

| Method Signature | Purpose |
|---|---|
| `void insertComment(String memberId, String userId, String inquirySource, String commentText, String activity)` | Auto-comment (no DDA) |
| `void insertComment(String memberId, String userId, String inquirySource, String commentText, String activity, String DDAnumber)` | Auto-comment with DDA |
| `Integer insertComment(Integer lastRefID, String memberId, String commentText, Integer status, String userId, String descSolution, Integer inquiryTypeCode, Integer inquiryCategoryCode, Integer applicationId, String inquirySource, String escalationPriority)` | Manual comment (no DDA) |
| `Integer insertComment(Integer lastRefID, String memberId, String commentText, Integer status, String userId, String descSolution, Integer inquiryTypeCode, Integer inquiryCategoryCode, Integer applicationId, String inquirySource, String escalationPriority, String DDAnumber)` | Manual comment with DDA |
| `Integer insertCommentEscalation(String inquiryIdNumber, String firstName, String lastName, String reviewer, Integer assignee, String closingComment, String issueDescription, String ecountId, String submitter, String deviceId)` | Create escalation record |
| `Integer updateCommentEscalation(Integer inquiryIdNumber, Integer commentId, Integer status, String closingComment, String issueDescription, String closer, Integer assignee)` | Update escalation record |
| `CommentEscalationValue[] getEscalationDetail(Integer inquiryIdNumber, Integer commentId)` | Retrieve escalation detail |
| `List getCommentHistory(String memberId, Integer applicationID, Integer refID, Integer commentId)` | Retrieve comment history (default limit 100) |
| `List getCommentHistory(String memberId, Integer applicationID, Integer refID, Integer commentId, Integer maxRowSize)` | Retrieve comment history (specified limit) |
| `List getCommentCategories()` | Reference data: all inquiry categories |
| `List getCommentTypesByCategory(Integer commentCategory)` | Reference data: types by category |
| `List getCommentTypes()` | Reference data: all inquiry types |
| `EscalationAssigneeValue[] getEscalationAssignees()` | Reference data: valid assignees |

There is no REST, SOAP, or messaging API. This is a purely in-process Java API.

### `CommentConstants` — Activity String Catalogue
Defines 40 activity string constants used by callers to trigger auto-comments. Notable examples:
- `ACTIVITY_PIN_RESET = "pin-reset"`
- `ACTIVITY_ACH_WITHDRAWAL = "ach-withdrawal"`
- `ACTIVITY_ADDRESS_UPDATE = "address-update"`
- `ACTIVITY_PAYMENT_REVERSAL = "third-party-deposit-cancel"` — has an inline `//TODO: to confirm` at line 70, indicating uncertainty about the correct activity string.
- `ACTIVITY_IEFT_BLOCK_BENEFICIARY = "ieft-block-beneficiary"` — added for JIRA 156 (comment at line 136).

## Security Posture

### Authentication & Authorisation
- **None at library level.** The library accepts `userId` / `employeeId` as opaque strings. There is no token validation, role check, or permission enforcement. The calling application is fully responsible.

### Input Validation
- No field length validation. All string parameters are passed directly to stored procedure parameters.
- `memberId` passed as `application_specific_key` could be any string; no format (e.g., GUID) is enforced.
- `activity` string in `JDBCCommentorDAOImpl.getInquiryType` (line 61) is passed as a positional bind parameter `?` — SQL injection safe. However, if the activity string does not match any row, Spring's `queryForObject` throws `EmptyResultDataAccessException` (unchecked), which propagates uncaught through `getInquiryType` and is caught as a generic `RuntimeException` in `CommentServiceImpl`, then re-thrown as `AutoCommentException`.

### Credential Exposure
- `src/test/resources/commentTest.xml` line 17–18: username `csa`, password `csa` committed in plaintext against a named QA server (`q-lis-db01.nam.wirecard.sys:2231`). This is a CWE-798 (Use of Hard-coded Credentials) finding.
- `trustServerCertificate=true` in the same file disables TLS certificate validation (CWE-295).

### Logging Security
- `JDBCCommentorDAOImpl` line 60: `log.info("getInquiryType : " + activity)` — logs the raw activity string. While `CommentConstants` strings are internal codes, any caller passing a freeform string would have it logged.
- `AutoCommentException.printStackTrace()` logs exception cause to SLF4J INFO, which may expose stack traces and internal class names to log aggregation systems.
- Error messages returned to callers: `"Unable to Add Auto Comment: " + e.getMessage()` — may expose database error messages containing schema details.

### Data Protection
- No field-level encryption or masking at any layer (see `02_data_architect.md` for detail).
- `CommentHistoryValue.getProblemDescriptionJSEscape()` uses `StringEscapeUtils.escapeJavaScript()` (Apache Commons Lang 2.x — not Commons Text; the older library is referenced by `commons-lang:commons-lang`). This is an XSS output-encoding safeguard for JSP/JavaScript rendering, but Commons Lang 2.x is end-of-life.

## Technical Debt

| Item | Location | Severity | Description |
|---|---|---|---|
| Raw `List` return types | `ICommentService` methods `getCommentCategories()`, `getCommentTypesByCategory()`, `getCommentTypes()` | Medium | Pre-generics `List` without type parameter; callers require unchecked casts |
| Concrete DAO injection | `CommentServiceImpl` fields (lines 31–58) | Medium | Service depends on concrete `*DAOImpl` classes not interfaces, preventing unit testing with mocks |
| `TODO: Auto-generated Javadoc` | All source files | Low | Unreviewed IDE-generated Javadoc; no meaningful documentation added |
| `TODO: to confirm` | `CommentConstants.java` line 70 | Medium | `ACTIVITY_PAYMENT_REVERSAL = "third-party-deposit-cancel"` is unconfirmed; if wrong, auto-comments fail silently with wrong inquiry type |
| `descSolution` always `""` | `CommentServiceImpl` lines 303, 344, 365 | Low | Solution description is never populated for auto-comments; reduces audit trail value |
| Hardcoded `applicationId = 12` | `comment.xml` line 25 | Medium | Inflexible; consuming applications that need a different application ID must override the bean definition |
| `programId = "00000000"` default | `GetCsaInquiryTypesCategoryDAOImpl.execute()` line 36 | Low | May return categories across all programs rather than program-specific subset |
| Raw `HashMap` without generics | `CommentEscalationDetailDAOImpl.execute()` line 36, others | Low | Unchecked raw type warnings; suppressed by compiler |
| `AutoCommentException` reimplements `getCause()` | `AutoCommentException.java` | Low | Manually stores and returns `cause` rather than using `super(message, cause)` constructor; `super.getCause()` would return `null` |
| `LinkedList` unused import | `UpdateCommentEscalationDAOImpl.java` line 6 | Low | `LinkedList` is imported but not used in the class body |
| Commons Lang 2.x dependency | `pom.xml` (inherited) | Medium | `commons-lang:commons-lang` is Apache Commons Lang 2, which is end-of-life; `org.apache.commons:commons-lang3` should be used instead |
| Test skipped in CI | `github-package-publish.yml` line 39 | High | `-Dmaven.test.skip` means no test is ever executed in CI; regressions go undetected |
| Credentials in source | `commentTest.xml` lines 17–18 | Critical | Plaintext database credentials committed to git history |

## Gen-3 Migration Requirements

To migrate this library's capability into a Gen-3 (Spring Boot microservice / cloud-native) architecture, the following are required:

1. **Extract CSA Comment Service as a standalone microservice** — Replace the shared JAR pattern with a dedicated Spring Boot service exposing REST endpoints (e.g., `POST /comments`, `GET /members/{id}/comments`, `POST /escalations`).

2. **Replace stored procedures with repository pattern** — Port `dbo.csa_insertcsdet`, `dbo.csa_bc_get_comment_history`, and all other stored procedures to Spring Data JPA repositories or Spring JDBC named queries. Stored procedure source DDL must be obtained from the DBA team (not in this repository).

3. **Replace JNDI DataSource with Spring Boot `DataSource` auto-configuration** — Use `application.yml` / environment variable driven datasource configuration backed by a secrets manager (Azure Key Vault or equivalent).

4. **Introduce secrets management** — Remove all hardcoded credentials. Use managed identity or vault-based secret retrieval for database credentials.

5. **Replace XML bean wiring** — Convert all `comment.xml` bean definitions to `@Configuration` / `@Bean` or `@Component` / `@Autowired` Spring Boot patterns.

6. **Add DAO interfaces** — Introduce DAO interfaces so `CommentService` depends on abstractions, enabling unit testing with Mockito.

7. **Generify the `List` return types** — Replace raw `List` with `List<CommentHistoryValue>`, `List<GetCsaInquiryTypesCategoryValue>`, etc. throughout `ICommentService`.

8. **Add input validation** — Apply `@Valid` / `@NotNull` / `@Size` constraints or explicit validation logic before database calls.

9. **Add observability** — Instrument with Micrometer metrics (comment insert rate, escalation count, error rate) and add structured logging with correlation IDs.

10. **Replace Commons Lang 2.x** — Upgrade to `commons-lang3` or remove the dependency if only `StringEscapeUtils` is needed (use `commons-text` instead).

11. **Implement transaction management** — Wrap `insertComment` + `insertCommentEscalation` sequences in a `@Transactional` boundary so partial failures roll back both writes.

12. **Rename package namespace** — Migrate from `com.ecount.services.comment` to the appropriate Onbe namespace (e.g., `com.onbe.services.comment`).

## Code-Level Risks

1. **`AutoCommentException` swallows root cause from `super()`** (`AutoCommentException.java` lines 40–44)
   - Constructor `AutoCommentException(String message, Throwable cause)` calls `super(message)` (not `super(message, cause)`), so `Throwable.getCause()` from the standard JDK mechanism returns `null`. The cause is stored only in the private `cause` field. If any framework catches `Throwable.getCause()` (e.g., logging frameworks, monitoring agents), the original exception is silently dropped.

2. **`EmptyResultDataAccessException` on unknown activity** (`JDBCCommentorDAOImpl.java` lines 58–65)
   - `queryForObject` throws `EmptyResultDataAccessException` if `activity` has no matching row in `inquiry_type_activity_xref`. This propagates up through `CommentServiceImpl` as a `RuntimeException`, which is caught and re-thrown as `AutoCommentException`. The caller receives a generic "Unable to Add Auto Comment" message with no indication that the activity string is invalid.

3. **Array-return on escalation detail may throw `ArrayStoreException`** (`CommentEscalationDetailDAOImpl.java` line 42)
   - `list.toArray(values)` will throw `ArrayStoreException` at runtime if `list` contains objects of a type incompatible with `CommentEscalationValue[]`. This would occur if the stored procedure `dbo.csa_get_service_records_escalation` result set mapping produces unexpected types — a silent contract breakage risk.

4. **`GetCsaInquiryCategoryByInquiryTypeDAOImpl` silently returns wrong data on null output** (lines 37–43)
   - If `out` is not null but `out.get("inquiry_type_category")` is null, `value.setInquiryTypeCategory(null)` is called and the `null`-valued object is added to the list. The subsequent `((GetCsaInquiryCategoryByInquiryTypeValue) categoryList.get(0)).getInquiryTypeCategory()` in `JDBCCommentorDAOImpl.getInquiryCategoryCode()` (line 48) would then pass `null` as the `inquiryCategoryCode` to `InsertCommentDAOImpl`, potentially causing a silent data quality issue or a stored procedure error.

5. **`InsertCommentDAOImpl` parameter declaration order mismatch** (`InsertCommentDAOImpl.java` constructor lines 165–178)
   - `INQUIRY_ID` is declared as `SqlOutParameter` (line 177) between `ESCALATION_PRIORITY` (line 176) and `DDA_NUMBER` (line 178). The order of `declareParameter` calls must match the stored procedure's parameter order exactly for `StoredProcedure` to work correctly. If `dbo.csa_insertcsdet` expects `dda_number` before the output parameter, or in a different position, this could cause silent parameter mapping errors.

6. **`TestInstance.Lifecycle.PER_CLASS` with stateful `inquiryIdNumber`** (`CommentServiceImplTest.java` line 22)
   - The test class stores `inquiryIdNumber` as an instance variable (line 29) shared across ordered tests. If `testInsertComment` (Order 1) succeeds but `testInsertCommentEscalation` (Order 3) fails to populate `this.inquiryIdNumber`, `testUpdateCommentEscalation` (Order 4) will call `getEscalationDetail(null, null)` — which returns `null` from the null-guard in `CommentServiceImpl` — and the subsequent `assert commentEscalation != null` (line 111) will throw `AssertionError`, masking the root cause.
