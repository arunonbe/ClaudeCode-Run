# Data Architect View — xsearch_LIB

## Data Stores
| Store | Type | Access | Notes |
|---|---|---|---|
| EcountCoreDataSource | SQL Server (relational) | Spring JDBC / StoredProcedure | Primary member, device, ECAP data |
| CbaseappDataSource | SQL Server (relational) | Spring JDBC | `DeviceInquirySpringDAO`, `MemberInquirySpringDAO` — secondary data source |
| WebCertOmahaDataSource | SQL Server (relational) | Spring JDBC | `MemberCommentInquirySpringDAO` — CSA comment history |
| JobSvcDataSource | SQL Server (relational) | Spring JDBC | `JobActionInquirySpringDAO` — job processing records |

Four separate SQL Server databases are accessed by this library.

## Schema / Key Queries (inferred from DAO classes)

### Member Search (`MemberInquirySpringDAO`, `MemberInquiryImpl`)
- Search by: lastName, firstName, cardNumber (PAN), DDA number, affiliateId, PPD, NSS (SSN), PUID, XPPD, DFI, routing/account number
- Returns: `MemberInquiryValue[]` — memberId, firstName, lastName, middleName

### Device Inquiry (`DeviceInquirySpringDAO`, `DeviceInquiryStoredProcedureImpl`)
- Search by: PUD (via `searchByPUD` on `DeviceInquiry`)
- Returns: `DeviceInquiryValue` — device details

### ECAP Inquiry (`EcapInquiryImpl`)
- Search by: credit card number
- Returns: `EcapInquiryValue`

### Member by Addenda (`MemberByAddendaInquiryImpl`)
- Search by: programId + addenda fields
- Returns: `List<MemberInquiryValue>`

### Redeemable Payment (`SearchRedeemablePaymentByIdAndMemberSpringImpl`, `SearchRedeemablePaymentsByMemberSpringImpl`)
- Search by: memberId and payment ID
- Returns: `RedeemablePaymentVO`

### Job Action (`JobActionInquirySpringDAO`)
- `SearchCreateEmailNotificationByPaymentId` — looks up email notification job by payment ID

### CSA Comments (`MemberCommentInquirySpringDAO`)
- Returns: `CommentHistoryValue` — comment text, timestamp, operator

## Sensitive Data
| Data Element | Classification | Location |
|---|---|---|
| Card Number (PAN, full 16-digit) | CHD / PCI DSS Req 3 | `SearchServiceImpl.cardNumber` parameter; `EcapInquiryValue`; `MemberInquiryValue` fields |
| SSN / NSS | PII (GLBA, CCPA) | `SearchServiceImpl.nss` parameter |
| DDA / Account Number | Sensitive account identifier | `MemberInquiryValue.memberId` / DDA search parameter |
| ACH Account Number | PII / NACHA | `SearchMemberByECheck`, `checkAcctNumber` |
| Member first/last/middle name | PII | `MemberInquiryValue` |
| Partner User ID (PUID) | Account identifier | `SearchMemberByClaimcode`, search parameter |
| CSA Comment text | Potentially sensitive | `CommentHistoryValue` |

## Encryption
- No encryption applied within this library to data at rest or in transit
- Data is retrieved from SQL Server and returned in plaintext Java objects
- Masking is applied by `MaskCCHelper` before data is returned to callers, but only for display-layer concerns
- Wire encryption (TLS) between the library and SQL Server depends on JDBC driver configuration — not configurable within this library

## Data Flow
```
Search criteria (from calling service)
        |
        v
SearchServiceImpl (validation + routing)
        |
     +--+----+------+--------+
     |       |      |        |
     v       v      v        v
MemberInq  DeviceInq  EcapInq  MemberByAddenda
SpringDAO  StoreProc   Impl     Impl
     |       |      |        |
     +--+----+------+--------+
        |
        v
EcountCoreDataSource / CbaseappDataSource / WebCertOmahaDataSource / JobSvcDataSource
(SQL Server — stored procedures and parameterised queries)
        |
        v
MemberInquiryValue[] / DeviceInquiryValue / RedeemablePaymentVO (returned to caller)
        |
        v
MaskCCHelper.maskThisCC() / maskThisSSN() / maskAchAccountNumber()
(called by consuming service before presenting to user)
```

## Data Quality and Retention
- Input sanitisation: single quotes replaced with escaped doubles (`''`) to prevent SQL errors — but this is not parameterised query protection; actual parameterisation is handled by Spring JDBC
- No data retention policies enforced at this layer
- No audit log of searches performed

## Compliance Gaps
- **PAN masking non-compliant:** `MaskCCHelper.maskThisCC()` masks 8 middle digits, leaving first 4 and last 4 visible — PCI DSS Req 3.3.1 permits display of at most first 6 / last 4 (BIN + last 4); exposing first 4 may expose BIN-level data beyond the permitted first 6
- **SSN in search parameters:** SSN (`nss`) is passed as a plain String through the search stack — if debug logging is active, SSN values may be captured in logs
- **Four separate database connections:** The multi-database architecture (EcountCore, Cbaseapp, WebCertOmaha, JobSvc) creates a broad data access surface; each connection needs individual audit and access control review
- **No search audit log:** Member lookups by PAN, SSN, or DDA leave no audit trail — required for PCI DSS Req 10 (log and monitor access to CHD)
- **Comment history via `WebCertOmahaDataSource`:** CSA comment content is a third database not obviously in the CDE boundary — boundary classification must be confirmed
