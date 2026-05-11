# nexpay-ivr-bff — Data Architect View

## Data Stores

| Store | Type | Access Pattern |
|---|---|---|
| Redis | In-memory cache | Jedis connection pool; keys prefixed `ivrbff:affiliate` and `ivrbff:content` (QA config) |
| Downstream auth service (`nexpay-auth-svc`) | REST service | HTTP client via `RestClientConfig`; not a data store directly |

There is **no relational database** in this service. `nexpay-ivr-bff` is a stateless BFF that:
1. Caches data in Redis
2. Calls downstream services for authoritative data

## Redis Data Model

From `application-qa.yaml`:
```yaml
redis:
  keys:
    prefixforaffiliate: 'ivrbff:affiliate'
    prefixforcontent: 'ivrbff:content'
  ssl: true          # TLS enforced in QA/production
  timeout: 5000      # ms
```

The specific keys/values stored in Redis are not visible in the scanned controller code (stub implementation). Based on the key prefix pattern:
- `ivrbff:affiliate:*` — affiliate-related cached data
- `ivrbff:content:*` — content-related cached data

Redis connection pool (Jedis) configuration in `RedisConfig`:
- `max-active: 10`, `max-idle: 4`, `min-idle: 4` (local defaults)
- SSL enabled in QA/production (`redis.ssl: true`)
- Password support for Azure Cache for Redis

## Sensitive Data in Transit

The `IvrCustomerInquiryResponse.SelectedFields` map carries highly sensitive values:

| Field Code | Description | Sensitivity |
|---|---|---|
| `SOCL_SCRT_ID` | Social Security / Social Insurance Number | Extremely sensitive — GLBA, CCPA, GDPR |
| `ACCT_ID` | Card account number (potentially PAN) | PCI DSS — if full PAN, Req. 3/4 applies |
| `DDA_ID` | Demand deposit account ID | Banking identifier — GLBA |
| `BRTH_DT` | Date of birth | PII — CCPA, GDPR |
| `HOME_PHON_ID`, `BSNS_PHON_ID` | Phone numbers | PII |
| `PSTL_CD` | Postal/ZIP code | PII |
| `EXPR_DT` | Card expiration date | PCI DSS SAD (if combined with PAN) |
| `AGNT_ID`, `SYS_ID`, `PRIN_ID` | Internal platform identifiers | Lower sensitivity |
| `RESS_CNTR_CD` | Address/residence country code | PII |

**PCI DSS Critical Observation**: If `ACCT_ID` is a full PAN and `EXPR_DT` is returned in the same response, this constitutes transmission of combined PAN + expiration date — PCI DSS Req. 4 (encrypt transmission of cardholder data over open networks) and Req. 3 (protect stored cardholder data in cache/Redis) apply.

## Encryption

### Redis
- `redis.ssl: true` in QA profile — TLS enforced for Azure Cache for Redis connections
- `redis.port` defaults to 6379 (standard); Azure Cache for Redis TLS port is 6380 — the port override must be configured in Azure App Configuration for QA/prod

### API Transport
- External APIM enforces TLS termination for all external callers
- Internal transport between ACA and APIM is on the Azure private network

### Application Layer
- No field-level encryption in the controller
- No hashing of sensitive fields before caching in Redis

## Data Flow

```
[External IVR System]
        | (HTTPS via external APIM)
        v
[nexpay-ivr-bff: POST /fs/customer/v4/inquiry]
        |
        +--> [AuditFilter]: extracts actor.id from OTel baggage / headers
        |
        +--> [FsCustomerInquiryController] (STUB — no downstream call yet)
        |           |
        |           v (future: call to downstream services)
        |    [nexpay-auth-svc] (auth endpoint: ${AUTH_SERVICE_URL})
        |    [nexpay-recipient-profile-svc or similar] (for customer data)
        |
        +--> [Redis (Jedis)] — cache read/write for affiliate/content data
        |
        v
[IvrCustomerInquiryResponse → JSON → IVR system]
```

## Data Quality and Retention

- Redis keys: No TTL policy visible in source. If affiliate/content cache entries have no expiry, stale data could be served indefinitely.
- The controller is currently a stub and does not read from any real data source — all values are hardcoded.
- No audit logging of what customer data was returned in the response. Only `accountId` (sanitised) is logged at INFO.

## Compliance Gaps

1. **PAN + expiry in same response**: `ACCT_ID` + `EXPR_DT` in `SelectedFields` — if `ACCT_ID` is a full PAN, this violates PCI DSS Req. 3.3 (mask PAN when displayed) and Req. 4 (protect in transit). Response should mask PAN (first 6/last 4 only).
2. **SSN (`SOCL_SCRT_ID`) in API response**: Returning full SSN/SIN over a REST API to an IVR system is an extreme PII risk. GLBA and CCPA mandate strict controls. The hardcoded value `987654321` is a 9-digit number that could be mistaken for a real SSN.
3. **Redis cache without TTL**: Sensitive cardholder data cached without expiry could be accessed long after it should have been invalidated.
4. **No response field masking**: The `obfNamePrfx` flag exists in the request model but is not used in the stub — intended obfuscation is not implemented.
5. **Hardcoded sensitive-looking values in production code**: `ACCT_ID=5424092085370868`, `SOCL_SCRT_ID=987654321` in `FsCustomerInquiryController.java` (lines 54–62) — even as stubs, these resemble real financial identifiers.
