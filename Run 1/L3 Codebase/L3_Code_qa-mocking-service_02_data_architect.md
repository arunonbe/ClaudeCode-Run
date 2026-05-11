# Data Architect View — qa-mocking-service

## Data Models

The repository has no application-defined data model. All data is expressed as static JSON WireMock mapping files. These files define:
- **Request matchers**: URL, HTTP method, and body JSON path expressions used to match incoming test requests
- **Response bodies**: JSON payloads that simulate Fiserv API responses

The mapping directory is structured as `mappings/fiserv/{operation-name}/{operation-name}-{status}.json`. There are approximately 36 distinct Fiserv operations covered, each with a success and an error stub (72+ total mapping files).

## Sensitive Data Fields Present in Stub Responses

The cardholder balance status stub (`mappings/fiserv/cardholder-balance-status/cardholder-balance-status-200.json`) is the most data-sensitive mapping in the repository. It defines a full Fiserv cardholder object schema containing the following sensitive field names, all currently set to the literal string `"string"` as placeholder values:

- `primaryCustomerSocialSecurityNumber` — SSN equivalent (PII, GLBA-protected)
- `secondaryCustomerSocialSecurityNumber` — SSN equivalent
- `primaryCustomerBirthDate` — date of birth (PII)
- `secondaryCardholderBirthDate` — date of birth
- `primaryCustomerHomePhoneNumber` — contact PII
- `primaryPinNumber`, `secondaryPinNumber` — PIN fields (SAD under PCI DSS Req 3.2)
- `checkingAccount`, `savingsAccountNumber`, `demandDepositAccountName`, `transitRoutingNumber` — DDA-related fields
- `cardholderAccountNumber` — potentially a PAN field

Other mappings (customer-inquiry, customer-update) include address fields: `principalAddress1`, `principalAddress2`, `cityPrincipalCardholder`, `stateOrCountryPrincipalCustomer`, `zipCode`. These are PII but currently contain only placeholder strings.

## Encryption Status

There is no encryption, tokenization, or masking applied within the service. All mock response content is stored as plain-text JSON on the filesystem and served unencrypted over HTTP (port 8082). This is acceptable for an isolated test environment but must not be connected to external networks or used with real data values. No TLS is configured in the docker-compose.yml.

## Database Schemas

There is no database. The service is stateless; WireMock uses only the JSON mapping files on disk.

## Data Flows

1. A test client (QA test automation suite or developer) sends an HTTP request to `localhost:8082`.
2. WireMock evaluates the request against the `mappings/` directory using URL and JSON body path matchers.
3. If a match is found, the corresponding JSON response body is returned.
4. No data is persisted, forwarded, or logged beyond WireMock's verbose console output.

The mapping directory is volume-mounted into the container (`./mappings:/home/wiremock/mappings`), meaning all stub content resides on the Docker host filesystem.

## Retention Concerns

Because this is a file-based static system with no database, there are no retention obligations in the traditional sense. However, git history permanently records every committed stub file. If real sensitive data were ever committed into a mapping file, it would persist in git history even after file deletion. This creates a latent compliance risk that must be mitigated through pre-commit scanning policies.

## PCI DSS Compliance Observations

- Current stubs use only placeholder values — compliant with PCI DSS Req 3.3 (do not use real PANs/SADs in non-production environments).
- The presence of `primaryPinNumber` and `secondaryPinNumber` fields in the balance-status stub schema is a schema fidelity risk. Even as placeholders, these field names should be reviewed to ensure they are never populated with real PIN values.
- No scanning controls (e.g., regex-based pre-commit hooks for PAN patterns) are evident in the repository.
- The WireMock `--verbose` flag causes full request and response bodies to be written to container stdout/logs, which could expose sensitive data if real values were ever used. Log forwarding must be reviewed before any environment upgrade.
