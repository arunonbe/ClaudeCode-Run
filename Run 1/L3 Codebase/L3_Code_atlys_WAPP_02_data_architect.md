# atlys_WAPP — Data Architect View

## Data Stores

The application connects to three SQL Server databases on a single named instance. The server name is read from `Web.config` `appSettings` key `"sv"`, which in the committed configuration is `ppamwdcdifsql1\ppamwdcdifsql1` (a named SQL Server instance — evidently a production or staging server hostname committed to source control).

| Connection Index | Database Name | Purpose |
|---|---|---|
| 0 (`Conn(0)`) | `ATLYS_E` | Core entity data: users, companies, regions, programs, messages, GL maps, periods, Durbin |
| 1 (`Conn(1)`) | `ATLYS_FcCR` | Forecast / cross-tab reporting data; FC controls, CB lists, forecast versions |
| 2 (`Conn(2)`) | `ATLYS_RvCR` | Revenue actuals, GP, commissions, FVD, bank reconcile, BIN reconcile, exchange rates, holidays |

Source: `AtlysSL.Web\SQLData.cs` lines 23–37. Connection strings are built at runtime by concatenating the `sv` appSetting with `Integrated Security=True` (Windows Authentication) — no SQL authentication credentials are stored.

Temporary report files are written to and read from the web application's `//Logs//` directory (`HostingEnvironment.ApplicationPhysicalPath + "//Logs//"`). These are GUID-named `.xml` files representing Excel exports. Files older than 11 minutes are auto-deleted. (Reference: `wsReporting.svc.cs` lines 167–201.)

## Schema & Tables

No DDL scripts are present in the repository. All schema knowledge is inferred from stored procedure calls and data-contract item classes.

**Inferred tables / views in ATLYS_E (Conn 0):**

| Stored Procedure | Inferred Object(s) | Description |
|---|---|---|
| `dbo.sys_user` | `tblUsersS` (referenced directly at line 847 of wsAtlys.svc.cs) | Users with `uid`, `uname`, `s_id`, `group_id`, `enabled`, `lockedout`, `email`, `pwd`, `pwd_expired` |
| `dbo.sys_companies` | Companies / Regions table | `co_name`, `id`, `currency`, `curr_name`, `type`, `enabled`, `txinstance`, `glinterface`, `le_country_code`, `le_branch_code`, `fc_db_name`, `rev_db_name`, `gp_db_name`, `cube1_name`, `cube2_name` |
| `dbo.sys_regions` | Regions | `co_name`, `id`, `currency`, `company_id`, `c_type` |
| `dbo.sys_countries` | Countries | `country_name`, `country_code`, `country_id`, `c_type` |
| `dbo.sys_prefixes` | Program prefixes | `prg_prefix`, `start_date`, `end_date`, `c_id` |
| `dbo.sys_currencies` | Currencies | `curr_name`, `currency`, `id` |
| `dbo.sys_interfaces` | GL interfaces | `name`, `id`, `rectype`, `bus_days` |
| `dbo.sys_txinstances` | Transaction instances | `name`, `id`, `ls`, `cube_ls`, `views_db`, `views_schema`, `qformat`, `rformat`, `cube_transaction`, `cube_issuance`, `company_dimension` |
| `dbo.sys_msgs` | Messages | `id` (BigInt), `body`, `importance`, `msg_read`, `status`, `subject`, `sent_dt`, `from_name`, `from_id`, `ToList`, `CcList`, `ref_type`, `ref`, `company_id`, `orig_id` |
| `dbo.sys_userrights` | User rights | `name` (right name strings) |
| `dbo.sys_paths` | Report/file paths | `name`, `folder`, `folder2`, `p_id`, `type_id` |
| `vRelMgrs` | View: relationship managers | `user_id`, `id` — directly queried with inline SQL at wsAtlys.svc.cs line 847 |

**Inferred tables / views in ATLYS_FcCR (Conn 1):**

