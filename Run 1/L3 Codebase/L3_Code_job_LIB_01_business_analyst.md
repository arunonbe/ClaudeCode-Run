# job_LIB — Business Analyst View

## Business Purpose

`job_LIB` is a shared Java library (Gen-1) that provides the core **Job Manager API** used across the Onbe/eCount prepaid-card platform. It exposes a contract for managing "jobs" — batch-processing units that enrol recipients, fund accounts, and track the mapping between partner user identifiers and internal ecount/eMember identifiers. It is consumed by the `jobservice_SVC` service and by numerous batch-processing components.

## Capabilities

- **User-Mapping management**: Look up, create, and update mappings between a client's partner user ID (PUID) and the internal ecount ID / eMember ID within a given program context.
- **Registration-lock management**: Create and clear null "lock" entries in the job account map (JAM) to prevent duplicate registrations during concurrent processing.
- **Job statistics retrieval**: Return completion metrics (processed, failed, remaining, skipped, percent-complete) for a job by job ID.
- **Processing-agent resolution**: Identify the XML-RPC agent responsible for a given program (product) by looking up a symbol table.
- **Validation versioning**: Retrieve the current validation-template version for a given validation ID (SimpleSolve integration).
- **Bulk PUID lookup**: Return all job account map entries for a set of ecount IDs.
- **Instant-issue card status**: Query the status of an instant-issue card package for a given ecount ID.

## Entities

| Entity | Description |
|---|---|
| `JobAccountMapEntry` | Mapping record linking ProgramId + PartnerUserId to EcountId + EmemberId; carries an `is_encoded` flag |
| `JobAccountMapEntryKey` | Composite key (programId, partnerUserId) |
| `Symbol` | Program-level configuration symbol (e.g., processing agent name) keyed by type + product code |
| `UserMapping` | DTO projection of a `JobAccountMapEntry` used in API responses |
| `JobStatistics` | Snapshot of job progress counters |

## Business Rules

1. A null/empty JAM entry acts as a distributed lock; `clearUserMappingLock` may only delete entries where the mapping is null (prevents accidental deletion of live records).
2. The processing-agent symbol is resolved by extracting the two-digit product code from the first two characters of the program ID.
3. Encoded PUIDs (is_encoded = 1) are re-fed through the `job_account_map_get2` stored procedure to decrypt them before being returned.
4. Return codes from all stored procedures are validated; known codes map to typed `JobManagerException.Type` values (e.g., `JOB_ACCOUNT_UNKNOWN`, `INVALID_PROGRAM_ID`, `LOCKED_ACCOUNT_MAPPING_NOT_FOUND`).
5. The partner-user ID may only be updated via `job_account_map_update2`; direct mutation is not permitted.

## Flows

1. **Registration flow**: Caller invokes `mapUser` → `job_account_map_set2` SP upserts the JAM row → if is_encoded flag returned, caller handles encoding.
2. **Lookup flow**: `findUserMapping` first tries by ecountId, then falls back to PUID lookup; if encoded, re-executes through the get SP.
3. **Lock-clear flow**: On registration failure, `clearUserMappingLock` removes the null-placeholder row to release the lock.
4. **Agent-resolution flow**: `findProgramProcessingAgent` slices the programId, queries the symbol table, and returns the XML-RPC agent hostname/name.

## Compliance Relevance

- Manages PUIDs and ecount IDs, which are internal identifiers potentially linkable to cardholders; constitutes **in-scope CDE-adjacent data** under PCI DSS.
- The `is_encoded` flag indicates that some partner user IDs are stored in an encoded/encrypted form — relevant to PCI DSS Requirement 3 (protect stored cardholder data).
- No direct PAN or SAD is stored in this library, but correlation with cardholder accounts is possible via ecountId.

## Risks

- Library version is **4.0.1**; inherits from a `com.citi.prepaid` parent POM, indicating legacy Citi-era provenance. The Citi branding in group IDs has not been fully migrated to Onbe namespaces.
- JMS transport (ActiveMQ/JNDI) is the inter-process communication mechanism — not a modern REST/gRPC approach.
- No authentication/authorization is enforced within the library itself; callers are trusted.
- The `JobManagerException` error model is tightly coupled to database return codes, creating a brittle contract.
