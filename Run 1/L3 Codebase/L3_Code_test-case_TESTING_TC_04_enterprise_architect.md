# Enterprise Architect Report — test-case_TESTING_TC

## Platform Generation

**Gen-1 and Gen-2 spanning**. The test cases cover:
- **Gen-1 (eCount/Citi)**: Job Service (XML-RPC-based), Banker, ACH/NACHA file processing, FDR processor, check issuance, NDM (Network Data Mover), j-Integra J2COM bridge, VBScript operational scripts.
- **Gen-2 (Wirecard/Northlane)**: Spring Boot-era ClientZone, CSA, API layer, Singapore MFA.
- No Gen-3 (NexPay) test cases are present, confirming this is a legacy QA artefact store.

## Integration Patterns

The test cases validate the following integration patterns:
- **Synchronous XML-RPC**: API test cases exercise the XML-RPC servlet layer (eCount Core) via Client API, CS-API, IVR.
- **Batch file exchange**: FLAT/XML/XLS file processing jobs, FTP-based file transfer, PGP encryption.
- **MQ-based**: FDR MQ test cases indicate IBM MQ integration for processor file exchange.
- **Bank Integration**: ACH OUT (NACHA), Check Interface (CPS), bank data feed files.
- **SFTP**: File transfer test cases reference FTP/SFTP connectivity.

## External Dependencies (Systems Under Test)

- eCount Core (Gen-1 Java application server)
- FDR (First Data Resources) processor
- Citi bank ACH/check interfaces
- MB (MetaBank) and Sunrise Bank check/ACH processors
- Personix card fulfillment
- Arroweye card fulfilment
- GXS (now IBM Sterling) EDI/file exchange
- NDM (Network Data Mover) for mainframe file transfer

## Position in the Broader Platform

This repository is a passive documentation layer that supports QA quality gates across the entire Gen-1/Gen-2 platform surface. It is not on the critical deployment path but is important for compliance evidence, regression coverage tracking, and onboarding new QA engineers.

## Migration Blockers

- The test cases are organized around Gen-1/Gen-2 features and processes. As the platform migrates to Gen-3 (NexPay), new test-case repositories or automated test suites will need to be created; this repository does not extend to Gen-3.
- ALM Data artefacts (Word documents) represent institutional knowledge about end-to-end bank integration flows that may be difficult to re-express in automated form without significant subject-matter-expert engagement.

## Strategic Status

**Legacy/maintenance only.** This repository should be considered a read-only knowledge archive. Active test management should migrate to a structured test management platform (e.g., Xray for Jira, TestRail) with linkage to CI pipelines. The contents are valuable as a baseline for migration to automated test suites, particularly for the ACH and bank integration flows which carry NACHA and Reg E compliance obligations.
