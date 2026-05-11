# Data Architect View — qa-test-automation

## Data Models

The repository contains no application-owned data models. It uses domain objects imported from eCount platform client libraries. The test code references the following external domain models:

- `com.ecount.service.order.domain.activity.OrderActivityFacility` — enum defining the originating facility for an order (WEB, ACCOUNTMANAGEMENT_API, etc.)
- `com.ecount.service.order.dto.SweepProfile` — contains `memberId`
- `com.ecount.service.request.domain.FundsValue` — amount and currency
- `com.ecount.service.request.domain.action.type.AddFundsAction` — fund addition action (amount, description, claimable flag, notification indicator)
- `com.ecount.service.request.domain.request.InstantIssueRequest`, `SweepRequest`, `RequestRef` — full order request objects
- `com.ecount.service.httpcryptoservice.bean.KeyDetailsBean` — PGP key metadata (keyId, keyName, errorString)

## Sensitive Data Handling

The `Environments.groovy` configuration file contains the following identifiers that must be treated as sensitive test system data:

- `programId: '04017384'`, `'04011269'`, `'04019765'` — real program identifiers tied to QA accounts
- `memberId: '19469094-D63F-4494-83E4-D9C587984F33'`, `'F5128DE1-9007-4326-8C97-2567E7CD7F23'` — UUIDs referencing real QA member records in the RepositoryService
- `ecountId: '0401611300741331'` — eCount card account identifier (potentially a masked PAN reference)
- `refId: 'TX-04011269-REST-TEST-69'` — transaction reference identifier
- `keyId: '0x7FDB6C83'` — PGP key identifier in the crypto service
- `keyPath: '\\\\q-na-app05\\pgpkeys\\RashmiDhandaronbe.asc'` — UNC path to a PGP public key file, which may encode a named individual

The `ecountId` value `0401611300741331` (16 digits) has the format of a card account number. Although this is a QA account and not a live PAN, it must be governed under Onbe's test data management policy. Storing this in a committed source file is a compliance risk under PCI DSS Req 3.2 if the value corresponds to a real card number that was ever active.

## Encryption Status

No encryption is applied by this test framework to data in transit or at rest. Tests communicate with backend services over XML-RPC, with TLS configured via a JKS truststore:

- `src/test/resources/certs/truststore-qa.jks` — QA environment truststore for TLS validation
- `src/test/resources/cbase/config/truststore.jks` — crypto service truststore

These TLS configurations ensure that XML-RPC communication is encrypted in transit, which is appropriate for connections to eCount services handling sensitive data.

## Database Schemas

The test framework does not directly access any database. All data access is intermediated through the XML-RPC service layer. The test framework treats all service backends as opaque endpoints.

## Data Flows

1. Test runner (Maven Surefire on a Docker container) loads Groovy specs.
2. `setupSpec()` reads configuration from `Environments.groovy` for the `qa` environment.
3. Spring XML context is initialized from classpath XML configuration files (e.g., `ordersvc-config.xml`, `crypto-svc-config.xml`), which wire XML-RPC client proxies.
4. Test methods invoke service methods over XML-RPC to live QA endpoints.
5. Assertions are made against the returned domain objects.
6. No test data is written to a local database; all state changes occur on QA server backends.

## Retention Concerns

The `Environments.groovy` file commits test system identifiers (programIds, memberIds, ecountId) into git history. If any of these identifiers ever corresponded to real cardholder accounts promoted from production data (which is prohibited but has occurred historically in legacy prepaid environments), they would constitute a PCI DSS violation in source control. A full audit of these values against production account records is advisable.

The truststore JKS files committed to the repository (`truststore-qa.jks`, `truststore.jks`) contain CA certificates for QA environment endpoints. These are not secrets but should be reviewed to confirm they do not contain client certificates with private keys.

## PCI DSS Compliance Observations

- The `ecountId` `0401611300741331` should be verified as synthetic or masked against production records.
- The `keyPath` referencing `Rashmi Dhandar onbe.asc` encodes a personal name — this UNC path should be updated to use a role-based path (e.g., `onbe-qa-pgp.asc`) to avoid PII in committed code.
- No real card numbers, CVVs, or PINs are visibly present, which is compliant with PCI DSS Req 3.2/3.3.
