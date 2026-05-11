# Data Architect — profile_SVC

## Data Stores

| Store | Type | Access Pattern | Module |
|---|---|---|---|
| FDR (First Data Resources) / Core2 DB | Relational RDBMS | JDBC via `NamedDataSourcesList` / `IDataSourceCreator` | `profile-impl` |
| Core System DB | Relational RDBMS | JDBC via `CoreProfileMember*` DAOs | `profile-impl` |

The service abstracts all database access behind `IProfileDao` and `ProfileDataLibrary`/`ProfileLibrary` — the specific RDBMS vendor is not visible in the source code but is consistent with Onbe's legacy SQL Server / Oracle infrastructure.

## Schema / Tables

The schema is not defined in this repository (DDL lives in a database schema repository or is deployed separately). The DAO naming convention reveals the following inferred table groups:

| DAO Class | Inferred Operation | Target |
|---|---|---|
| `FdrProfileClassConfigure` | INSERT / UPDATE profile class | FDR profile class table |
| `FdrProfileClassExtract` | SELECT profile class | FDR profile class table |
| `FdrProfileClassLogInquiry` | SELECT change log | FDR profile audit/log table |
| `FdrProfileProgramBegin` | Transaction begin | FDR program context |
| `FdrProfileProgramCommit` | Transaction commit | FDR program context |
| `FdrProfileProgramSchemaInquiry` | Schema metadata read | FDR |
| `FdrProfileScopeConfigure` | INSERT / UPDATE scope | FDR scope table |
| `FdrProfileScopeExtract` | SELECT scope | FDR scope table |
| `CoreProfileMemberBegin` | Transaction begin | Core system member context |
| `CoreProfileMemberCommit` | Transaction commit | Core system member context |
| `CoreProfileMemberSchemaInquiry` | Schema metadata read | Core system |

## Sensitive Data

| Data Class | Location | Classification |
|---|---|---|
| Member UUID | Passed as `Member` parameter on all operations; stored in profile class qualifiers | PII (cardholder identifier) |
| Program ID (`pid`) | All program-level operations | Business reference — not directly PII but links to CHD-bearing programs |
| Profile class values (`Map<String, Object>`) | Stored in FDR DB | Classification depends on profile name; `payment_reversal` and `app_user_membership` examples suggest payment and account configuration data may be present |
| Scope details (sid, name, description) | FDR scope tables | Product/brand identifiers — low sensitivity |
| Audit log entries | FDR log table | Change history; may contain member IDs and value snapshots |
| Agent identifier | All operations | Calling system name — operational metadata |

## Encryption

| Layer | Status |
|---|---|
| Transport (XML-RPC) | Depends on infrastructure TLS configuration; not enforced at application level |
| Database at-rest | Depends on RDBMS-level encryption (consumer / DBA responsibility) |
| Profile class values | No application-level encryption — values stored as raw Map entries |
| Member UUIDs | Not encrypted at application level |

## Data Flow

```
Caller (Java client or remote XML-RPC client)
  --> ProfileXMLRPCClient (XML-RPC over HTTP)
      --> Director service (service location resolution, cached 1 hour)
          --> ProfileXmlRPCServlet (profile-xmlrpc module)
              --> ProfileProxy
                  --> ProfileImpl
                      --> ProfileLibrary (agent-scoped singleton)
                          --> ProfileDataLibrary
                              --> FDR DAO (FdrProfileClass*/FdrProfileScope*)
                                  --> FDR RDBMS
                              --> Core DAO (CoreProfileMember*)
                                  --> Core2 RDBMS
```

## Data Quality / Retention

| Concern | Detail |
|---|---|
| Audit log | `ClassLogInquiry` indicates change log exists at DB level; retention policy not defined in this repo |
| Profile class values as `Map<String, Object>` | Schemaless — no validation of values at the service layer; data quality entirely depends on callers |
| Director service cache | Service location cached for 1 hour in `SimpleProfileServiceLocationResolvingCache` — stale cache may route to wrong instance post-failover |
| No schema versioning | Profile class schema managed via `ClassCreate`/`ClassDelete` operations at runtime — no migration tooling visible |

## Compliance Gaps

| Gap | Standard | Impact |
|---|---|---|
| No transport-level encryption enforced at application layer | PCI DSS Req 4.2 | XML-RPC over plain HTTP is possible if infrastructure TLS is misconfigured |
| Member UUIDs and profile values stored without application-level encryption | PCI DSS Req 3 | If profile values contain payment data, encryption at application level is required |
| Audit log (`ClassLogInquiry`) retention policy not defined | PCI DSS Req 10.7 | Log retention must meet compliance minimums |
| `agent` parameter is unauthenticated string — callers are not verified | PCI DSS Req 8 | No cryptographic caller authentication |
| Tests skipped in deploy pipeline | PCI DSS Req 6.2 | Security testing bypassed in production builds |
