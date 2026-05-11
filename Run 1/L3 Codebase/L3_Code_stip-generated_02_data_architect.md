# stip-generated — Data Architect View

## Data Stores
None. The repository is empty of source files.

## Schema / Tables
None defined in this repository.

## Sensitive Data Handling
Not implemented. In the intended STIP domain context, generated code would handle:
- Card account data (BIN, last-4 equivalent for decisions — no full PAN should be stored in stand-in processing per PCI DSS Req 3)
- Transaction amounts and merchant data
- Velocity counters and limit thresholds

## Encryption
Not implemented.

## Data Flow
Not implemented. Expected data flow for generated STIP code would be:
```
STIP Request (card identifier + transaction details)
    → Generated request DTO (from stip-models schema)
    → STIP decision engine
    → Generated response DTO
    → Authorisation response (approve/decline + reason code)
```

## Data Quality / Retention
Not applicable — no data assets present.

## Compliance Gaps
| Gap | Standard | Notes |
|---|---|---|
| No stand-in processing code | PCI DSS, FFIEC BC | STIP is a resilience control; its absence is a gap in operational continuity |
| No data handling controls defined | PCI DSS Req 3, 4 | Expected to be defined when implementation is present |
| No audit logging for stand-in decisions | PCI DSS Req 10 | Stand-in transaction decisions must be logged for reconciliation and audit |

## Recommendations
When implementing:
1. Generated DTOs must never include full PAN, CVV, or PIN fields — use tokenised or masked references only.
2. Stand-in decision logs must be retained per Onbe's PCI DSS log retention policy (minimum 12 months, 3 months immediately available).
3. Any generated client code that communicates over network must use TLS 1.2+ only.
