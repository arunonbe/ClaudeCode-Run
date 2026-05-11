# client-rewards_LIB — Business Analyst View

## Business Purpose

`client-rewards_LIB` is a batch-processing library that orchestrates the end-to-end lifecycle of a client rewards (incentive disbursement) program. It handles three sequential stages:

1. **Input file ingestion** — accepts an XML file from a client (e.g., Sprint) containing reward recipient records and imports them into the platform's relational database.
2. **Request file generation** — reads redeemed-but-unprocessed reward records from the database and produces an XML payment request file destined for the downstream payment rail (`requestfile-impl`).
3. **Record expiration** — runs as a standalone batch job to mark eligible reward records as expired via a database stored procedure.

The repo was originally developed circa 2008 (JAXB classes generated 2008-08-18 and 2008-12-15 per file headers) for Sprint as the first known client (sample files reference `SPRINT_3801_*`). The `programid` in sample data is `9966` and prefix `0401`, indicating multi-client extensibility.

---

## Business Capabilities

| Capability | Module | Entry Point Class |
|---|---|---|
| Ingest client reward XML input file | `client-inputfile` | `ReadInputFile` |
| Create reward file header record in DB | `client-inputfile` | `CreateClientRewardsFileSP` → `dbo.create_client_rewards_file` |
| Create per-recipient reward record in DB | `client-inputfile` | `CreateClientRewardsCustomerInfoSP` → `dbo.create_client_rewards_customer_information` |
| Track file import status (loading/loaded/error) | `client-inputfile` | `CreateClientRewardsFileStatusSP` → `dbo.create_client_rewards_file_status` |
| Generate XML payment request file for redeemed rewards | `client-requestfile` | `RequestFileBuilder` / `CreateRequestFile` |
| Mark reward records as PROCESSED after file creation | `client-requestfile` | `UpdateClientRewardsStatusSP` → `dbo.update_client_rewards_status` |
| Expire reward records on schedule | `client-expire-records` | `ExpireRecords` → `dbo.update_client_rewards_customer_information` |
| Generate XML reply/acknowledgement file | `client-inputfile` | `ReadInputFile.createReplyFile()` |

---

## Business Entities

### Reward File (`client_rewards_file` table — inferred from `CreateClientRewardsFileSP`)
- `file_name` (VARCHAR, max 100) — the XML input filename
- `program_id` (VARCHAR, max 10) — client programme identifier (e.g., "3801" for Sprint)
- `promotion_id` (INTEGER) — promotion within the programme
- `partner_id` (INTEGER) — resolved via JobSvc lookup on `program_id`
- `batch_description` (VARCHAR, max 50)
- `created_date` (TIMESTAMP)

### Reward Customer Information (`client_rewards_customer_information` table — inferred from `CreateClientRewardsCustomerInfoSP`)
- `id` (INTEGER, OUT) — surrogate key
- `file_id` (VARCHAR) — FK to reward file
- `firstname`, `middlename`, `lastname`, `suffixname` — recipient name
- `email` — recipient contact
- `address1`, `address2`, `city`, `state`, `postal_code`, `country` — US/CA address
- `home_phone`, `business_phone`, `mobile_phone` — phone numbers (trimmed to 10 digits)
- `amount` (INTEGER) — reward monetary value
- `expired` (TINYINT) — 0=not expired, 1=expired
- `status` (TINYINT) — 0=unredeemed, 1=redeemed, 2=processed
- `created_date`, `updated_date` (TIMESTAMP)

### Reward File Status (`client_rewards_file_status` table — inferred from `CreateClientRewardsFileStatusSP`)
- `file_id` (INTEGER) — FK to reward file
- `status` (TINYINT) — 0=loading, 1=loaded, 2=error
- `comment` (VARCHAR) — human-readable status note
- `updated_date` (TIMESTAMP)

### Input File (XML, XSD-validated)
Defined in `Inputfile.xsd`:
- File-level attributes: `filename`, `programid`, `promotionid`, `batchdescription`, `createdate`
- Record-level `userinfo` elements: name, address, phones, `amount`
- Country restricted to `US` or `CA`

### Reply File (XML)
Defined in `Replyfile.xsd`:
- `inputfile_name`, `processed_date`, `processed_time`, `result_code` (1=success, 0=fail), `result_message`

---

## Business Rules & Validations

All rules are enforced either in `Inputfile.xsd` or in `IClientRewardsConstants`:

