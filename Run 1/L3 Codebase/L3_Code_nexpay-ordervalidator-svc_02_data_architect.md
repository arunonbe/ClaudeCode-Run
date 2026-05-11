# Data Architect View — nexpay-ordervalidator-svc

## Data Architecture Summary

The nexpay-ordervalidator-svc is primarily a **stateless** validation service. It does not maintain its own persistent store for validation decisions. It accepts a validation request, evaluates rules synchronously, and returns a result. This is architecturally appropriate for a validation gate — it ensures that validation results are always computed from the current state of rules, not from cached prior decisions.

However, the service does connect to an R2DBC (reactive relational) data source for the integration/dev-test profiles (referenced in `application.yaml` lines 167–172), suggesting that future iterations may persist validation history or maintain account-level state for velocity controls.

## Inbound Data Model

The validation request model is defined by the OpenAPI specification in `nexpay-ordervalidator-api`. The key request structure is:

```
ValidationRequest {
    transactionId:   String (required)
    accountId:       String
    validationType:  Enum[FUNDS, NON_MONETARY]
    requestedAmount: String  ← string representation of decimal
    programId:       String
    timestamp:       OffsetDateTime
}
```

**Data quality concern**: `requestedAmount` is typed as `String` in the model, requiring explicit parsing to `double` within `FundsValidationService.validateFunds()` (line 81). This means the service must handle formatting edge cases (locale-specific decimals, currency symbols, etc.) and could be subject to numeric parsing attacks if not properly validated upstream.

## Rule State

The fund limit rule is implemented as a compile-time constant in `FundsValidationService.java`:

```java
private static final double FUND_LIMIT = 1000.0;
```

This constant represents the maximum `requestedAmount` value that will pass funds validation. There is no database, configuration store, or program-specific lookup. The rule is global and non-configurable without a code change.

For a production-grade payment validator, rule state should be stored in:
1. **Azure App Configuration** (for global thresholds, modifiable at runtime)
2. **Program configuration service** (`nexpay-config-svc`) (for per-program limits)
3. **Risk engine / fraud platform** (for dynamic, recipient-level velocity limits)

## Address Verification Data Flow

The `application.yaml` integration profile includes configuration for the address verification service:

```yaml
address:
  verification:
    service-url: https://apim-az1-cluster-qa-ss.azure-api.net/omaddressverificationsvc
    oauth2:
      auth-url: https://login.microsoftonline.com/2d652670-5422-4688-a20e-c2d32cc46751/oauth2/v2.0/token
      client-id: 8106a982-8d61-423e-a32f-08ff30928646
      secret: [REDACTED — credential in source file]
```

The `application.yaml` (lines 126–179 of the integration/dev-test section) contains two significant data exposures:

1. **Azure App Configuration connection string with credentials** (lines 126–127): A full connection string including `Id` and `Secret` is committed to source code under the `dev-test` profile. While labelled as a dev/test instance, this represents a violation of PCI DSS Requirement 8.2.1 (use of individual user IDs and secure authentication) and Requirement 12.3.3 (review of cryptographic key storage).

2. **OAuth2 client secret** (line 179): The `secret: 0pf8Q~...` field is a live OAuth2 client secret committed to source code under the `integration` profile. Even if this secret is for a non-production environment, committing credentials to version control is a control failure under PCI DSS Requirement 8 and the NIST CSF Protect function.

**Immediate action required**: Rotate the exposed credentials, remove them from source code, and store them in Azure Key Vault referenced via App Configuration.

## Outbound Data Model

```
ValidationCompleted {
    transactionId:      String
    validationType:     Enum[FUNDS, NON_MONETARY]
    validationResult:   Enum[PASSED, FAILED, PENDING]
    errorMessage:       String
    processingTime:     Long (milliseconds)
    validationDetails:  ValidationDetails {
        accountStatus:       String  ← hardcoded "ACTIVE" in non-monetary path
        cardholderVerified:  Boolean ← hardcoded true
        riskScore:           String  ← hardcoded "LOW"
        availableBalance:    String  ← hardcoded "1000.00"
    }
}
```

The hardcoded `validationDetails` values are the most significant data architecture concern for non-monetary validation. Downstream consumers of this response who rely on `riskScore: LOW` or `cardholderVerified: true` are receiving fabricated data, not actual risk or cardholder verification status. If downstream services use these fields in routing or reporting logic, this creates a silent incorrect data dependency.

## R2DBC Configuration (Integration Profile)

```yaml
nexpay:
  r2dbc:
    username: sa
    url: r2dbc:mssql://sqlserver:1433/nexpay
    password: [REDACTED — rotate immediately]
    validation-query: "SELECT 222"
```

This R2DBC configuration is for a Microsoft SQL Server database used in integration tests. The credentials (`sa` / `123`) are test-only defaults. The use of SQL Server here while QA/Prod uses PostgreSQL is a concern for test-to-production parity — schema differences between MSSQL and PostgreSQL can mask bugs that only appear in the production environment.

## Data Lineage

```
Client Request
    │ ValidationRequest
    ▼
ValidationApiDelegateImpl
    │
    ├─→ NonMonetaryValidationService → CardCreationRequest → [evaluate rules in-memory]
    │                                          │
    │                                          └─→ ValidationCompleted (hardcoded details)
    │
    └─→ FundsValidationService → [evaluate amount vs FUND_LIMIT]
                                         │
                                         └─→ ValidationCompleted
```

No data is persisted in the validation path. No external data store is consulted. The service is a pure function of its input and compiled rules.

## Recommendations

1. **Externalise `FUND_LIMIT`** to Azure App Configuration with per-program override support.
2. **Remove and rotate credentials** committed to source under `dev-test` and `integration` profiles.
3. **Implement real account/cardholder status lookups** for `validationDetails` rather than hardcoding.
4. **Add velocity state** (Redis or database-backed counters) for per-recipient, per-day transaction volume control.
5. **Align integration test database** from MSSQL to PostgreSQL to match production behaviour.
