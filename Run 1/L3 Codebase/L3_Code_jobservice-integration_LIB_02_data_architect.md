# jobservice-integration_LIB — Data Architect View

## Summary

This repository's data architecture is **identical to `jobserviceintegration_LIB`**. Both repositories share the same Maven artifact, the same Java source structure, the same `Common` module utilities, and the same client conversion modules. The data model, file formats, sensitive data inventory, encryption posture, data flow, and compliance gaps are the same.

See `E:\OnbeEast363\analysis\per-repo\jobserviceintegration_LIB\02_data_architect.md` for the full analysis.

## Delta vs. jobserviceintegration_LIB

The only structural delta detected is the module directory name: `legacyForLife` (lowercase `l`) vs `LegacyForLife`. This does not affect the data model or data flows.

## Data Stores

No persistent data stores. File-based ETL only:
- Client input files (ZIP/flat) — filesystem read
- ecount batch output files — filesystem write
- Promotion config properties file — filesystem read
- ecount reply files — filesystem read

## Sensitive Data

Same as sibling repo:
- Recipient first/last/middle name, email, home/business/mobile phone, full mailing address
- Partner user ID (PUID)
- Payment amount (financial)
- No PAN, CVV, or track data

## Encryption

None. Identical posture to `jobserviceintegration_LIB`.

## Compliance Gaps

Same gaps as `jobserviceintegration_LIB`:
1. PII in plain-text files
2. No audit trail
3. Log4j 1.2.15 binary JAR (CVE-2019-17571)
4. Binary JARs in source control
5. Silent data truncation and phone number replacement
6. No data minimisation

## Duplicate Artifact Risk

Both this repo and `jobserviceintegration_LIB` produce `com.ecount.service:jobserviceintegration:1.0.1-SNAPSHOT`. If both are published to the same Maven repository, one will overwrite the other — creating a non-deterministic build dependency for any consumer of this artifact.

**Action required**: Audit which repository is the canonical source and archive the other, or assign distinct version numbers.
