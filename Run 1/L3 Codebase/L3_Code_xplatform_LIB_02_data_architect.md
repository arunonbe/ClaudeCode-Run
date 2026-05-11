# Data Architect View — xplatform_LIB

## Data Stores
| Store | Access Method | Notes |
|---|---|---|
| eCount Core Database (SQL Server) | Spring JDBC / Hibernate ORM | Primary operational database; member, account, device, affiliate data |
| JobSvc Database (SQL Server) | Spring JDBC | Job processing records; accessed via JNDI `java:comp/env/jdbc/JobSvcDataSource` |
| CBTS (Cross-Border Transfer Service) | `cbtsclient` RPC client | External Wirecard-heritage service for international disbursements |
| In-memory object cache | `CacheableObjectFactoryImpl` / SwarmCache | Affiliate and metadata objects; cluster-aware via SwarmCache (JGroups multicast) |
| Config files | `ConfigDB` / `ConfigurationFile` (from xplatformlibrary) | eCount XML config files loaded from filesystem path set in `CBASE_HOME_URL` |

## Schema / Key Tables (inferred from code)
| Entity | Key Fields |
|---|---|
| Affiliate | affiliateId, shortName, metadata entries |
| Member | memberId, programId, registration fields (name, address, phone, email) |
| Device / ECard | deviceId, memberId, cardNumber (PAN), accountType |
| AccountSummary | memberId, balance, feeSource records |
| JobAccountMap | jobId, ecountId (DDA), partnerUserId (PUID) |
| Ticket | ticketId, memberId, status, comments |
| GetPuid | programId, puid → memberId lookup |

## Sensitive Data
| Data Element | Classification | Location |
|---|---|---|
| Card Number (PAN) | CHD / PCI DSS in-scope | Device entity; flows through `AccountHistoryViewManager`, `DeviceManager` |
| Member ID / DDA number | Sensitive account identifier | Member entities throughout |
| Partner User ID (PUID) | Account identifier | `GetPuid`, `JobAccountMapDetails` |
| Registration PII (name, address, DOB, SSN) | PII / CHD-adjacent | `BasicRegistration`, `SecureProfileAddenda` |
| Program ID | Client identifier | Embedded in all business contexts |
| Azure AD tokens | Credentials | `msal4j` — token acquisition for Azure-integrated operations |

## Encryption
- No evidence of field-level encryption within this library's own source code
- Encryption is delegated to the `xplatformlibrary` layer (which provides RSA, 3DES, Twofish, DES3 cipher classes)
- JKS keystores used for RSA operations (referenced in xsso_SVC which depends on this library)
- CBTS communication encryption is managed by the `cbtsclient` library (not directly visible in this repo)

## Data Flow
```
Downstream service call
        |
        v
xPlatform business manager (MemberManagerImpl, EManageManagerImpl, etc.)
        |
     +--+--+
     |     |
     v     v
Hibernate  Spring JDBC
 ORM       DataSource
     |     |
     +--+--+
        |
        v
SQL Server (eCount Core DB / JobSvc DB)
        |
     (async/separate)
        v
CBTS Client (cross-border transfers)
```

## Data Quality and Retention
- No data quality rules enforced at this library layer — validation is expected upstream
- No retention or archival policies implemented within the library
- Caching (SwarmCache) means affiliate/metadata changes may not be immediately consistent across nodes

## Compliance Gaps
- No evidence of PAN tokenisation or masking within the library's data access layer — raw card numbers may be retrieved and passed in memory
- `GetPuid` stored procedure result (`getMemberId()`) exposes member identity without apparent logging
- Hibernate ORM configuration not visible in this repo — lazy loading and caching behaviour for CHD entities is unverified
- Azure AD token handling via `msal4j` — token storage and expiry management not auditable from this repo alone
- SwarmCache uses JGroups multicast — if running in a non-isolated network, cache invalidation messages could leak affiliate configuration
