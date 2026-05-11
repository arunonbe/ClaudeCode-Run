# Data Architect Report — petstore-spring-flux-rest-server

## Data Models

### Domain Entity: Pet
File: `petstore-spring-flux-rest-server-impl/src/main/java/com/onbe/petstore/entity/Pet.java`

```java
@Getter @Setter
public class Pet {
    @Id private Long id;
    private String name;
    private String tag;
}
```

Simple three-field entity. No sensitive data fields. No PAN, CVV, SSN, DDA, or PII fields are present in this demo entity.

### API Model: Pet (OpenAPI-generated)
The `Pet` API model is generated from the OpenAPI specification (`petstore/v2/petstore-expanded-openapi.yaml` hosted in the central `openapi-doc` repository). It includes `id`, `name`, and `tag` fields — consistent with the classic Petstore spec.

### API Model: NewPet (OpenAPI-generated)
`NewPet` is the request body for `addPet` operations. Contains `name` and optional `tag` fields.

### Database Schema
File: `petstore-spring-flux-rest-server-boot/src/main/resources/schema.sql`

```sql
create table pet
(
    id   int identity primary key,
    name varchar(255) not null,
    tag  varchar(255)
);
```

Single table, no foreign keys, no encrypted columns, no audit columns (`created_at`, `updated_at`, `created_by`). In a production payments context, the absence of audit columns on transactional tables would be a PCI DSS Req 10 gap — however, this is a demo application and the schema is intentionally minimal.

## Sensitive Data Handling

### No Sensitive Data in Domain Model
The Petstore domain (pets) contains no cardholder data, PII, or payment-sensitive data. This is a deliberate design choice for a reference application — it allows developers to focus on the infrastructure patterns without the complexity of CHD handling.

### Dapr Secrets (Sensitive Configuration Data)
File: `petstore-spring-flux-rest-server-boot/src/main/resources/application.yaml`, lines 42–48

The Dapr secrets list includes two entries:
- `SPRING_R2DBC_USERNAME` — database username retrieved from Dapr secret store
- `MERCHANTENRICHMENT_TRIPLE_APITOKEN` — API token for a merchant enrichment service

The database password is not listed in the Dapr secrets configuration — only the username. The password presumably comes from a different configuration mechanism or is also managed by Dapr under a different key. This is a partial implementation and should be reviewed; a database username without a corresponding password management mechanism may indicate the password is present elsewhere in configuration.

`MERCHANTENRICHMENT_TRIPLE_APITOKEN` discloses the name of an external payment enrichment service. This is a service-specific API token whose name suggests integration with Triple (a merchant enrichment/categorization vendor). The token itself is retrieved from Dapr secret store at runtime, so no actual credential value is exposed. However, the service name being in a reference application's YAML is a minor information disclosure.

### Debug Logging Configuration Risk
File: `application.yaml`, line 50
```yaml
logging:
  level:
    org.springframework: DEBUG
    io.r2dbc.mssql.QUERY: DEBUG
```
The `io.r2dbc.mssql.QUERY: DEBUG` logging level will emit all SQL queries to the log. In a production payment service with CHD, this would risk logging queries that reference account numbers, transaction amounts, or other sensitive data. This debug logging is scoped to the `local` profile only — but teams adopting this pattern must ensure the `local` profile is never active in production.

## Data Flows

```
[Client (HTTP)] --> [Spring WebFlux: PetStoreControllerDelegate]
    --> [PetService] --> [PetRepository (R2DBC)] --> [SQL Server: pet table]
    --> [PetService] --> [DatabaseClient (raw SQL)] --> [SQL Server: pet table]

[Startup: DaprSecretsConfiguration]
    --> [Dapr Sidecar] --> [Secret Store (local: local-secret-store.yaml | prod: Azure Key Vault)]
        --> [Spring Environment: SPRING_R2DBC_USERNAME, MERCHANTENRICHMENT_TRIPLE_APITOKEN]

[Azure App Configuration] <-- [PetStoreConfig.init() scheduler]
    --> [AppConfigurationRefresh.refreshConfigurations()]
    --> [FeatureManager] --> [PetStoreControllerDelegate.deletePet()]
```

## Encryption Status

- **Data at rest:** SQL Server (local dev: Docker container, prod: Azure SQL) — TDE not configured in schema.sql, but Azure SQL enables TDE by default in production.
- **R2DBC URL (local):** `r2dbc:mssql://localhost:1433/petstore` — no `encrypt=true` specified. This is acceptable for local Docker development but must be `r2dbc:mssql://[host]:1433/petstore?encrypt=true&trustServerCertificate=false` in production.
- **Dapr secrets:** Stored in Azure Key Vault (production), accessed via Dapr gRPC (localhost). TLS enforced by Dapr for Key Vault communication.
- **HTTP transport:** Managed by Azure APIM (TLS termination at the gateway).

## PCI DSS Compliance Assessment

As a demo application, direct PCI DSS compliance is not applicable. As a template:
- R2DBC connection URL in production must include `encrypt=true` — gap in current template.
- SQL debug logging (`io.r2dbc.mssql.QUERY: DEBUG`) must be excluded from all non-local profiles — currently scoped correctly to `local` only, but pattern should include explicit comment warning.
- No audit columns on `pet` table — production schemas must include `created_at`, `updated_at`, `created_by`, `modified_by` for PCI DSS Req 10.2 compliance.
- `MERCHANTENRICHMENT_TRIPLE_APITOKEN` in YAML reveals an integration dependency name — consider replacing with a generic placeholder in the reference app.
