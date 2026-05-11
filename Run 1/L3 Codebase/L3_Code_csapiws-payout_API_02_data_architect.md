# Data Architect View — csapiws-payout_API

## Data Stores
| Store | JNDI Name | Purpose | Technology |
|---|---|---|---|
| CbaseappDataSource | `jdbc/CbaseappDataSource` | Affiliate lookup (Hibernate); CommentService DAOs | SQL Server (jTDS driver) |
| JobSvcDataSource | `jdbc/JobSvcDataSource` | PUID lookup via GetPuid | SQL Server (jTDS driver) |
| EcountCoreDataSource | `jdbc/EcountCoreDataSource` | DDA device inquiry via CoreDeviceDDAInquiry | SQL Server (jTDS driver) |
| C-Base xPlatform | Proprietary RPC (EMember/EDevice) | Member inquiry, card device inquiry, registration update | Proprietary (xPlatform 2019.1.1) |
| CMS | HTTP (cms.service.url from external properties) | Payout app content URLs (terms, fees, logo) | HTTPS to northlane.com CMS |

Note: This service uses xPlatform RPC for member/device operations, not the ecount-core-rest-api REST client used in V3. The xPlatform version (2019.1.1) is newer than V2 (2.4.5) but older than V3 (6.5.8, via ecount-core-rest-api).

## Configuration Source
External properties file: `file:d:/c-base/config/CSWS/applicationContext-CSWS.properties`
- The file is loaded from the server filesystem — not committed to the repository.
- Log4j configuration: `file:///D:/C-Base/config/CSWS/log4j-Payout.xml` (also filesystem-based).
- Both paths use Windows drive letter `D:` — this service targets Windows Server deployment.
- External properties inject: appId, agent, classification, endpoint, comment.appId, escalation.status, authSyncPrograms, cms.* properties.

## Schema

### payoutAccountInquiry Input Parameters
```
application_id        String — resolved via "cs_api_payout_app_id" affiliate attribute
card_number           String — optional (one of card/puid/ppd/dda required)
puid                  String — optional
ppd                   String — optional (Partner Payment Details)
mobilePhone           String — optional
ddaNumber             String — optional (Demand Deposit Account)
balance_detail        int — 0/1 flag
journal_detail        int — 0/1/2 flag (2 = include PPID in transaction addenda)
registration_detail   int — 0/1 flag
start_date            int — journal start date (0 = no minimum)
end_date              int — journal end date
max_items             int — max transaction records
```

### PayoutAccountInquiry Response
```
Inherits from AccountInquiry:
  Balance:             balance_available, balance_ledger, balance_pending, balance_date
  CardDetail:          card_number (masked), puid, program_id, created_date,
                       last_plastic_date, expiration, account_status
  TransactionDetail[]: transaction_date, amount, fee, type, details (merchant or XXXX)
  PaymentDetail[]:     PPD promotion data
  CommentHistory[]:    historical CS comments
  Registration:        address, name, phone, email
  Response:            code (int), message

PayoutApp extension:
  termsURL             String — from CMS
  feesURL              String — from CMS
  ATMType              String — from affiliate "free_starsf_atm" / "free_moneypass_atm" flag
  CSPhone              String — from affiliate "contact_info_phone" attribute
  CustomLogoURL        String — path "/i/payoutAppLogo.png" (static)

PayoutAppRegistration extension:
  (cardholder registration as visible to payout portal)
```

### UpdateRegistrationDetails (input to updateRegistrationAction)
```
puid                  String (required)
application_id        String
ddaNumber             String — DDA account for payout
address_1             String (max 26)
address_2             String (max 26, optional)
city                  String (max 18)
state                 String (max 2)
postal                String (max 10)
country               String (max 2) — US, CA, or MX
home_email            String (max 50)
home_phone            String (max 16)
mobile_phone          String (max 16, optional)
business_phone        String (max 16, optional)
first_name            String (max 25)
last_name             String (max 25)
middle_name           String (max 25, optional)
suffix_name           String (max 25, optional)
```

### State Validation Sets
Three static HashSet beans defined in XML:
- `USStatesSet`: 59 US state/territory codes (AL through WY + territories)
- `CAStatesSet`: 13 Canadian province/territory codes
- `MXStatesSet`: 32 Mexican state/territory codes (AG through ZA)