| Stored Procedure | Description |
|---|---|
| `dbo.sys_controls` | Forecast controls: version, period ranges, lock flags |
| `dbo.sys_cblists` | Combo-box lookup lists: program types, channels, industries, frequencies, statuses, FC versions, sales reps, rel managers, acct managers, countries, user columns, dormancy tables, utility tables, metrics |
| `dbo.sys_forecast_cross_tab` | Forecast pivot table |
| `dbo.sys_forecast_details_cross_tab` | Forecast detail pivot |
| `dbo.sys_issue_details_cross_tab` | Issuance detail pivot |
| `dbo.sys_forecast2_cross_tab` | Rollup forecast pivot |
| `dbo.sys_dash_cross_tab` | Dashboard summary pivot |
| `dbo.sys_forecast_version` | FC version list |
| `dbo.sys_program_search` | Program search / info |
| `dbo.sys_programs` (implied) | Program master data |
| `dbo.sys_cblists` | Reference data lists |

**Inferred tables / views in ATLYS_RvCR (Conn 2):**

| Stored Procedure | Description |
|---|---|
| `dbo.sys_durbin` | BIN-level Durbin exemption data |
| `dbo.sys_revenue_cross_tab` | Revenue actuals pivot |
| `dbo.sys_gp` | Gross profit by product/program |
| `dbo.sys_gp_details_cross_tab` | GP detail pivot |
| `dbo.sys_comm` | Commissions (actual) |
| `dbo.sys_fvd_cross_tab` | Fee value data pivot |
| `dbo.sys_bal_reconcile` | Balance reconciliation |
| `dbo.sys_bank_reconcile` | Bank reconciliation |
| `dbo.sys_bank_reconcile_ddaj` | Bank reconcile DDAJ variant |
| `dbo.sys_cube_reconcile` | OLAP vs. transactional reconciliation |
| `dbo.sys_fdr` | FDR (First Data Resources?) data |
| `dbo.sys_exchange_rates` (implied) | Currency exchange rates |
| `dbo.sys_holidays` | Holiday schedule |
| `dbo.sys_gl_batch` (implied) | GL batch mapping rules |
| `dbo.sys_glmap` (implied) | Chart of accounts mapping |
| `dbo.sys_smots` | SMoTS settlement/detail/ECS data |
| `dbo.sys_reports` | General reporting (split list, all programs) |
| `dbo.sys_sf_upload` | Salesforce upload data |

## Sensitive Data Handling

**BIN Data**: `DurbinListItem.Bin` (`string`) is transmitted over the WCF service to the Silverlight client and stored in `ATLYS_RvCR` via `dbo.sys_durbin`. BINs are the first 6–8 digits of a PAN and are considered card data under PCI DSS. The field is named `@bin` in the stored procedure (`wsAtlys.svc.cs` line 587).

**User Credentials**: Passwords are AES-256 encrypted client-side before transmission (`Enc.EncQS`, `AtlysSL\Enc.cs`), using a hardcoded key `"WJKGRSCQ3#4yujfg"` and passphrase `"theSLAPPass"`. The server decrypts using `DecQS` (`wsAtlys.svc.cs` lines 6046–6067) and passes plaintext to `dbo.sys_user` SP via `@pwd` and `@newpwd` parameters. Passwords appear to be stored in SQL (hashed or plaintext — not determinable without DB access).

**User PII**: `MsgUser` contains `email` field (`s2` in the data contract). User names, emails, and login times are stored and returned from `dbo.sys_user`.

**Session Tokens**: The session ID (`s_id`, `sid`) is a server-generated token stored in SQL (`tblUsersS.s_id`) and passed on every WCF call. It controls all authorization. Session tokens are transmitted in cleartext within the WCF binary-encoded HTTP binding (not HTTPS is not enforced at the WCF level in `Web.config` — `httpTransport` used, not `httpsTransport`).

**Financial Data**: Revenue amounts, commission rates, gross profit figures, cost rates (IVR, telephony, CS, stock, royalty, ATM, ACH) are financial confidential data. These are queried and returned as decimal values in `GPItem`, `GPMetricsItem`, `CommItem`, etc.

## Encryption & Protection

