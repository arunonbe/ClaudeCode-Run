# nexpay-config-svc — Business Analyst View

## 1. Service Purpose and Business Context

`nexpay-config-svc` is the **centralised configuration microservice** for the NexPay Gen-3 platform. It is the system of record for all payment program configuration: which countries are supported, which payment modalities (ACH, prepaid card, push-to-card, virtual card) are available per program, what registration settings apply (self-registration, OTP, address validation), and promotional campaign definitions.

In Onbe's payments business, a "program" corresponds to a client's disbursement product (e.g., an insurance company's claim payment card program, or an auto-finance company's refund disbursement). The config service defines the rules and capabilities of each program. Downstream services (order orchestrator, card processor, recipient profile) query the config service to determine how to process a given disbursement event.

The service name `nexpay-config-svc` and its database schema confirms it is the **operational config authority** for NexPay — not a Spring Cloud Config server (there is no `spring-cloud-config-server` dependency). It is a domain service that manages configuration *data* via a REST API backed by a PostgreSQL database.

## 2. Business Domain Model

The Flyway migration scripts reveal the core domain model:

| Entity | Business Purpose | Key Fields |
|---|---|---|
| `countries` | ISO 3166-1 country reference data | `country_code`, `alpha_2_code`, `region`, `is_active` |
| `currencies` | ISO 4217 currency reference data | `currency_code`, `numeric_code`, `minor_unit`, `is_fund` |
| `programs` | Client payment programs | `program_id`, `program_name`, `default_currency_code`, `is_active` |
| `promotions` | Promotional campaigns within programs | `promotion_id`, `program_id`, `is_default`, `start_date`, `end_date` |
| `program_modality` | Payment modality per program | (V4 migration) |
| `program_registration` | Registration settings per program | (V4 migration) |
| `address_detail` | Address format rules | (V7 migration) |
| `country_address_config` | Country-level address validation config | (V8 migration) |
| `program_country_config` | Which countries are enabled per program | (V9 migration) |

The progression of Flyway migrations (V1 through V10) shows an actively evolving data model, with V10 adding audit tracking fields (`source`, `reason`) to the revision info table.

## 3. Integration Points

The config service is consumed by:

- **`nexpay-clientadminweb-bff`**: Program modality details, registration settings, country address config (for admin portal display and editing).
- **`nexpay-order-orchestrator`** (inferred): Queries program config to determine routing rules during order processing.
- **`nexpay-ordervalidator-svc`** (inferred): Validates orders against program country and modality constraints.
- **`nexpay-config-test-svc`**: Regression testing of the config service API (per IaC `qa.tfvars` mapping).

## 4. Business Rules Observed

### 4.1 Audit Trail (Hibernate Envers)

The `Program` entity (`Program.java` line 32) is annotated `@Audited`, and V2 migration adds Envers audit tables. This means every change to program configuration creates an immutable audit record. V10 adds `source` and `reason` fields to the revision info — allowing the system to record *which* application made the change and *why*. This directly supports PCI DSS Requirement 10.2.7 (activities by individuals with root or administrative privileges) and Reg E change management obligations.

### 4.2 Idempotency

The `application.yaml` comment block (lines 57–63) references a platform-level `IdempotencyProperties` library (Redis-based distributed lock, 24h TTL). This is critical for config API operations: concurrent requests to create or update a program should be deduplicated. The `CountriesIdempotencyIntegrationTest` integration test (`nexpay-config-boot/src/test`) confirms idempotency is tested at the API level.

### 4.3 Promotion Default Constraint

`V1__Initial_schema.sql` line 106–108: a partial unique index ensures only one default promotion per program (`WHERE is_default = TRUE`). This is a business rule enforced at the database level, not just application code, making it more robust.

### 4.4 Secure Transport

PostgreSQL is configured with `require_secure_transport = true` (`qa.tfvars` line 278) and VNet integration (no public access). All database connections are encrypted in transit.

## 5. API Surface (Integration Tests as Specification)

The integration test suite effectively serves as the living specification for the API:

| Integration Test | API Endpoint Implied |
|---|---|
| `CountriesApiIntegrationTest` | GET/POST/PUT/DELETE `/countries` |
| `CurrenciesApiIntegrationTest` | GET `/currencies` |
| `ProgramsApiIntegrationTest` | CRUD `/programs` |
| `ProgramRevisions ApiIntegrationTest` | GET `/programs/{id}/revisions` |
| `PromotionsApiIntegrationTest` | CRUD `/programs/{id}/promotions` |
| `ProgramModalityDetailsApiIntegrationTest` | GET `/programs/{id}/modality-detail` |
| `ProgramRegistrationSettingsApiIntegrationTest` | GET `/programs/{id}/registration-settings` |
| `ProgramCountryConfigApiIntegrationTest` | GET/POST `/programs/{id}/countries` |
| `AddressDetailsApiIntegrationTest` | GET `/address-details` |
| `CountryAddressConfigApiIntegrationTest` | GET `/countries/{id}/address-config` |

## 6. Business Risks

1. **No program-level access control**: The config service is an internal-network service (not external-facing per `qa.tfvars` `external_enabled: false`). Access is network-gated, not identity-gated. Any service inside the ACA environment can call any config endpoint without programId-scoped authorisation. If a malicious or misconfigured microservice can reach the config-svc, it can read or modify all program configurations.

2. **Seed test data in production migrations**: `V5__Seed_test_data.sql` is present in the production migration path (`db/migration/`). Test data seeding should not be present in a production schema migration. If this migration runs in production it could introduce synthetic program records that are not real client programs, creating regulatory traceability issues.

3. **Active deletion of programs**: The `is_active` flag pattern (`programs.is_active`) suggests soft-deletes are used. However, if hard-delete endpoints are also exposed, deletion of a program while active orders are in flight could break downstream processing. The API contract should enforce that programs with active promotions or orders cannot be hard-deleted.