| Rule | Source | Detail |
|---|---|---|
| Country must be US or CA | `Inputfile.xsd` line 46 | `xs:enumeration` |
| Postal code 5–10 chars | `Inputfile.xsd` line 45 | `minLength=5, maxLength=10` |
| State max 2 chars | `Inputfile.xsd` line 44 | |
| Email must match pattern or be empty | `Inputfile.xsd` line 40 | `(.)+@(.)+\.(.)+` or empty |
| `programid` max 10 chars | `Inputfile.xsd` line 10 | |
| `amount` max 1,000,000,000 | `Inputfile.xsd` line 50 | |
| Phone numbers trimmed to first 10 digits | `CreateClientRewardsCustomerInfoSP.formatStrPhoneNumber()` | Non-digit chars stripped |
| Duplicate file rejected | `InputDAO.executeBatch()` lines 55–58 | `DataIntegrityViolationException` on unique index |
| File status: 0→loading, 1→loaded, 2→error | `IClientRewardsConstants` | Used throughout `InputDAO` |
| Reward status: 0→unredeemed, 1→redeemed, 2→processed | `IClientRewardsConstants` | Lifecycle enforced across modules |
| Reward expired: 0→not expired, 1→expired | `IClientRewardsConstants` | Set to 0 on insert |
| Batch update max 200 records per SP call | `ClientRewardsRequestFileDAO` line 157 | `batchMaxRecords = 200` |

---

## Business Flows

### Flow 1: Input File Processing (`client-inputfile`)
1. `ReadInputFile.main()` reads properties for input/reply/archive folder paths.
2. Scans input folder for `.xml` files (`FileExtension` filter).
3. For each file: validates against `Inputfile.xsd` via JAXB unmarshalling.
4. Calls `ReadInputFileService.setInputfile()` → `InputDAO.executeBatch()`:
   a. `dbo.create_client_rewards_file` → inserts file header, returns `file_id`.
   b. `dbo.create_client_rewards_file_status` → inserts status "File Loading..." (status=0).
   c. `dbo.create_client_rewards_customer_information` → inserts each recipient row.
   d. `dbo.create_client_rewards_file_status` → inserts status "File Loaded." (status=1).
   e. If any SP returns 0 or exception: rollback + inserts status "DB Error." (status=2).
5. Creates reply XML in reply folder.
6. Copies source file to archive folder (note: `deleteFile` is commented out — source not actually deleted).

### Flow 2: Request File Generation (`client-requestfile`)
1. `RequestFileBuilder.main()` boots Spring context.
2. Calls `ClientRewardsRequestFileServiceImpl.getClientRewardsFileInfo()` → `GetRewardsCustomerInformationSP` (`dbo.get_rewards_customer_information` with `status=REDEEMED=1`).
3. Groups records by partner ID, program ID, promotion ID, and batch description.
4. For each partner: builds `RequestFileVO` / `BatchVO` / `RequestVO` / `AccountCreationVO` / `FundsAdditionVO` and writes an XML request file via `PaymentRequestFile`/`RequestBuilder`.
5. If file created successfully, calls `dbo.update_client_rewards_status` to mark all records `PROCESSED=2` in batches of 200.
6. Moves request file from base path to move path.

### Flow 3: Reward Expiration (`client-expire-records`)
1. `ExpireRecords.main()` boots Spring context.
2. Calls `ExpireRecordsServiceImpl.expireRecords()` → `ExpireRecordsDAO.executeExpireRecords()` → `UpdateExpireRecordsSP`.
3. Executes `dbo.update_client_rewards_customer_information` with no parameters — full expiration logic is inside the stored procedure.

---

## Compliance & Regulatory Concerns

- **PII in transit (unencrypted)**: The XML input files contain full names, addresses, phone numbers, and email addresses. No encryption is referenced for file transfer; files are read from a plain filesystem path (`D:\c-base\...`).
- **PII in database**: Full PII (name, address, phone, email) persists in `client_rewards_customer_information`. No field-level encryption is implemented in the Java layer.
- **No authentication on database connection**: Properties files contain plaintext agent credentials (`agent=b2ctest`, `database=cbaseapp_jdbc`).
- **Amount handling**: `amount` is stored as an integer, implying cents or whole units. No currency field exists; GDPR/CCPA data minimisation is not applied.
- **Country restriction to US/CA**: Aligns with OFAC/sanctions screening scope but does not replace it.
- **No audit trail**: There is no operator-level audit log beyond file status history. No immutable audit log for GLBA or SOX requirements.
- **Hardcoded dev credentials in checked-in properties**: `subContext.properties` contains `agent=b2ctest` and a test member GUID (`{AE6BBCC6-52DD-41E9-9298-A270BEC19DE3}`) in `ClientRewardsInput.properties`.

---

## Business Risks

| Risk | Severity | Evidence |
|---|---|---|
| Input file not deleted after archiving | High | `ReadInputFile.moveFile()` calls `copyFile()` but the `deleteFile()` call is commented out (line 423) — PII files remain in input folder |
| No duplicate-check on archive | Medium | Archive folder may accumulate files with the same name silently overwriting |
| Silent SP failure masked | High | `InputDAO.executeBatch()` only rolls back if SP returns `0`; SP exceptions other than `DataIntegrityViolationException` are swallowed by catch-all |
| Partner ID lookup failure silently sets `partner_id=0` | High | `CreateClientRewardsFileSP.getPartnerID()` catches `Throwable` and returns `0`, no abort |
| No retry mechanism for failed files | Medium | File on error is archived without any retry queue |
| Dev/test config checked in | High | `subContext.properties` references `ECIFLEXAPPDEV` server and `b2ctest` credential |
| Batch processing has no file locking | Medium | No file lock on input folder; concurrent runs would process same files |
