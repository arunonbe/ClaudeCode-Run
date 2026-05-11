# Business Analyst — profile_SVC

## Business Purpose
Profile SVC is a **cardholder and program profile data service** in Onbe's Gen-2 (legacy ecount/Core2) platform. It stores and retrieves flexible key-value configuration data ("profile classes") associated with programs (`pid`), members (cardholders), and scopes (products/brands/affiliates). It is the canonical store for per-program and per-cardholder business settings (e.g., payment reversal rules, membership flags, application settings).

The service is accessed exclusively via **XML-RPC** over HTTP(S). It exposes both a Java client library (`profile-client`) and an XML-RPC servlet (`profile-xmlrpc`).

## Capabilities

| Capability | Interface Method | Description |
|---|---|---|
| Retrieve program-level settings | `ClassRetrieve(agent, member, memo, pid, name)` | Fetch a named profile class for a program |
| Get member/global-level settings | `ClassGet(agent, member, memo, topic, key)` | Fetch settings at "global" or "member" (cardholder) scope |
| Write/upsert settings | `ClassPut(agent, owner, memo, topic, key, operation, values)` | Create, update, or create-or-update a profile class (operations: "create", "update", "create-update") |
| Update program settings | `ClassUpdate(agent, member, memo, pid, name, values)` | Patch values in an existing program-level class |
| Create program settings | `ClassCreate(agent, member, memo, pid, name, values)` | Create a new program-level profile class |
| Delete program settings | `ClassDelete(agent, member, memo, pid, name)` | Remove a program-level profile class |
| Select profile classes | `ClassSelect(agent, topic, key)` | Query profile classes by topic and key |
| Drop profile classes | `ClassDrop(agent, owner, memo, topic, key)` | Delete a member/global-scoped profile class |
| Retrieve audit log | `ClassLogInquiry(agent, member, memo, name)` | Retrieve change log for a named profile class |
| Create scope | `ScopeCreate(agent, member, memo, sid, name, description)` | Register a new scope (product/brand/affiliate) |
| Retrieve scopes | `ScopeRetrieve(agent, member, memo, sid)` | List scopes; wildcard `00000000` returns all |
| Update scope | `ScopeUpdate(agent, member, memo, sid, name, description)` | Rename or redescribe a scope |
| Delete scope | `ScopeDelete(agent, member, memo, sid)` | Remove a scope |

## Key Entities

| Entity | Key Fields | Description |
|---|---|---|
| ProfileClass | `pid` (program ID), `name`, `values` (Map) | Named KV configuration block scoped to a program |
| ProfileClassKey | `name`, `qualifiers` | Subject profile class identifier for topic-scoped operations |
| ProfileClassTopic | `name` ("global" or "member"), `qualifiers` (e.g., member UUID) | Scope discriminator for member vs global settings |
| ProfileScopeDetail | `sid`, `name`, `description` | Product/brand/affiliate scope registration |
| Member | UUID string (e.g., `{1846cd84-7f5c-11d8-9c7d-009027d30cbb}`) | Cardholder identifier |
| Agent | String (e.g., `B2CTEST`) | Calling application identifier |

## Business Rules
1. All operations require an `agent` identifier (calling system) and a `member` (requesting user/cardholder UUID).
2. `ClassPut` supports three write modes: `"create"`, `"update"`, `"create-update"` (upsert).
3. Scope operations use an 8-digit `sid`; wildcard `00000000` matches all products in `ScopeRetrieve`.
4. `ClassLogInquiry` provides audit history — all changes are logged.
5. `ClassRetrieve` and `ClassGet` are read-only; `ClassPut`/`ClassCreate`/`ClassUpdate`/`ClassDelete`/`ClassDrop` are mutations and return a control ID (`cid`) for correlation.
6. Errors propagate as `CoreSystemDALError` with a specific RPC error code.
7. The XML-RPC client caches the service location from Director service for 1 hour.

## Key Flows

### Read Profile Class (Member Scope)
```
Caller (Java client or XML-RPC)
  --> ProfileXMLRPCClient.ClassGet(agent, member, memo, topic="member", key)
      --> HTTP POST to ProfileService (via Director location cache)
          RPC interface: ECountCore.Profile.ClassGet
      --> ProfileXmlRPCServlet.doPost()
          --> ProfileProxy.ClassGet()
              --> ProfileImpl.ClassGet()
                  --> ProfileLibrary.class_get(member, memo, topic, key)
                      --> FdrProfileClassExtract DAO
                          --> Database query
                      --> Return Map<String, Object> values
```

### Write Profile Class
```
Caller
  --> ProfileXMLRPCClient.ClassPut(agent, owner, memo, topic, key, "create-update", values)
      --> RPC call --> ProfileProxy --> ProfileImpl.ClassPut()
          --> ProfileLibrary.class_put()
              --> FdrProfileClassConfigure DAO
                  --> Database insert/update
              --> return cid (control/audit ID)
```

## Compliance Relevance

| Standard | Relevance |
|---|---|
| PCI DSS | Profile data may include payment configuration (e.g., `payment_reversal` is an example profile name); access must be controlled |
| PCI DSS Req 10 | `ClassLogInquiry` provides an audit trail of profile changes |
| SOC 1 / SOC 2 | Profile classes govern program-level business rules — change control is critical |
| GLBA | Member-scoped profile data may include preferences or identifiers linked to cardholder PII |

## Business Risks

| Risk | Severity | Notes |
|---|---|---|
| XML-RPC protocol — no modern security controls | High | XML-RPC has no built-in auth, TLS optional; service-level network controls required |
| `agent` parameter is a free-form string — no cryptographic authentication of caller | High | Any system knowing the RPC endpoint and agent name can invoke mutations |
| Tests skip on deploy (`-Dmaven.test.skip`) | Medium | CI pipeline skips tests for production deploys |
| PACT contract testing disabled (`VERIFY_PROVIDER_PACT: false`) | Medium | No consumer-driven contract validation |
| Service is part of Gen-2 legacy stack | High | Long-term migration to Gen-3 required; XML-RPC is not aligned with REST/gRPC platform direction |
