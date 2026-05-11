# Solution Architect View — manage-payment-rest-api

## Technical Architecture

`manage-payment-rest-api` is a **single-module Spring Boot 3.4.5 application** packaged as an executable JAR. It is a REST API adapter that wraps legacy payment service libraries behind a modern OpenAPI interface.

### Package Structure (inferred from pom.xml and config)

```
com.onbe.external.api/manage-payment-rest-api/
├── controller/
│   ├── AccountManagementRestController    → POST /v1/accounts, GET /v1/accounts/card, etc.
│   └── DebitRestController               → POST/PUT/DELETE /v1/accounts/debit/*
├── handler/
│   ├── AccountManagementRestHandlerImpl  → orchestrates accountmanagementapi-impl
│   └── DebitServiceRestHandlerImpl       → orchestrates debitapi-impl
├── model/domain/
│   ├── Registration, Card, Load, Link    → request objects
│   ├── AchWithdraw, CheckWithdraw        → withdrawal types
│   └── CreateAccountRequest, etc.        → composite request/response types
├── validation/
│   ├── StringParameterConstraintValidator, EmailParameterConstraintValidator, etc.
│   └── InternationalContext              → Redis-backed country validation rules
├── security/
│   ├── AuthenticationFilter              → reads External-Auth-Response JWT header
│   └── JwtSecurityValidator              → domain-method-program RBAC
├── config/
│   └── DatabaseConfiguration            → 4 HikariCP connection pools
└── resources/
    ├── application.yml + profile YAMLs
    ├── accountmanagementapi.yaml         → imported Spring config for account mgmt
    ├── debitapi.yaml                     → imported Spring config for debit API
    └── log4j2-spring.xml                 → log4j2 configuration
```

## API Surface

| Method | Path | Operation | PCI Scope |
|---|---|---|---|
| POST | `/v1/accounts` | Create account (+optional card, load) | In scope |
| POST | `/v1/accounts/add-funds` | Load funds | In scope |
| PUT | `/v1/accounts/registration` | Update cardholder profile | In scope (PII) |
| POST | `/v1/accounts/withdraw` | ACH/check withdrawal | In scope |
| GET | `/v1/accounts/card` | Card number + expiry | **CDE — SAD** |
| GET | `/v1/accounts/cvv` | CVV | **CDE — SAD** |
| GET | `/v1/accounts/transaction-status` | Transaction status | In scope |
| POST | `/v1/accounts/bulk-order` | InstantPay bulk card order | In scope |
| POST | `/v1/accounts/link-card` | Link physical card | In scope |
| GET | `/v1/accounts/balance` | Program balance | In scope |
| POST | `/v1/accounts/debit/begin` | Begin two-phase debit | In scope |
| PUT | `/v1/accounts/debit/commit` | Commit debit | In scope |
| DELETE | `/v1/accounts/debit/cancel` | Cancel debit | In scope |

OpenAPI spec is auto-generated at build time and published to Azure APIM (external gateway, suffix `managepayments`).

## Security Posture

### Authentication / Authorization
- JWT validation via `AuthenticationFilter` reading `External-Auth-Response` header — this means JWT validation is performed upstream (APIM or auth gateway) and only the validated JWT payload is forwarded.
- Feature-level RBAC: `{METHOD=createAccount, API=AccountManagement, PROGRAM=04016113, FEATURE=Return-Card-Number}` — fine-grained control per program per operation per feature.
- **Gap**: If a request bypasses APIM and reaches the ACA Container App directly (using the ACA internal FQDN), there may be no JWT validation layer. APIM must be the exclusive ingress path.

### Data Protection in Transit
- Redis: TLS port 6380 (`ssl.enabled: true`) — correct.
- SQL Server: TLS with `trustServerCertificate=true` — certificate validation disabled.
- Director/Banker: `https://` endpoints — TLS enforced by the upstream service.
- Logbook field masking: `ssn`, `cardNumber`, `cvv` — correct scope, but field-name-exact matching only.

### Secrets Management
- Credentials injected via environment variables (Container Apps environment variables from Key Vault via App Configuration).
- **Critical gap**: `dapr-components/dapr-secrets.json` with Visa security service key and shared secret committed to repository. Must be rotated immediately and file removed from git history.

## Technical Debt

| Item | Severity | Description |
|---|---|---|
| Visa credentials in `dapr-secrets.json` | Critical | Committed to repo; must be rotated and deleted from git history |
| `trustServerCertificate=true` | High | TLS cert validation disabled for all 4 database connections |
| Container runs as root | High | No USER instruction in Dockerfile |
| `accountmanagementapi-impl` / `debitapi-impl` | High | Depends on legacy libraries that use Apache Axis SOAP and Spring Remoting to call legacy backends. Both protocols are EOL. |
| `jakarta-spring-remoting` / `jakarta-axis-*` dependencies | High | These are transformed legacy libraries, not modern replacements — see `jakarta-migrator` analysis |
| `show-details: always` on health endpoint | Medium | Exposes DB connectivity status to anonymous callers |
| Logbook at TRACE in default profile | Medium | Produces excessive HTTP body logs; sensitive data adjacent |
| No OTel/distributed tracing | Medium | No trace correlation across services for a payment API |
| SpringDoc Swagger UI enabled in all profiles | Medium | `springdoc.paths-to-match: /v1/**` — API explorer accessible; should be disabled in production |
| `xstream:1.4.21` | Medium | XStream XML deserialization risk; verify no user-controlled XML is deserialized through XStream |
| `aether.connector.https.securityMode=insecure` in some CI paths | Low | See jakarta-migrator analysis for this shared CI pattern |

## Gen-3 Migration Path

This service is architected as a **long-lived bridge**, but its dependency on `accountmanagementapi-impl` and `debitapi-impl` ties its evolution to the legacy platform. The migration path requires:

1. **Phase 1** (Immediate): Rotate and remove committed credentials; fix `trustServerCertificate`; add non-root user in Dockerfile.
2. **Phase 2** (Near-term): Replace `accountmanagementapi-impl` calls for card issuance with `nexpay-cardprocessor-svc` client calls. This requires:
   - Gen-3 card issuance API to support the same program/product routing.
   - Data migration or dual-write for cardholder records from `cbaseapp` to NexPay PostgreSQL.
3. **Phase 3** (Medium-term): Replace `debitapi-impl` / Banker SOAP with Gen-3 debit capability.
4. **Phase 4** (Long-term): Once all operations route to Gen-3 services, sunset `accountmanagementapi-impl`, `debitapi-impl`, and the `jakarta-axis-*` / `jakarta-spring-remoting` dependencies.

## Code-Level Risks

1. **`ExternalAuthResponse` header trust**: The service trusts the `External-Auth-Response` header as a pre-validated JWT. If network policies do not restrict direct ACA ingress to APIM only, this header can be forged.
2. **`partnerUserId` validation**: The `partnerUserId` field (1–40 alphanumeric) is a client-controlled identifier. Its use in SQL stored procedure calls must be validated against SQL injection (stored procedures use parameterised queries via JDBC `?` placeholders — this should be confirmed).
3. **Addenda key-value pairs**: `AddendaKeyValue` allows arbitrary key-value pairs in payment requests. These pass through to legacy services without type constraints, creating an injection risk if the legacy service interpolates addenda values into SQL or XML without sanitisation.
4. **`cbaseapp` memberUid in prod config** (`memberId: 5FCFFE5C-D07B-490C-82DD-00003311D26D`): The production `application-prod.yml` hardcodes an internal service member GUID. This is not a secret, but it should be managed as configuration, not code.
