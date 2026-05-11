# Data Architect View — strict-null-checks_DEMO

## Data Stores
None. This repository has no persistence layer, no database, no cache, and no file I/O.

## Schema / Tables
Not applicable.

## Sensitive Data
None present. The `Employee` record holds only `id` and `name` string fields — no PII, no financial data, no cardholder data.

## Encryption
Not applicable. No data is persisted or transmitted.

## Data Flow
```
[Developer/IDE] --> [Source files] --> [Maven build] --> [Instrumented JAR (demo only)]
```
No runtime data flows exist.

## Data Quality and Retention
Not applicable.

## Compliance Gaps
- No compliance gaps because no data is processed.
- If the patterns in this repo are adopted across production services, those services must still undergo independent PCI DSS, GLBA, and Reg E data handling reviews.
