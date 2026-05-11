# Enterprise Architect Report — debit-api_API

## 1. Platform Generation Classification

| Attribute | Value |
|---|---|
| Generation | Gen-2 (ECount Core2 era) — partially modernized |
| Runtime | Spring Boot 3.x on Java 21 (containerized) |
| Protocol | SOAP/WSDL (legacy); no REST/JSON surface |
| Core integration | ECount Core2 XML-RPC (proprietary Onbe internal protocol) |
| Config system | Azure App Configuration + Azure Key Vault (Gen-3 pattern partially adopted) |
| Service discovery | Director XML-RPC (Gen-2 proprietary) |
| Database | SQL Server via JDBC (Gen-2) |

The service is in a **migration-in-progress** state: it has been lifted from a legacy JEE/Tomcat WAR (`debitapi-war` module still present in the repo) into Spring Boot, but the business logic, protocol surface (SOAP), and Core2 integration remain Gen-2.

---

## 2. Domain Context

**Domain**: Payments — Debit Card Transaction Management  
**Sub-domain**: Cardholder Fund Debits  
**Bounded context**: Debit API sits between:
- **Upstream callers**: Onbe order-management services, partner integrations, manual-trigger systems that need to debit prepaid card balances
- **Downstream systems**: ECount Core2 ledger (cbase), Job Service, Order Service

The service does **not** handle:
- Card issuance or provisioning
- ACH or push-to-card disbursements (handled elsewhere)
- Fraud/AML decisioning (expected to be upstream)

---

## 3. Service Role in Platform

```
Order Management / Partner Systems
         │ SOAP/WSDL
         ▼
   [debit-api_API]  ←── Director (service discovery + credentials)
         │
         ├──── ECount Core2 (cbase) ─── Card Ledger / Transfer Engine
         ├──── Job Service ─────────── Negative-balance facility
         ├──── Order Service ────────── Order state
         └──── Audit DB (cbaseapp) ─── Audit trail
```

---

## 4. Upstream / Downstream Dependencies

| Direction | System | Interface | Coupling |
|---|---|---|---|
| Upstream | Onbe Order Management | SOAP/WSDL | Tight (WSDL contract) |
| Upstream | Partner integrations | SOAP/WSDL | Tight (WSDL contract) |
| Downstream | ECount Core2 | XML-RPC (ECoreTransfer, ECoreDevice, ECoreMember) | Tight — synchronous, no fallback |
| Downstream | Director | XML-RPC over HTTPS | Tight — required at startup for credential/service resolution |
| Downstream | cbaseapp SQL Server | JDBC | Tight |
| Downstream | jobsvc SQL Server | JDBC | Medium — only used for negative-balance path |
| Downstream | ordersvc SQL Server | JDBC | Medium |
| Downstream | Azure App Config + KV | HTTPS | Loose (startup configuration only) |
| Downstream | Azure APIM | WSDL publish | Loose (publishing only) |

---

## 5. Architectural Patterns Observed

| Pattern | Implementation | Quality |
|---|---|---|
| Command pattern | `BeginDebitController`, `CommitDebitController`, etc. (debitapi-ws module) | Consistent |
| Strategy pattern | `TransactionStrategy` / velocity rules | Clean |
| Interceptor / AOP chain | `GlobalRequestIDInterceptor` → `AuditMethodInterceptor` wrapping `IDebitWebService` via `ProxyFactoryBean` (DebitApiWsConfig lines 353–362) | Spring AOP correctly used |
| Factory pattern | Service beans created in `DebitApiImplConfig` with `ProxyFactoryBean` wrappers | Correct but verbose |
| ThreadLocal logging | `DirectorXMLRPCClient` uses `ThreadLocal<Logger>` (line 38) to avoid shared-classloader issues | Unusual pattern, justified in comments |
| Thread pool executor | `DebitApiWsConfig.executor()` with `LinkedBlockingQueue` — handles concurrent debit requests | Queue is unbounded (risk) |

---

## 6. Current Status

| Aspect | Status |
|---|---|
| Active deployments | Prod (`B2C` agent), QA (`B2CSTAGE`), Staging (`B2CSTAGE`) |
| Last git tags | `20260423.165104`, `20260423.165138`, `20260426.041106` (from `.git/refs/tags`) |
| Spring Boot version | 3.x (Boot 3 parent) |
| Java version | 21 |
| Known tech debt | WAR module (`debitapi-war`) still present; `allow-circular-references: true` |
| Contract testing | Pact configured but provider verification disabled |

---

## 7. Blockers for Gen-3 Migration

| Blocker | Detail |
|---|---|
| SOAP protocol surface | All consumers rely on WSDL-defined SOAP contracts; migration to REST requires coordinated consumer changes |
| ECount Core2 XML-RPC dependency | All debit operations require Core2; Gen-3 requires Core2 replacement or adapter |
| Director XML-RPC service discovery | Must be replaced with Gen-3 service mesh / Azure Service Bus endpoint config |
| `com.cbase.*` domain objects (ECount Core) | Business logic (`BeginDebitService`, etc.) tightly coupled to Core2 value objects (`TransferDefinition`, `TransactionDefinition`, `AccountDefinitionDDA`) |
| `allow-circular-references: true` | Indicates Spring bean graph has cycles; must be resolved before microservice decomposition |
| Legacy `debitapi-war` module | Dead code presence in repo causes confusion; should be removed |
