# stip-generated — Business Analyst View

## Business Purpose
`stip-generated` is the Stand-In Processing (STIP) generated-code repository. STIP is a critical payments domain capability: it enables card transaction authorisation to proceed when a primary authorisation system is unavailable, using pre-loaded rules and standing instructions to approve or decline transactions in a degraded-mode or offline scenario. This is a core resilience mechanism for prepaid card networks operating under Visa/Mastercard network rules.

The repository name suffix `-generated` indicates this repository is intended to hold auto-generated code (e.g., code generated from a schema, API specification, or model — likely from `stip-models`). This is a common pattern in Onbe's architecture where model definitions drive code generation.

## Observed State
**The repository contains only git metadata (`.git/` directory). No source files, build files, documentation, or generated code are present.** The working tree is empty beyond the initialised git repository structure.

## Capabilities (Intended vs. Observed)
| Intended Capability | Observed Evidence |
|---|---|
| Generated STIP domain code (DTOs, clients, stubs) | None — repository is empty |
| Auto-generated from stip-models | No generated files present |

## Business Entities
None present in source. Based on the STIP domain context, expected entities would include:
- Stand-In Rules / Standing Instructions
- Transaction Authorization Request/Response
- Card Account Profile (for offline balance/limit decisions)
- Merchant Category Code rules
- Velocity limits and controls
- Fallback approval criteria

## Business Rules
None codified in this repository.

## Business Flows
None implemented. Intended flow context:
1. Primary authorisation system unreachable
2. STIP engine evaluates standing rules for the presented card/transaction
3. Approve or decline based on pre-loaded criteria
4. Reconcile with primary system when connectivity restores

## Compliance Relevance
STIP is highly compliance-relevant:
- **PCI DSS**: Stand-in processing involves authorisation decisions on payment transactions — all cardholder data handling rules apply (Req 3, 4, 10).
- **Network rules**: Visa/Mastercard stand-in processing rules govern what decisions are permissible.
- **Reg E**: Consumer dispute rights apply to transactions processed in stand-in mode.
- **FFIEC**: Operational resilience and business continuity requirements are directly served by STIP capability.

## Risks
| Risk | Severity | Notes |
|---|---|---|
| Repository is empty | Critical | STIP generated code does not exist — stand-in processing capability may be absent or housed elsewhere |
| No code generation pipeline visible | High | Cannot confirm whether generation happens in CI/CD or is missing entirely |
| Critical payments domain with no implementation | Critical | If STIP is a required capability and this is its intended home, its absence is a business continuity risk |
