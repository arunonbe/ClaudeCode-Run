# Data Architect View — sweep-client_LIB

## Data Stores
The sweep client itself does not own a database. It reads from and writes to external systems:

| Store | Type | Ownership | Access |
|-------|------|-----------|--------|
| xPlatform / CBase profile store | Proprietary (CBase platform) | External | Read — `AppPromotionInstantSweepOrderProfileClass.retrieveAll()` |
| Order Service | Remote service | External | Read/Write — HTTP Invoker (Spring) |

No local persistent data store is used by this application.

## Schema / Tables
Not applicable — no owned schema. The `SweepProfile` DTO is an in-memory transfer object only.

## Sensitive Data
| Field | Classification | Notes |
|-------|---------------|-------|
| `memberId` (GUID `778C2F5A-3956-4099-B567-A0F6926BDFCD`) | Internal identifier | Uniquely identifies an Onbe member profile; not cardholder PII |
| `programId` / `promotionId` | Business identifiers | No PII |
| `activeTime` | Operational parameter | No PII |

No cardholder data, PAN, SSN, or financial account data is handled by this client directly.

## Encryption
No encryption in transit observed at the client level:
- HTTP Invoker (Spring `CustomHttpInvokerReqeustExecutor`) is used to call the Order Service — whether TLS is enforced depends on the URL configuration provided at runtime (`${CBASE_HOME_URL}/config/service/order/sweep.client.properties`).
- No message-level signing or encryption.

## Data Flow
```
CBase/xPlatform profile store
        |
        | [AppPromotionInstantSweepOrderProfileClass.retrieveAll()]
        v
ProfileReader (in-memory list of AppPromotionInstantSweepOrder)
        |
        | [BeanUtils.copyProperties]
        v
SweepProfile DTO
        |
        | [HTTP Invoker]
        v
Order Service (CreateSweepOrders / CloseSweepOrders / etc.)
```

## Data Quality and Retention
Not applicable — no owned data store.

## Compliance Gaps
| Gap | Standard | Severity |
|-----|----------|----------|
| No TLS enforcement observed at the client config layer — depends entirely on externally supplied URL | PCI DSS Req 4 | Medium |
| Default properties file contains `agent=B2CTEST` — risk of test agent used in production | PCI DSS Req 6 | High |
| XStream marshaller used for HTTP Invoker serialisation — XStream has known deserialization CVEs | PCI DSS Req 6.3 | High |
| No audit log of sweep operations (profile IDs, methods invoked, outcome) persisted | PCI DSS Req 10 | Medium |