This is the only CS API component with Mexico state validation.

## Sensitive Data — Locations (Values NOT Reproduced)
| Data Type | Location | Risk |
|---|---|---|
| JDBC credentials | Server JNDI (not in code) | Properly externalised via container-managed JNDI |
| applicationContext-CSWS.properties | D:/c-base/config/CSWS/ (server filesystem, not committed) | Properly externalised; however the referenced `applicationContext-CSWS.properties` in cs-api-v3_API contains JWE keys — this payout service does not use JWE |
| CMS service URL | External properties (northlane.com domain) | Internal/staging URL may be in properties file on server |
| displayMerchantName list | accountManagementContext.xml (hardcoded) | 8 program IDs listed in XML — information disclosure (acceptable, not sensitive credentials) |
| appContextFactory bean | References affiliateServiceApplicationContext.xml from JAR classpath | JNDI lookup on server |
| Log4j config path | web.xml | Windows path D:/C-Base/config/CSWS/log4j-Payout.xml — internal path disclosure |

## Data Flow — payoutAccountInquiry
```
Payout Portal Client
    │ HTTPS SOAP
    ▼
Apache Axis Servlet (/CardManagementPayoutV3/services/AccountManagement)
    │
    ├── AccountManagementJaxRPC.payoutAccountInquiry()
    │
    ├── PayoutSearchAccount.execute()
    │   ├── AffiliateService.getAffiliateForValue("cs_api_payout_app_id", application_id)
    │   │   └── CbaseappDataSource (Hibernate / stored proc)
    │   │
    │   ├── GetPuid (JobSvcDataSource) — PUID to memberId resolution
    │   │
    │   ├── EMember (xPlatform RPC) — member inquiry
    │   │
    │   ├── IDeviceManager / EDevice (xPlatform RPC) — card device inquiry
    │   │
    │   ├── PPDPromotionXref — PPD promotion data per transaction
    │   │
    │   ├── ICommentService (CbaseappDataSource) — comment history
    │   │
    │   └── ContentManagementServiceClient (CMS HTTP) — PayoutApp URLs
    │
    ▼
PayoutAccountInquiry response
```

## Data Flow — updateRegistrationAction
```
Client → UpdateRegistrationAction.execute(UpdateRegistrationDetails)
    ├── AffiliateService — affiliate/flag check
    ├── EMember.puidMemberSearch() → memberId (xPlatform RPC)
    ├── EMember.processInquiryExtended() → current registration
    ├── CoreDeviceDDAInquiry (EcountCoreDataSource) — DDA device lookup
    ├── State/postal validation against USStatesSet / CAStatesSet / MXStatesSet
    ├── EMember.processUpdate() → write registration (xPlatform RPC)
    └── ICommentService.addComment() → audit comment (csUserId = "cs-api-Payout")
```

## Encryption
- **At rest**: No application-level encryption. JDBC credentials managed by container JNDI.
- **In transit**: HTTPS at server/load balancer level. No JWE/JWT in this standalone payout service (unlike V3 payout sub-service).
- **Card masking**: Applied in PayoutSearchAccount on return (format consistent with V3 inquiry).
- **DDA numbers**: Passed in plaintext via SOAP — no JWE encryption in this service. This contrasts with `cs-api-v3_API/csapi-v3-payout-ws` which uses JWE for DDA numbers. This is a security gap.

## Compliance Gaps
1. **DDA numbers in plaintext SOAP**: This service accepts and returns DDA numbers without JWE encryption. The V3 payout sub-service encrypts DDA numbers via JWE. This is an inconsistency that could expose account routing information in transit if TLS is the only protection.
2. **jTDS JDBC driver (1.2)**: Very old SQL Server JDBC driver — potential TLS 1.2 compatibility issues for database connections.
3. **No credential management**: Properties injected from filesystem file — no secrets manager, no rotation capability without file edit and possible service restart.
4. **PUID in logs**: INFO-level log statements in PayoutSearchAccount may expose PUID values.
5. **No affiliate-level `cs_api_enabled` flag check**: Payout inquiry uses `cs_api_payout_app_id` mapping as the sole access gate.
