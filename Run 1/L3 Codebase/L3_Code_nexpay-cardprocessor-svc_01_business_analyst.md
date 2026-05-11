# Business Analyst Report — nexpay-cardprocessor-svc

## 1. Service Identity and Business Purpose

`nexpay-cardprocessor-svc` is the **card issuance and management orchestration service** for the NexPay Gen-3 platform. Its business purpose is to abstract the complexity of multiple card processors behind a unified API, enabling Onbe to issue prepaid cards through either Thredd or FIS (and potentially Fiserv in the future) using a single internal API contract. This service is critical to Onbe's core business of disbursing funds to recipients via prepaid cards.

POM description (`pom.xml` line 17): *"NexPay Card Processor - Orchestration layer for card management operations."*

## 2. Supported Business Operations

| API Endpoint | Operation | Business Capability |
|---|---|---|
| `POST /v1/cards` | Synchronous card creation | Issue a prepaid card immediately; optionally activate and fund in one atomic call |
| `GET /v1/cards/{cardId}/balance` | Balance inquiry | Retrieve current spendable balance for a card |
| `POST /v1/jobs` | Asynchronous card creation | Queue a card creation job; return immediately with job ID for long-running operations |
| `GET /v1/jobs/{jobId}` | Job status polling | Poll the status of an asynchronous card creation job |
| `POST /v1/cards/{cardId}/activate` | Card activation | Activate a previously issued but inactive card |

## 3. Multi-Processor Business Model

The service supports **two card processors** with a third (Fiserv) planned:

| Processor | Authentication | Card Type Support | Integration Style |
|---|---|---|---|
| **Thredd** | JWT Bearer (client_credentials) | Virtual and Physical | REST/JSON |
| **FIS** | Credentials in payload | Virtual | Form-encoded, text/key-value response |

The business routing is driven by the `ScopeMap` table: each program (`PROGRAM` scope) or redemption product (`REDEMPTION_PRODUCT` scope) is mapped to a `ProcessorConfig`, which points to a specific processor account. This allows:
- **Multi-processor programs**: Different programs can use different processors
- **Offering-level overrides**: Within a program, different `offeringCode` values can route to different processor configurations
- **Time-bounded configs**: `effective_from` / `effective_to` on `ScopeMap` and `ProcessorConfig` allow scheduled processor migrations

## 4. Post-Issue Actions Business Flow

The `postIssue` section of the `CreateCardRequest` enables **compound card creation** in a single API call:
- `activate: true` — card is activated immediately after issuance (avoids a separate activation call)
- `initialLoad.amountMinorUnits` — funds are loaded immediately after issuance

The `atomicityMode` field (`ALL_OR_NOTHING` vs. `ISSUE_EVEN_IF_ACTIONS_FAIL`) is a business control that determines behavior when post-issue actions fail:
- `ALL_OR_NOTHING`: If the initial fund load fails, the card creation is considered failed (business wants all-or-nothing transactional semantics)
- `ISSUE_EVEN_IF_ACTIONS_FAIL` (default): Card is issued even if activation or load fails (card issuance is decoupled from funding)

## 5. Scope-Based Routing Business Model

The `scope` field in the request (`type: PROGRAM | REDEMPTION_PRODUCT`, `id: PRG-1001`) represents the business context for card issuance:
- **PROGRAM scope**: Card is issued under a client program (e.g., a health insurance company's disbursement program). The program has an associated processor configuration.
- **REDEMPTION_PRODUCT scope**: Card is issued for a specific redemption product (e.g., a gift card variant in a reward program).

The `offeringCode` within a program allows further segmentation (e.g., reloadable vs. single-load variants of the same program).

## 6. Card Product Model

`CardProduct` defines the properties of the card being issued:
- `loadType`: `Reloadable` vs. `SingleLoad`
- `currency`: ISO currency code
- `cardType`: `Virtual` vs. `Physical`
- `limits_json`: Velocity/spend limits

This separates the business definition of a card product from the processor-specific configuration, enabling the same card product to be offered through multiple processors.

## 7. Regulatory and Compliance Business Context

- **PCI DSS CDE**: This service is a **PCI DSS Cardholder Data Environment (CDE) system**. It issues PANs (via Thredd), stores masked PANs, processes cardholder PII (name, DOB, address), and manages card balances. It is subject to PCI DSS Requirements 1-12.
- **Reg E**: Card issuance, activation, and load transactions trigger Reg E obligations (error resolution rights, disclosure requirements).
- **OFAC**: The recipient data passed in `CreateCardRequest` should be OFAC-screened before card issuance. This service does not perform OFAC screening — it is expected upstream in the order orchestrator.
- **Card association rules**: Both Thredd and FIS are subject to Visa/Mastercard association rules for prepaid card issuance. Velocity limits in `CardProduct.limits_json` enforce association compliance.

## 8. Async Card Creation Business Case

The `POST /v1/jobs` endpoint supports asynchronous card issuance for scenarios where processor response times are variable (e.g., physical card manufacturing orders that may take seconds to minutes). The job polling pattern (`GET /v1/jobs/{jobId}`) allows callers to decouple their workflow from processor latency.
