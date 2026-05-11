# Data Architect View — talend-xml-test

## Data Stores
None — no source code present in this repository.

## Schema / Tables
None — no code to analyse.

## Sensitive Data
None present in this repository. If the intended ETL harness processes payment or cardholder data, the following data classes would be in scope when code is developed:
- PAN / masked card numbers (PCI DSS Req 3)
- ACH routing and account numbers (NACHA / Reg E)
- Cardholder PII (CCPA, GLBA)

## Encryption
None — no code to analyse.

## Data Flow
None — no code to analyse. When developed, the expected flow for a Talend XML test harness would be:
```
[XML source file / test fixture]
        |
[Talend job (ETL transform)]
        |
[Validated output / assertion]
```

## Data Quality and Retention
None — no code to analyse.

## Compliance Gaps
| Gap | Standard | Severity |
|-----|----------|----------|
| Repository is empty — no test harness exists | PCI DSS Req 6 (secure development / testing) | High |
| No test data management policy in place (no synthetic data fixtures, no masking strategy defined) | PCI DSS Req 3/6 | High |
| No XML schema validation or data quality assertions committed | Data quality / audit | Medium |
