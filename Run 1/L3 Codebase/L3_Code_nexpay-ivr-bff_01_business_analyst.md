# nexpay-ivr-bff — Business Analyst View

## Business Purpose

`nexpay-ivr-bff` is a **Gen-3 NexPay Backend-for-Frontend (BFF)** microservice that acts as the API gateway for **Interactive Voice Response (IVR) systems** interacting with the NexPay platform. It translates IVR system requests (typically from a telephony platform or card processor's IVR) into NexPay-native calls, returning structured customer account data in the format expected by the IVR.

The service is deployed to external APIM, indicating it serves external-facing IVR integrations — likely a telephony switch or call-centre IVR system that uses card account data to guide callers through balance inquiries, cardholder verification, and account management.

## Capabilities

- **Customer inquiry**: Accepts an account ID (card number or DDA), validates it, and returns a structured set of customer account fields selected by the caller (`POST /fs/customer/v4/inquiry`)
- **Field selection**: The request supports a `selectFields` parameter to specify which account fields to return (e.g., `AGNT_ID`, `BRTH_DT`, `SYS_ID`, `SOCL_SCRT_ID`, `ACCT_ID`, `HOME_PHON_ID`, `RESS_CNTR_CD`, `PRIN_ID`, `BSNS_PHON_ID`, `EXPR_DT`, `PSTL_CD`, `DDA_ID`)
- **API key authentication**: Requires `x-api-key` and `x-api-secret` headers on every request
- **Audit trail**: AuditFilter extracts actor identity from OTel baggage, X-Actor-Id header, or JWT claims
- **Redis caching**: Redis connection pool (Jedis) is configured — likely used for caching customer data or session tokens (specific usage not yet visible in controller)
- **Downstream auth service integration**: `ServiceProperties` configures an `auth` service endpoint (`nexpay-auth-svc`)
- **Virtual thread support**: `spring.threads.virtual.enabled: true` — Project Loom virtual threads enabled

## Entities

| Entity | Description |
|---|---|
| `IvrCustomerInquiryRequest.Body` | Request body with `Common` (accountId, debug), `selectFields`, `obfNamePrfx`, `listFieldAsComn`, `bodyjson`, `odsNaming`, `limitFieldCount` |
| `IvrCustomerInquiryRequest.Common` | Inner class: `accountId` (required), `debug` flag |
| `IvrCustomerInquiryResponse` | Response: `statusCode`, `customers`, `responseCode`, `errorCode`, `resultCode`, `message` |
| `IvrCustomerInquiryResponse.CustomerResult` | Single customer result: contains `selectedFields` map |
| `IvrCustomerInquiryResponse.SelectedFields` | Map of field name → value (e.g., `ACCT_ID`, `HOME_PHON_ID`, `SOCL_SCRT_ID`) |

## Business Rules

1. `body.common.accountId` is required and must not be blank
2. `x-api-key` and `x-api-secret` headers are required on every request; missing header returns HTTP 401
3. The response field set currently appears to be **hardcoded** in the controller (stub implementation) — not yet driven by `selectFields` from the request or a downstream system call
4. Account ID is sanitised in log output (control characters replaced) to prevent log injection

## Current Implementation Status

**The `FsCustomerInquiryController` is a stub/mock implementation.** The controller returns hardcoded field values (`AGNT_ID=8000`, `BRTH_DT=2001-01-01`, `SOCL_SCRT_ID=987654321`, etc.) rather than making downstream calls. The comment "Received customer inquiry for accountId" confirms it accepts input but the response is static test data.

Key indicators of stub status:
- `SOCL_SCRT_ID` (Social Security / Social Insurance Number equivalent) returned as hardcoded `987654321` — this is a placeholder
- `ACCT_ID` returned as hardcoded `5424092085370868` — a fixed card number in the response
- No call to `nexpay-auth-svc` or any other downstream service in the controller
- A `DummyController` class is present in `nexpay-ivr-impl/src/main/java/.../dummy/DummyController.java`

## Flows

1. **IVR system inquiry flow** (intended, not yet fully implemented):
   - IVR presents `accountId` with `x-api-key` + `x-api-secret`
   - BFF validates request → authenticates caller → fetches customer data from downstream (auth svc / profile svc)
   - Returns structured field map to IVR

2. **Audit flow**:
   - `AuditFilter` intercepts request → extracts actor ID from OTel baggage, `X-Actor-Id` header, or JWT principal → propagates in OTel baggage for downstream tracing

## Compliance Relevance

- The intended `selectFields` set includes **`SOCL_SCRT_ID`** (Social Security/Social Insurance Number), **`BRTH_DT`** (date of birth), **`ACCT_ID`** (card account number/PAN), **`HOME_PHON_ID`** (phone), **`PSTL_CD`** (postal code) — these are PCI DSS and GLBA sensitive fields
- If `ACCT_ID` is a full PAN, this response constitutes PCI DSS-sensitive data transmission and must be protected with TLS and access controls
- `SOCL_SCRT_ID` (SSN) is extremely sensitive — GLBA, CCPA, state privacy law
- `DDA_ID` (demand deposit account number) is a banking identifier
- The IVR integration is an **external-facing** service (external APIM) — PCI DSS Req. 6 applies to external API surfaces

## Risks

- **Hardcoded sensitive data in controller**: `SOCL_SCRT_ID=987654321`, `ACCT_ID=5424092085370868` — even as test stubs, hardcoded account-like values in a production code file are a risk if accidentally deployed
- **No downstream data source yet**: The service cannot fulfil its stated purpose; it will return stub data to real IVR systems if deployed in current state
- **External APIM exposure**: `EXTERNAL_APIM: true` means this stub is potentially exposed to external callers
- **API key auth only**: `x-api-key` / `x-api-secret` in headers is a weak authentication model for external IVR integrations; OAuth2/mTLS is preferred for PCI-scope APIs