| Mechanism | Implementation | Strength / Weakness |
|---|---|---|
| Password transit encryption | AES-256 (AesManaged), PBKDF2 key derivation via `Rfc2898DeriveBytes` | Key (`WJKGRSCQ3#4yujfg`) and passphrase (`theSLAPPass`) hardcoded in source. Anyone with source access can decrypt all captured traffic. |
| Transport encryption | HTTP custom binding with `binaryMessageEncoding` + `httpTransport` (`Web.config` lines 111–119) | No TLS enforced. Traffic is HTTP binary-encoded, not HTTPS. |
| SQL connection | Windows Integrated Security (`Integrated Security=True`) | No SQL credentials in config — good. Service account identity controls DB access. |
| Report file temp storage | GUID-named `.xml` files in web root `//Logs//` | Files are world-accessible if web root is served. Auto-delete after 11 minutes provides limited protection. |
| Error logging | Plaintext flat file `errlog.txt` in web root `//Logs//` | Stack traces and error messages may expose schema details if the `//Logs//` directory is served. |

No column-level encryption, no tokenization, no HSM references are present in the codebase.

## Data Flow

```
Silverlight Client (.xap in browser)
    |
    | AES-encrypted passwords; binary WCF HTTP
    v
AtlysSL.Web (IIS / ASP.NET 4.0)
    |-- wsAtlys.svc (wsAtlys class, ~6069 lines)
    |-- wsReporting.svc (wsReporting class)
    |
    | Integrated Security (Windows Auth service account)
    |-- ATLYS_E (dbo.sys_user, sys_companies, sys_msgs, sys_userrights, ...)
    |-- ATLYS_FcCR (sys_controls, sys_cblists, sys_forecast_*, ...)
    |-- ATLYS_RvCR (sys_durbin, sys_gp, sys_comm, sys_bank_reconcile, ...)
    |
    v
SQL Server: ppamwdcdifsql1\ppamwdcdifsql1
```

Report export path:
```
wsReporting.XMLr() → GUID .xml file in //Logs// → URL returned to client → client downloads via browser
```

## Data Quality & Retention

- **No data validation in service layer**: The WCF service passes parameters directly to stored procedures. Input validation (length, format, type) is delegated entirely to SQL stored procedures. No server-side sanitization is visible in C# code.
- **One SQL injection vector found**: `RelMgrId` method (`wsAtlys.svc.cs` line 847) constructs an inline SQL query with `dic["sid"]` interpolated directly: `String.Format("SELECT id FROM vRelMgrs vrm INNER JOIN dbo.tblUsersS us ON vrm.user_id = us.user_id WHERE us.s_id = '{0}'", dic["sid"])`. If a session ID were somehow attacker-controlled, this is a SQL injection risk.
- **Error log retention**: `errlog.txt` is truncated when it exceeds 100,000 bytes. No structured logging, no log rotation by date.
- **Temp file retention**: Report `.xml` files in `//Logs//` are deleted if older than 11 minutes, triggered on any new service call (opportunistic cleanup, not guaranteed).
- **No ORM**: All data access is raw ADO.NET with `SqlCommand`, `SqlDataAdapter`, `DataTable`. No Entity Framework or migration framework.

## Compliance Gaps

| Gap | Evidence | Standard |
|---|---|---|
| No HTTPS enforcement at WCF level | `httpTransport` binding in `Web.config`, not `httpsTransport` | PCI DSS Req 4.2.1 (encrypt PAN/credentials in transit) |
| Hardcoded encryption key in source | `"WJKGRSCQ3#4yujfg"` and `"theSLAPPass"` in `Enc.cs` and `wsAtlys.svc.cs` | PCI DSS Req 3.7.1 (key management); NIST SP 800-57 |
| BIN data transmitted to browser client | `DurbinListItem.Bin` returned to Silverlight app | PCI DSS Req 3.3 (limit SAD storage/transmission) |
| SQL injection vector | Inline SQL at wsAtlys.svc.cs line 847 | PCI DSS Req 6.3.3; OWASP A03 |
| Error logs contain stack traces in web-accessible directory | `errlog.txt` in `//Logs//` | PCI DSS Req 10; OWASP A09 |
| No TLS on transport | HTTP binary binding | PCI DSS Req 4 |
| Server name committed to source | `ppamwdcdifsql1\ppamwdcdifsql1` in `Web.config` | Security baseline / secret management |
