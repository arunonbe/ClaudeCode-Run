# client-rewards_LIB — Data Architect View

## Data Stores

The library connects to a single Microsoft SQL Server database named **`cbaseapp`** (JDBC alias `cbaseapp_jdbc`). The DataSource is obtained at runtime from a Director-managed DBCP connection pool via `com.ecount.Core2.system.dal.ds.DirectorConfiguredDBCPdatasourceCreator`. The Director service address is `http://ECIFLEXAPPDEV/service/dispatch.asp` (dev environment value hardcoded in properties files).

A commented-out alternative DataSource bean in `applicationContext.xml` (all three modules) shows the server is `ECIFLEXSQLDEV:1433` and schema `cbaseapp`, using jTDS driver (`net.sourceforge.jtds.jdbc.Driver`), user `b2ctest`.

There are no secondary data stores: no message broker, no cache, no NoSQL store. File system is used as a temporary staging area for inbound XML and outbound XML files.

---

## Schema & Tables

All table interactions occur exclusively via stored procedures in the `dbo` schema. No ORM or dynamic SQL is used. The following tables are inferred from stored procedure signatures and result set column mappings:

### `client_rewards_file`
Populated by `dbo.create_client_rewards_file` (`CreateClientRewardsFileSP`, `client-inputfile`):

| Column | Type (inferred) | Notes |
|---|---|---|
| `id` | INTEGER (IDENTITY) | Returned as OUT param |
| `file_name` | VARCHAR(100) | From `Inputfile.filename` |
| `program_id` | VARCHAR(10) | Client programme code |
| `promotion_id` | INTEGER | From `Inputfile.promotionid` |
| `partner_id` | INTEGER | Resolved via JobSvc from `program_id` |
| `batch_description` | VARCHAR(50) | From `Inputfile.batchdescription` |
| `created_date` | DATETIME | Set to `new java.util.Date()` at insert time |
| Unique index | — | Enforced; duplicate insert throws `DataIntegrityViolationException` |

Read by `dbo.get_rewards_file_header` (`GetRewardsFileHeaderSP`, `client-requestfile`) returning columns: `id`, `file_name`, `program_id`, `promotion_id`, `partner_id`, `batch_description`, `created_date`.

### `client_rewards_file_status`
Populated by `dbo.create_client_rewards_file_status` (`CreateClientRewardsFileStatusSP`, `client-inputfile`):

| Column | Type (inferred) | Notes |
|---|---|---|
| `id` | INTEGER (IDENTITY) | Returned as OUT param |
| `file_id` | INTEGER | FK → `client_rewards_file.id` |
| `status` | TINYINT | 0=loading, 1=loaded, 2=error |
| `comment` | VARCHAR | "File Loading...", "File Loaded.", "DB Error." |
| `updated_date` | DATETIME | Set to `new java.util.Date()` |

### `client_rewards_customer_information`
Populated by `dbo.create_client_rewards_customer_information` (`CreateClientRewardsCustomerInfoSP`, `client-inputfile`); read by `dbo.get_rewards_customer_information`; updated by `dbo.update_client_rewards_status` and `dbo.update_client_rewards_customer_information`:

| Column | Type (inferred) | Notes |
|---|---|---|
| `id` | INTEGER (IDENTITY) | Returned as OUT param |
| `file_id` | VARCHAR / INTEGER | FK → `client_rewards_file.id` |
| `firstname` | VARCHAR(25) | From XSD constraint |
| `middlename` | VARCHAR(25) | Optional |
| `lastname` | VARCHAR(24) | |
| `suffixname` | VARCHAR(25) | Optional |
| `email` | VARCHAR(50) | Optional, regex validated at XSD |
| `address1` | VARCHAR(26) | |
| `address2` | VARCHAR(26) | Optional |
| `city` | VARCHAR(18) | |
| `state` | VARCHAR(2) | |
| `postal_code` | VARCHAR(5–10) | |
| `country` | VARCHAR(2) | US or CA |
| `home_phone` | VARCHAR(10) | Trimmed in Java |
| `business_phone` | VARCHAR(10) | Trimmed in Java |
| `mobile_phone` | VARCHAR(10) | Passed as BigInteger, mapped to string |
| `amount` | INTEGER | Reward value; no currency field |
| `expired` | TINYINT | 0=not expired, 1=expired |
| `status` | TINYINT | 0=unredeemed, 1=redeemed, 2=processed |
| `created_date` | DATETIME | |
| `updated_date` | DATETIME | |
| `partner_id` | VARCHAR/INTEGER | Read back by `get_rewards_customer_information` |
| `program_id` | VARCHAR | Read back |
| `promotion_id` | INTEGER | Read back |
| `batch_description` | VARCHAR | Read back (denormalized from file header) |

---

## Sensitive Data Handling

The following sensitive personal data is stored in `client_rewards_customer_information`:

