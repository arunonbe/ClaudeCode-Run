# Enterprise Architect View — RecipientApp

## Source Availability Limitation

The `RecipientApp` repository contains only a `.git` directory with no checked-out source files. All architectural analysis is based on inferred context from the repository name, naming conventions in the Onbe 363-repo codebase, and the positioning of this repository relative to `recipient-screening-api` and the NexPay/Onbe Gen-3 platform.

## Inferred Platform Generation

**Gen-3 (NexPay/Onbe)** — inferred from:
- The `RecipientApp` name suggests it belongs to the "Recipient" domain introduced in the NexPay/Onbe product generation
- Capitalized naming convention (`RecipientApp`) is consistent with other Onbe Gen-3 frontend or mobile applications
- No evidence of Gen-1 (`com.ecount`, `com.citi.prepaid`) or Gen-2 (`Wirecard`, `Northlane`, Spring Boot 1.x) naming patterns in the repository name

## Inferred Integration Patterns

If `RecipientApp` is a recipient-facing application:

1. **REST API consumption**: Calls `recipient-screening-api` or similar services to initiate/check screening status.
2. **OAuth 2.0 / OIDC**: Authentication of recipient users, likely via Azure Active Directory B2C or a custom identity provider in the Onbe platform.
3. **Push notifications**: Mobile application would require Firebase Cloud Messaging (FCM) or Apple Push Notification Service (APNs) for payment status alerts.
4. **Deep linking / universal links**: For payment disbursement workflows initiated from client programs.

If `RecipientApp` is a backend API service:

1. **REST API**: Exposes recipient management endpoints consumed by payout orchestration.
2. **Event-driven**: May publish recipient-registered or recipient-updated events to Azure Service Bus for consumption by downstream services.
3. **ECountCore integration**: Would need to create or look up eCount member records for newly enrolled recipients.

## External Dependencies

Inferred (cannot be confirmed without source):
- **Azure Active Directory B2C** or **Onbe Identity Provider** — for recipient authentication
- **recipient-screening-api** — for OFAC/sanctions screening of newly enrolled recipients
- **ECountCore / eCount platform** — for account registration and status management
- **Azure Key Vault** — secrets management (Gen-3 standard)
- **Azure Container Registry** — Docker image storage (Gen-3 CI standard)

## Position in the Broader Platform

Inferred position in the disbursement workflow:
```
[Client Program] → initiates disbursement
[Payout Orchestrator] → resolves recipient
[RecipientApp] → manages recipient identity/DDA registration
[recipient-screening-api] → OFAC screening
[Card Processor / ACH Rail] → fund delivery
[RecipientApp] → recipient views payment status
```

If this is the upstream system for recipient identity data, it is a **primary data source** for the OFAC screening pipeline and must apply the same data protection standards as `recipient-screening-api`.

## Migration Blockers

Cannot be assessed without source code. If this is a mobile application, migration considerations include:
- App store distribution pipelines (Apple App Store, Google Play)
- Mobile SDK versioning and OS compatibility
- Backward compatibility requirements for recipients using older app versions

If this is a backend service:
- Same Gen-2 infrastructure dependencies as `recipient-screening-api` (SQL Server on `wirecard.sys`) may apply
- ECountCore dependency for account management

## Strategic Status

**Unknown — requires source code access.** Given the repository's presence in the 363-repo corpus alongside active Gen-3 services, it is likely either:
1. An actively maintained production application — in which case it requires immediate full analysis.
2. A recently created repository with content not yet committed — in which case it should be flagged for follow-up as it becomes active.

The absence of source in the working tree is the most significant finding for this repository at the enterprise level.