| Data Element | Classification | Stored As |
|---|---|---|
| First, middle, last name | PII | Plaintext VARCHAR |
| Email address | PII | Plaintext VARCHAR |
| Address (address1, address2, city, state, postal, country) | PII | Plaintext VARCHAR |
| Home phone, business phone, mobile phone | PII | Plaintext VARCHAR (trimmed to 10 digits) |
| `amount` (reward value) | Financial | Plaintext INTEGER |

**No field-level encryption is implemented** anywhere in the Java layer. There is no evidence of any tokenisation, masking, or encryption-at-rest controls in code. All PII is transmitted from XML file to the database in cleartext over JDBC.

The `amount` field is an integer with no currency indicator. Based on context (reward disbursements), it is likely a whole-dollar or cent value.

---

## Encryption & Protection

| Control | Present | Detail |
|---|---|---|
| JDBC connection encryption (TLS) | Not specified | jTDS driver URL in commented bean uses no `ssl=` parameter |
| File transfer encryption | None | Files read directly from local filesystem path; no SFTP/PGP evidence |
| Database field encryption | None | All columns stored as plaintext |
| Properties file secrets encryption | None | `agent`, `database`, member GUID in plaintext `.properties` files |
| Input XML schema validation | Yes | JAXB + XSD validation before any DB insert (`ReadInputFile.parseValidateInputFile()`) |
| Reply file integrity | None | No signature or checksum on reply XML |

---

## Data Flow

```
[Client FTP/filesystem]
        |
        | XML file (PII + amount)
        v
[client-inputfile: ReadInputFile]
   |  JAXB unmarshal + XSD validate
   v
[SQL Server: dbo.create_client_rewards_file]          --> client_rewards_file
[SQL Server: dbo.create_client_rewards_file_status]   --> client_rewards_file_status (status=0)
[SQL Server: dbo.create_client_rewards_customer_information] --> client_rewards_customer_information (status=0=unredeemed)
[SQL Server: dbo.create_client_rewards_file_status]   --> client_rewards_file_status (status=1)
   |
   | XML reply file (result code + message)
   v
[Reply folder on filesystem]
   |
   | Source XML copied to archive folder (NOT deleted — bug)
   v
[Archive folder on filesystem]

--- later, by separate batch run ---

[client-requestfile: RequestFileBuilder]
   |
   | reads status=REDEEMED (1) records
   v
[SQL Server: dbo.get_rewards_customer_information]
   |
   | groups by partner_id / program_id / promotion_id / batch_description
   v
[com.ecount.payment.common.PaymentRequestFile] --> XML request file on filesystem
   |
   | if file written successfully
   v
[SQL Server: dbo.update_client_rewards_status (status=PROCESSED=2)]

--- separate scheduled batch ---

[client-expire-records: ExpireRecords]
   v
[SQL Server: dbo.update_client_rewards_customer_information]
   (marks records as expired — logic inside SP)
```

---

## Data Quality & Retention

- **No data retention policy** is implemented in code. Expiry is handled by `dbo.update_client_rewards_customer_information` but no delete or archival procedure is visible.
- **Duplicate file check**: The unique index on `client_rewards_file` prevents reprocessing the same filename, but only if the file name is distinct. File naming relies on client convention.
- **Phone normalisation**: `formatStrPhoneNumber()` strips non-digit characters and truncates to 10 digits, which may silently lose meaningful data (e.g., international numbers).
- **Amount precision**: `amount` is INTEGER; no decimal/fractional amounts are supported.
- **Batch description mismatch detection**: The request file builder groups by batch description using string equality — no normalisation (case, whitespace).
- **Date parsing bug**: `GetRewardsFileHeaderSP` uses `new SimpleDateFormat("mm-dd-yyyy")` (line 101) where `mm` is minutes, not months — this will produce incorrect `created_date` values on `ClientRewardsFileDTO`.
- **No soft-delete**: Records are updated in place; no historical snapshots beyond the file status table.

---

## Compliance Gaps

| Gap | Regulation | Detail |
|---|---|---|
| PII stored in plaintext | GDPR Art.32, CCPA, GLBA Safeguards Rule | `firstname`, `lastname`, `email`, `address*`, phones all unencrypted |
| No data-at-rest encryption evidence | PCI DSS Req.3 (if amounts are card-linked rewards) | No encryption key management visible |
| No data minimisation | GDPR Art.5(1)(c) | Full address, multiple phone numbers retained indefinitely |
| No right-to-erasure mechanism | GDPR Art.17 | No delete capability in the codebase |
| Credential exposure in properties files | GLBA, internal security policy | `agent=b2ctest`, member GUID, director URL in version-controlled files |
| No TLS enforcement on DB connection | PCI DSS Req.4 | jTDS URL does not specify SSL |
| No audit log for data access | GLBA, SOX | Only file-level status history; no row-level read audit |
| Amount field type-safety | Internal | Integer truncation could misrepresent fractional reward values |
